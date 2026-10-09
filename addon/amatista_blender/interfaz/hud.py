"""Lo que Amatista dibuja sobre la vista 3D.

Etapa 1: una tarjeta pequeña con la práctica, el progreso y el paso actual.
Etapa 2 (guía): la tarjeta pasa a ser el acompañante. Add-on 3.2: la
tarjeta toma la temática del módulo (temas.py): color de acento, nombre del
tema, la mascota en pixel art y su globo con consejos y datos curiosos que
cambia solo cada ~12 s:

      ╭──────────────────────────────╮
      │ [▣] TUERCA · CONSEJO          │   ← globo de la mascota
      │     G mueve, R gira y S…      │
      ╰─╲────────────────────────────╯
    ╭───────────────────────────────────────────╲
    │ [▣] EL TALLER DE JUGUETES       ▰▰▰▱▱ 40 % │  ← franja del tema
    │     PASO 2 DE 6 · JEFE: ROBO-TREN REBELDE  │
    │ Hazla delgada                              │
    │ «Cube» mide 2 en Z. Lo buscamos entre…     │
    │ 1 [Clic] Selecciona «Cube»                 │
    │ 2 [S] › [Z] Escala solo en Z               │
    │ N › Amatista: «Hazlo conmigo»              │
    ╰────────────────────────────────────────────╯

y encima aparecen los avisos breves del acompañante («¡Listo!», «¡Vas
mejor!») que se desvanecen solos. En la escena (visor3d.py) se resaltan los
objetos del paso y se dibujan reglas, planos y piezas fantasma.

Se dibuja con gpu + blf solo mientras hay una práctica abierta. No evalúa
nada: lee el último reporte y la última guía. Se apaga en Preferencias del
add-on › «Tarjeta en la vista 3D». En modo Silencioso no hay globo.
"""
import math
import time

import bpy

try:
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
except ImportError:  # Blender sin GPU (modo background)
    blf = gpu = batch_for_shader = None

from .. import ajustes, aprendizaje, guia, practicas, temas

_MANEJADORES = []

FONDO = (0.07, 0.07, 0.08, 0.92)
BORDE = (0.608, 0.349, 0.714, 1.0)  # #9B59B6 (sin tema)
NEON = (0.0, 0.898, 1.0, 1.0)  # #00E5FF
BARRA_FONDO = (0.2, 0.2, 0.23, 1.0)
TEXTO = (0.92, 0.92, 0.93, 1.0)
TEXTO_SUAVE = (0.64, 0.64, 0.68, 1.0)
VERDE = (0.35, 0.84, 0.55, 1.0)
NARANJA = (1.0, 0.62, 0.26, 1.0)  # #FF9F43
TECLA_FONDO = (0.16, 0.16, 0.19, 1.0)
TECLA_BORDE = (0.42, 0.42, 0.48, 1.0)
SOMBRA = (0.0, 0.0, 0.0, 0.28)
BLANCO = (0.97, 0.97, 0.98, 1.0)
OSCURO = (0.05, 0.05, 0.07, 1.0)

COLOR_TONO = {"logrado": VERDE, "cerca": NEON, "animo": TEXTO, "ojo": NARANJA}
ETIQUETA_MENSAJE = {"hola": "", "consejo": "CONSEJO", "dato": "¿SABÍAS QUE…?"}

_PALETA = {"clave": None, "valor": None}


def paleta(practica):
    """Colores y datos del tema de la práctica (en caché mientras no cambie la práctica)."""
    clave = practica.id if practica is not None else None
    if _PALETA["clave"] == clave and _PALETA["valor"] is not None:
        return _PALETA["valor"]
    tema = temas.tema_de_practica(clave)
    acento = temas.color_rgba(tema["colores"]["acento"])
    suave = temas.color_rgba(tema["colores"]["suave"])
    cielo = temas.color_rgba(tema["colores"]["cielo"])
    try:
        jefe = tema["jefe"] if practica is not None and aprendizaje.es_cierre(practica) else None
    except Exception:  # noqa: BLE001 - sin plan de estudios no hay jefe
        jefe = None
    valor = {
        "tema": tema,
        "acento": acento,
        "suave": suave,
        "fondo": (*temas.mezclar(FONDO, cielo, 0.45)[:3], FONDO[3]),
        "franja": (*temas.mezclar(FONDO, acento, 0.16)[:3], 0.96),
        "borde": (*acento[:3], 0.9),
        "jefe": jefe,
        "pixeles": {"a": acento, "s": suave, "w": BLANCO, "o": OSCURO},
    }
    _PALETA.update(clave=clave, valor=valor)
    return valor


