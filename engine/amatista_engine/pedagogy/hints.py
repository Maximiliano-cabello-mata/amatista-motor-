"""Pistas progresivas (sección 20) y su registro.

Las pistas de un objetivo se revelan de una en una (nivel 1, 2, 3...). El
estado es un dict {target_id: nivel revelado}: el add-on lo guarda en la
escena y el resumen que se envía a Amatista cuenta cuántas se usaron.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from ..models import Hint, PracticeDefinition

# A partir de este nivel la pista ya es el paso a paso: cuenta como «con guía».
NIVEL_GUIA = 3


@dataclass(frozen=True)
class HintReveal:
    target_id: str
    hint: Optional[Hint]
    level: int  # nivel revelado tras esta petición
    total: int  # pistas disponibles en el objetivo

    @property
    def exhausted(self) -> bool:
        return self.level >= self.total


def revealed(practice: PracticeDefinition, state: Mapping[str, int], target_id: str):
    """Pistas ya reveladas de un objetivo, en orden."""
    target = practice.target(target_id)
    if target is None:
        return ()
    return tuple(h for h in target.hints if h.level <= int(state.get(target_id, 0)))


def next_hint(practice: PracticeDefinition, state: Dict[str, int], target_id: str) -> HintReveal:
    """Revela la siguiente pista del objetivo y actualiza `state`.

    Si ya no quedan, devuelve la última (sin subir el contador).
    """
    target = practice.target(target_id)
    if target is None or not target.hints:
        return HintReveal(target_id, None, 0, 0)
    pistas = sorted(target.hints, key=lambda h: h.level)
    actual = int(state.get(target_id, 0))
    siguiente = next((h for h in pistas if h.level > actual), None)
    if siguiente is None:
        return HintReveal(target_id, pistas[-1], actual, len(pistas))
    state[target_id] = siguiente.level
    return HintReveal(target_id, siguiente, siguiente.level, len(pistas))


def hints_used(state: Mapping[str, int]) -> int:
    return sum(max(0, int(n)) for n in state.values())


def max_level(state: Mapping[str, int]) -> int:
    return max((int(n) for n in state.values()), default=0)
