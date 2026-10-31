"""El avance: qué pasos ya están hechos según la escena real (motor 7).

Una sola regla: **avanza el resultado**. Un paso está hecho cuando su
objetivo pasa en el reporte del motor, venga de donde venga: con la
herramienta que se sugirió, con otra, en otro orden o todo de una vez.
Nada depende de qué herramienta se usó, de si se leyó una ficha, de un
temporizador ni de lo que diga la plataforma. La práctica está terminada
cuando el reporte dice ``completed`` y en ese mismo instante.

El paso «actual» es el primero del guion que no está hecho (el guion ya
viene ordenado por ``requires``, así que siempre se puede hacer). Lo que se
le dice al alumno sale del mensaje de **ese** objetivo: nunca de otra pieza.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .pasos import Guion, Paso

HECHO, ACTUAL, PENDIENTE = "hecho", "actual", "pendiente"


@dataclass(frozen=True)
class EstadoPaso:
    id: str
    estado: str
    mensaje: str = ""


@dataclass(frozen=True)
class Avance:
    practica_id: str
    pasos: Tuple[EstadoPaso, ...]
    completo: bool
    hechos: int
    total: int
    actual: Optional[str] = None  # id del paso que toca (None: terminado)
    por_que: str = ""  # por qué el paso que toca todavía no está (el mensaje de su objetivo)
    recien: Tuple[str, ...] = ()  # pasos que se cumplieron con el último cambio
    deshechos: Tuple[str, ...] = ()  # pasos que estaban hechos y dejaron de estarlo
    pausa: str = ""  # un vigilante pausó el progreso: qué arreglar

    def estado(self, paso_id: str) -> str:
        return next((p.estado for p in self.pasos if p.id == paso_id), PENDIENTE)

    @property
    def progreso(self) -> float:
        return 100.0 if self.completo else (100.0 * self.hechos / self.total if self.total else 0.0)


def avanzar(guion: Guion, reporte, anterior: Optional[Avance] = None) -> Avance:
    """El avance del guion con el reporte de ahora (y el de antes, para saber qué cambió)."""
    resultados = {r.target_id: r for r in getattr(reporte, "results", ()) or ()}
    completo = bool(getattr(reporte, "completed", False))
    estados = []
    actual: Optional[Paso] = None
    for p in guion.pasos:
        r = resultados.get(p.id)
        hecho = completo or bool(r is not None and r.passed)
        if hecho:
            estados.append(EstadoPaso(p.id, HECHO, r.message if r is not None else ""))
        elif actual is None:
            actual = p
            estados.append(EstadoPaso(p.id, ACTUAL, r.message if r is not None else ""))
        else:
            estados.append(EstadoPaso(p.id, PENDIENTE, r.message if r is not None else ""))
    antes = {e.id: e.estado for e in (anterior.pasos if anterior is not None and anterior.practica_id == guion.practica_id
                                      else ())}
    recien = tuple(e.id for e in estados if e.estado == HECHO and antes and antes.get(e.id) != HECHO)
    deshechos = tuple(e.id for e in estados if e.estado != HECHO and antes.get(e.id) == HECHO)
    por_que = ""
    if actual is not None:
        r = resultados.get(actual.id)
        por_que = (r.message if r is not None and r.message else "") or actual.listo
    pausa = ""
    if getattr(reporte, "paused_by", None):
        g = next((r for r in getattr(reporte, "guards", ()) if r.target_id == reporte.paused_by), None)
        pausa = g.message if g is not None else "Algo se rompió en la escena: deshaz el último cambio (Ctrl + Z)."
    return Avance(
        practica_id=guion.practica_id, pasos=tuple(estados), completo=completo,
        hechos=sum(1 for e in estados if e.estado == HECHO), total=len(estados),
        actual=None if completo else (actual.id if actual is not None else None), por_que="" if completo else por_que,
        recien=recien, deshechos=deshechos, pausa=pausa,
    )


__all__ = ["ACTUAL", "Avance", "EstadoPaso", "HECHO", "PENDIENTE", "avanzar"]
