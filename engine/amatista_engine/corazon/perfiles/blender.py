"""Perfil de Blender (4.2 a 5.x): sale de la tabla del motor 7 (``guion/donde.py``).

Esa tabla sigue siendo la única fuente para no tener dos listas que se
contradigan; aquí solo se traduce al contrato del corazón.
"""
from __future__ import annotations

from ... import terminos
from ...guion import donde as _donde
from ..adaptador import Perfil
from ..contrato import Lugar


def _lugar(d) -> Lugar:
    return Lugar(herramienta=d.herramienta, nombre=d.nombre, lugar=d.lugar, tipo=d.tipo, ruta=d.ruta,
                 atajo=d.atajo, objetivo=d.objetivo, modo=d.modo)


def _traducir(texto: str, idioma: str = "") -> str:
    return terminos.menus(texto, idioma or None)


PERFIL = Perfil(
    software="blender",
    nombre="Blender",
    lugares={clave: _lugar(d) for clave, d in _donde.TABLA.items()},
    por_validador=dict(_donde.POR_VALIDADOR),
    mallas=dict(_donde.MALLAS),
    traducir=_traducir,
)

__all__ = ["PERFIL"]
