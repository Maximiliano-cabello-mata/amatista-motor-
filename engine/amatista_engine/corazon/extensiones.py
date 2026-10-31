"""Extensiones: cómo entra un comportamiento nuevo sin tocar el corazón.

Hasta el motor 7, cada idea nueva se escribía dentro del motor o del add-on
y obligaba a una versión nueva (3.2, 3.3, … 6.2, 7). Desde el corazón, una
idea nueva es una **extensión**: un objeto con un id, su propia versión y lo
que aporta en alguno de estos puntos:

=================  ==========================================================  ====================================
punto              qué recibe                                                  qué devuelve
=================  ==========================================================  ====================================
``validadores``    el registro de validadores                                  nada (registra los suyos)
``pasos``          (paso, práctica)                                            el paso, cambiado o igual
``pistas``         (paso, avance, contexto)                                    una ``Pista`` extra o None
``senal``          (paso, lugar, señal propuesta, contexto)                    otra ``Senal`` o None (se queda)
``andamio``        (herramienta, escalón, historial, contexto)                 otro escalón o None
``turno``          el ``Turno`` antes de mostrarse                             el turno, cambiado o igual
``observadores``   (evento, turno)                                             nada (telemetría, latido, logros)
``perfiles``       —                                                           un ``Perfil`` de otro programa
=================  ==========================================================  ====================================

Una extensión declara qué contrato necesita (``requiere="1"``); si el
corazón es otro, no se instala y se dice por qué. Si una extensión falla
al correr, el corazón la salta y sigue: nunca rompe el programa del alumno.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from .contrato import CONTRATO

PUNTOS = ("validadores", "pasos", "pistas", "senal", "andamio", "turno", "observadores", "perfiles")


def _mayor(contrato: str) -> str:
    return contrato.rsplit("/", 1)[-1].split(".", 1)[0]


@dataclass(frozen=True)
class Extension:
    id: str
    version: str = "1.0.0"
    nombre: str = ""
    descripcion: str = ""
    requiere: str = "1"  # versión mayor del contrato amatista.corazon
    prioridad: int = 100  # menor corre antes
    aporta: Mapping[str, Sequence[Any]] = field(default_factory=dict)

    def de(self, punto: str) -> Tuple[Any, ...]:
        valor = self.aporta.get(punto, ())
        if callable(valor) or not isinstance(valor, (list, tuple)):
            return (valor,)
        return tuple(valor)


class ErrorExtension(ValueError):
    pass


@dataclass
class Extensiones:
    """Las extensiones instaladas en un corazón, en orden de prioridad."""

    _lista: List[Extension] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)  # lo que falló al correr (para el modo desarrollador)

    def instalar(self, ext: Extension) -> None:
        if not ext.id:
            raise ErrorExtension("La extensión necesita un id")
        if any(e.id == ext.id for e in self._lista):
            raise ErrorExtension(f"La extensión «{ext.id}» ya está instalada")
        if ext.requiere != _mayor(CONTRATO):
            raise ErrorExtension(f"«{ext.id}» pide amatista.corazon/{ext.requiere} y este corazón es {CONTRATO}")
        desconocidos = sorted(set(ext.aporta) - set(PUNTOS))
        if desconocidos:
            raise ErrorExtension(f"«{ext.id}» aporta a puntos que no existen: {', '.join(desconocidos)}")
        self._lista.append(ext)
        self._lista.sort(key=lambda e: (e.prioridad, e.id))

    def quitar(self, ext_id: str) -> None:
        self._lista = [e for e in self._lista if e.id != ext_id]

    def ids(self) -> Tuple[str, ...]:
        return tuple(e.id for e in self._lista)

    def __contains__(self, ext_id: str) -> bool:
        return ext_id in self.ids()

    def de(self, punto: str) -> Tuple[Tuple[str, Any], ...]:
        return tuple((e.id, a) for e in self._lista for a in e.de(punto) if a is not None)

    def correr(self, punto: str, *args: Any) -> List[Any]:
        """Corre todas las de un punto y devuelve lo que devolvieron (sin las que fallaron)."""
        salida = []
        for ext_id, funcion in self.de(punto):
            try:
                salida.append(funcion(*args))
            except Exception as error:  # noqa: BLE001 - una extensión nunca rompe el corazón
                self.errores.append(f"{ext_id} › {punto}: {error}")
        return salida

    def encadenar(self, punto: str, valor: Any, *args: Any) -> Any:
        """Cada una recibe lo que dejó la anterior (pasos, turno). None = lo deja igual."""
        for ext_id, funcion in self.de(punto):
            try:
                nuevo = funcion(valor, *args)
            except Exception as error:  # noqa: BLE001
                self.errores.append(f"{ext_id} › {punto}: {error}")
                continue
            if nuevo is not None:
                valor = nuevo
        return valor

    def primera(self, punto: str, *args: Any) -> Any:
        """La primera que devuelve algo distinto de None (senal, andamio)."""
        for ext_id, funcion in self.de(punto):
            try:
                valor = funcion(*args)
            except Exception as error:  # noqa: BLE001
                self.errores.append(f"{ext_id} › {punto}: {error}")
                continue
            if valor is not None:
                return valor
        return None

    def resumen(self) -> List[Dict[str, Any]]:
        return [{"id": e.id, "version": e.version, "nombre": e.nombre or e.id, "puntos": sorted(e.aporta)}
                for e in self._lista]


# --- Extensiones que vienen con el corazón -------------------------------------------------------
_INCLUIDAS: Dict[str, Callable[[], Extension]] = {}


def incluida(ext_id: str) -> Callable[[Callable[[], Extension]], Callable[[], Extension]]:
    def poner(fabrica: Callable[[], Extension]) -> Callable[[], Extension]:
        _INCLUIDAS[ext_id] = fabrica
        return fabrica

    return poner


def crear(ext_id: str) -> Extension:
    from . import incluidas  # noqa: F401 - registra las fábricas

    if ext_id not in _INCLUIDAS:
        raise ErrorExtension(f"No hay una extensión incluida con id «{ext_id}» (hay: {', '.join(sorted(_INCLUIDAS))})")
    return _INCLUIDAS[ext_id]()


def disponibles() -> Tuple[str, ...]:
    from . import incluidas  # noqa: F401

    return tuple(sorted(_INCLUIDAS))


__all__ = ["ErrorExtension", "Extension", "Extensiones", "PUNTOS", "crear", "disponibles", "incluida"]
