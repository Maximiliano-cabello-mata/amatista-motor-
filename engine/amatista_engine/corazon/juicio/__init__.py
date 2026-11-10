"""Juicio del Corazón: compara lo que hay con el ejemplo y decide qué decirle al alumno.

Tres módulos, cada uno con una sola tarea y sin estado:

- ``plano``       lo que se espera: las piezas del ejemplo, con sus medidas.
- ``diferencia``  lo que hay contra lo que se espera, pieza por pieza y en la
                  escala del alumno (su tren puede ser el doble de grande).
- ``decision``    una sola indicación, elegida por reglas en orden fijo.

Es Python puro y barato (una pasada por los objetos): se puede llamar en cada
cambio de la escena. No reemplaza a los validadores: cuando las piezas ya
están bien, cede la palabra al reporte del motor (guardar, materiales…).

    juicio = juzgar(practica, escena, reporte)
    juicio.decision.texto      # «Cylinder» (Rueda) mide 0.45 m en Y; en tu figura…
    juicio.avance              # (piezas bien, piezas del ejemplo)
"""
from .decision import AGREGAR, AJUSTAR_TAMANO, GIRAR, LISTO, SEGUIR, Decision, decidir
from .diferencia import BIEN, FALTA, GIRADA, TAMANO, Ajuste, Diferencia, EstadoPieza, comparar
from .plano import PiezaEsperada, Plano, plano_de

__all__ = ["AGREGAR", "AJUSTAR_TAMANO", "Ajuste", "BIEN", "Decision", "Diferencia", "EstadoPieza", "FALTA", "GIRADA",
           "GIRAR", "Juicio", "LISTO", "PiezaEsperada", "Plano", "SEGUIR", "TAMANO", "comparar", "decidir", "juzgar",
           "plano_de"]

from dataclasses import dataclass  # noqa: E402
from typing import Optional, Tuple  # noqa: E402


@dataclass(frozen=True)
class Juicio:
    diferencia: Diferencia
    decision: Decision

    @property
    def avance(self) -> Tuple[int, int]:
        return self.diferencia.bien, self.diferencia.total


def juzgar(practica, escena, reporte=None, tolerancia: Optional[float] = None) -> Optional[Juicio]:
    """El juicio de una escena contra el ejemplo de su práctica; None si la práctica no tiene piezas que comparar."""
    plano = plano_de(practica)
    if plano is None:
        return None
    diferencia = comparar(plano, escena, reporte, tolerancia)
    return Juicio(diferencia, decidir(diferencia, reporte))
