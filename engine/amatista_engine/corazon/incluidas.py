"""Extensiones que vienen con el corazón (y sirven de ejemplo para escribir otras).

Cada una es pequeña y se apoya en un hallazgo de la investigación:

- ``vistas-espaciales``: la habilidad espacial predice cómo se aprende CAD y
  se entrena. En los pasos de mover, girar o escalar agrega la pista
  «¿Desde otro ángulo?» con las vistas del programa (si su perfil las tiene).
- ``rescate-tras-tropiezos``: tres tropiezos seguidos (pasos deshechos o la
  última pista agotada) bajan el andamio a «mostrar», como el termómetro de
  ánimo del motor 6.2, sin esperar a la próxima práctica.
"""
from __future__ import annotations

from ..guion import Pista
from . import andamiaje
from .extensiones import Extension, incluida

ESPACIALES = ("transform.move", "transform.rotate", "transform.scale")


def _desde_otro_angulo(paso, avance, contexto):
    """Pista extra para pasos espaciales (mover, girar, escalar): mirar la pieza desde otra vista con el teclado numérico."""
    if paso is None or paso.herramienta not in ESPACIALES:
        return None
    perfil = contexto.get("perfil")
    vistas = perfil.lugar("view.numpad") if perfil is not None else None
    if vistas is None or not vistas.atajo:
        return None
    return Pista(4, "¿Desde otro ángulo?",
                 f"Antes de mover más, mira tu pieza desde otro lado ({vistas.atajo}). Desde un solo ángulo "
                 "las piezas parecen tocarse aunque estén lejos.", "view.numpad")


@incluida("vistas-espaciales")
def vistas_espaciales() -> Extension:
    """Extensión «vistas-espaciales»: añade la pista de mirar desde otro ángulo."""
    return Extension("vistas-espaciales", "1.0.0", "Vistas espaciales",
                     "Pista extra para mirar desde otro ángulo en los pasos de mover, girar y escalar.",
                     aporta={"pistas": [_desde_otro_angulo]})


def _rescate(herramienta, escalon, historial, contexto):
    """Tras 3 tropiezos seguidos vuelve al escalón MOSTRAR (enseñar dónde está la herramienta); None si no aplica."""
    if contexto.get("tropiezos_seguidos", 0) >= 3 and escalon != andamiaje.MOSTRAR:
        return andamiaje.MOSTRAR
    return None


@incluida("rescate-tras-tropiezos")
def rescate_tras_tropiezos() -> Extension:
    """Extensión «rescate-tras-tropiezos»: sube la ayuda cuando el alumno tropieza varias veces seguidas."""
    return Extension("rescate-tras-tropiezos", "1.0.0", "Rescate tras tropiezos",
                     "Tres tropiezos seguidos vuelven a mostrar la herramienta.", prioridad=50,
                     aporta={"andamio": [_rescate]})


__all__ = ["rescate_tras_tropiezos", "vistas_espaciales"]
