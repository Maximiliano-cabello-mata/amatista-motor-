"""Malla, modificadores y materiales."""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import count_message, count_ok, count_rule, describe, result, select, selector, text


def _contar_geometria(target: TargetDefinition, scene: SceneState, campo: str, nombre: str) -> ValidationResult:
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type == "MESH"]
    minimo, maximo = count_rule(target, default_min=1)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay mallas «{que}».", {"selector": sel})
    fallan = []
    for obj in objetos:
        valor = getattr(obj, campo)
        if valor is None or not count_ok(valor, minimo, maximo):
            fallan.append({"object": obj.name, "value": valor})
    mensaje = (
        f"«{que}» tiene la cantidad de {nombre} esperada."
        if not fallan
        else count_message(fallan[0]["value"] or 0, minimo, maximo, f"{nombre} en «{fallan[0]['object']}»")
    )
    return result(
        target, not fallan, mensaje, {"selector": sel, "expected": {"min": minimo, "max": maximo}, "failed": fallan}
    )


def vertex_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _contar_geometria(target, scene, "vertices", "vértices")


def face_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _contar_geometria(target, scene, "faces", "caras")


def modifier_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Todos los objetos seleccionados tienen el modificador (BEVEL, MIRROR...)."""
    modificador = text(target, "modifier", required=True).upper()
    sel = selector(target)
    objetos = select(scene, sel)
    que = describe(sel)
    sin = [o.name for o in objetos if modificador not in o.modifiers]
    return result(
        target,
        bool(objetos) and not sin,
        f"«{que}» ya tiene el modificador {modificador}."
        if objetos and not sin
        else (f"No hay objetos «{que}»." if not objetos else f"Agrega el modificador {modificador} a «{sin[0]}»."),
        {"selector": sel, "modifier": modificador, "missing": sin},
    )


def material_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Los objetos seleccionados tienen material (o uno con params.material en el nombre)."""
    nombre = text(target, "material")
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type in ("MESH", "CURVE", "SURFACE", "META", "FONT")]
    que = describe(sel)

    def tiene(obj) -> bool:
        if not obj.materials:
            return False
        return not nombre or any(nombre.lower() in m.lower() for m in obj.materials)

    sin = [o.name for o in objetos if not tiene(o)]
    return result(
        target,
        bool(objetos) and not sin,
        f"«{que}» ya tiene material."
        if objetos and not sin
        else (f"No hay objetos «{que}»." if not objetos else f"Asigna un material a «{sin[0]}»."),
        {"selector": sel, "material": nombre or None, "missing": sin},
    )

