"""Lógica entre validadores (motor v3): «basta con una de estas opciones».

    {"validator": "logic.any", "params": {"options": [
        {"validator": "material.matches", "params": {"transmission_min": 0.5}},
        {"validator": "material.matches", "params": {"alpha_max": 0.6}}
    ]}}

Sirve para aceptar caminos distintos (vidrio por transmisión o por alfa;
una espada o una taza) sin escribir código.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import result

MAX_OPCIONES = 6


def opciones(target: TargetDefinition) -> List[Dict[str, Any]]:
    crudas = target.params.get("options")
    if not isinstance(crudas, list) or not 2 <= len(crudas) <= MAX_OPCIONES:
        raise ValueError(f"logic.any necesita «options» con 2 a {MAX_OPCIONES} opciones")
    for opcion in crudas:
        if not isinstance(opcion, dict) or not isinstance(opcion.get("validator"), str):
            raise ValueError("cada opción de logic.any necesita «validator» y «params»")
        if opcion["validator"] == "logic.any":
            raise ValueError("logic.any no se puede anidar")
    return crudas


def make_any(registry):
    def any_of(target: TargetDefinition, scene: SceneState) -> ValidationResult:
        resultados = []
        for opcion in opciones(target):
            funcion = registry.get(opcion["validator"])
            if funcion is None:
                raise ValueError(f"logic.any: el validador «{opcion['validator']}» no existe")
            sub = TargetDefinition(id=target.id, validator=opcion["validator"], params=dict(opcion.get("params") or {}))
            r = funcion(sub, scene)
            if r.passed:
                return result(target, True, r.message, {"option": opcion["validator"], "matched": r.details})
            resultados.append(r)
        return result(
            target, False, resultados[0].message,
            {"options": [{"validator": r.validator, "message": r.message} for r in resultados]},
        )

    return any_of
