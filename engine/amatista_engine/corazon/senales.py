"""Qué señal pedir y cómo vive una señal hasta que deja de hacer falta.

Las tres reglas que faltaban en el add-on (análisis del 31 de octubre):

1. **Nada desaparece por reloj.** El brillo duraba 9 s, la ficha 16 s, los
   avisos 5 s. Aquí una señal termina solo cuando su paso se cumple
   (``CUMPLIDA``) o cuando deja de ser verdad (``PERDIDA``), y entonces se
   dice qué pasó y se ofrece repetirla.
2. **Nada se dice sin comprobarlo.** El texto «te dejé elegida…» sale solo
   si el adaptador confirma (``VIGENTE``); en cada revisión se vuelve a
   comprobar.
3. **Lo más fuerte que el programa sepa hacer, sin estorbar.** Si el
   programa no sabe hacer una señal, cae a «decir dónde está», que siempre
   es verdad. Las señales que roban la pantalla (abrir un menú o una
   ventana) solo se hacen si el alumno las pide.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from .adaptador import Capacidades, Perfil
from .contrato import (
    ABRIR_DIALOGO, ABRIR_MENU, ABRIR_PANEL, BARRA, CUMPLIDA, DECIR, DIALOGO, ELEGIR_HERRAMIENTA, FALLIDA, MENU,
    MOSTRADA, PERDIDA, PESTANA, PROPUESTA, SELECCIONAR, SUAVES, VIGENTE, EstadoSenal, Lugar, ResultadoSenal, Senal,
)

# Cómo se señala cada tipo de lugar, si el programa sabe hacerlo.
POR_LUGAR = {BARRA: ELEGIR_HERRAMIENTA, MENU: ABRIR_MENU, PESTANA: ABRIR_PANEL, DIALOGO: ABRIR_DIALOGO}


def _hecho(lugar: Lugar, tipo: str) -> str:
    if tipo == ELEGIR_HERRAMIENTA:
        return f"Te dejé elegida «{lugar.nombre}»: es el botón resaltado {lugar.lugar}."
    if tipo == ABRIR_MENU:
        return f"Te abrí el menú «{lugar.nombre}» junto a tu ratón."
    if tipo == ABRIR_PANEL:
        return f"Te abrí «{lugar.nombre}» {lugar.lugar}."
    if tipo == ABRIR_DIALOGO:
        return f"Te abrí la ventana «{lugar.nombre}»."
    return ""


def _perdida(lugar: Lugar, tipo: str) -> str:
    if tipo == ELEGIR_HERRAMIENTA:
        return (f"Ahora tienes otra herramienta elegida. «{lugar.nombre}» sigue {lugar.lugar}"
                + (f" (atajo: {lugar.atajo})" if lugar.atajo else "") + ".")
    if tipo == ABRIR_PANEL:
        return f"Se cerró «{lugar.nombre}». Está {lugar.lugar}."
    return ""


def elegir(lugar: Optional[Lugar], perfil: Perfil, capacidades: Capacidades, *, a_pedido: bool,
           primitiva: str = "", idioma: str = "", automatica: bool = False) -> Optional[Senal]:
    """La señal para la herramienta del paso, o None si no hay lugar conocido.

    ``a_pedido``: el alumno la pidió («¿Dónde está?»). Sin pedirla, solo se
    eligen señales suaves (las que no tapan nada).
    """
    if lugar is None:
        return None
    base = perfil.frase(lugar, idioma, primitiva)
    tipo = POR_LUGAR.get(lugar.tipo, DECIR)
    if not capacidades.puede(tipo) or (not a_pedido and tipo not in SUAVES):
        tipo = DECIR
    return Senal(
        tipo=tipo, herramienta=lugar.herramienta, objetivo=lugar.objetivo, modo=lugar.modo, texto_base=base,
        texto_hecho=perfil.en_pantalla(_hecho(lugar, tipo), idioma) if tipo != DECIR else "",
        texto_perdida=perfil.en_pantalla(_perdida(lugar, tipo), idioma) if tipo != DECIR else "",
        automatica=automatica,
    )


def seleccionar(objetos: Sequence[str], capacidades: Capacidades, texto_base: str = "") -> Optional[Senal]:
    """Seleccionar las piezas de las que habla el mensaje (el programa las marca con su borde)."""
    objetos = tuple(dict.fromkeys(o for o in objetos if o))[:3]
    if not objetos or not capacidades.puede(SELECCIONAR):
        return None
    nombres = ", ".join(f"«{o}»" for o in objetos)
    return Senal(tipo=SELECCIONAR, objetos=objetos, texto_base=texto_base,
                 texto_hecho=f"Lo dejé seleccionado: {nombres} (borde naranja en la vista 3D).",
                 texto_perdida=f"Ya no está seleccionado {nombres}.")


def iniciar(senal: Senal, ahora: float) -> EstadoSenal:
    return EstadoSenal(senal, PROPUESTA, ahora)


def tras_ejecutar(estado: EstadoSenal, resultado: ResultadoSenal, ahora: float) -> EstadoSenal:
    """El adaptador intentó la señal: queda vigente, mostrada (no dura) o fallida."""
    if not resultado.hecho:
        return replace(estado, estado=FALLIDA, desde=ahora)
    if estado.senal.tipo == DECIR:
        return replace(estado, estado=VIGENTE, desde=ahora)
    return replace(estado, estado=VIGENTE if estado.senal.duradera else MOSTRADA, desde=ahora)


def revisar(estado: Optional[EstadoSenal], sigue: bool, ahora: float) -> Optional[EstadoSenal]:
    """En cada revisión: una señal vigente que dejó de ser verdad pasa a perdida (y lo dice)."""
    if estado is None or estado.estado != VIGENTE or estado.senal.tipo == DECIR:
        return estado
    if sigue:
        return estado
    return replace(estado, estado=PERDIDA, desde=ahora)


def cumplir(estado: Optional[EstadoSenal], ahora: float) -> Optional[EstadoSenal]:
    if estado is None:
        return None
    return replace(estado, estado=CUMPLIDA, desde=ahora)


__all__ = ["POR_LUGAR", "cumplir", "elegir", "iniciar", "revisar", "seleccionar", "tras_ejecutar"]
