"""Motor 7 · Guion: la práctica paso a paso, avanzando por el resultado real.

Lo que se rehízo (pedido del creador, 31 de octubre de 2026): el add-on
decía «la herramienta que brilla a la izquierda» cuando no brillaba nada,
daba instrucciones vagas, encimaba tarjetas y, con el tren terminado, el
alumno no avanzaba porque la pista lo mandaba a otra herramienta. Las
simulaciones (addon/tests/simular_alumnos.py) lo midieron: con el motor 6.2
solo 24 de 100 alumnos simulados terminaban el tren.

Tres piezas, sin bpy:

- ``pasos``: el guion (qué hacer en cada paso, con verbo y pieza).
- ``avance``: qué está hecho según el reporte del motor; nada más decide.
- ``pistas`` y ``donde``: qué falta, dónde está de verdad la herramienta y
  cómo se hace, del paso que toca.
"""
from . import donde
from .avance import ACTUAL, HECHO, PENDIENTE, Avance, EstadoPaso, avanzar
from .pasos import Guion, Paso, guion_de_practica, resumen
from .pistas import COMO, DONDE, QUE_FALTA, TITULOS, Pista, pista

VERSION = "7.0.0"

__all__ = [
    "ACTUAL", "Avance", "COMO", "DONDE", "EstadoPaso", "Guion", "HECHO", "PENDIENTE", "Paso", "Pista", "QUE_FALTA",
    "TITULOS", "VERSION", "avanzar", "donde", "guion_de_practica", "pista", "resumen",
]
