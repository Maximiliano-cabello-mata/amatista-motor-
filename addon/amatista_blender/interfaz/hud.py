"""Lo que Amatista dibuja sobre la vista 3D.

Etapa 1: una tarjeta pequeña con la práctica, el progreso y el paso actual.
Etapa 2 (guía): la tarjeta pasa a ser el acompañante:

    ┌───────────────────────────────────────────┐
    │ AMATISTA · PASO 2 DE 6           ▰▰▰▱▱ 40 %│
    │ Hazla delgada                             │
    │ «Cube» mide 2 en Z. Lo buscamos entre…    │
    │ 1 [Clic] Selecciona «Cube»                │
    │ 2 [S] › [Z] Escala solo en Z              │
    │ 3 [0.1] › [Enter] Escribe 0.1 y confirma  │
    │ N › Amatista: «Hazlo conmigo»             │
    └───────────────────────────────────────────┘

y encima aparecen los avisos breves del acompañante («¡Listo!», «¡Vas
mejor!») que se desvanecen solos. En la escena (visor3d.py) se resaltan los
objetos del paso y se dibujan reglas, planos y piezas fantasma.

Se dibuja con gpu + blf solo mientras hay una práctica abierta. No evalúa
nada: lee el último reporte y la última guía. Se apaga en Preferencias del
add-on › «Tarjeta en la vista 3D».
"""
import time

import bpy

try:
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
except ImportError:  # Blender sin GPU (modo background)
    blf = gpu = batch_for_shader = None

from .. import ajustes, aprendizaje, guia, practicas

_MANEJADORES = []

FONDO = (0.07, 0.07, 0.08, 0.9)
BORDE = (0.608, 0.349, 0.714, 1.0)  # #9B59B6
NEON = (0.0, 0.898, 1.0, 1.0)  # #00E5FF
BARRA_FONDO = (0.2, 0.2, 0.23, 1.0)
TEXTO = (0.9, 0.9, 0.9, 1.0)
TEXTO_SUAVE = (0.62, 0.62, 0.66, 1.0)
VERDE = (0.35, 0.84, 0.55, 1.0)
NARANJA = (1.0, 0.62, 0.26, 1.0)  # #FF9F43
TECLA_FONDO = (0.18, 0.18, 0.21, 1.0)
TECLA_BORDE = (0.42, 0.42, 0.48, 1.0)

COLOR_TONO = {"logrado": VERDE, "cerca": NEON, "animo": TEXTO, "ojo": NARANJA}


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


def _ancho(texto, tam):
    blf.size(0, tam)
    return blf.dimensions(0, texto)[0]


def _recortar(texto, tam, ancho_max):
    if _ancho(texto, tam) <= ancho_max:
        return texto
    while texto and _ancho(texto + "…", tam) > ancho_max:
        texto = texto[:-1]
    return texto + "…"


def _partir(texto, tam, ancho_max, max_lineas=3):
    """Texto en líneas que caben en `ancho_max` píxeles."""
    lineas, actual = [], ""
    for palabra in str(texto or "").split():
        prueba = f"{actual} {palabra}".strip()
        if _ancho(prueba, tam) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = _recortar(lineas[-1] + " …", tam, ancho_max)
    return lineas


def _tecla(shader, x, y, texto, tam, escala):
    """Dibuja una tecla (cajita con borde) y devuelve su ancho."""
    relleno = 5 * escala
    ancho = max(_ancho(texto, tam) + 2 * relleno, 18 * escala)
    alto = tam + 7 * escala
    _rectangulo(shader, x, y - 4 * escala, ancho, alto, TECLA_BORDE)
    _rectangulo(shader, x + 1, y - 4 * escala + 1, ancho - 2, alto - 2, TECLA_FONDO)
    _texto(x + (ancho - _ancho(texto, tam)) / 2, y, texto, tam, TEXTO)
    return ancho


def _alto_instruccion(paso, tam, ancho_texto):
    return max(1, len(_partir(paso.text, tam, ancho_texto, 2))) * (tam + 5) + 6


def _dibujar_avisos(shader, x, y, ancho, escala):
    """Avisos del acompañante apilados sobre la tarjeta; se desvanecen al final."""
    ahora = time.time()
    for aviso in reversed(guia.avisos_vigentes()):
        restante = aviso["hasta"] - ahora
        alfa = max(0.0, min(1.0, restante / 0.8))
        color = COLOR_TONO.get(aviso["tono"], TEXTO)
        tam_t, tam = int(13 * escala), int(11 * escala)
        lineas = _partir(aviso["texto"], tam, ancho - 28 * escala, 2) if aviso["texto"] else []
        alto = (30 + 15 * len(lineas)) * escala
        _rectangulo(shader, x, y, ancho, alto, (*FONDO[:3], FONDO[3] * alfa), 10 * escala)
        _rectangulo(shader, x, y, 4 * escala, alto, (*color[:3], alfa))
        _texto(x + 14 * escala, y + alto - 20 * escala, _recortar(aviso["titulo"], tam_t, ancho - 28 * escala), tam_t,
               (*color[:3], alfa))
        for i, linea in enumerate(lineas):
            _texto(x + 14 * escala, y + alto - (36 + 15 * i) * escala, linea, tam, (*TEXTO_SUAVE[:3], alfa))
        y += alto + 6 * escala


