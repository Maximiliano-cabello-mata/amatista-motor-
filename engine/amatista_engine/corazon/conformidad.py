"""¿Este adaptador cumple el contrato del corazón? (como un kit de conformidad)

Un adaptador nuevo (Maya, 3ds Max, otro A-Frame) se da por bueno cuando
``revisar_adaptador`` no devuelve problemas. Revisa lo que hace que el alumno
no se confunda: que la foto sea una escena, que el perfil ubique las
herramientas base, que una señal que no sabe hacer diga «no» en lugar de
romper, y que lo que dice haber hecho se pueda comprobar.
"""
from __future__ import annotations

from typing import List

from ..models import SceneState
from .adaptador import HERRAMIENTAS_BASE, Adaptador
from .contrato import DECIR, ELEGIR_HERRAMIENTA, TIPOS_SENAL, Senal
from .senales import POR_LUGAR


def revisar_adaptador(adaptador: Adaptador, *, probar_senales: bool = True) -> List[str]:
    problemas: List[str] = []
    try:
        cap = adaptador.capacidades()
    except Exception as error:  # noqa: BLE001
        return [f"capacidades() falló: {error}"]
    if not cap.puede(DECIR):
        problemas.append("todo adaptador tiene que poder «decir»")
    raras = sorted(set(cap.senales) - set(TIPOS_SENAL))
    if raras:
        problemas.append(f"señales que el contrato no conoce: {', '.join(raras)}")
    perfil = getattr(adaptador, "perfil", None)
    if perfil is None:
        problemas.append("el adaptador no tiene perfil")
    else:
        if perfil.software != cap.software:
            problemas.append(f"el perfil es de «{perfil.software}» y las capacidades de «{cap.software}»")
        faltan = perfil.faltan(HERRAMIENTAS_BASE)
        if faltan:
            problemas.append(f"el perfil no ubica: {', '.join(faltan)}")
        for h, lugar in perfil.lugares.items():
            if lugar.herramienta != h:
                problemas.append(f"el lugar «{h}» dice ser «{lugar.herramienta}»")
            if not lugar.lugar:
                problemas.append(f"«{h}» no dice dónde está")
    try:
        escena = adaptador.capturar()
        if not isinstance(escena, SceneState):
            problemas.append("capturar() no devuelve una SceneState")
    except Exception as error:  # noqa: BLE001
        problemas.append(f"capturar() falló: {error}")
    if not probar_senales:
        return problemas
    for tipo in TIPOS_SENAL:
        if cap.puede(tipo):
            continue
        try:
            r = adaptador.ejecutar(Senal(tipo=tipo, herramienta="transform.move"))
            if r.hecho:
                problemas.append(f"dice que hizo «{tipo}» sin saber hacerla")
        except Exception as error:  # noqa: BLE001
            problemas.append(f"ejecutar(«{tipo}») rompe en lugar de decir que no: {error}")
    if perfil is not None and cap.puede(ELEGIR_HERRAMIENTA):
        lugar = next((lg for lg in perfil.lugares.values() if POR_LUGAR.get(lg.tipo) == ELEGIR_HERRAMIENTA), None)
        if lugar is not None:
            s = Senal(ELEGIR_HERRAMIENTA, lugar.herramienta, lugar.objetivo, modo=lugar.modo)
            r = adaptador.ejecutar(s)
            if r.hecho and not adaptador.comprobar(s):
                problemas.append(f"dice que eligió «{lugar.nombre}» pero comprobar() dice que no")
    return problemas


__all__ = ["revisar_adaptador"]
