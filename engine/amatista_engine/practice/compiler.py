"""Compilador de prácticas (sección 21 de la especificación del Motor de Desarrollo).

Revisa lo que el lector no puede saber solo: que los validadores existan en
este motor, que los parámetros obligatorios estén y tengan sentido, que los
roles citados estén declarados, que las dependencias apunten a objetivos
reales y sin ciclos, y que las herramientas estén en el catálogo.

    resultado = compile_practice(datos)
    if resultado.ok: guardar(resultado.practice)
    else: mostrar(resultado.errors)

Los avisos (warnings) no impiden compilar: por ejemplo, un objetivo sin
título o sin pistas.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..errors import InvalidPracticeError
from ..models import PracticeDefinition
from ..registry import ValidatorRegistry
from ..tools.registry import ToolRegistry
from ..validators.base import SELECTORES
from .loader import parse_practice
from .schema import PILDORA_IDEAL, SCHEMA_V2

TIPOS_OBJETO = ("MESH", "CURVE", "SURFACE", "META", "FONT", "EMPTY", "CAMERA", "LIGHT", "ARMATURE", "LATTICE", "GPENCIL")


@dataclass
class CompileResult:
    practice: Optional[PracticeDefinition]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.practice is not None and not self.errors

    def summary(self) -> Dict[str, Any]:
        p = self.practice
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "practice": p.id if p else None,
            "targets": len(p.targets) if p else 0,
            "validators": len({t.validator for t in p.targets}) if p else 0,
            "skills": len(p.skills) if p else 0,
        }


TEXTOS = ("text", "role", "axis", "primitive", "object_type", "light_type", "modifier", "collection")


def _tipo_incorrecto(tipo: str, valor: Any) -> str:
    """Qué debería ser un parámetro según su tipo registrado ("" = está bien)."""
    if tipo == "int":
        ok = isinstance(valor, int) and not isinstance(valor, bool) or (
            isinstance(valor, float) and math.isfinite(valor) and valor.is_integer())
        return "" if ok else "un número entero"
    if tipo == "float":
        ok = isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)
        return "" if ok else "un número"
    if tipo == "bool":
        return "" if isinstance(valor, bool) else "true o false"
    if tipo in TEXTOS:
        return "" if isinstance(valor, str) else "un texto"
    return ""


def _revisar_tipos(target, spec, errores) -> bool:
    """Los parámetros tienen el tipo que leen los validadores (así nada termina en «Error interno»)."""
    donde = f"Objetivo «{target.id}»"
    antes = len(errores)
    tipos = {nombre: "text" for nombre in SELECTORES} if spec.selects else {}
    tipos.update({p.name: p.kind for p in spec.params})
    for nombre, valor in target.params.items():
        problema = _tipo_incorrecto(tipos.get(nombre, ""), valor)
        if problema:
            errores.append(f"{donde}: «{nombre}» debe ser {problema} (es {json.dumps(valor, ensure_ascii=False)}).")
    for nombre in ("equals", "min", "max"):
        valor = target.params.get(nombre)
        if tipos.get(nombre) == "int" and not _tipo_incorrecto("int", valor) and valor < 0:
            errores.append(f"{donde}: «{nombre}» no puede ser negativo.")
    for param in spec.params:
        if param.required and param.kind in TEXTOS and target.params.get(param.name) == "":
            errores.append(f"{donde}: «{param.name}» ({param.label}) no puede estar vacío.")
    propiedad = target.params.get("property")
    if spec.id.startswith("animation.") and isinstance(propiedad, str):
        from ..validators.animation import ALIAS

        if propiedad.lower() not in ALIAS:
            errores.append(f"{donde}: «property» debe ser location, rotation_euler o scale (es «{propiedad}»).")
    tipo_luz = target.params.get("light_type")
    if isinstance(tipo_luz, str) and tipo_luz and tipo_luz.upper() not in ("POINT", "SUN", "SPOT", "AREA"):
        errores.append(f"{donde}: «light_type» debe ser POINT, SUN, SPOT o AREA (es «{tipo_luz}»).")
    if spec.id == "material.matches":
        from ..validators.materials import CONDICIONES

        if not any(c in target.params for c in CONDICIONES):
            errores.append(f"{donde}: material.matches necesita al menos una condición ({', '.join(CONDICIONES)}).")
    if spec.selects and spec.id in ("object.exists",) and not any(target.params.get(k) for k in SELECTORES):
        errores.append(f"{donde}: {target.validator} necesita a qué objetos aplicarse (role, name, name_prefix o type).")
    return len(errores) == antes


def _revisar_parametros(target, spec, roles_declarados, errores, avisos, registry=None):
    donde = f"Objetivo «{target.id}»"
    if not _revisar_tipos(target, spec, errores):
        return
    for param in spec.params:
        if param.required and param.name not in target.params:
            errores.append(f"{donde}: {target.validator} necesita el parámetro «{param.name}» ({param.label}).")
    conocidos = {p.name for p in spec.params} | ({*SELECTORES, "reference", "inside"} if spec.selects else set())
    conocidos |= {"tolerance", "reference", "reference_role", "inside", "exact"}  # exact: motor 4 (ruta/medidas.py)
    if spec.id == "logic.any":
        _revisar_opciones(target, errores, avisos, registry)
    if spec.id == "spatial.below" and not (target.params.get("reference_role") or target.params.get("reference")):
        errores.append(f"{donde}: spatial.below necesita «reference_role» o «reference» (el objeto de arriba).")
    for nombre in target.params:
        if nombre not in conocidos:
            avisos.append(f"{donde}: {target.validator} no usa el parámetro «{nombre}» (se ignora).")
    for nombre in ("role", "reference_role"):
        rol = target.params.get(nombre)
        if rol and roles_declarados and rol not in roles_declarados:
            errores.append(
                f"{donde}: hace referencia al rol «{rol}», pero ese rol no existe en la práctica "
                f"(roles: {', '.join(sorted(roles_declarados))})."
            )
    eje = target.params.get("axis")
    validos = ("x", "y", "z", "horizontal") if spec.id == "shape.thinnest_axis" else ("x", "y", "z")
    if eje is not None and str(eje).lower() not in validos:
        errores.append(f"{donde}: el eje debe ser x, y o z (es «{eje}»).")
    tipo = target.params.get("type")
    if tipo is not None and str(tipo).upper() not in TIPOS_OBJETO:
        avisos.append(f"{donde}: el tipo de objeto «{tipo}» no es común en Blender.")
    for minimo, maximo in (("min", "max"),):
        if minimo in target.params and maximo in target.params:
            try:
                if float(target.params[minimo]) > float(target.params[maximo]):
                    errores.append(f"{donde}: «min» es mayor que «max».")
            except (TypeError, ValueError):
                errores.append(f"{donde}: «min» y «max» deben ser números.")
    if spec.selects and not any(k in target.params for k in SELECTORES) and spec.id not in (
        "object.count", "transform.scale_applied", "material.exists", "material.distinct", "material.matches",
        "mesh.no_duplicates", "camera.frames", "light.three_point",
    ):
        errores.append(f"{donde}: {target.validator} necesita a qué objetos aplicarse (role, name, name_prefix o type).")


def _revisar_opciones(target, errores, avisos, registro=None):
    """logic.any: cada opción es un validador real con sus parámetros."""
    from ..bootstrap import create_default_registry
    from ..validators.logic import opciones

    try:
        crudas = opciones(target)
    except ValueError as error:
        errores.append(f"Objetivo «{target.id}»: {error}.")
        return
    registro = registro or create_default_registry()
    for i, opcion in enumerate(crudas):
        spec = registro.spec(opcion["validator"])
        if spec is None:
            errores.append(f"Objetivo «{target.id}»: la opción {i + 1} usa el validador «{opcion['validator']}», que no existe.")
            continue
        sub = type(target)(id=target.id, validator=opcion["validator"], params=dict(opcion.get("params") or {}))
        _revisar_parametros(sub, spec, set(), errores, avisos)


def _revisar_v2(practica, registry, tools, errores, avisos):
    """Vigilantes, píldoras, repaso y curso (amatista.practice/2)."""
    ids = {t.id for t in practica.targets}
    roles = {r.id for r in practica.roles}
    for guard in practica.guards:
        spec = registry.spec(guard.validator)
        if spec is None:
            errores.append(f"Vigilante «{guard.id}»: el validador «{guard.validator}» no existe en este motor.")
        else:
            _revisar_parametros(guard, spec, roles, errores, avisos, registry)
        if guard.fix is None:
            avisos.append(f"Vigilante «{guard.id}»: sin «fix»; el alumno verá el problema pero no un botón para arreglarlo.")
        if not guard.messages.get("fail") and not guard.tip:
            avisos.append(f"Vigilante «{guard.id}»: conviene un messages.fail que explique por qué se pausó el progreso.")
    vigilantes = {g.id for g in practica.guards}
    for pildora in practica.pills:
        donde = f"Píldora «{pildora.id}»"
        disparo = pildora.trigger
        if disparo.on == "target" and disparo.target not in ids:
            errores.append(f"{donde}: aparece con el objetivo «{disparo.target}», que no existe.")
        if disparo.on == "guard" and disparo.target not in vigilantes:
            errores.append(f"{donde}: aparece con el vigilante «{disparo.target}», que no existe.")
        if disparo.on == "tool" and disparo.tool not in tools:
            errores.append(f"{donde}: la herramienta «{disparo.tool}» no está en el catálogo.")
        if len(pildora.text) > PILDORA_IDEAL:
            avisos.append(
                f"{donde}: {len(pildora.text)} caracteres. Una píldora se lee de un vistazo (ideal ≤ {PILDORA_IDEAL})."
            )
    if practica.schema == SCHEMA_V2:
        if not practica.pills:
            avisos.append("La práctica no tiene píldoras de teoría (pills): el alumno no verá teoría dentro de Blender.")
        elif not any(p.trigger.on == "start" for p in practica.pills):
            avisos.append("Ninguna píldora aparece al empezar (trigger start): la práctica arranca sin contexto.")
        if not practica.place.course:
            avisos.append("La práctica no dice a qué curso pertenece (course.id).")
        if practica.estimated_minutes is None:
            avisos.append("Falta estimatedMinutes: el alumno no sabrá cuánto dura.")
    if practica.place.next == practica.id:
        errores.append("course.next no puede ser la misma práctica.")


def _revisar_archivo_del_ejemplo(practica, errores) -> None:
    """El archivo del ejemplo y file.named piden lo mismo: lo que acepta uno lo acepta el otro."""
    if practica.example is None:
        return
    from ..ejemplo import lo_que_pide
    from ..ejemplo.revision import palabra_archivo

    archivo = lo_que_pide(practica.example.steps).get("archivo")
    if not archivo:
        return
    palabra = palabra_archivo(archivo)
    for target in practica.targets:
        contiene = str(target.params.get("contains") or "").lower()
        if target.validator != "file.named" or not contiene:
            continue
        if contiene not in archivo.lower() or palabra not in contiene:
            errores.append(
                f"Objetivo «{target.id}»: pide un nombre con «{contiene}», pero el ejemplo guarda «{archivo}» y su "
                f"revisión pide «{palabra}». Usa en el ejemplo un archivo cuya palabra sea «{contiene}» "
                f"(por ejemplo mi_{contiene}.blend).")


def compile_practice(
    data: Any,
    registry: Optional[ValidatorRegistry] = None,
    tools: Optional[ToolRegistry] = None,
) -> CompileResult:
    """Valida por completo una práctica (dict JSON o PracticeDefinition)."""
    if registry is None:
        from ..bootstrap import create_default_registry

        registry = create_default_registry()
    tools = tools or ToolRegistry.default()

    if isinstance(data, PracticeDefinition):
        practica = data
    else:
        try:
            practica = parse_practice(data)
        except InvalidPracticeError as error:
            return CompileResult(None, errors=list(error.errors))

    errores: List[str] = []
    avisos: List[str] = []
    roles = {r.id for r in practica.roles}
    ids = {t.id for t in practica.targets}

    for target in practica.targets:
        spec = registry.spec(target.validator)
        if spec is None:
            errores.append(
                f"Objetivo «{target.id}»: el validador «{target.validator}» no existe en esta versión de "
                f"Amatista Engine (disponibles: {', '.join(registry.ids())})."
            )
        else:
            _revisar_parametros(target, spec, roles, errores, avisos, registry)
        for requisito in target.requires:
            if requisito == target.id:
                errores.append(f"Objetivo «{target.id}»: no puede depender de sí mismo.")
            elif requisito not in ids:
                errores.append(f"Objetivo «{target.id}»: depende de «{requisito}», que no existe.")
        if not target.title:
            avisos.append(f"Objetivo «{target.id}»: sin título (el alumno verá el id).")
        if not target.hints and not target.optional:
            avisos.append(f"Objetivo «{target.id}»: sin pistas.")

    _revisar_archivo_del_ejemplo(practica, errores)

    from ..pedagogy.graph import find_cycle

    ciclo = find_cycle(practica.targets)
    if ciclo:
        errores.append(f"Las dependencias forman un ciclo: {' → '.join(ciclo)}.")

    for tool_id in practica.allowed_tools + practica.warn_tools:
        if tool_id not in tools:
            avisos.append(f"La herramienta «{tool_id}» no está en el catálogo de Amatista Engine.")
    roles_usados = {t.params.get(clave) for t in practica.targets + practica.guards
                    for clave in ("role", "reference_role") if isinstance(t.params.get(clave), str)}
    _revisar_v2(practica, registry, tools, errores, avisos)
    for rol in roles - roles_usados:
        avisos.append(f"El rol «{rol}» está declarado pero ningún objetivo lo usa.")
    if not practica.roles and any(t.params.get("role") for t in practica.targets):
        avisos.append("La práctica usa roles pero no los declara en «roles»: el Tagger no podrá ofrecerlos.")

    return CompileResult(practica, errores, avisos)
