"""Ayudantes comunes de los validadores.

Selector de objetos: casi todos los validadores aceptan los mismos
parámetros para decidir a qué objetos se aplican (se combinan con Y):

    role         rol educativo (propiedad amatista_role)
    name         nombre exacto
    name_prefix  nombre que empieza así ("Pata" → Pata, Pata.001...)
    type         tipo de Blender (MESH, CAMERA, LIGHT...)
    tag          etiqueta educativa (propiedad amatista_tags)
    collection   colección que contiene al objeto

Sin selector, se aplican a todos los objetos de la escena.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..models import SceneObject, SceneState, TargetDefinition, ValidationResult

SELECTORES = ("role", "name", "name_prefix", "type", "tag", "collection")
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
    return "objetos"


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


def count_message(found: int, minimo: Optional[int], maximo: Optional[int], que: str) -> str:
    """Mensajes generados (sección 22 de la especificación)."""
    if minimo is not None and minimo == maximo:
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
