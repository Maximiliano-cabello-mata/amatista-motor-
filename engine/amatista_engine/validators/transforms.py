"""Dimensiones, posición, rotación, escala aplicada y relaciones espaciales."""
from __future__ import annotations

import math

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import axis, describe, in_range, number, result, select, selector, text


def _seleccion_obligatoria(target: TargetDefinition, scene: SceneState):
    sel = selector(target)
    if not sel:
        raise ValueError(f"{target.validator} requiere params.role o params.name")
    return sel, select(scene, sel)


def _rango(target, valores, etiqueta, unidad=""):
    """valores: [(objeto, valor)]. Pasa si todos están en [min, max]."""
    minimo = number(target, "min", float("-inf"))
    maximo = number(target, "max", float("inf"))
    fallan = [
        {"object": obj.name, "value": round(valor, 4)}
        for obj, valor in valores
        if not in_range(valor, minimo, maximo)
    ]
    return minimo, maximo, fallan


def dimension_range(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    sel, objetos = _seleccion_obligatoria(target, scene)
    eje, indice = axis(target)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay objetos «{que}» para medir.", {"selector": sel, "role": sel.get("role")})
    minimo, maximo, fallan = _rango(target, [(o, o.dimensions[indice]) for o in objetos], "dimensión")
    if fallan:
        valor = fallan[0]["value"]
        direccion = "grande" if valor > maximo else "pequeño"
        mensaje = (
            f"«{fallan[0]['object']}» mide {valor:.2f} en {eje.upper()}: es demasiado {direccion} "
            f"(entre {minimo:g} y {maximo:g})."
        )
    else:
        mensaje = f"Las medidas de «{que}» en {eje.upper()} son correctas."
    return result(
        target,
        not fallan,
        mensaje,
        {"selector": sel, "role": sel.get("role"), "axis": eje, "min": minimo, "max": maximo, "failed": fallan},
    )


def object_position(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    sel, objetos = _seleccion_obligatoria(target, scene)
    eje, indice = axis(target)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay objetos «{que}» para ubicar.", {"selector": sel})
    minimo, maximo, fallan = _rango(target, [(o, o.location[indice]) for o in objetos], "posición")
    return result(
        target,
        not fallan,
        f"«{que}» está en la posición correcta en {eje.upper()}."
        if not fallan
        else f"«{fallan[0]['object']}» está en {eje.upper()} = {fallan[0]['value']:.2f}; "
        f"debe quedar entre {minimo:g} y {maximo:g}.",
        {"selector": sel, "axis": eje, "min": minimo, "max": maximo, "failed": fallan},
    )


def object_rotation(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Rotación en grados (los objetos la guardan en radianes)."""
    sel, objetos = _seleccion_obligatoria(target, scene)
    eje, indice = axis(target)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay objetos «{que}» para revisar su giro.", {"selector": sel})
    minimo, maximo, fallan = _rango(
        target, [(o, math.degrees(o.rotation[indice]) % 360.0) for o in objetos], "rotación"
    )
    return result(
        target,
        not fallan,
        f"El giro de «{que}» en {eje.upper()} es correcto."
        if not fallan
        else f"«{fallan[0]['object']}» está girado {fallan[0]['value']:.0f}° en {eje.upper()} "
        f"(se espera entre {minimo:g}° y {maximo:g}°).",
        {"selector": sel, "axis": eje, "min": minimo, "max": maximo, "failed": fallan},
    )


def scale_applied(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    sel = selector(target)
    objetos = select(scene, sel)
    tolerancia = number(target, "tolerance", 0.0001)
    sin_aplicar = [o.name for o in objetos if any(abs(s - 1.0) > tolerancia for s in o.scale)]
    que = describe(sel)
    return result(
        target,
        bool(objetos) and not sin_aplicar,
        f"La escala de «{que}» está aplicada."
        if objetos and not sin_aplicar
        else (
            f"No hay objetos «{que}»."
            if not objetos
            else f"Aplica la escala de «{sin_aplicar[0]}» (Ctrl+A › Escala)."
        ),
        {"selector": sel, "not_applied": sin_aplicar},
    )


def below(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Cada objeto seleccionado queda debajo del objeto de referencia.

    params: role/name (los de abajo), reference_role o reference (el de
    arriba), tolerance (default 0.02) y inside (true: el centro de cada uno
    queda dentro de la huella X/Y de la referencia).
    """
    sel, objetos = _seleccion_obligatoria(target, scene)
    rol_ref = text(target, "reference_role")
    nombre_ref = text(target, "reference")
    if not rol_ref and not nombre_ref:
        raise ValueError("spatial.below requiere params.reference_role o params.reference")
    referencias = scene.objects_with_role(rol_ref) if rol_ref else tuple(
        o for o in scene.objects if o.name == nombre_ref
    )
    que = describe(sel)
    ref_texto = rol_ref or nombre_ref
    if not objetos or not referencias:
        falta = que if not objetos else ref_texto
        return result(target, False, f"Todavía falta «{falta}» para comparar posiciones.", {"selector": sel})
    tolerancia = number(target, "tolerance", 0.02)
    dentro = bool(target.params.get("inside", True))
    ref_min, ref_max = referencias[0].caja()
    fallan = []
    for obj in objetos:
        caja_min, caja_max = obj.caja()
        if caja_max[2] > ref_min[2] + tolerancia:
            fallan.append({"object": obj.name, "reason": "arriba"})
            continue
        centro = [(a + b) / 2.0 for a, b in zip(caja_min, caja_max)]
        if dentro and not (
            ref_min[0] - tolerancia <= centro[0] <= ref_max[0] + tolerancia
            and ref_min[1] - tolerancia <= centro[1] <= ref_max[1] + tolerancia
        ):
            fallan.append({"object": obj.name, "reason": "fuera"})
    if not fallan:
        mensaje = f"Todas las «{que}» quedan debajo de «{ref_texto}»."
    elif fallan[0]["reason"] == "arriba":
        mensaje = f"«{fallan[0]['object']}» atraviesa o sobresale por encima de «{ref_texto}»."
    else:
        mensaje = f"«{fallan[0]['object']}» está fuera de la huella de «{ref_texto}»: muévelo debajo."
    return result(target, not fallan, mensaje, {"selector": sel, "reference": ref_texto, "failed": fallan})
