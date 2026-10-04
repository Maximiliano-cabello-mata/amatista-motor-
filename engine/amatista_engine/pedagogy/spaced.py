"""Repaso espaciado (motor v3): cajas de Leitner para las píldoras.

El plan de estudios pide aprendizaje espaciado: la práctica se reparte en
el tiempo en lugar de concentrarse. Cada píldora con pregunta (check) que
el alumno ya vio entra en la caja 1; si acierta en el repaso sube de caja
(el próximo repaso se aleja: 1, 3, 7, 14 y 30 días) y si falla vuelve a la
caja 1. Una práctica nueva pide repasar (practice/2 › review) las píldoras
de prácticas anteriores que ya tocan.

El estado es un dict JSON {"practica#pildora": {"box": 1, "due": epoch}}:
lo guarda el add-on en la carpeta del usuario y el servidor en
REPASOS_PILDORAS (sql/008). Funciones puras y deterministas (reciben `now`).
"""
from __future__ import annotations

from typing import Dict, Iterable, List

DIA = 86400.0
INTERVALOS_DIAS = (1, 3, 7, 14, 30)
CAJA_MAXIMA = len(INTERVALOS_DIAS)

Estado = Dict[str, Dict[str, float]]


def item_id(practice_id: str, pill_id: str) -> str:
    return f"{practice_id}#{pill_id}"


def introduce(state: Estado, item: str, now: float) -> Estado:
    """La primera vez que se ve una píldora: caja 1, repaso mañana."""
    if item in state:
        return state
    nuevo = dict(state)
    nuevo[item] = {"box": 1, "due": now + INTERVALOS_DIAS[0] * DIA}
    return nuevo


def answer(state: Estado, item: str, correct: bool, now: float) -> Estado:
    """Resultado de un repaso: sube de caja si acierta, vuelve a la 1 si falla."""
    actual = state.get(item, {"box": 1, "due": now})
    caja = min(int(actual.get("box", 1)) + 1, CAJA_MAXIMA) if correct else 1
    nuevo = dict(state)
    nuevo[item] = {"box": caja, "due": now + INTERVALOS_DIAS[caja - 1] * DIA}
    return nuevo


def due(state: Estado, now: float, items: Iterable[str] = ()) -> List[str]:
    """Ítems que ya toca repasar (de `items`, o todos), del más atrasado al más reciente."""
    candidatos = list(items) if items else list(state)
    vencidos = [i for i in candidatos if i in state and state[i].get("due", 0) <= now]
    return sorted(vencidos, key=lambda i: state[i]["due"])


def mastered(state: Estado) -> List[str]:
    return sorted(i for i, v in state.items() if int(v.get("box", 1)) >= CAJA_MAXIMA)
