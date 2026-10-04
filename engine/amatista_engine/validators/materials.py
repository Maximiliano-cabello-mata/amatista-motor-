"""Materiales con el Principled BSDF (motor v3).

material.distinct cuenta materiales distintos que de verdad pintan caras;
material.matches busca materiales con propiedades físicas (metálico,
rugosidad, transmisión, alfa) en un rango: «metal brillante», «vidrio»,
«metal quemado».
"""
from __future__ import annotations

from typing import Dict, List

from ..models import MaterialInfo, SceneState, TargetDefinition, ValidationResult
from .base import count_message, count_ok, count_rule, describe, result, select, selector

PINTABLES = ("MESH", "CURVE", "SURFACE", "META", "FONT")
# params → (propiedad, comparación)
CONDICIONES = {
    "metallic_min": ("metallic", ">="),
    "metallic_max": ("metallic", "<="),
    "roughness_min": ("roughness", ">="),
    "roughness_max": ("roughness", "<="),
    "transmission_min": ("transmission", ">="),
    "alpha_max": ("alpha", "<="),
}
NOMBRES = {"metallic": "Metálico", "roughness": "Rugosidad", "transmission": "Transmisión", "alpha": "Alfa"}


def _usados(target: TargetDefinition, scene: SceneState) -> Dict[str, MaterialInfo]:
    """Materiales que pintan algo en los objetos seleccionados (por nombre)."""
    sel = selector(target)
    materiales: Dict[str, MaterialInfo] = {}
    for obj in select(scene, sel):
        if obj.object_type not in PINTABLES:
            continue
        nombres = obj.materials_used if obj.materials_used is not None else obj.materials
        detalles = {m.name: m for m in obj.material_details}
        for nombre in nombres:
            materiales[nombre] = detalles.get(nombre, MaterialInfo(nombre))
    return materiales


def distinct(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Al menos N materiales distintos aplicados (equals / min / max)."""
    sel = selector(target)
    minimo, maximo = count_rule(target, default_min=1)
    usados = _usados(target, scene)
    que = "materiales distintos" + (f" en «{describe(sel)}»" if sel else "")
    return result(
        target,
        count_ok(len(usados), minimo, maximo),
        count_message(len(usados), minimo, maximo, que),
        {"selector": sel, "found": len(usados), "materials": sorted(usados), "expected": {"min": minimo, "max": maximo}},
    )


def _cumple(material: MaterialInfo, condiciones: List[tuple]) -> bool:
    for propiedad, comparacion, valor in condiciones:
        actual = getattr(material, propiedad)
        if comparacion == ">=" and actual < valor - 1e-6:
            return False
        if comparacion == "<=" and actual > valor + 1e-6:
            return False
    return True


def matches(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Al menos `count` materiales aplicados cumplen todas las condiciones.

    params: metallic_min/max, roughness_min/max, transmission_min, alpha_max,
    count (default 1) y label («metal brillante») para los mensajes.
    """
    condiciones = []
    for clave, (propiedad, comparacion) in CONDICIONES.items():
        if clave in target.params:
            condiciones.append((propiedad, comparacion, float(target.params[clave])))
    if not condiciones:
        raise ValueError("material.matches necesita al menos una condición (metallic_min, roughness_max…)")
    cuantos = int(target.params.get("count", 1))
    etiqueta = str(target.params.get("label", "") or "el material pedido")
    usados = _usados(target, scene)
    cumplen = sorted(n for n, m in usados.items() if _cumple(m, condiciones))
    pedido = ", ".join(
        f"{NOMBRES[p]} {'≥' if c == '>=' else '≤'} {v:g}" for p, c, v in condiciones
    )
    if len(cumplen) >= cuantos:
        mensaje = f"Ya tienes {etiqueta}: «{cumplen[0]}»."
    elif not usados:
        mensaje = f"Todavía no hay materiales aplicados. Crea uno para {etiqueta} ({pedido})."
    else:
        mensaje = f"Falta {etiqueta}: un material con {pedido}."
    return result(
        target,
        len(cumplen) >= cuantos,
        mensaje,
        {"conditions": [list(c) for c in condiciones], "matching": cumplen, "label": etiqueta, "count": cuantos},
    )
