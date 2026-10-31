"""La banda del guion: el paso que toca, arriba al centro de la vista 3D (motor 7).

Una sola cosa de Amatista se dibuja sobre la vista 3D mientras el guion
manda (interfaz/turno.py lo decide). Va arriba, debajo de la cabecera,
entre la barra de herramientas y la barra lateral: abajo a la izquierda
Blender abre «Ajustar última operación» y abajo al centro la tarjeta del
motor 6 se tapaba con ese panel. No tiene botones (los clics van al panel
N › Amatista, que son botones de Blender de verdad).

    ┌──────────────────────────────────────────────────────┐
    │ PASO 3 DE 10 · LAS RUEDAS                 ▓▓▓▓░░░░░░ │
    │ Las ruedas son cilindros: cuatro por vagón…          │
    │ • Tienes 3 de 8 «Rueda». Faltan 5.                   │
    └──────────────────────────────────────────────────────┘
"""
import bpy

try:
    import gpu
except ImportError:  # Blender sin GPU (modo background)
    gpu = None

from .. import ajustes

ANCHO = 560
FONDO = (0.075, 0.07, 0.095, 0.93)
ACENTO = (0.62, 0.42, 1.0, 1.0)  # amatista
AMBAR = (1.0, 0.72, 0.35, 1.0)
_MANEJADOR = []


def _libre(contexto, escala):
    """(x0, x1, arriba) del hueco libre en la vista: entre la barra T y la barra N, debajo de la cabecera."""
    region, area = contexto.region, contexto.area
    x0, x1, arriba = 12 * escala, region.width - 12 * escala, region.height - 12 * escala
    if area is None:
        return x0, x1, arriba
    superpuestas = contexto.preferences.system.use_region_overlap
    for r in area.regions:
        if r.width <= 1 or r.height <= 1:
            continue
        if superpuestas and r.type == "TOOLS":
            x0 = max(x0, r.x - region.x + r.width + 10 * escala)
        elif superpuestas and r.type == "UI":
            x1 = min(x1, r.x - region.x - 10 * escala)
        elif superpuestas and r.type in ("HEADER", "TOOL_HEADER") and r.y >= region.y + region.height - r.height - 2:
            arriba = min(arriba, r.y - region.y - 8 * escala)
    return x0, x1, arriba - 26 * escala  # el texto «Perspectiva de usuario» y los ejes de navegación


def dibujar():
    if gpu is None:
        return
    from ..interfaz import hud, turno
    from .. import guion

    contexto = bpy.context
    if contexto.region is None or not turno.me_toca(turno.GUION, contexto):
        return
    p = ajustes.prefs()
    if p is not None and not getattr(p, "mostrar_hud", True):
        return
    hud.actualizar_idioma(contexto)
    v = guion.vista()
    if not v["haz"]:
        return
    escala = contexto.preferences.system.ui_scale or 1.0
    x0, x1, arriba = _libre(contexto, escala)
    ancho = min(ANCHO * escala, x1 - x0)
    if ancho < 200 * escala:
        return
    relleno = 12 * escala
    tam, tam_grande, tam_chico = int(12 * escala), int(14 * escala), int(10 * escala)
    if v["modo"] == "mirando":
        cabecera = f"MIRA · {v['titulo']}".upper()
    elif v["completo"]:
        cabecera = "¡TERMINADO!"
    elif v["modo"] == "pausa":
        cabecera = "EN PAUSA"
    else:
        cabecera = (f"PASO {v['numero']} DE {v['total']}" + (f" · {v['parte']}" if v["parte"] else "")).upper()
    lineas = hud._partir(v["haz"], tam_grande, ancho - 2 * relleno, 3)
    segunda = v["aviso"] or v["pista"] or v["por_que"]
    color_segunda = hud.VERDE if v["aviso"] else ((0.85, 0.78, 1.0, 1.0) if v["pista"] else AMBAR)
    lineas2 = hud._partir(segunda, tam, ancho - 2 * relleno - 12 * escala, 3) if segunda else []
    alto = relleno * 2 + tam_chico + 8 * escala + len(lineas) * (tam_grande + 6 * escala)
    alto += len(lineas2) * (tam + 5 * escala) + (6 * escala if lineas2 else 0)
    alto += 14 * escala  # «Botones: N › Amatista»
    x = x0 + (x1 - x0 - ancho) / 2
    y = arriba - alto
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    acento = hud.VERDE if v["completo"] else ACENTO
    hud._tarjeta(shader, x, y, ancho, alto, FONDO, acento, escala, radio=9.0)
    cy = y + alto - relleno - tam_chico
    hud._texto(x + relleno, cy, cabecera, tam_chico, acento)
    if v["total"] and v["modo"] in ("trabajando", "terminado"):
        hechos = sum(1 for _t, e in v["pasos"] if e == "hecho")
        hud._barra(shader, x + ancho - relleno - 120 * escala, cy, 120 * escala, 6 * escala,
                   1.0 if v["completo"] else hechos / max(1, v["total"]), acento)
    cy -= 8 * escala
    for linea in lineas:
        cy -= tam_grande + 6 * escala
        hud._texto(x + relleno, cy + 4 * escala, linea, tam_grande, hud.TEXTO)
    if lineas2:
        cy -= 6 * escala
        for i, linea in enumerate(lineas2):
            cy -= tam + 5 * escala
            if i == 0:
                hud._punto(shader, x + relleno + 4 * escala, cy + tam * 0.4, 4 * escala, color_segunda)
            hud._texto(x + relleno + 14 * escala, cy + 2 * escala, linea, tam, color_segunda)
    hud._texto(x + relleno, y + 8 * escala, "Pistas y pasos: barra lateral (N) › Amatista", tam_chico, hud.TEXTO_SUAVE)
    gpu.state.blend_set("NONE")


def activar(encendido=True):
    from .. import saneamiento

    if gpu is None or bpy.app.background:
        return
    vista = bpy.types.SpaceView3D
    if encendido and not _MANEJADOR:
        _MANEJADOR.append(saneamiento.agregar_dibujo(vista, dibujar, (), "WINDOW", "POST_PIXEL"))
    elif not encendido:
        while _MANEJADOR:
            saneamiento.quitar_dibujo(vista, _MANEJADOR.pop(), "WINDOW")


__all__ = ["activar", "dibujar"]
