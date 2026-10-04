"""Grafo de la práctica (sección 23): dependencias y objetivo actual.

Un objetivo puede declarar "requires": [ids]. El orden de presentación
respeta esas dependencias y, entre objetivos libres, el orden del JSON.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..models import (
    ACTUAL,
    BLOQUEADO,
    COMPLETADO,
    DESCONOCIDO,
    PENDIENTE,
    TargetDefinition,
    TargetStatus,
    ValidationResult,
)


def find_cycle(targets: Sequence[TargetDefinition]) -> Optional[List[str]]:
    """Primer ciclo de dependencias encontrado (lista de ids) o None."""
    requisitos = {t.id: [r for r in t.requires if r] for t in targets}
    estado: Dict[str, int] = {}
    pila: List[str] = []

    def visitar(nodo: str) -> Optional[List[str]]:
        estado[nodo] = 1
        pila.append(nodo)
        for siguiente in requisitos.get(nodo, ()):
            if siguiente not in requisitos:
                continue
            if estado.get(siguiente) == 1:
                return pila[pila.index(siguiente):] + [siguiente]
            if estado.get(siguiente) is None:
                ciclo = visitar(siguiente)
                if ciclo:
                    return ciclo
        pila.pop()
        estado[nodo] = 2
        return None

    for target in targets:
        if estado.get(target.id) is None:
            ciclo = visitar(target.id)
            if ciclo:
                return ciclo
    return None


def ordered(targets: Sequence[TargetDefinition]) -> Tuple[TargetDefinition, ...]:
    """Orden topológico estable. Si hay un ciclo (el compilador lo rechaza) se usa el orden del JSON."""
    if find_cycle(targets):
        return tuple(targets)
    pendientes = list(targets)
    colocados: List[TargetDefinition] = []
    hechos = set()
    while pendientes:
        for target in pendientes:
            if all(r in hechos or r not in {t.id for t in targets} for r in target.requires):
                colocados.append(target)
                hechos.add(target.id)
                pendientes.remove(target)
                break
    return tuple(colocados)


def statuses(
    targets: Sequence[TargetDefinition],
    results: Mapping[str, ValidationResult],
) -> Tuple[Tuple[TargetStatus, ...], Optional[str]]:
    """Estado de cada objetivo y el id del objetivo actual (o None si no queda ninguno)."""
    aprobados = {tid for tid, r in results.items() if r.passed is True}
    actual: Optional[str] = None
    pasos = []
    for target in ordered(targets):
        r = results.get(target.id)
        if r is not None and r.passed is None:
            estado = DESCONOCIDO
        elif r is not None and r.passed:
            estado = COMPLETADO
        elif any(req not in aprobados for req in target.requires):
            estado = BLOQUEADO
        elif actual is None and not target.optional:
            estado = ACTUAL
            actual = target.id
        else:
            estado = PENDIENTE
        pasos.append(
            TargetStatus(
                target_id=target.id,
                title=target.title or target.id,
                status=estado,
                passed=r.passed if r else None,
                message=r.message if r else "",
                weight=target.weight,
                optional=target.optional,
                hints_available=len(target.hints),
            )
        )
    if actual is None:
        # Sin obligatorios libres: el primer opcional pendiente pasa a actual.
        for indice, paso in enumerate(pasos):
            if paso.status == PENDIENTE:
                pasos[indice] = TargetStatus(**{**paso.__dict__, "status": ACTUAL})
                actual = paso.target_id
                break
    return tuple(pasos), actual
