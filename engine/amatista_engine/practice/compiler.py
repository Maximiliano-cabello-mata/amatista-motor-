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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..errors import InvalidPracticeError
from ..models import PracticeDefinition
from ..registry import ValidatorRegistry
from ..tools.registry import ToolRegistry
from ..validators.base import SELECTORES
from .loader import parse_practice

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


def _revisar_parametros(target, spec, roles_declarados, errores, avisos):
    donde = f"Objetivo «{target.id}»"
    for param in spec.params:
        if param.required and param.name not in target.params:
            errores.append(f"{donde}: {target.validator} necesita el parámetro «{param.name}» ({param.label}).")
    conocidos = {p.name for p in spec.params} | ({*SELECTORES, "reference", "inside"} if spec.selects else set())
    conocidos |= {"tolerance", "reference", "reference_role", "inside"}
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
    if eje is not None and str(eje).lower() not in ("x", "y", "z"):
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
        "object.count", "transform.scale_applied", "material.exists"
    ):
        errores.append(f"{donde}: {target.validator} necesita a qué objetos aplicarse (role, name, name_prefix o type).")


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
            _revisar_parametros(target, spec, roles, errores, avisos)
        for requisito in target.requires:
            if requisito == target.id:
                errores.append(f"Objetivo «{target.id}»: no puede depender de sí mismo.")
            elif requisito not in ids:
                errores.append(f"Objetivo «{target.id}»: depende de «{requisito}», que no existe.")
        if not target.title:
            avisos.append(f"Objetivo «{target.id}»: sin título (el alumno verá el id).")
        if not target.hints and not target.optional:
            avisos.append(f"Objetivo «{target.id}»: sin pistas.")

    from ..pedagogy.graph import find_cycle

    ciclo = find_cycle(practica.targets)
    if ciclo:
        errores.append(f"Las dependencias forman un ciclo: {' → '.join(ciclo)}.")

    for tool_id in practica.allowed_tools + practica.warn_tools:
        if tool_id not in tools:
            avisos.append(f"La herramienta «{tool_id}» no está en el catálogo de Amatista Engine.")
    roles_usados = {t.params.get("role") for t in practica.targets} | {
        t.params.get("reference_role") for t in practica.targets
    }
    for rol in roles - roles_usados:
        avisos.append(f"El rol «{rol}» está declarado pero ningún objetivo lo usa.")
    if not practica.roles and any(t.params.get("role") for t in practica.targets):
        avisos.append("La práctica usa roles pero no los declara en «roles»: el Tagger no podrá ofrecerlos.")

    return CompileResult(practica, errores, avisos)