def _dibujar_v3(shader, x, y, ancho, escala, practica, reporte):
    """Motor v3: franja de pausa (naranja) y la píldora de teoría con sus teclas grandes.

    Se apilan sobre la tarjeta; devuelve la altura donde siguen los avisos.
    """
    tam, tam_t, tam_chico = int(12 * escala), int(14 * escala), int(10 * escala)
    relleno = 12 * escala
    if reporte.paused:
        vigilante = practica.guard(reporte.paused_by)
        alto = 46 * escala
        _rectangulo(shader, x, y, ancho, alto, NARANJA, 10 * escala)
        _rectangulo(shader, x + 2, y + 2, ancho - 4, alto - 4, (0.16, 0.09, 0.03, 0.95), 9 * escala)
        _texto(x + relleno, y + alto - 18 * escala, "PROGRESO EN PAUSA", tam_chico, NARANJA)
        titulo = vigilante.title if vigilante is not None else reporte.paused_by
        _texto(x + relleno, y + 10 * escala, _recortar(titulo, tam, ancho - 2 * relleno), tam, TEXTO)
        y += alto + 8 * escala
    pildora = aprendizaje.pildora_principal()
    if pildora is not None and not reporte.completed:
        alto = (52 if pildora.keys else 34) * escala
        _rectangulo(shader, x, y, ancho, alto, FONDO, 10 * escala)
        _rectangulo(shader, x, y, 4 * escala, alto, NEON)
        _texto(x + relleno, y + alto - 16 * escala, "TEORÍA", tam_chico, NEON)
        _texto(x + relleno + 52 * escala, y + alto - 16 * escala,
               _recortar(pildora.title, tam_t, ancho - 2 * relleno - 52 * escala), tam_t, TEXTO)
        if pildora.keys:
            cx = x + relleno
            for i, tecla in enumerate(pildora.keys[:5]):
                if i:
                    _texto(cx + 3 * escala, y + 12 * escala, "+", tam, TEXTO_SUAVE)
                    cx += 14 * escala
                cx += _tecla(shader, cx, y + 12 * escala, str(tecla), tam_t, escala * 1.2) + 2 * escala
        y += alto + 8 * escala
    return y


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
    g = guia.guia_actual() if guia.nivel() != guia.NIVEL_SILENCIOSO else None

    escala = contexto.preferences.system.ui_scale
    margen = 16 * escala
    ancho = (360 if g else 300) * escala
    relleno = 14 * escala
    ancho_texto = ancho - 2 * relleno
    tam, tam_titulo, tam_chico = int(12 * escala), int(15 * escala), int(10 * escala)

    # Alto según el contenido.
    lineas_feedback = _partir(g.feedback, tam, ancho_texto, 3) if g else []
    instrucciones = list(g.instructions[:4]) if g and not g.completed else []
    alto = (64 if g else 92) * escala
    if g:
        alto += len(lineas_feedback) * (tam + 5) + 8 * escala
        alto += sum(_alto_instruccion(i, tam, ancho_texto - 120 * escala) for i in instrucciones)
        alto += 22 * escala
    x, y = margen, margen + 24 * escala

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    _rectangulo(shader, x - 2 * escala, y - 2 * escala, ancho + 4 * escala, alto + 4 * escala, BORDE, 14 * escala)
    _rectangulo(shader, x, y, ancho, alto, FONDO, 12 * escala)
    _rectangulo(shader, x, y + alto - 4 * escala, ancho * 0.35, 4 * escala, NEON)

    arriba = y + alto - 22 * escala
    if g and g.step_total and not g.completed:
        encabezado = f"AMATISTA · PASO {g.step_number} DE {g.step_total}"
    else:
        encabezado = "AMATISTA · " + practica.title.upper()
    _texto(x + relleno, arriba, _recortar(encabezado, tam_chico, ancho_texto - 110 * escala), tam_chico, NEON)

    barra_ancho = 70 * escala
    barra_x = x + ancho - relleno - barra_ancho - 36 * escala
    _rectangulo(shader, barra_x, arriba + 1 * escala, barra_ancho, 6 * escala, BARRA_FONDO)
    color = VERDE if reporte.completed else NEON
    _rectangulo(shader, barra_x, arriba + 1 * escala, max(2.0, barra_ancho * reporte.progress / 100.0), 6 * escala, color)
    _texto(barra_x + barra_ancho + 6 * escala, arriba, f"{reporte.progress:.0f} %", tam_chico, TEXTO)

    if g is None:
        # Modo silencioso: la tarjeta de la etapa 1.
        _texto(x + relleno, arriba - 26 * escala, _recortar(practica.title, tam_titulo, ancho_texto), tam_titulo, TEXTO)
        if reporte.completed:
            linea, color_linea = "✓ Práctica completada", VERDE
        elif reporte.current_target_id:
            paso = next((s for s in reporte.steps if s.target_id == reporte.current_target_id), None)
            linea, color_linea = f"Paso {reporte.step_number} de {len(reporte.steps)}: {paso.title if paso else ''}", TEXTO
        else:
            linea, color_linea = "", TEXTO
        _texto(x + relleno, y + 30 * escala, _recortar(linea, tam, ancho_texto), tam, color_linea)
        _pie(x + relleno, y + 12 * escala, ancho_texto, tam_chico, None)
        gpu.state.blend_set("NONE")
        return

    cursor = arriba - 26 * escala
    _texto(x + relleno, cursor, _recortar(g.title, tam_titulo, ancho_texto), tam_titulo,
           VERDE if g.completed else TEXTO)
    cursor -= 8 * escala
    color_tono = COLOR_TONO.get(g.tone, TEXTO)
    for linea in lineas_feedback:
        cursor -= tam + 5
        _texto(x + relleno, cursor, linea, tam, color_tono)
    cursor -= 6 * escala
    for numero, paso in enumerate(instrucciones, start=1):
        cursor -= tam + 9 * escala
        cx = x + relleno
        _texto(cx, cursor, f"{numero}", tam, NEON)
        cx += 14 * escala
        for i, tecla in enumerate(paso.keys):
            if i:
                _texto(cx + 2 * escala, cursor, "›", tam, TEXTO_SUAVE)
                cx += 12 * escala
            cx += _tecla(shader, cx, cursor, tecla, tam_chico, escala) + 2 * escala
        cx += 6 * escala
        lineas = _partir(paso.text, tam, x + ancho - relleno - cx, 2)
        for j, linea in enumerate(lineas):
            _texto(cx, cursor - j * (tam + 5), linea, tam, TEXTO)
        cursor -= (len(lineas) - 1) * (tam + 5)
    _pie(x + relleno, y + 10 * escala, ancho_texto, tam_chico, g)

    siguiente = _dibujar_v3(shader, x, y + alto + 12 * escala, ancho, escala, practica, reporte)
    _dibujar_avisos(shader, x, siguiente, ancho, escala)
    gpu.state.blend_set("NONE")


