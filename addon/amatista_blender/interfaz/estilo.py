"""Piezas de interfaz reutilizables: íconos de Amatista, tarjetas, barra de
progreso, chips y párrafos con ajuste de línea.

Blender no permite CSS: el «diseño» sale de cajas (tarjetas), escala de
filas, alineación, íconos propios y textos cortos. Todo panel de Amatista
usa estas funciones para verse igual.
"""
import textwrap
from pathlib import Path

import bpy
import bpy.utils.previews

_ICONOS = None
CARPETA_ICONOS = Path(__file__).resolve().parents[1] / "iconos"

ICONO_ESTADO = {
    "completado": "completado",
    "actual": "actual",
    "pendiente": "pendiente",
    "bloqueado": "bloqueado",
    "desconocido": "pendiente",
}
NIVELES = {1: "Desde cero", 2: "Básico", 3: "Consolidación", 4: "Intermedio", 5: "Avanzado"}


def cargar_iconos():
    global _ICONOS
    if _ICONOS is not None:
        return
    _ICONOS = bpy.utils.previews.new()
    for archivo in sorted(CARPETA_ICONOS.glob("*.png")):
        _ICONOS.load(archivo.stem, str(archivo), "IMAGE")


def liberar_iconos():
    global _ICONOS
    if _ICONOS is not None:
        bpy.utils.previews.remove(_ICONOS)
        _ICONOS = None


def icono(nombre):
    """icon_value de un ícono propio (0 si no está: Blender muestra el vacío)."""
    if _ICONOS is None or nombre not in _ICONOS:
        return 0
    return _ICONOS[nombre].icon_id


def ancho_caracteres(context, margen=4):
    """Cuántos caracteres caben en la región (para partir párrafos)."""
    region = getattr(context, "region", None)
    escala = (context.preferences.system.ui_scale if context and context.preferences else 0) or 1.0
    ancho = region.width if region else 300
    return max(18, int(ancho / (6.6 * escala)) - margen)


def parrafo(layout, context, texto, icon="NONE", margen=4, alerta=False):
    """Texto largo partido en líneas; la primera lleva el ícono."""
    if not texto:
        return
    col = layout.column(align=True)
    col.scale_y = 0.85
    col.alert = alerta
    lineas = []
    for bloque in str(texto).split("\n"):
        lineas.extend(textwrap.wrap(bloque, ancho_caracteres(context, margen)) or [""])
    for i, linea in enumerate(lineas):
        if i == 0 and icon != "NONE":
            col.label(text=linea, icon=icon)
        else:
            col.label(text=linea, icon="BLANK1" if icon != "NONE" else "NONE")


def tarjeta(layout, titulo="", icono_propio=None, icon="NONE", derecha=""):
    """Caja con encabezado. Devuelve la columna del cuerpo."""
    caja = layout.box()
    if titulo:
        fila = caja.row(align=True)
        if icono_propio:
            fila.label(text=titulo, icon_value=icono(icono_propio))
        else:
            fila.label(text=titulo, icon=icon)
        if derecha:
            sub = fila.row()
            sub.alignment = "RIGHT"
            sub.label(text=derecha)
    return caja.column(align=False)


def barra(layout, factor, texto=""):
    """Barra de progreso (UILayout.progress existe desde Blender 4.0)."""
    factor = max(0.0, min(1.0, float(factor)))
    fila = layout.row()
    fila.scale_y = 1.25
    try:
        fila.progress(factor=factor, type="BAR", text=texto or f"{factor * 100:.0f} %")
    except (AttributeError, TypeError):
        llenos = int(round(factor * 20))
        fila.label(text="▰" * llenos + "▱" * (20 - llenos) + f"  {texto or f'{factor * 100:.0f} %'}")


def anillo(layout, factor, texto=""):
    try:
        layout.progress(factor=max(0.0, min(1.0, factor)), type="RING", text=texto)
    except (AttributeError, TypeError):
        layout.label(text=texto or f"{factor * 100:.0f} %")


def chip(layout, texto, icon="NONE", icono_propio=None, activo=False):
    sub = layout.row(align=True)
    sub.alignment = "LEFT"
    sub.active = activo
    if icono_propio:
        sub.label(text=texto, icon_value=icono(icono_propio))
    else:
        sub.label(text=texto, icon=icon)
    return sub


def separador(layout, factor=0.6):
    layout.separator(factor=factor)


def boton_principal(layout, operador, texto, icon="NONE", icono_propio=None, escala=1.5, **propiedades):
    fila = layout.row()
    fila.scale_y = escala
    if icono_propio:
        op = fila.operator(operador, text=texto, icon_value=icono(icono_propio))
    else:
        op = fila.operator(operador, text=texto, icon=icon)
    for clave, valor in propiedades.items():
        setattr(op, clave, valor)
    return op


def seccion(layout, context, idname, titulo, icon="NONE", cerrada=False):
    """Sección plegable (UILayout.panel, Blender 4.1+). Devuelve el cuerpo o None si está cerrada."""
    if hasattr(layout, "panel"):
        cabecera, cuerpo = layout.panel(idname, default_closed=cerrada)
        cabecera.label(text=titulo, icon=icon)
        return cuerpo
    caja = layout.box()
    caja.label(text=titulo, icon=icon)
    return caja


def nivel_texto(nivel):
    return f"Nivel {nivel} · {NIVELES.get(int(nivel or 1), '')}"
