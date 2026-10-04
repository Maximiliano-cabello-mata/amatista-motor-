"""Tarjeta flotante sobre la vista 3D: práctica, progreso y paso actual.

Se dibuja con gpu + blf en cada vista 3D (esquina inferior izquierda) solo
mientras hay una práctica abierta. No evalúa nada: lee el último reporte.
Se apaga en Preferencias del add-on › «Tarjeta en la vista 3D».
"""
import bpy

try:
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
except ImportError:  # Blender sin GPU (modo background)
    blf = gpu = batch_for_shader = None

from .. import ajustes, practicas

_MANEJADOR = None

FONDO = (0.07, 0.07, 0.08, 0.86)
BORDE = (0.608, 0.349, 0.714, 1.0)  # #9B59B6
NEON = (0.0, 0.898, 1.0, 1.0)  # #00E5FF
BARRA_FONDO = (0.2, 0.2, 0.23, 1.0)
TEXTO = (0.88, 0.88, 0.88, 1.0)
TEXTO_SUAVE = (0.62, 0.62, 0.66, 1.0)
VERDE = (0.35, 0.84, 0.55, 1.0)


def _rectangulo(shader, x, y, ancho, alto, color, corte=0.0):
    """Rectángulo con la esquina superior derecha cortada en diagonal (.corte-poly)."""
    if corte > 0:
        puntos = [(x, y), (x + ancho, y), (x + ancho, y + alto - corte), (x + ancho - corte, y + alto), (x, y + alto)]
        indices = [(0, 1, 2), (0, 2, 3), (0, 3, 4)]
    else:
        puntos = [(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)]
        indices = [(0, 1, 2), (0, 2, 3)]
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=indices)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _texto(x, y, texto, tam, color):
    fuente = 0
    blf.size(fuente, tam)
    blf.color(fuente, *color)
    blf.position(fuente, x, y, 0)
    blf.draw(fuente, texto)


def _recortar(texto, tam, ancho_max):
    blf.size(0, tam)
    if blf.dimensions(0, texto)[0] <= ancho_max:
        return texto
    while texto and blf.dimensions(0, texto + "…")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "…"


def dibujar():
    p = ajustes.prefs()
    if p is not None and not p.mostrar_hud:
        return
    contexto = bpy.context
    escena = contexto.scene
    if escena is None or not escena.amatista.practica_json:
        return
    practica = practicas.practica_activa(contexto)
    reporte = practicas.ESTADO["reporte"]
    if practica is None or reporte is None:
        return

    escala = contexto.preferences.system.ui_scale
    margen = 16 * escala
    ancho = 300 * escala
    alto = 92 * escala
    x, y = margen, margen + 24 * escala

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    _rectangulo(shader, x - 2 * escala, y - 2 * escala, ancho + 4 * escala, alto + 4 * escala, BORDE, 14 * escala)
    _rectangulo(shader, x, y, ancho, alto, FONDO, 12 * escala)
    # Franja de acento (naranja Blender sería del curso; aquí neón Amatista).
    _rectangulo(shader, x, y + alto - 4 * escala, ancho * 0.35, 4 * escala, NEON)

    relleno = 14 * escala
    _texto(x + relleno, y + alto - 26 * escala, _recortar("AMATISTA · " + practica.title, int(13 * escala),
           ancho - 2 * relleno), int(13 * escala), TEXTO)

    barra_y = y + alto - 46 * escala
    barra_ancho = ancho - 2 * relleno - 48 * escala
    _rectangulo(shader, x + relleno, barra_y, barra_ancho, 8 * escala, BARRA_FONDO)
    color = VERDE if reporte.completed else NEON
    _rectangulo(shader, x + relleno, barra_y, max(2.0, barra_ancho * reporte.progress / 100.0), 8 * escala, color)
    _texto(x + relleno + barra_ancho + 8 * escala, barra_y - 1 * escala, f"{reporte.progress:.0f} %", int(12 * escala), TEXTO)

    if reporte.completed:
        linea = "✓ Práctica completada"
        color_linea = VERDE
    elif reporte.current_target_id:
        paso = next((s for s in reporte.steps if s.target_id == reporte.current_target_id), None)
        linea = f"Paso {reporte.step_number} de {len(reporte.steps)}: {paso.title if paso else ''}"
        color_linea = TEXTO
    else:
        linea, color_linea = "", TEXTO
    _texto(x + relleno, y + 30 * escala, _recortar(linea, int(12 * escala), ancho - 2 * relleno), int(12 * escala), color_linea)

    estado = practicas.ESTADO["sync"]
    pie = {
        practicas.SYNC_GUARDADO: "Guardado en tu cuenta",
        practicas.SYNC_PENDIENTE: "Pendiente de enviar",
        practicas.SYNC_SIN_CUENTA: "Sin cuenta vinculada",
        practicas.SYNC_ENVIANDO: "Enviando…",
    }.get(estado, "N › Amatista para ver los objetivos")
    _texto(x + relleno, y + 12 * escala, _recortar(pie, int(10 * escala), ancho - 2 * relleno), int(10 * escala), TEXTO_SUAVE)
    gpu.state.blend_set("NONE")


def activar(encendido=True):
    global _MANEJADOR
    if gpu is None or bpy.app.background:
        return
    if encendido and _MANEJADOR is None:
        _MANEJADOR = bpy.types.SpaceView3D.draw_handler_add(dibujar, (), "WINDOW", "POST_PIXEL")
    elif not encendido and _MANEJADOR is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_MANEJADOR, "WINDOW")
        _MANEJADOR = None
    practicas.redibujar()


def register():
    p = ajustes.prefs()
    activar(p.mostrar_hud if p else True)


def unregister():
    activar(False)
