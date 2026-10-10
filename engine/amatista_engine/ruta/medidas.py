"""Medidas amables (motor 4): la forma tiene que tener sentido, las medidas no estorban.

Antes cada validador pedía su número exacto (la rueda a 0.15 del suelo, el
vagón 1.3 veces más largo que alto) y el alumno se peleaba con decimales que
nadie ve en la vista 3D. Ahora el motor afloja esas tolerancias según el
nivel de la práctica, igual que figure.recognize ya lo hacía con la figura:

    nivel 1   la forma y la idea   (holgura × 1.6)
    nivel 2   proporciones a ojo   (holgura × 1.4)
    nivel 3   cerca del modelo     (holgura × 1.2)
    nivel 4-5 medidas reales       (como las escribió el autor)

Lo que NO se afloja es el sentido: una rueda sigue teniendo que tocar el
suelo y el vagón, una chimenea sigue yendo encima. Solo se ensancha el margen
para que «casi tocando» cuente como tocando. Un objetivo con
"params": {"exact": true} se revisa tal cual en cualquier nivel.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict

from ..models import TargetDefinition

HOLGURA = {1: 1.6, 2: 1.4, 3: 1.2, 4: 1.0, 5: 1.0}

# Validadores con «tolerance» (se multiplica) y su valor si el autor no la escribió.
TOLERANCIAS = {"spatial.grounded": 0.05, "spatial.touching": 0.05, "spatial.below": 0.02,
               "spatial.on_top": 0.25, "dimension.approx": 0.35}
# Las que son metros (las otras son fracciones de la medida del objeto).
EN_METROS = {"spatial.grounded", "spatial.touching", "spatial.below"}
# Margen mínimo en metros en los primeros niveles: 5 cm de diferencia no se ven en la vista 3D.
MINIMO_DISTANCIA = {1: 0.1, 2: 0.08}


def holgura(nivel: int) -> float:
    """Cuánto se aflojan las medidas en este nivel (1.0 = como las escribió el autor)."""
    return HOLGURA.get(max(1, min(5, int(nivel or 1))), 1.0)


def ajustar_parametros(validador: str, params: Dict, nivel: int) -> Dict:
    """Los parámetros de medida con la holgura del nivel (un dict nuevo; no toca el original)."""
    factor = holgura(nivel)
    if factor <= 1.0 or params.get("exact"):
        return params
    nuevos = dict(params)
    if validador in TOLERANCIAS:
        base = params.get("tolerance", TOLERANCIAS[validador])
        if isinstance(base, (int, float)) and not isinstance(base, bool):
            minimo = MINIMO_DISTANCIA.get(nivel, 0.0) if validador in EN_METROS else 0.0
            nuevos["tolerance"] = round(max(base * factor, minimo), 4)
    elif validador == "shape.proportion":
        minimo = params.get("min_ratio")
        if isinstance(minimo, (int, float)) and minimo > 1.0:
            # «1.3 veces más largo» pasa a «se nota más largo» (1.19 en nivel 1), nunca a «igual».
            nuevos["min_ratio"] = round(1.0 + (minimo - 1.0) / factor, 3)
        maximo = params.get("max_ratio")
        if isinstance(maximo, (int, float)):
            nuevos["max_ratio"] = round(maximo * factor, 3)
    elif validador == "shape.thinnest_axis":
        razon = params.get("max_ratio", 0.6)
        if isinstance(razon, (int, float)):
            # Delgada sigue siendo delgada: nunca más de 0.7 de lo más grande.
            nuevos["max_ratio"] = round(min(0.7, razon * factor ** 0.5), 3)
    return nuevos


def ajustar(target: TargetDefinition, nivel: int) -> TargetDefinition:
    """El objetivo con sus medidas aflojadas para el nivel (el mismo objeto si no cambia nada)."""
    params = target.params or {}
    if target.validator == "logic.any" and isinstance(params.get("options"), list) and not params.get("exact"):
        opciones = [
            {**o, "params": ajustar_parametros(str(o.get("validator", "")), dict(o.get("params") or {}), nivel)}
            if isinstance(o, dict) else o
            for o in params["options"]
        ]
        nuevos = {**params, "options": opciones}
    else:
        nuevos = ajustar_parametros(target.validator, params, nivel)
    if nuevos is params or nuevos == params:
        return target
    return replace(target, params=nuevos)
