"""Progreso ponderado por objetivos (sección 17).

Los objetivos opcionales no suman ni restan: nunca aparecen como error.

Dos reglas hacen que el progreso no retroceda mientras el alumno avanza:

- Un objetivo solo suma cuando sus requisitos (`requires`) ya están cumplidos.
  «Ruedas de pie» se cumple en vacío con una sola rueda; si sumara entonces,
  al agregar la octava rueda acostada el progreso bajaría.
- Un objetivo de conteo suma en proporción a lo que ya hay: con 4 de 8 ruedas
  vale la mitad de su peso, en lugar de quedarse en cero hasta la última.
"""
from typing import Iterable, Mapping, Optional, Set

from ..models import TargetDefinition, ValidationResult


def desbloqueados(targets: Iterable[TargetDefinition], results: Mapping[str, ValidationResult]) -> Set[str]:
    """Ids de los objetivos cuyos requisitos, directos e indirectos, ya están cumplidos."""
    por_id = {t.id: t for t in targets}
    memoria: dict = {}

    def libre(tid: str, camino: frozenset = frozenset()) -> bool:
        if tid in memoria:
            return memoria[tid]
        objetivo = por_id.get(tid)
        if objetivo is None or tid in camino:  # requisito desconocido o ciclo: no bloquea
            return True
        valor = True
        for req in objetivo.requires:
            if req not in por_id:
                continue
            resultado = results.get(req)
            if not (resultado is not None and resultado.passed is True and libre(req, camino | {tid})):
                valor = False
                break
        memoria[tid] = valor
        return valor

    return {tid for tid in por_id if libre(tid)}


def avance_parcial(result: Optional[ValidationResult]) -> float:
    """Parte cumplida (0 a 1) de un objetivo de conteo que todavía no pasa; 0 si no es de conteo."""
    if result is None or result.passed is not False:
        return 0.0
    detalles = result.details or {}
    esperado = detalles.get("expected")
    minimo = esperado.get("min") if isinstance(esperado, dict) else esperado
    hallados = detalles.get("found")
    if not isinstance(minimo, int) or isinstance(minimo, bool) or minimo <= 0:
        return 0.0
    if not isinstance(hallados, int) or isinstance(hallados, bool) or hallados <= 0 or hallados >= minimo:
        return 0.0  # de más (pasó el máximo) no es avance parcial
    return hallados / minimo


def calculate_progress(
    targets: Iterable[TargetDefinition],
    results: Mapping[str, ValidationResult],
) -> float:
    targets = tuple(targets)
    obligatorios = tuple(t for t in targets if not t.optional)
    total_weight = sum(max(0.0, target.weight) for target in obligatorios)

    if total_weight <= 0:
        return 0.0

    libres = desbloqueados(targets, results)
    earned = 0.0

    for target in obligatorios:
        if target.id not in libres:
            continue
        result = results.get(target.id)
        peso = max(0.0, target.weight)
        if result is not None and result.passed is True:
            earned += peso
        else:
            earned += peso * avance_parcial(result)

    return round((earned / total_weight) * 100.0, 2)
