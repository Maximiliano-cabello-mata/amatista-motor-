"""Lo que Amatista dibuja sobre la vista 3D: la tarjeta de la misión (Amatista Motor 4).

Una sola tarjeta, abajo a la izquierda, con una sola cosa que hacer:

    ╭──────────────────────────────────────────────╲
    │ [▣] PARTE 2 DE 4 · LAS RUEDAS       MISIÓN 4/11 │  ← franja del tema y mascota
    │     Tren de juguete                             │
    │ ● ● ◉ ○ ○ ○   ○ ○   ○ ○ ○                       │  ← la ruta: una bolita por misión
    │ Ruedas de pie y delgadas                        │  ← la misión
    │ Aplana el cilindro y luego ponlo de pie.        │  ← qué hacer, en una frase
    │ ✓ [S] › [Z]   Aplánalo                          │  ← se enciende al usar la tecla
    │ 2 [R] › [X]   Ponlo de pie                      │  ← la que toca «respira»
    │ ▌ ¡Casi! Ya está plana, falta girarla.          │  ← el instructor, sin decimales
    │ [Escalar] [Rotar] [✓ Añadir] (Mover) (Guardar)   │  ← herramientas: ahora · usadas · después
    │ ¿Atorado? N › Amatista › «Muéstrame cómo»       │
    ╰─────────────────────────────────────────────────╯

Animaciones (mision.py): la tarjeta entra deslizándose al empezar una misión;
la cumplida se celebra con un sello «¡Eso es!» que suelta chispas, y la
bolita de esa misión salta. Encima aparecen los avisos breves del
acompañante («¡Vas mejor!»). En la escena (visor3d.py) se resaltan los
objetos de la misión y se dibujan reglas, planos y piezas fantasma.

Se dibuja con gpu + blf solo mientras hay una práctica abierta y no evalúa
nada: lee la última ruta. Se apaga en Preferencias del add-on › «Tarjeta en
la vista 3D»; las animaciones, en «Animaciones».
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

from .. import _motor, ajustes, aprendizaje, guia, mision, practicas, temas

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


# --- La tarjeta de la misión (Amatista Motor 4) -------------------------------------------


def _con_alfa(color, alfa):
    return (color[0], color[1], color[2], color[3] * alfa)


def _punto(shader, cx, cy, radio, color, pasos=14):
    puntos = [(cx, cy)] + [(cx + radio * math.cos(2 * math.pi * i / pasos), cy + radio * math.sin(2 * math.pi * i / pasos))
                           for i in range(pasos + 1)]
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=[(0, i, i + 1) for i in range(1, pasos + 1)])
    shader.uniform_float("color", color)
    batch.draw(shader)


def _anillo(shader, cx, cy, radio, grosor, color, pasos=18):
    puntos, indices = [], []
    for i in range(pasos + 1):
        ang = 2 * math.pi * i / pasos
        puntos += [(cx + radio * math.cos(ang), cy + radio * math.sin(ang)),
                   (cx + (radio - grosor) * math.cos(ang), cy + (radio - grosor) * math.sin(ang))]
        if i:
            b = 2 * i
            indices += [(b - 2, b - 1, b), (b - 1, b + 1, b)]
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=indices)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _tecla_mision(shader, x, y, texto, tam, escala, estado, pulso, acento, alfa):
    """Una tecla de la misión: hecha (verde), la que toca (borde del tema que respira) o pendiente."""
    relleno = 5 * escala
    ancho = max(_ancho(texto, tam) + 2 * relleno, 18 * escala)
    alto = tam + 7 * escala
    r = 3 * escala
    if estado == "hecha":
        fondo, borde, color = (0.14, 0.32, 0.22, 1.0), VERDE, BLANCO
    elif estado == "toca":
        fondo, borde, color = TECLA_FONDO, (*acento[:3], 0.45 + 0.55 * pulso), BLANCO
        _panel(shader, x - 3 * escala, y - 8 * escala, ancho + 6 * escala, alto + 6 * escala,
               _con_alfa((*acento[:3], 0.22 * pulso), alfa), r + 3 * escala)
    else:
        fondo, borde, color = TECLA_FONDO, TECLA_BORDE, TEXTO
    _panel(shader, x, y - 5 * escala, ancho, alto, _con_alfa((0, 0, 0, 0.45), alfa), r)
    _panel(shader, x, y - 4 * escala, ancho, alto, _con_alfa(borde, alfa), r)
    _panel(shader, x + 1, y - 4 * escala + 1 + 1 * escala, ancho - 2, alto - 2 - 1 * escala, _con_alfa(fondo, alfa), r)
    _texto(x + (ancho - _ancho(texto, tam)) / 2, y, texto, tam, _con_alfa(color, alfa))
    return ancho


def _alto_paso(paso, tam, ancho_texto, escala, tam_chico):
    return _alto_instruccion(paso, tam, ancho_texto, escala, tam_chico)


def _nombre_corto(herramienta):
    return herramienta.name.split(" (")[0]


def _cinturon(shader, x, y, ancho, escala, ruta, pal, alfa):
    """Las herramientas de la práctica: la de ahora encendida, las usadas con ✓ y las que vienen con borde."""
    registro = _motor.MOTOR.tools
    if registro is None or not ruta.herramientas:
        return
    tam = int(10 * escala)
    estados = [(h, mision.estado_herramienta(h)) for h in ruta.herramientas]
    orden = {"ahora": 0, "mision": 1, "usada": 2, "despues": 3, "antes": 4}
    actuales = [e for e in estados if ruta.mision and e[0] in ruta.mision.herramientas]
    resto = [e for e in estados if e not in actuales]
    cx = x
    for hid, estado in sorted(actuales, key=lambda e: orden[e[1]]) + resto:
        h = registro.get(hid)
        if h is None:
            continue
        texto = _nombre_corto(h)
        marca = "✓ " if estado == "usada" else ""
        ancho_chip = _ancho(marca + texto, tam) + 14 * escala
        if cx + ancho_chip > x + ancho:
            break
        alto = 18 * escala
        if estado == "ahora":
            p = mision.pulso()
            _panel(shader, cx - 2 * escala, y - 2 * escala, ancho_chip + 4 * escala, alto + 4 * escala,
                   _con_alfa((*pal["acento"][:3], 0.25 + 0.25 * p), alfa), 9 * escala)
            _panel(shader, cx, y, ancho_chip, alto, _con_alfa(pal["acento"], alfa), 8 * escala)
            color = OSCURO
        elif estado == "mision":
            _panel(shader, cx, y, ancho_chip, alto, _con_alfa((*pal["acento"][:3], 0.32), alfa), 8 * escala)
            color = BLANCO
        elif estado == "usada":
            _panel(shader, cx, y, ancho_chip, alto, _con_alfa((0.14, 0.32, 0.22, 1.0), alfa), 8 * escala)
            color = VERDE
        elif estado == "antes":
            _panel(shader, cx, y, ancho_chip, alto, _con_alfa((1, 1, 1, 0.08), alfa), 8 * escala)
            color = TEXTO_SUAVE
        else:  # la usarás después: solo el borde
            _panel(shader, cx, y, ancho_chip, alto, _con_alfa((*pal["acento"][:3], 0.55), alfa), 8 * escala)
            _panel(shader, cx + 1 * escala, y + 1 * escala, ancho_chip - 2 * escala, alto - 2 * escala,
                   _con_alfa(pal["fondo"], alfa), 7 * escala)
            color = TEXTO_SUAVE
        _texto(cx + 7 * escala, y + 5 * escala, marca + texto, tam, _con_alfa(color, alfa))
        cx += ancho_chip + 5 * escala


def _puntos_ruta(shader, x, y, ancho, escala, ruta, pal, alfa):
    """Una bolita por misión, con un hueco entre partes: ● hecha · ◉ la de ahora · ○ las que vienen."""
    total = max(1, ruta.total)
    huecos = max(0, len(ruta.partes) - 1)
    paso = min(14 * escala, (ancho - huecos * 6 * escala) / total)
    radio = max(2.0, min(4.5 * escala, paso * 0.36))
    datos, avance = mision.logro()
    cx = x + radio
    parte = 0
    for m in ruta.misiones:
        if m.parte != parte:
            parte = m.parte
            cx += 6 * escala
        cy = y + radio
        if m.estado == "actual":
            p = mision.pulso()
            _punto(shader, cx, cy, radio * (1.5 + 0.25 * p), _con_alfa((*pal["acento"][:3], 0.25), alfa))
            _punto(shader, cx, cy, radio * 1.05, _con_alfa(pal["acento"], alfa))
        elif m.estado in ("hecha", "adelantada"):
            crece = 1.0
            if datos is not None and datos.get("numero") == m.numero:
                crece = 1.0 + 0.8 * (1 - mision.suave(avance * 2.5))  # la recién cumplida «salta»
            _punto(shader, cx, cy, radio * crece, _con_alfa(VERDE if m.estado == "adelantada" else pal["acento"], alfa))
        else:
            _anillo(shader, cx, cy, radio, 1.2 * escala, _con_alfa((1, 1, 1, 0.35), alfa))
        cx += paso


def _chispas(shader, cx, cy, escala, avance, pal):
    """Chispas que saltan del sello y caen (deterministas: siempre el mismo dibujo)."""
    colores = (pal["acento"], VERDE, BLANCO, pal["suave"])
    t = avance * mision.LOGRO
    for i in range(18):
        ang = math.radians(20 + i * 140 / 17)
        rapidez = (120 + 50 * ((i * 7) % 5) / 4) * escala
        px = cx + math.cos(ang) * rapidez * t
        py = cy + math.sin(ang) * rapidez * t - 160 * escala * t * t
        lado = (4 + (i % 3)) * escala
        color = colores[i % len(colores)]
        _rectangulo(shader, px, py, lado, lado, (*color[:3], max(0.0, 1.0 - avance) * color[3]))


def _sello(shader, x, y, ancho, escala, pal):
    """«¡Misión cumplida!» sobre la tarjeta: aparece con un rebote, suelta chispas y se desvanece."""
    datos, avance = mision.logro()
    if datos is None:
        return 0.0
    aparece = mision.suave(min(1.0, avance * 4))
    se_va = 1.0 - max(0.0, (avance - 0.75) / 0.25)
    alfa = max(0.0, min(1.0, aparece * se_va))
    tam = int((15 + 3 * (1 - aparece)) * escala)
    tam_extra = int(10 * escala)
    texto = datos["texto"]
    extra = ""
    for cola in (" ¡Y sin pistas!",):
        if texto.endswith(cola):
            texto, extra = texto[: -len(cola)], cola.strip()
    texto = "✓  " + texto
    ancho_sello = min(ancho, max(_ancho(texto, tam), _ancho(extra, tam_extra) if extra else 0) + 40 * escala)
    alto = (46 if extra else 36) * escala
    sx = x + (ancho - ancho_sello) / 2
    sy = y + 8 * escala + (1 - aparece) * 14 * escala
    _panel(shader, sx, sy - 3 * escala, ancho_sello, alto, (0, 0, 0, 0.35 * alfa), 18 * escala)
    _panel(shader, sx, sy, ancho_sello, alto, (0.18, 0.62, 0.38, 0.97 * alfa), 18 * escala)
    _panel(shader, sx + 18 * escala, sy + alto - 9 * escala, ancho_sello - 36 * escala, 4 * escala,
           (1, 1, 1, 0.18 * alfa), 2 * escala)
    base = sy + alto - 10 * escala - tam * 0.85
    _texto(sx + (ancho_sello - _ancho(texto, tam)) / 2, base, _recortar(texto, tam, ancho_sello - 20 * escala), tam,
           (*BLANCO[:3], alfa))
    if extra:
        _texto(sx + (ancho_sello - _ancho(extra, tam_extra)) / 2, sy + 7 * escala, extra, tam_extra,
               (0.86, 1.0, 0.9, alfa))
    _chispas(shader, sx + ancho_sello / 2, sy + alto / 2, escala, avance, pal)
    return alto + 14 * escala


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
    ruta = mision.ruta()
    if practica is None or reporte is None or ruta is None or ruta.practica_id != practica.id:
        return
    pal = paleta(practica)
    m = ruta.mision
    silencioso = guia.nivel() == guia.NIVEL_SILENCIOSO

    escala = contexto.preferences.system.ui_scale or 1.0
    margen = 16 * escala
    ancho = 380 * escala
    relleno = 14 * escala
    ancho_texto = ancho - 2 * relleno
    tam, tam_titulo, tam_chico = int(12 * escala), int(16 * escala), int(10 * escala)
    corte = 14 * escala
    acento = pal["acento"]

    # --- Qué dice la tarjeta ---
    if ruta.completada:
        titulo = practica.title
        objetivo = practica.completion or "Terminaste todas las misiones."
        mensaje, tono = f"{ruta.total} de {ruta.total} misiones · {_resumen_pistas()}", "logrado"
        pasos = []
    elif m is not None:
        titulo = m.titulo
        objetivo = m.objetivo
        mensaje, tono = ("" if silencioso else m.mensaje), (m.tono or "animo")
        pasos = [] if silencioso else list(m.pasos)
    else:
        titulo, objetivo, mensaje, tono, pasos = practica.title, "", "", "animo", []
    if ruta.pausa:
        mensaje, tono = ruta.pausa, "ojo"
    lineas_titulo = _partir(titulo, tam_titulo, ancho_texto, 2)
    lineas_objetivo = _partir(objetivo, tam, ancho_texto, 2) if objetivo else []
    lineas_mensaje = _partir(mensaje, tam, ancho_texto - 10 * escala, 2) if mensaje else []

    alto = 34 * escala + 22 * escala  # franja + bolitas
    alto += len(lineas_titulo) * (tam_titulo + 6 * escala) + 4 * escala
    alto += len(lineas_objetivo) * (tam + 5 * escala) + (6 * escala if lineas_objetivo else 0)
    alto += sum(_alto_paso(i, tam, ancho_texto, escala, tam_chico) for i in pasos) + (4 * escala if pasos else 0)
    alto += (len(lineas_mensaje) * (tam + 5 * escala) + 10 * escala) if lineas_mensaje else 0
    alto += 30 * escala if ruta.herramientas and not ruta.completada else 0
    alto += 24 * escala  # pie

    entra = mision.entrada()
    alfa = entra
    x, y = _origen(contexto, margen, escala)
    y -= (1 - entra) * 18 * escala

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    borde = NARANJA if ruta.pausa else (VERDE if ruta.completada else pal["borde"])
    _tarjeta(shader, x, y, ancho, alto, _con_alfa(pal["fondo"], alfa), _con_alfa(borde, alfa), escala, corte, radio=10.0)

    # Franja: mascota, parte de la ruta y número de misión.
    arriba = y + alto
    franja = 34 * escala
    _panel(shader, x, arriba - franja, ancho, franja, _con_alfa(pal["franja"], alfa), 10 * escala, corte, abajo=False)
    _rectangulo(shader, x, arriba - franja, ancho, 1 * escala, _con_alfa((*acento[:3], 0.35), alfa))
    _mascota(shader, x + relleno, arriba - franja + 7 * escala, 2 * escala, pal["tema"]["id"], pal["pixeles"], alfa,
             salto=_salto() * escala)
    tx = x + relleno + 28 * escala
    if ruta.pausa:
        linea1, color1, linea2 = "PROGRESO EN PAUSA", NARANJA, "Arregla esto y sigues donde ibas"
    elif ruta.completada:
        linea1, color1, linea2 = "PRÁCTICA COMPLETADA", VERDE, practica.title
    elif ruta.parte_actual is not None:
        linea1, color1, linea2 = f"PARTE {m.parte + 1} DE {len(ruta.partes)}", acento, ruta.parte_actual.titulo
    else:
        linea1, color1, linea2 = practica.title.upper(), acento, ""
    derecha = f"MISIÓN {m.numero}/{ruta.total}" if m is not None and not ruta.completada else f"{ruta.hechas}/{ruta.total} ✓"
    ancho_derecha = _ancho(derecha, tam_chico + int(1 * escala))
    libre = ancho - (tx - x) - relleno - ancho_derecha - 8 * escala
    _texto(tx, arriba - 14 * escala, _recortar(linea1, int(9 * escala), libre), int(9 * escala), _con_alfa(color1, alfa))
    _texto(tx, arriba - 28 * escala, _recortar(linea2, tam_chico + int(1 * escala), libre), tam_chico + int(1 * escala),
           _con_alfa(TEXTO, alfa))
    _texto(x + ancho - relleno - ancho_derecha, arriba - 21 * escala, derecha, tam_chico + int(1 * escala),
           _con_alfa(TEXTO, alfa))

    cursor = arriba - franja - 16 * escala
    _puntos_ruta(shader, x + relleno, cursor, ancho_texto, escala, ruta, pal, alfa)
    cursor -= 8 * escala

    for linea in lineas_titulo:
        cursor -= tam_titulo + 6 * escala
        _texto(x + relleno, cursor, linea, tam_titulo, _con_alfa(VERDE if ruta.completada else BLANCO, alfa))
    cursor -= 4 * escala
    for linea in lineas_objetivo:
        cursor -= tam + 5 * escala
        _texto(x + relleno, cursor, linea, tam, _con_alfa(TEXTO_SUAVE, alfa))
    if lineas_objetivo:
        cursor -= 6 * escala

    toca = mision.paso_siguiente(m) if m is not None else None
    pulso = mision.pulso()
    for numero, paso in enumerate(pasos, start=1):
        cursor -= tam + 9 * escala
        cx = x + relleno
        hecho = mision.paso_hecho(paso)
        color_num = VERDE if hecho else acento
        _panel(shader, cx - 3 * escala, cursor - 4 * escala, 14 * escala, tam + 6 * escala,
               _con_alfa((*color_num[:3], 0.2), alfa), 4 * escala)
        _texto(cx + 1 * escala, cursor, "✓" if hecho else f"{numero}", tam, _con_alfa(color_num, alfa))
        cx += 16 * escala
        estado = "hecha" if hecho else ("toca" if toca == numero - 1 else "")
        for i, tecla in enumerate(paso.keys):
            if i:
                _texto(cx + 2 * escala, cursor, "›", tam, _con_alfa(TEXTO_SUAVE, alfa))
                cx += 12 * escala
            cx += _tecla_mision(shader, cx, cursor, tecla, tam_chico, escala, estado, pulso, acento, alfa) + 2 * escala
        cx += 6 * escala
        lineas = _partir(paso.text, tam, x + ancho - relleno - cx, 2)
        for j, linea in enumerate(lineas):
            _texto(cx, cursor - j * (tam + 5 * escala), linea, tam, _con_alfa(TEXTO_SUAVE if hecho else TEXTO, alfa))
        cursor -= (len(lineas) - 1) * (tam + 5 * escala)
    if pasos:
        cursor -= 4 * escala

    if lineas_mensaje:
        color_tono = acento if tono == "cerca" else COLOR_TONO.get(tono, TEXTO)
        alto_msg = len(lineas_mensaje) * (tam + 5 * escala) + 4 * escala
        _panel(shader, x + relleno, cursor - alto_msg - 2 * escala, 3 * escala, alto_msg, _con_alfa(color_tono, alfa),
               1.5 * escala)
        for linea in lineas_mensaje:
            cursor -= tam + 5 * escala
            _texto(x + relleno + 10 * escala, cursor, linea, tam, _con_alfa(color_tono, alfa))
        cursor -= 10 * escala

    if ruta.herramientas and not ruta.completada:
        cursor -= 24 * escala
        _cinturon(shader, x + relleno, cursor, ancho_texto, escala, ruta, pal, alfa)

    _rectangulo(shader, x + relleno, y + 24 * escala, ancho_texto, 1 * escala, _con_alfa((1, 1, 1, 0.06), alfa))
    _texto(x + relleno, y + 9 * escala, _recortar(_pie(ruta, m), tam_chico, ancho_texto), tam_chico,
           _con_alfa(TEXTO_SUAVE, alfa))

    siguiente = y + alto + 12 * escala
    siguiente += _sello(shader, x, siguiente, ancho, escala, pal)
    if not silencioso:
        _dibujar_avisos(shader, x, siguiente, ancho, escala, pal)
    gpu.state.blend_set("NONE")


def _resumen_pistas():
    usadas = sum(practicas.pistas().values())
    return "sin pistas" if not usadas else f"{usadas} pista{'s' if usadas != 1 else ''}"


def _pie(ruta, m):
    if ruta.completada:
        return "N › Amatista: siguiente práctica"
    g = guia.guia_actual()
    if g is not None and g.action is not None and not g.completed:
        return f"¿Atorado? N › Amatista › «Muéstrame cómo»"
    estado = practicas.ESTADO["sync"]
    return {
        practicas.SYNC_GUARDADO: "Tu avance está guardado en tu cuenta",
        practicas.SYNC_PENDIENTE: "Tu avance se enviará cuando haya conexión",
        practicas.SYNC_SIN_CUENTA: "Vincula tu cuenta para guardar tu avance",
        practicas.SYNC_ENVIANDO: "Guardando tu avance…",
    }.get(estado, "N › Amatista para ver tu ruta")


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
