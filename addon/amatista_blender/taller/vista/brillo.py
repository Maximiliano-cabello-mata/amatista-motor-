"""Las herramientas que necesitas brillan (motor 6).

Pedido del creador: «que las herramientas que necesite el alumno brillen…
no queremos explícitamente darle las respuestas en las manos, pero tampoco
queremos que sea un calvario».

Cuando el alumno se atasca (o pide «¿Con qué?»), Amatista no dice el valor ni
hace el paso: hace brillar **dónde está** la herramienta. Un borde que late
alrededor de la barra de herramientas (T) si es una herramienta de la barra
(Mover, Rotar, Escalar…), o alrededor de la cabecera de la vista 3D si se
usa desde un menú (Agregar). Al lado aparece una etiqueta corta con el
nombre de la herramienta y su tecla, sin el cómo. Se apaga sola a los pocos
segundos, al usarla o al avanzar.

Se respeta «Animaciones» (sin animaciones: el borde no late) y se puede
apagar en Preferencias › Amatista › «Hacer brillar la herramienta…».
"""
import math
import time

import bpy

try:
    import gpu
except ImportError:  # Blender sin GPU (modo background)
    gpu = None

from ... import _motor, ajustes

DURA = 9.0
COLOR = (0.75, 0.52, 1.0, 1.0)  # amatista
ESTADO = {"hasta": 0.0, "region": "", "texto": "", "herramienta": ""}
_MANEJADORES = []


def _prefs_ok():
    p = ajustes.prefs()
    return p is None or getattr(p, "brillo_herramientas", True)


def donde(herramienta_id):
    """(región, nombre, tecla) de una herramienta del catálogo: TOOLS (barra T) o HEADER (menú), o None."""
    registro = getattr(_motor.MOTOR, "tools", None)
    h = registro.get(herramienta_id) if registro is not None else None
    if h is None:
        return None
    accion = h.action or {}
    nombre = getattr(h, "name", "") or herramienta_id
    tecla = getattr(h, "shortcut", "") or ""
    if "tool" in accion:
        return "TOOLS", nombre, tecla
    if "menu" in accion:
        return "HEADER", nombre, tecla
    return None


def encender(herramientas, segundos=DURA):
    """Hace brillar la primera herramienta de la lista que se pueda señalar. Devuelve si encendió algo."""
    if not _prefs_ok():
        return False
    for hid in herramientas or ():
        lugar = donde(hid)
        if lugar is None:
            continue
        region, nombre, tecla = lugar
        donde_texto = "en la barra de herramientas (izquierda)" if region == "TOOLS" else "en el menú de arriba"
        ESTADO.update(hasta=time.time() + segundos, region=region, herramienta=hid,
                      texto=f"{nombre}{f' ({tecla})' if tecla else ''} está {donde_texto}")
        _redibujar()
        if not bpy.app.timers.is_registered(_latir):
            bpy.app.timers.register(_latir, first_interval=0.05)
        return True
    return False


def apagar():
    if ESTADO["hasta"]:
        ESTADO.update(hasta=0.0, region="", texto="", herramienta="")
        _redibujar()


def activo():
    return ESTADO["hasta"] > time.time()


def _redibujar():
    if bpy.app.background:
        return
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _latir():
    _redibujar()
    if not activo():
        apagar()
        return None
    return 1.0 / 20.0


def _intensidad():
    p = ajustes.prefs()
    if p is not None and not getattr(p, "animaciones", True):
        return 0.85
    return 0.55 + 0.45 * (0.5 + 0.5 * math.sin(time.time() * 5.0))


def _borde(region, grosor):
    from ...interfaz import hud

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    a = _intensidad()
    color = (*COLOR[:3], a)
    ancho, alto = region.width, region.height
    for x, y, w, h in ((0, 0, ancho, grosor), (0, alto - grosor, ancho, grosor), (0, 0, grosor, alto),
                       (ancho - grosor, 0, grosor, alto)):
        hud._panel(shader, x, y, w, h, color, 0)
    gpu.state.blend_set("NONE")


def dibujar_region(nombre_region):
    """POST_PIXEL de la barra T o de la cabecera: el borde que late."""
    if gpu is None or not activo() or ESTADO["region"] != nombre_region:
        return
    from ...interfaz import turno

    contexto = bpy.context
    if not turno.me_toca(turno.TALLER, contexto) or contexto.region is None:
        return
    escala = contexto.preferences.system.ui_scale or 1.0
    _borde(contexto.region, 3 * escala)


def dibujar_etiqueta():
    """POST_PIXEL de la vista 3D: la etiqueta junto al borde (qué es y dónde está, nunca cómo se usa)."""
    if gpu is None or not activo() or not ESTADO["texto"]:
        return
    from ...interfaz import hud, turno

    contexto = bpy.context
    region = contexto.region
    if region is None or not turno.me_toca(turno.TALLER, contexto):
        return
    escala = contexto.preferences.system.ui_scale or 1.0
    tam = int(12 * escala)
    texto = ("◀ " if ESTADO["region"] == "TOOLS" else "▲ ") + ESTADO["texto"]
    ancho = hud._ancho(texto, tam) + 20 * escala
    alto = tam + 14 * escala
    x = 12 * escala
    y = region.height - alto - (12 if ESTADO["region"] == "HEADER" else 70) * escala
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    a = _intensidad()
    hud._panel(shader, x, y, ancho, alto, (0.11, 0.08, 0.16, 0.92), 6 * escala)
    hud._panel(shader, x, y, 3 * escala, alto, (*COLOR[:3], a), 0)
    hud._texto(x + 10 * escala, y + (alto - tam) / 2 + 2 * escala, texto, tam, (0.92, 0.88, 1.0, 1.0))
    gpu.state.blend_set("NONE")


def activar(encendido=True):
    from ... import saneamiento

    if gpu is None or bpy.app.background:
        return
    vista = bpy.types.SpaceView3D
    if encendido and not _MANEJADORES:
        for region in ("TOOLS", "HEADER"):
            _MANEJADORES.append((saneamiento.agregar_dibujo(vista, dibujar_region, (region,), region, "POST_PIXEL"), region))
        _MANEJADORES.append((saneamiento.agregar_dibujo(vista, dibujar_etiqueta, (), "WINDOW", "POST_PIXEL"), "WINDOW"))
    elif not encendido:
        while _MANEJADORES:
            manejador, region = _MANEJADORES.pop()
            saneamiento.quitar_dibujo(vista, manejador, region)
        apagar()
        if bpy.app.timers.is_registered(_latir):
            bpy.app.timers.unregister(_latir)


__all__ = ["activar", "activo", "apagar", "donde", "encender"]