# --- Primitivas -----------------------------------------------------------------------------


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


def _arco(cx, cy, radio, desde, hasta, pasos=4):
    return [(cx + radio * math.cos(math.radians(desde + (hasta - desde) * i / pasos)),
             cy + radio * math.sin(math.radians(desde + (hasta - desde) * i / pasos))) for i in range(pasos + 1)]


def _panel(shader, x, y, ancho, alto, color, radio=0.0, corte=0.0, abajo=True):
    """Panel con esquinas redondeadas y, si se pide, la esquina superior derecha facetada.

    abajo=False deja rectas las esquinas de abajo (franjas pegadas a otro panel).
    """
    radio = max(0.0, min(radio, ancho / 2, alto / 2))
    if radio < 1.0 and corte <= 0:
        _rectangulo(shader, x, y, ancho, alto, color)
        return
    contorno = []
    if abajo and radio >= 1.0:
        contorno += _arco(x + radio, y + radio, radio, 180, 270)
        contorno += _arco(x + ancho - radio, y + radio, radio, 270, 360)
    else:
        contorno += [(x, y), (x + ancho, y)]
    if corte > 0:
        contorno += [(x + ancho, y + alto - corte), (x + ancho - corte, y + alto)]
    elif radio >= 1.0:
        contorno += _arco(x + ancho - radio, y + alto - radio, radio, 0, 90)
    else:
        contorno.append((x + ancho, y + alto))
    if radio >= 1.0:
        contorno += _arco(x + radio, y + alto - radio, radio, 90, 180)
    else:
        contorno.append((x, y + alto))
    centro = (x + ancho / 2, y + alto / 2)
    puntos = [centro] + contorno
    n = len(contorno)
    indices = [(0, i, i % n + 1) for i in range(1, n + 1)]
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=indices)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _tarjeta(shader, x, y, ancho, alto, fondo, borde, escala, corte=0.0, radio=9.0):
    """Sombra suave + borde fino + fondo: la base de todas las tarjetas del HUD."""
    r = radio * escala
    _panel(shader, x - 1 * escala, y - 4 * escala, ancho + 2 * escala, alto + 2 * escala,
           (0, 0, 0, SOMBRA[3] * 0.5), r + 2 * escala, corte)
    _panel(shader, x, y - 2 * escala, ancho, alto, SOMBRA, r, corte)
    _panel(shader, x - 1.5 * escala, y - 1.5 * escala, ancho + 3 * escala, alto + 3 * escala, borde,
           r + 1.5 * escala, corte + 0.6 * escala if corte else 0.0)
    _panel(shader, x, y, ancho, alto, fondo, r, corte)


def _cuadros(shader, cuadros, color):
    """Muchos cuadrados del mismo color en una sola llamada (pixel art)."""
    if not cuadros:
        return
    puntos, indices = [], []
    for cx, cy, lado in cuadros:
        base = len(puntos)
        puntos += [(cx, cy), (cx + lado, cy), (cx + lado, cy + lado), (cx, cy + lado)]
        indices += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=indices)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _mascota(shader, x, y, celda, tema_id, colores, alfa=1.0, salto=0.0):
    """La mascota del tema en pixel art 10×10; (x, y) es la esquina inferior izquierda."""
    dibujo = temas.pixeles(tema_id)
    por_color = {}
    filas = len(dibujo)
    for r, fila in enumerate(dibujo):
        for c, letra in enumerate(fila):
            if letra in colores:
                por_color.setdefault(letra, []).append((x + c * celda, y + salto + (filas - 1 - r) * celda, celda))
    for letra, cuadros in por_color.items():
        color = colores[letra]
        _cuadros(shader, cuadros, (*color[:3], color[3] * alfa))


