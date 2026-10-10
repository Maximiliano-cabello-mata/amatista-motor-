"""Ayudantes comunes de los validadores.

Selector de objetos: casi todos los validadores aceptan los mismos
parámetros para decidir a qué objetos se aplican (se combinan con Y):

    role         rol educativo (propiedad amatista_role)
    name         nombre exacto
    name_prefix  nombre que empieza así ("Pata" → Pata, Pata.001...)
    type         tipo de Blender (MESH, CAMERA, LIGHT...)
    tag          etiqueta educativa (propiedad amatista_tags)
    collection   colección que contiene al objeto
    primitive    primitiva de la que salió la malla (cube, cylinder, sphere,
                 cone, torus, plane, icosphere, monkey) según el nombre de
                 sus datos («Cylinder.003»). Motor v3.

Sin selector, se aplican a todos los objetos de la escena.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..models import SceneObject, SceneState, TargetDefinition, ValidationResult

SELECTORES = ("role", "name", "name_prefix", "type", "tag", "collection", "primitive")
# Nombre en español o en inglés → nombre de los datos que pone Blender.
PRIMITIVAS = {
    "cube": "cube", "cubo": "cube",
    "cylinder": "cylinder", "cilindro": "cylinder",
    "sphere": "sphere", "esfera": "sphere", "uv_sphere": "sphere",
    "icosphere": "icosphere", "icoesfera": "icosphere",
    "cone": "cone", "cono": "cone",
    "torus": "torus", "toroide": "torus", "dona": "torus",
    "plane": "plane", "plano": "plane",
    "circle": "circle", "circulo": "circle",
    "monkey": "suzanne", "mono": "suzanne", "suzanne": "suzanne",
}
EJES = {"x": 0, "y": 1, "z": 2}


def result(
    target: TargetDefinition,
    passed: bool,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    return ValidationResult(
        target_id=target.id,
        validator=target.validator,
        passed=passed,
        message=message,
        details=details or {},
    )


def text(target: TargetDefinition, name: str, required: bool = False) -> str:
    valor = str(target.params.get(name, "") or "").strip()
    if required and not valor:
        raise ValueError(f"{target.validator} requiere params.{name}")
    return valor


def number(target: TargetDefinition, name: str, default: float) -> float:
    valor = target.params.get(name, default)
    try:
        return float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{target.validator}: params.{name} debe ser un número") from exc


def axis(target: TargetDefinition, default: str = "z") -> Tuple[str, int]:
    eje = str(target.params.get("axis", default)).lower()
    if eje not in EJES:
        raise ValueError(f"{target.validator} requiere axis x, y o z")
    return eje, EJES[eje]


def selector(target: TargetDefinition) -> Dict[str, str]:
    return {clave: text(target, clave) for clave in SELECTORES if text(target, clave)}


def describe(sel: Dict[str, str], practice_label=None) -> str:
    """Texto corto para mensajes: «pata», «Mesa», «objetos MESH»..."""
    if "role" in sel:
        return practice_label(sel["role"]) if practice_label else sel["role"]
    if "name" in sel:
        return sel["name"]
    if "name_prefix" in sel:
        return f"{sel['name_prefix']}…"
    if "type" in sel:
        return f"objetos {sel['type']}"
    if "tag" in sel:
        return f"#{sel['tag']}"
    if "collection" in sel:
        return f"colección {sel['collection']}"
    if "primitive" in sel:
        return {"cube": "cubos", "cylinder": "cilindros", "sphere": "esferas", "cone": "conos",
                "plane": "planos", "torus": "donas", "icosphere": "icoesferas",
                "suzanne": "monos"}.get(primitiva(sel["primitive"]), sel["primitive"])
    return "objetos"


def primitiva(nombre: str) -> str:
    clave = str(nombre or "").strip().lower()
    return PRIMITIVAS.get(clave, clave)


def select(scene: SceneState, sel: Dict[str, str]) -> Tuple[SceneObject, ...]:
    def coincide(obj: SceneObject) -> bool:
        if "role" in sel and sel["role"] not in obj.roles:
            return False
        if "name" in sel and obj.name != sel["name"]:
            return False
        if "name_prefix" in sel and not obj.name.lower().startswith(sel["name_prefix"].lower()):
            return False
        if "type" in sel and obj.object_type.upper() != sel["type"].upper():
            return False
        if "tag" in sel and sel["tag"] not in obj.tags:
            return False
        if "collection" in sel and sel["collection"] not in obj.collections:
            return False
        if "primitive" in sel and obj.primitive != primitiva(sel["primitive"]):
            return False
        return True

    return tuple(obj for obj in scene.objects if coincide(obj))


def count_rule(target: TargetDefinition, default_min: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
    """(mínimo, máximo) a partir de equals / min / max."""
    params = target.params
    if "equals" in params:
        igual = int(params["equals"])
        if igual < 0:
            raise ValueError(f"{target.validator} requiere equals >= 0")
        return igual, igual
    minimo = int(params["min"]) if "min" in params else default_min
    maximo = int(params["max"]) if "max" in params else None
    if minimo is not None and maximo is not None and minimo > maximo:
        raise ValueError(f"{target.validator}: min no puede ser mayor que max")
    return minimo, maximo


def count_ok(found: int, minimo: Optional[int], maximo: Optional[int]) -> bool:
    return (minimo is None or found >= minimo) and (maximo is None or found <= maximo)


# Plurales que no salen de quitar la «s» o el «es».
IRREGULARES = {"luces": "luz", "veces": "vez", "cruces": "cruz", "lápices": "lápiz", "peces": "pez",
               "voces": "voz", "raíces": "raíz", "focos": "foco"}


def singular(que: str) -> str:
    """«esferas» → «esfera», «luces» → «luz», «materiales distintos» → «material distinto» (hasta « en …»).

    Lo que va entre comillas («Rueda») es un nombre y no cambia.
    """
    cabeza, sep, resto = que.partition(" en ")
    palabras = []
    for p in cabeza.split(" "):
        if p.startswith("«") or p.endswith("»"):
            pass
        elif p.lower() in IRREGULARES:
            p = IRREGULARES[p.lower()]
        elif p.endswith("es") and len(p) > 4 and p[-3] in "lrnd":
            p = p[:-2]
        elif p.endswith("s") and p[:1].islower() and len(p) > 3:
            p = p[:-1]
        palabras.append(p)
    return " ".join(palabras) + sep + resto


def count_message(found: int, minimo: Optional[int], maximo: Optional[int], que: str) -> str:
    """Mensajes generados (sección 22 de la especificación).

    Un nombre entre comillas («Vagón», la etiqueta de un rol) no lleva plural: «Tienes 2 de tipo «Vagón»».
    """
    exacto = minimo is not None and minimo == maximo
    if found == 1 and not exacto:
        que = singular(que)
    if not exacto and que.startswith("«"):
        que = f"de tipo {que}"
    if exacto:
        if found == minimo:
            return f"{found}/{minimo} {que}. Objetivo completado."
        if found == 0:
            return f"0/{minimo} {que}. Todavía no hay ninguno."
        if found < minimo:
            faltan = minimo - found
            return f"Tienes {found}/{minimo} {que}. Falta{'n' if faltan > 1 else ''} {faltan}."
        return f"Tienes {found}/{minimo} {que}. Hay {found - minimo} de más."
    if minimo is not None and found < minimo:
        return f"Tienes {found} {que}; se necesitan al menos {minimo}."
    if maximo is not None and found > maximo:
        return f"Tienes {found} {que}; el máximo es {maximo}."
    return f"Tienes {found} {que}. Objetivo completado."


def in_range(value: float, minimo: float, maximo: float) -> bool:
    return minimo <= value <= maximo
