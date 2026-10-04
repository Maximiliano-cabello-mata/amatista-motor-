"""Progreso ponderado por objetivos (sección 17).

Los objetivos opcionales no suman ni restan: nunca aparecen como error.
"""
from typing import Iterable, Mapping

from ..models import TargetDefinition, ValidationResult


def calculate_progress(
    targets: Iterable[TargetDefinition],
    results: Mapping[str, ValidationResult],
) -> float:
    obligatorios = tuple(t for t in targets if not t.optional)
    total_weight = sum(max(0.0, target.weight) for target in obligatorios)

    if total_weight <= 0:
        return 0.0

    earned = 0.0

    for target in obligatorios:
        result = results.get(target.id)
        if result is not None and result.passed is True:
            earned += max(0.0, target.weight)

    return round((earned / total_weight) * 100.0, 2)
