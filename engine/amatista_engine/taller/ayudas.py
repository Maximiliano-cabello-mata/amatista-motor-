"""La escalera de pistas con freno (§6.4 de la investigación).

En los datos de ASSISTments, los alumnos que llegan a la pista final (la
respuesta) en más del 30 % de sus problemas no mejoran en el siguiente
intento (§4.3). Por eso la escalera sube de a un escalón, pide intentarlo
antes de dar las teclas y nunca hace el paso por el alumno:

1. **Qué**: lo que falta, sobre el modelo («la rueda todavía flota»).
2. **Con qué**: la herramienta se ilumina en la barra, sin la secuencia.
3. **Cómo**: la secuencia de teclas, después de 20 segundos de intentarlo o
   de un intento fallido (el freno).
4. **Mírame**: la demostración de esa pieza.

La fase de la habilidad decide hasta dónde llega: una habilidad nueva tiene
las teclas a un clic; una que ya hace sola, solo «qué falta»; en un reto no
hay más ayuda que esa.

Atascado: sin avance en 90 segundos o con tres deshacer seguidos, Amatista
ofrece (no impone) el siguiente escalón.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Tuple

from .modelo import ACOMPANADA, DOMINADA, NUEVA, SOLA

NINGUNA, QUE, CON_QUE, COMO, MIRAME = 0, 1, 2, 3, 4
NOMBRES = {NINGUNA: "", QUE: "Qué falta", CON_QUE: "Con qué", COMO: "Cómo", MIRAME: "Mírame"}
FRENO_SEGUNDOS = 20.0  # antes de las teclas hay que intentarlo
ATASCADO_SEGUNDOS = 90.0
ATASCADO_DESHACER = 3

# Hasta qué escalón llega la ayuda según la fase de la habilidad y si hay freno antes de «cómo».
TECHO = {NUEVA: MIRAME, ACOMPANADA: MIRAME, SOLA: CON_QUE, DOMINADA: QUE}
SIN_FRENO = {NUEVA}  # a una habilidad nueva las teclas se le dan a un clic


@dataclass(frozen=True)
class Escalera:
    """Las pistas de la actividad en curso."""

    nivel: int = NINGUNA  # el escalón más alto que ya se mostró
    inicio: float = 0.0  # cuándo empezó la actividad
    fallos: int = 0  # intentos fallidos (Comprobar sin éxito)
    ultimo_avance: float = 0.0  # cuándo se llenó la última pieza o se cumplió el último objetivo
    deshacer: int = 0  # Ctrl+Z seguidos
    techo: int = MIRAME
    freno: bool = True

    @property
    def nombre(self) -> str:
        return NOMBRES[self.nivel]


@dataclass(frozen=True)
class Pista:
    nivel: int
    titulo: str
    texto: str
    teclas: Tuple[str, ...] = ()
    herramientas: Tuple[str, ...] = ()
    demo: bool = False


def escalera_para(fase: str, ahora: float, reto: bool = False) -> Escalera:
    """La escalera vacía de una actividad nueva: su techo y si tiene freno."""
    techo = QUE if reto else TECHO.get(fase, MIRAME)
    return Escalera(inicio=ahora, ultimo_avance=ahora, techo=techo, freno=fase not in SIN_FRENO)


def puede_pedir(e: Escalera, ahora: float) -> Tuple[bool, float]:
    """(¿se puede pedir el siguiente escalón?, segundos que faltan por el freno)."""
    siguiente = e.nivel + 1
    if siguiente > e.techo:
        return False, 0.0
    if siguiente == COMO and e.freno and e.fallos == 0:
        falta = FRENO_SEGUNDOS - (ahora - e.inicio)
        if falta > 0:
            return False, falta
    return True, 0.0


def pedir_pista(e: Escalera, ahora: float) -> Tuple[Escalera, Optional[int], float]:
    """Sube un escalón si se puede: (escalera nueva, escalón mostrado o None, espera del freno)."""
    puede, espera = puede_pedir(e, ahora)
    if not puede:
        return e, None, espera
    nueva = replace(e, nivel=e.nivel + 1)
    return nueva, nueva.nivel, 0.0


def avance(e: Escalera, ahora: float) -> Escalera:
    """Se llenó una pieza o se cumplió un objetivo: el reloj de «atascado» vuelve a cero."""
    return replace(e, ultimo_avance=ahora, deshacer=0)


def fallo(e: Escalera) -> Escalera:
    return replace(e, fallos=e.fallos + 1)


def deshizo(e: Escalera) -> Escalera:
    return replace(e, deshacer=e.deshacer + 1)


def atascado(e: Escalera, ahora: float) -> bool:
    """¿Ofrecer la siguiente pista? (sin avance en 90 s o tres deshacer seguidos)."""
    if e.nivel >= e.techo:
        return False
    return ahora - e.ultimo_avance >= ATASCADO_SEGUNDOS or e.deshacer >= ATASCADO_DESHACER


def pista_para(nivel: int, habilidad, pieza=None) -> Pista:
    """El texto de un escalón. pieza: la PiezaRevisada que toca (molde) o None.

    habilidad: la Habilidad que se practica (sus teclas, su «cómo» y sus herramientas).
    """
    teclas = tuple(pieza.teclas) if pieza is not None and pieza.teclas else tuple(getattr(habilidad, "teclas", ()) or ())
    herramientas = tuple(getattr(habilidad, "herramientas", ()) or ())
    if nivel == QUE:
        texto = pieza.mensaje if pieza is not None and pieza.mensaje else (getattr(habilidad, "que", "") or "")
        return Pista(QUE, NOMBRES[QUE], texto)
    if nivel == CON_QUE:
        return Pista(CON_QUE, NOMBRES[CON_QUE], "Mira la herramienta que brilla en la barra de la izquierda.",
                     herramientas=herramientas)
    if nivel == COMO:
        como = getattr(habilidad, "como", "") or ""
        return Pista(COMO, NOMBRES[COMO], como or "Estas son las teclas.", teclas=teclas, herramientas=herramientas)
    if nivel == MIRAME:
        return Pista(MIRAME, NOMBRES[MIRAME], "Mira cómo se hace y después hazlo tú.", teclas=teclas,
                     herramientas=herramientas, demo=True)
    return Pista(NINGUNA, "", "")


__all__ = [
    "ATASCADO_DESHACER", "ATASCADO_SEGUNDOS", "COMO", "CON_QUE", "Escalera", "FRENO_SEGUNDOS", "MIRAME", "NINGUNA",
    "NOMBRES", "Pista", "QUE", "atascado", "avance", "deshizo", "escalera_para", "fallo", "pedir_pista", "pista_para",
    "puede_pedir",
]
