"""Cómo se conecta un programa 3D al corazón: el perfil y el adaptador.

Dos piezas por programa, separadas a propósito:

- **Perfil** (``Perfil``, datos puros, vive en ``corazon/perfiles/``): dónde
  está cada herramienta en la pantalla de ese programa, qué herramienta
  arregla cada validador y cómo se llaman las primitivas. Se prueba sin el
  programa y lo usa también el servidor.
- **Adaptador** (``Adaptador``, vive dentro del programa: el add-on de
  Blender, el Motor Web de A-Frame, un plug-in de Maya): toma la foto de la
  escena, hace las señales y comprueba si siguen siendo verdad.

Un adaptador nuevo hereda de ``AdaptadorBase`` y sobreescribe lo que su
programa sabe hacer; lo demás cae a «solo texto», que siempre es verdad.
``conformidad.revisar_adaptador`` dice si cumple el contrato.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Mapping, Optional, Tuple

from ..models import SceneState
from .contrato import DECIR, TIPOS_EVENTO, Lugar, ResultadoSenal, Senal

# Las herramientas que todo perfil debe saber ubicar (las del primer módulo de cualquier curso).
HERRAMIENTAS_BASE = ("object.add", "transform.move", "transform.rotate", "transform.scale", "file.save")


@dataclass(frozen=True)
class Capacidades:
    """Lo que un adaptador sabe hacer en su programa."""

    software: str
    version: str = ""
    senales: FrozenSet[str] = frozenset({DECIR})
    eventos: FrozenSet[str] = frozenset(TIPOS_EVENTO)
    idioma: str = "es"

    def puede(self, tipo_senal: str) -> bool:
        return tipo_senal == DECIR or tipo_senal in self.senales


@dataclass(frozen=True)
class Perfil:
    """La interfaz de un programa, en datos. ``estado``: estable | borrador."""

    software: str
    nombre: str
    lugares: Mapping[str, Lugar]
    por_validador: Mapping[str, str] = field(default_factory=dict)
    mallas: Mapping[str, str] = field(default_factory=dict)
    estado: str = "estable"
    # (texto, idioma) → texto con los menús como salen en pantalla; por defecto no cambia nada.
    traducir: Optional[Callable[[str, str], str]] = None

    def lugar(self, herramienta: str) -> Optional[Lugar]:
        if not herramienta:
            return None
        if herramienta in self.lugares:
            return self.lugares[herramienta]
        raiz = herramienta.split(".", 1)[0]
        return self.lugares.get(raiz)

    def herramienta_para(self, validador: str) -> str:
        return self.por_validador.get(validador, "")

    def en_pantalla(self, texto: str, idioma: str = "") -> str:
        if self.traducir is None or not texto:
            return texto
        try:
            return self.traducir(texto, idioma)
        except Exception:  # noqa: BLE001 - traducir nunca rompe el turno
            return texto

    def frase(self, lugar: Lugar, idioma: str = "", primitiva: str = "") -> str:
        """Dónde está y cómo se abre, en una frase que siempre es verdad."""
        ruta = lugar.ruta
        if primitiva and lugar.herramienta == "object.add" and ruta:
            ruta = f"{ruta} › {self.mallas.get(primitiva, primitiva.capitalize())}"
        if ruta:
            partes = [f"{ruta}, {lugar.lugar}"]
        elif lugar.lugar.startswith(("el ", "la ")):
            partes = [f"«{lugar.nombre}»: {lugar.lugar}"]
        else:
            partes = [f"«{lugar.nombre}» está {lugar.lugar}"]
        if lugar.atajo:
            partes.append(f"atajo: {lugar.atajo}")
        return self.en_pantalla(". ".join(partes) + ".", idioma)

    def faltan(self, herramientas: Tuple[str, ...] = HERRAMIENTAS_BASE) -> Tuple[str, ...]:
        return tuple(h for h in herramientas if self.lugar(h) is None)


class Adaptador:
    """Lo que el corazón le pide a un programa. Ver ``AdaptadorBase``."""

    id: str = ""
    perfil: Perfil

    def capacidades(self) -> Capacidades:  # pragma: no cover - interfaz
        raise NotImplementedError

    def capturar(self) -> SceneState:  # pragma: no cover - interfaz
        raise NotImplementedError

    def ejecutar(self, senal: Senal) -> ResultadoSenal:  # pragma: no cover - interfaz
        raise NotImplementedError

    def comprobar(self, senal: Senal) -> bool:  # pragma: no cover - interfaz
        raise NotImplementedError

    def herramienta_activa(self) -> str:  # pragma: no cover - interfaz
        raise NotImplementedError


class AdaptadorBase(Adaptador):
    """Un adaptador que solo sabe decir. Cada programa sobreescribe lo que puede hacer.

    ``hacer`` es un diccionario tipo de señal → función(senal) → ResultadoSenal y
    ``ver`` uno tipo → función(senal) → bool; así un adaptador agrega señales sin
    tocar este archivo.
    """

    def __init__(self, perfil: Perfil, *, id: str = "", version: str = "", idioma: str = "es") -> None:
        self.perfil = perfil
        self.id = id or perfil.software
        self._version = version
        self._idioma = idioma
        self.hacer: Dict[str, Callable[[Senal], ResultadoSenal]] = {}
        self.ver: Dict[str, Callable[[Senal], bool]] = {}

    def capacidades(self) -> Capacidades:
        return Capacidades(software=self.perfil.software, version=self._version,
                           senales=frozenset({DECIR, *self.hacer}), idioma=self._idioma)

    def capturar(self) -> SceneState:
        return SceneState(blender_version="", file_path="", file_saved=False)

    def ejecutar(self, senal: Senal) -> ResultadoSenal:
        if senal.tipo == DECIR:
            return ResultadoSenal(True)
        hacer = self.hacer.get(senal.tipo)
        if hacer is None:
            return ResultadoSenal(False, f"{self.perfil.nombre} no sabe hacer «{senal.tipo}» todavía")
        try:
            return hacer(senal)
        except Exception as error:  # noqa: BLE001 - una señal nunca rompe el programa
            return ResultadoSenal(False, f"error: {error}")

    def comprobar(self, senal: Senal) -> bool:
        if senal.tipo == DECIR:
            return True
        ver = self.ver.get(senal.tipo)
        if ver is None:
            return False
        try:
            return bool(ver(senal))
        except Exception:  # noqa: BLE001
            return False

    def herramienta_activa(self) -> str:
        return ""


__all__ = ["Adaptador", "AdaptadorBase", "Capacidades", "HERRAMIENTAS_BASE", "Perfil"]