def _pie(x, y, ancho, tam, g):
    estado = practicas.ESTADO["sync"]
    if g is not None and g.action is not None and not g.completed:
        pie = f"N › Amatista › «{g.action.label}»"
    else:
        pie = {
            practicas.SYNC_GUARDADO: "Guardado en tu cuenta",
            practicas.SYNC_PENDIENTE: "Pendiente de enviar",
            practicas.SYNC_SIN_CUENTA: "Sin cuenta vinculada",
            practicas.SYNC_ENVIANDO: "Enviando…",
        }.get(estado, "N › Amatista para ver los pasos")
    _texto(x, y, _recortar(pie, tam, ancho), tam, TEXTO_SUAVE)


def activar(encendido=True):
    from . import visor3d

    if gpu is None or bpy.app.background:
        return
    if encendido and not _MANEJADORES:
        _MANEJADORES.append((bpy.types.SpaceView3D.draw_handler_add(dibujar, (), "WINDOW", "POST_PIXEL"), "WINDOW"))
        _MANEJADORES.append((bpy.types.SpaceView3D.draw_handler_add(visor3d.dibujar_escena, (), "WINDOW", "POST_VIEW"), "WINDOW"))
        _MANEJADORES.append((bpy.types.SpaceView3D.draw_handler_add(visor3d.dibujar_etiquetas, (), "WINDOW", "POST_PIXEL"), "WINDOW"))
    elif not encendido:
        while _MANEJADORES:
            manejador, region = _MANEJADORES.pop()
            bpy.types.SpaceView3D.draw_handler_remove(manejador, region)
    practicas.redibujar()


def register():
    p = ajustes.prefs()
    activar(p.mostrar_hud if p else True)


def unregister():
    activar(False)
