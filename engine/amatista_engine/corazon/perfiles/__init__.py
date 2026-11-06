"""Perfiles de interfaz: dónde está cada herramienta en nuestro software libre 3D.

Un perfil es solo datos (``adaptador.Perfil``): se prueba sin el programa y
lo usa el servidor para escribir las mismas frases que verá el alumno. Para
sumar otro software libre se escribe su perfil aquí (o se trae en una extensión
con el punto ``perfiles``) y su adaptador dentro del programa.

Estado de cada uno:

- ``blender``: estable (sale de la tabla del motor 7, ``guion/donde.py``).
- ``aframe``: estable para el Motor Web de las lecciones (arrastrar, tocar, zonas).
"""
from __future__ import annotations

from typing import Dict, Optional

from ..adaptador import Perfil

_PERFILES: Dict[str, Perfil] = {}


def registrar(perfil: Perfil, reemplazar: bool = False) -> None:
    if perfil.software in _PERFILES and not reemplazar:
        raise ValueError(f"Ya hay un perfil para {perfil.software}")
    _PERFILES[perfil.software] = perfil


def perfil(software: str) -> Optional[Perfil]:
    _cargar()
    return _PERFILES.get(software)


def todos() -> Dict[str, Perfil]:
    _cargar()
    return dict(_PERFILES)


_CARGADOS = False


def _cargar() -> None:
    global _CARGADOS
    if _CARGADOS:
        return
    _CARGADOS = True
    from . import aframe, blender

    for modulo in (blender, aframe):
        if modulo.PERFIL.software not in _PERFILES:
            _PERFILES[modulo.PERFIL.software] = modulo.PERFIL


__all__ = ["perfil", "registrar", "todos"]