def _salto():
    """La mascota sube y baja un píxel con cada redibujado lento (cada 3 s): «respira» sin animar a 60 fps."""
    return 1.0 if int(time.time() // 3) % 2 else 0.0


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
    """Dibuja una tecla (cajita con borde y canto inferior) y devuelve su ancho."""
    relleno = 5 * escala
    ancho = max(_ancho(texto, tam) + 2 * relleno, 18 * escala)
    alto = tam + 7 * escala
    r = 3 * escala
    _panel(shader, x, y - 5 * escala, ancho, alto, (0, 0, 0, 0.45), r)
    _panel(shader, x, y - 4 * escala, ancho, alto, TECLA_BORDE, r)
    _panel(shader, x + 1, y - 4 * escala + 1 + 1 * escala, ancho - 2, alto - 2 - 1 * escala, TECLA_FONDO, r)
    _texto(x + (ancho - _ancho(texto, tam)) / 2, y, texto, tam, TEXTO)
    return ancho


def _barra(shader, x, y, ancho, alto, factor, color):
    """Barra de progreso redondeada con un brillo encima."""
    _panel(shader, x, y, ancho, alto, BARRA_FONDO, alto / 2)
    lleno = max(alto, ancho * max(0.0, min(1.0, factor)))
    _panel(shader, x, y, lleno, alto, color, alto / 2)
    _panel(shader, x + alto / 2, y + alto * 0.55, max(0.0, lleno - alto), alto * 0.3, (1, 1, 1, 0.22), alto * 0.15)


def _ancho_teclas(teclas, tam_chico, escala):
    """Lo que ocupan el número y las teclas de un micro paso (igual al dibujarlo)."""
    ancho = 16 * escala
    for i, tecla in enumerate(teclas):
        if i:
            ancho += 12 * escala
        ancho += max(_ancho(tecla, tam_chico) + 10 * escala, 18 * escala) + 2 * escala
    return ancho + 6 * escala


def _alto_instruccion(paso, tam, ancho_texto, escala=1.0, tam_chico=10):
    # Mismo ancho que al dibujar: antes se suponían 120 px de teclas y con tres
    # teclas el texto partía en más líneas de las calculadas y se salía de la tarjeta.
    libre = ancho_texto - _ancho_teclas(paso.keys, tam_chico, escala)
    lineas = max(1, len(_partir(paso.text, tam, libre, 2)))
    return tam + 9 * escala + (lineas - 1) * (tam + 5 * escala)


def _origen(contexto, margen, escala):
    """Esquina inferior izquierda libre: a la derecha de la barra T y encima del
    panel «Ajustar última operación» (que Blender abre abajo a la izquierda al
    agregar un cubo y tapaba la tarjeta)."""
    x, y = margen, margen + 24 * escala
    area, ventana = contexto.area, contexto.region
    if area is None or ventana is None:
        return x, y
    superpuestas = contexto.preferences.system.use_region_overlap
    for region in area.regions:
        if region.width <= 1 or region.height <= 1:
            continue  # región escondida
        if region.type == "TOOLS" and superpuestas:
            x = max(x, region.x - ventana.x + region.width + 8 * escala)
        elif region.type == "HUD":
            arriba = region.y - ventana.y + region.height
            if 0 < arriba < ventana.height * 0.6:
                y = max(y, arriba + 10 * escala)
    return x, y


# --- Tarjetas -----------------------------------------------------------------------------------


def _dibujar_avisos(shader, x, y, ancho, escala, pal=None):
    """Avisos del acompañante apilados sobre la tarjeta; se desvanecen al final."""
    ahora = time.time()
    for aviso in reversed(guia.avisos_vigentes()):
        restante = aviso["hasta"] - ahora
        alfa = max(0.0, min(1.0, restante / 0.8))
        color = COLOR_TONO.get(aviso["tono"], TEXTO)
        if aviso["tono"] == "cerca" and pal is not None:
            color = pal["acento"]
        tam_t, tam = int(13 * escala), int(11 * escala)
        sangria = (40 if pal is not None else 14) * escala
        lineas = _partir(aviso["texto"], tam, ancho - sangria - 14 * escala, 2) if aviso["texto"] else []
        alto = (30 + 15 * len(lineas)) * escala
        fondo = pal["fondo"] if pal is not None else FONDO
        _panel(shader, x, y - 2 * escala, ancho, alto, (0, 0, 0, SOMBRA[3] * alfa), 8 * escala, 10 * escala)
        _panel(shader, x, y, ancho, alto, (*fondo[:3], fondo[3] * alfa), 8 * escala, 10 * escala)
        _panel(shader, x, y, 4 * escala, alto, (*color[:3], alfa), 2 * escala)
        if pal is not None:
            _mascota(shader, x + 12 * escala, y + alto - 30 * escala, 2 * escala, pal["tema"]["id"], pal["pixeles"], alfa)
        _texto(x + sangria, y + alto - 20 * escala, _recortar(aviso["titulo"], tam_t, ancho - sangria - 14 * escala),
               tam_t, (*color[:3], alfa))
        for i, linea in enumerate(lineas):
            _texto(x + sangria, y + alto - (36 + 15 * i) * escala, linea, tam, (*TEXTO_SUAVE[:3], alfa))
        y += alto + 6 * escala


def _dibujar_v3(shader, x, y, ancho, escala, practica, reporte, pal=None):
    """Motor v3: franja de pausa (naranja) y la píldora de teoría con sus teclas grandes.

    Se apilan sobre la tarjeta; devuelve la altura donde siguen los avisos.
    """
    tam, tam_t, tam_chico = int(12 * escala), int(14 * escala), int(10 * escala)
    relleno = 12 * escala
    acento = pal["acento"] if pal is not None else NEON
    fondo = pal["fondo"] if pal is not None else FONDO
    if reporte.paused:
        vigilante = practica.guard(reporte.paused_by)
        alto = 46 * escala
        _tarjeta(shader, x, y, ancho, alto, (0.16, 0.09, 0.03, 0.95), NARANJA, escala, 10 * escala)
        _texto(x + relleno, y + alto - 18 * escala, "PROGRESO EN PAUSA", tam_chico, NARANJA)
        titulo = vigilante.title if vigilante is not None else reporte.paused_by
        _texto(x + relleno, y + 10 * escala, _recortar(titulo, tam, ancho - 2 * relleno), tam, TEXTO)
        y += alto + 10 * escala
    pildora = aprendizaje.pildora_principal()
    if pildora is not None and not reporte.completed:
        alto = (52 if pildora.keys else 34) * escala
        _panel(shader, x, y - 2 * escala, ancho, alto, SOMBRA, 8 * escala)
        _panel(shader, x, y, ancho, alto, fondo, 8 * escala)
        _panel(shader, x, y, 4 * escala, alto, acento, 2 * escala)
        _texto(x + relleno, y + alto - 16 * escala, "TEORÍA", tam_chico, acento)
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


def _dibujar_globo(shader, x, y, ancho, escala, pal, reporte):
    """El globo de la mascota: saludo, consejos y datos curiosos que rotan solos.

    Devuelve la altura donde sigue lo de arriba.
    """
    tema = pal["tema"]
    mascota = tema["mascota"]
    tam, tam_chico = int(11 * escala), int(9 * escala)
    relleno = 10 * escala
    lado = 30 * escala
    texto_x = x + relleno + lado + 10 * escala
    ancho_texto = x + ancho - relleno - texto_x
    jefe = pal["jefe"]
    if reporte.completed and jefe:
        tipo, texto = "jefe", f"¡Venciste a {jefe['nombre']}! El módulo «{tema['nombre']}» es tuyo."
    elif jefe and temas.indice_actual() % 4 == 0:
        tipo, texto = "jefe", f"{jefe['nombre']}: «{jefe.get('frase', '')}»"
    else:
        tipo, texto = temas.mensaje_mascota(tema, temas.indice_actual())
    lineas = _partir(texto, tam, ancho_texto, 3)
    alto = max(lado + 2 * relleno, 2 * relleno + tam_chico + 6 * escala + len(lineas) * (tam + 4))
    cola = 7 * escala
    y += cola
    _tarjeta(shader, x, y, ancho, alto, pal["fondo"], (*pal["acento"][:3], 0.55), escala, radio=10.0)
    # La colita del globo, hacia la tarjeta de abajo.
    batch = batch_for_shader(shader, "TRIS", {"pos": [(x + 22 * escala, y + 1), (x + 36 * escala, y + 1),
                                                       (x + 20 * escala, y - cola)]}, indices=[(0, 1, 2)])
    shader.uniform_float("color", pal["fondo"])
    batch.draw(shader)
    # La mascota en su marquito.
    mx, my = x + relleno, y + alto - relleno - lado
    _panel(shader, mx - 2 * escala, my - 2 * escala, lado + 4 * escala, lado + 4 * escala, pal["franja"], 6 * escala)
    _mascota(shader, mx, my, lado / 10, tema["id"], pal["pixeles"], salto=_salto() * escala)
    etiqueta = mascota.get("nombre", "").upper()
    if tipo == "jefe":
        etiqueta += " · JEFE FINAL"
    elif ETIQUETA_MENSAJE.get(tipo):
        etiqueta += " · " + ETIQUETA_MENSAJE[tipo]
    _texto(texto_x, y + alto - relleno - tam_chico, _recortar(etiqueta, tam_chico, ancho_texto), tam_chico, pal["acento"])
    for i, linea in enumerate(lineas):
        _texto(texto_x, y + alto - relleno - tam_chico - (i + 1) * (tam + 4) - 2 * escala, linea, tam, TEXTO)
    return y + alto + 10 * escala


def _dibujar_cabecera(shader, x, y_arriba, ancho, escala, pal, linea2, reporte, corte):
    """Franja del tema: mascota, nombre del tema, segunda línea y progreso."""
    alto = 34 * escala
    r = 10 * escala
    _panel(shader, x, y_arriba - alto, ancho, alto, pal["franja"], r, corte, abajo=False)
    _rectangulo(shader, x, y_arriba - alto, ancho, 1 * escala, (*pal["acento"][:3], 0.35))
    _panel(shader, x + r, y_arriba - 3 * escala, ancho * 0.35, 3 * escala, pal["acento"], 1.5 * escala)
    relleno = 12 * escala
    lado = 20 * escala
    _mascota(shader, x + relleno, y_arriba - alto + 7 * escala, lado / 10, pal["tema"]["id"], pal["pixeles"],
             salto=_salto() * escala)
    tam_chico = int(10 * escala)
    tx = x + relleno + lado + 8 * escala
    barra_ancho = 64 * escala
    barra_x = x + ancho - relleno - barra_ancho - 34 * escala
    libre = barra_x - tx - 8 * escala
    _texto(tx, y_arriba - 15 * escala, _recortar(pal["tema"]["nombre"].upper(), tam_chico, libre), tam_chico,
           pal["acento"])
    _texto(tx, y_arriba - 28 * escala, _recortar(linea2, int(9 * escala), libre), int(9 * escala), TEXTO_SUAVE)
    color = VERDE if reporte.completed else pal["acento"]
    _barra(shader, barra_x, y_arriba - 22 * escala, barra_ancho, 7 * escala, reporte.progress / 100.0, color)
    _texto(barra_x + barra_ancho + 6 * escala, y_arriba - 22 * escala, f"{reporte.progress:.0f} %", tam_chico, TEXTO)
    return y_arriba - alto


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
    pal = paleta(practica)

    escala = contexto.preferences.system.ui_scale or 1.0
    margen = 16 * escala
    ancho = (360 if g else 300) * escala
    relleno = 14 * escala
    ancho_texto = ancho - 2 * relleno
    tam, tam_titulo, tam_chico = int(12 * escala), int(15 * escala), int(10 * escala)
    corte = 14 * escala

    # Alto según el contenido.
    lineas_feedback = _partir(g.feedback, tam, ancho_texto, 3) if g else []
    instrucciones = list(g.instructions[:4]) if g and not g.completed else []
    alto = (70 if g else 98) * escala
    if g:
        alto += len(lineas_feedback) * (tam + 5 * escala) + 8 * escala
        alto += sum(_alto_instruccion(i, tam, ancho_texto, escala, tam_chico) for i in instrucciones)
        alto += 22 * escala
    x, y = _origen(contexto, margen, escala)

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    _tarjeta(shader, x, y, ancho, alto, pal["fondo"], pal["borde"], escala, corte, radio=10.0)

    if g and g.step_total and not g.completed:
        linea2 = f"PASO {g.step_number} DE {g.step_total}"
    elif reporte.completed:
        linea2 = "PRÁCTICA COMPLETADA"
    else:
        linea2 = practica.title.upper()
    if pal["jefe"]:
        linea2 += " · " + ("¡JEFE VENCIDO!" if reporte.completed else f"JEFE: {pal['jefe']['nombre'].upper()}")
    abajo_cabecera = _dibujar_cabecera(shader, x, y + alto, ancho, escala, pal, linea2, reporte, corte)

    if g is None:
        # Modo silencioso: la tarjeta de la etapa 1, con la franja del tema.
        _texto(x + relleno, abajo_cabecera - 22 * escala, _recortar(practica.title, tam_titulo, ancho_texto),
               tam_titulo, TEXTO)
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

    cursor = abajo_cabecera - 22 * escala
    _texto(x + relleno, cursor, _recortar(g.title, tam_titulo, ancho_texto), tam_titulo,
           VERDE if g.completed else TEXTO)
    cursor -= 8 * escala
    color_tono = COLOR_TONO.get(g.tone, TEXTO)
    if g.tone == "cerca":
        color_tono = pal["acento"]
    for linea in lineas_feedback:
        cursor -= tam + 5 * escala
        _texto(x + relleno, cursor, linea, tam, color_tono)
    cursor -= 6 * escala
    for numero, paso in enumerate(instrucciones, start=1):
        cursor -= tam + 9 * escala
        cx = x + relleno
        # Número en una pastilla del color del tema.
        _panel(shader, cx - 3 * escala, cursor - 4 * escala, 14 * escala, tam + 6 * escala,
               (*pal["acento"][:3], 0.18), 4 * escala)
        _texto(cx + 1 * escala, cursor, f"{numero}", tam, pal["acento"])
        cx += 16 * escala
        for i, tecla in enumerate(paso.keys):
            if i:
                _texto(cx + 2 * escala, cursor, "›", tam, TEXTO_SUAVE)
                cx += 12 * escala
            cx += _tecla(shader, cx, cursor, tecla, tam_chico, escala) + 2 * escala
        cx += 6 * escala
        lineas = _partir(paso.text, tam, x + ancho - relleno - cx, 2)
        for j, linea in enumerate(lineas):
            _texto(cx, cursor - j * (tam + 5 * escala), linea, tam, TEXTO)
        cursor -= (len(lineas) - 1) * (tam + 5 * escala)
    _rectangulo(shader, x + relleno, y + 26 * escala, ancho_texto, 1 * escala, (1, 1, 1, 0.06))
    _pie(x + relleno, y + 10 * escala, ancho_texto, tam_chico, g)

    siguiente = _dibujar_globo(shader, x, y + alto + 12 * escala, ancho, escala, pal, reporte)
    siguiente = _dibujar_v3(shader, x, siguiente, ancho, escala, practica, reporte, pal)
    _dibujar_avisos(shader, x, siguiente, ancho, escala, pal)
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


def _rotar_mascota():
    """Cada pocos segundos: redibuja para que el globo cambie de mensaje y la mascota brinque.

    Solo pide un redibujado (no evalúa nada) y solo si hay una práctica abierta.
    """
    try:
        sc = bpy.context.scene
        if sc is not None and sc.amatista.practica_json:
            practicas.redibujar()
    except (AttributeError, ReferenceError):
        pass
    return 3.0


def activar(encendido=True):
    from . import visor3d

    if gpu is None or bpy.app.background:
        return
    if encendido and not bpy.app.timers.is_registered(_rotar_mascota):
        bpy.app.timers.register(_rotar_mascota, first_interval=3.0, persistent=True)
    elif not encendido and bpy.app.timers.is_registered(_rotar_mascota):
        bpy.app.timers.unregister(_rotar_mascota)
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
