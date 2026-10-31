"""Ramas: variantes del motor sin versiones nuevas (``amatista.rama/1``).

Una rama es un archivo JSON que dice **qué corazón armar**: para qué
programa, con qué extensiones, con qué umbrales del andamio y si la señal se
hace sola. Una rama puede **heredar** de otra y cambiar solo lo que la
distingue. Así «Blender para principiantes», «Blender modo reto» o «A-Frame
en el celular» son ramas del mismo corazón 1.x, no versiones 8, 9 y 10.

.. code-block:: json

    {"formato": "amatista.rama/1", "id": "blender-reto", "hereda": "blender-principiante",
     "nombre": "Blender · modo reto", "quitar": ["vistas-espaciales"],
     "andamio": {"senalar": 0, "recordar": 0, "reto": 1}, "senal_sola": false}

Las ramas del repositorio viven en ``practices/ramas/``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from . import andamiaje, extensiones as _ext
from .adaptador import Adaptador, Capacidades, Perfil
from .director import Director

FORMATO = "amatista.rama/1"


class ErrorRama(ValueError):
    pass


@dataclass(frozen=True)
class Rama:
    id: str
    software: str
    nombre: str = ""
    descripcion: str = ""
    hereda: str = ""
    extensiones: Tuple[str, ...] = ()
    quitar: Tuple[str, ...] = ()
    andamio: Mapping[str, Any] = field(default_factory=dict)
    senal_sola: Optional[bool] = None

    @property
    def umbrales(self) -> andamiaje.Umbrales:
        return andamiaje.Umbrales.desde(self.andamio)


def rama_desde_dict(datos: Mapping[str, Any]) -> Rama:
    if not isinstance(datos, Mapping) or datos.get("formato") != FORMATO:
        raise ErrorRama(f"Una rama empieza con \"formato\": \"{FORMATO}\"")
    if not datos.get("id"):
        raise ErrorRama("La rama necesita un id")
    desconocidas = sorted(set(datos.get("andamio") or {}) - set(andamiaje.Umbrales.__dataclass_fields__))
    if desconocidas:
        raise ErrorRama(f"Rama «{datos['id']}»: el andamio no tiene {', '.join(desconocidas)}")
    sola = datos.get("senal_sola")
    return Rama(id=str(datos["id"]), software=str(datos.get("software", "")), nombre=str(datos.get("nombre", "")),
                descripcion=str(datos.get("descripcion", "")), hereda=str(datos.get("hereda", "")),
                extensiones=tuple(datos.get("extensiones") or ()), quitar=tuple(datos.get("quitar") or ()),
                andamio=dict(datos.get("andamio") or {}), senal_sola=None if sola is None else bool(sola))


def leer_rama(ruta) -> Rama:
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ErrorRama(f"No se pudo leer {ruta}: {error}") from error
    return rama_desde_dict(datos)


def cargar_ramas(carpeta) -> Dict[str, Rama]:
    salida: Dict[str, Rama] = {}
    for ruta in sorted(Path(carpeta).glob("*.json")):
        r = leer_rama(ruta)
        if r.id in salida:
            raise ErrorRama(f"Dos ramas con el id «{r.id}»")
        salida[r.id] = r
    return salida


def resolver(rama: Rama, todas: Mapping[str, Rama]) -> Rama:
    """La rama con lo heredado ya aplicado (de la raíz a la hoja)."""
    cadena, vista = [], set()
    actual: Optional[Rama] = rama
    while actual is not None:
        if actual.id in vista:
            raise ErrorRama(f"La rama «{rama.id}» hereda en círculo")
        vista.add(actual.id)
        cadena.append(actual)
        if not actual.hereda:
            break
        if actual.hereda not in todas:
            raise ErrorRama(f"La rama «{actual.id}» hereda de «{actual.hereda}», que no existe")
        actual = todas[actual.hereda]
    software, exts, andamio, sola, nombre, desc = "", [], {}, None, "", ""
    for r in reversed(cadena):
        software = r.software or software
        exts = [e for e in exts if e not in r.quitar] + [e for e in r.extensiones if e not in exts]
        andamio.update(r.andamio)
        sola = r.senal_sola if r.senal_sola is not None else sola
        nombre, desc = r.nombre or nombre, r.descripcion or desc
    return Rama(id=rama.id, software=software, nombre=nombre, descripcion=desc, extensiones=tuple(exts),
                andamio=andamio, senal_sola=sola)


def revisar(todas: Mapping[str, Rama]) -> Tuple[str, ...]:
    """Problemas de un conjunto de ramas (herencia, extensiones y programas que no existen)."""
    from . import perfiles

    problemas = []
    disponibles = set(_ext.disponibles())
    for r in todas.values():
        try:
            final = resolver(r, todas)
        except ErrorRama as error:
            problemas.append(str(error))
            continue
        faltan = [e for e in final.extensiones if e not in disponibles]
        if faltan:
            problemas.append(f"Rama «{r.id}»: no hay extensiones {', '.join(faltan)}")
        if perfiles.perfil(final.software) is None:
            problemas.append(f"Rama «{r.id}»: no hay perfil para el programa «{final.software}»")
    return tuple(problemas)


def armar_extensiones(rama: Rama, extra: Iterable[_ext.Extension] = ()) -> _ext.Extensiones:
    exts = _ext.Extensiones()
    for ext_id in rama.extensiones:
        exts.instalar(_ext.crear(ext_id))
    for e in extra:
        exts.instalar(e)
    return exts


def crear_director(practica, rama: Rama, *, adaptador: Optional[Adaptador] = None, perfil: Optional[Perfil] = None,
                   capacidades: Optional[Capacidades] = None, todas: Optional[Mapping[str, Rama]] = None,
                   extra: Sequence[_ext.Extension] = (), historial: Optional[andamiaje.Historial] = None,
                   guion=None, ahora: float = 0.0) -> Director:
    """El director de una práctica según la rama (con su herencia resuelta)."""
    from . import perfiles

    final = resolver(rama, todas or {rama.id: rama})
    perfil = perfil or (adaptador.perfil if adaptador is not None else None) or perfiles.perfil(final.software)
    if perfil is None:
        raise ErrorRama(f"No hay perfil para «{final.software}»")
    capacidades = capacidades or (adaptador.capacidades() if adaptador is not None else Capacidades(perfil.software))
    return Director(practica, perfil, capacidades, guion=guion, extensiones=armar_extensiones(final, extra),
                    historial=historial, umbrales=final.umbrales,
                    senal_sola=True if final.senal_sola is None else final.senal_sola, ahora=ahora)


__all__ = ["ErrorRama", "FORMATO", "Rama", "armar_extensiones", "cargar_ramas", "crear_director", "leer_rama",
           "rama_desde_dict", "resolver", "revisar"]
