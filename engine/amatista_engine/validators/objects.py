"""Existencia y cantidad de objetos y roles."""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import count_message, count_ok, count_rule, describe, result, select, selector, text


def object_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    sel = selector(target)
    if not sel:
        raise ValueError("object.exists requiere params.name, role, name_prefix o type")
    encontrados = select(scene, sel)
    que = describe(sel)
    return result(
        target,
        bool(encontrados),
        f"Encontramos «{que}»." if encontrados else f"No encontramos «{que}».",
        {"selector": sel, "found": len(encontrados), "objects": [o.name for o in encontrados]},
    )


def object_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    sel = selector(target)
    minimo, maximo = count_rule(target, default_min=1)
    encontrados = select(scene, sel)
    que = describe(sel)
    return result(
        target,
        count_ok(len(encontrados), minimo, maximo),
        count_message(len(encontrados), minimo, maximo, que),
        {
            "selector": sel,
            "expected": {"min": minimo, "max": maximo},
            "found": len(encontrados),
            "objects": [o.name for o in encontrados],
        },
    )


def role_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    rol = text(target, "role", required=True)
    encontrados = scene.objects_with_role(rol)
    return result(
        target,
        bool(encontrados),
        f"Hay un objeto con el rol «{rol}»." if encontrados else f"Ningún objeto tiene todavía el rol «{rol}».",
        {"role": rol, "found": len(encontrados), "objects": [o.name for o in encontrados]},
    )


def role_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    rol = text(target, "role", required=True)
    if not any(k in target.params for k in ("equals", "min", "max")):
        minimo = maximo = 1
    else:
        minimo, maximo = count_rule(target)
    encontrados = scene.objects_with_role(rol)
    return result(
        target,
        count_ok(len(encontrados), minimo, maximo),
        count_message(len(encontrados), minimo, maximo, f"«{rol}»"),
        {
            "role": rol,
            "expected": minimo if minimo == maximo else {"min": minimo, "max": maximo},
            "found": len(encontrados),
            "objects": [o.name for o in encontrados],
        },
    )
