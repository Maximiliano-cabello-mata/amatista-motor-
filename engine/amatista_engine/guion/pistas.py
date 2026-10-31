"""Las pistas del paso que toca: tres, claras y siempre de ESE paso (motor 7).

1. **Qué falta**: lo que el motor ve en la escena para este paso.
2. **Dónde está**: el lugar real de la herramienta (donde.py) y su atajo,
   con los menús en el idioma de Blender. El add-on, además, la señala de
   verdad si puede (la deja elegida, abre el menú o la pestaña).
3. **Cómo se hace**: las pistas del autor y los micro pasos con teclas.

Sin freno y sin escalera escondida: el alumno pide la que necesita. Ningún
texto de aquí dice que algo brilla.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from . import donde as _donde
from .avance import Avance
from .pasos import Guion

QUE_FALTA, DONDE, COMO = 1, 2, 3
TITULOS = {QUE_FALTA: "¿Qué falta?", DONDE: "¿Dónde está?", COMO: "¿Cómo se hace?"}


@dataclass(frozen=True)
class Pista:
    nivel: int
    titulo: str
    texto: str
    herramienta: str = ""
    teclas: Tuple[str, ...] = ()


def pista(guion: Guion, avance: Avance, nivel: int, idioma: str = "") -> Optional[Pista]:
    """La pista de ese nivel para el paso que toca (None si no hay paso)."""
    if avance is None or avance.completo or not avance.actual:
        return None
    paso = guion.paso(avance.actual)
    if paso is None:
        return None
    from .. import terminos

    if nivel == QUE_FALTA:
        texto = avance.pausa or avance.por_que or paso.listo
        return Pista(QUE_FALTA, TITULOS[QUE_FALTA], terminos.menus(texto, idioma or None), paso.herramienta)
    if nivel == DONDE:
        d = _donde.de(paso.herramienta)
        if d is None:
            texto = "Esto se hace con lo que ya tienes en la vista 3D: " + (paso.como[0] if paso.como else paso.haz)
        else:
            texto = _donde.frase(d, idioma, paso.primitiva)
        return Pista(DONDE, TITULOS[DONDE], texto, paso.herramienta)
    if nivel == COMO:
        lineas = list(paso.como) or [paso.haz]
        return Pista(COMO, TITULOS[COMO], terminos.menus(" ".join(lineas[:3]), idioma or None), paso.herramienta,
                     paso.teclas)
    return None


__all__ = ["COMO", "DONDE", "Pista", "QUE_FALTA", "TITULOS", "pista"]
