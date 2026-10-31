"""La tarjeta del taller: abajo al centro de la vista 3D, una sola cosa a la vez.

    ╭──────────────────────────────────────────────────────╮
    │ HAZLO CONMIGO  Estirar en un solo eje         2 de 3 │  ← qué paso del ciclo es
    │ Una tabla larga y plana, apoyada en el suelo.        │  ← qué hacer (≤ 25 palabras)
    │ ● A «Tabla» le falta largo.                          │  ← lo que dice el molde, sin números
    │ [S] › [X]                                            │  ← teclas, solo si se pidieron
    │ ●●○  2 de 3 piezas      [¿Qué falta?] [Pausa] [Saltar]│  ← máximo tres botones
    ╰──────────────────────────────────────────────────────╯

Los botones se tocan con el ratón: un gizmo invisible por botón (vista/
__init__.py) atrapa el clic solo dentro de su rectángulo y todo lo demás
sigue yendo a Blender. Durante «Mira» las teclas salen grandes encima de la
tarjeta, al estilo screencast.

Se respeta «Animaciones» de las preferencias (sin animaciones: la tarjeta no
entra deslizándose ni respira).

Motor 6: la tarjeta es una **referencia, no un estorbo**. Mientras el alumno
trabaja y no pasa nada nuevo (REPOSO segundos), se achica a una línea (lo que
dice el molde o lo que pide) y se vuelve más transparente; se abre sola al
acercar el ratón, con cada novedad (una pieza llena, una pista, un aviso) y
en «Mira», en la pausa y en el logro. Solo se dibuja si le toca
(interfaz/turno.py): nunca encima de otra tarjeta de Amatista.
"""
import math
import time

import bpy

try:
    import blf  # noqa: F401 - lo usan las primitivas de hud
    import gpu
except ImportError:  # Blender sin GPU (modo background)
    gpu = None

from ... import _motor, ajustes
from ...interfaz import hud
from .. import datos, demo, sesion

taller = _motor.taller
ayudas = _motor.taller.ayudas

TEXTO = hud.TEXTO
SUAVE = hud.TEXTO_SUAVE
FONDO = (0.075, 0.07, 0.095, 0.94)
COLOR_TIPO = {
    "mira": (0.62, 0.42, 0.95, 1.0),
    "conmigo": (1.0, 0.70, 0.22, 1.0),
    "tu": (0.36, 0.62, 1.0, 1.0),
    "proyecto": (0.35, 0.84, 0.55, 1.0),
    "reto": (1.0, 0.45, 0.40, 1.0),
    "repaso": (0.30, 0.82, 0.86, 1.0),
    "prueba": (0.30, 0.82, 0.86, 1.0),
}
COLOR_ESTADO = {"llena": hud.VERDE, "casi": (1.0, 0.45, 0.40, 1.0), "equivocada": (1.0, 0.45, 0.40, 1.0),
                "vacia": (1.0, 0.70, 0.22, 1.0)}
NOMBRE_TIPO = {"mira": "MIRA", "conmigo": "HAZLO CONMIGO", "tu": "HAZLO TÚ", "proyecto": "ÚSALO", "reto": "RETO",
               "repaso": "RECUÉRDALO", "prueba": "DEMUÉSTRALO"}
FASE = {"nueva": "Nueva", "acompanada": "Con ayuda", "sola": "Ya te sale", "dominada": "Dominada"}
ENTRADA = 0.3
ANCHO = 540

BOTONES = {}  # {región: [(x0, y0, x1, y1, acción, activo)]} en coordenadas de la región
HOVER = {"region": 0, "indice": -1}
MAX_BOTONES = 3
# Motor 6: la tarjeta compacta.
REPOSO = 5.0  # segundos sin novedades antes de achicarse
CERCA = 48  # px alrededor de la tarjeta que cuentan como «el ratón está encima»
RATON = {"region": 0, "x": -1.0, "y": -1.0, "t": 0.0}
RECTAS = {}  # {región: (x0, y0, x1, y1)} de la última tarjeta dibujada
NOVEDAD = {"clave": None, "t": 0.0}


ULTIMA_FORMA = {}  # {región: ¿se dibujó compacta?}


def raton(region, x, y):
    """Lo llama el gizmo de los botones en cada movimiento del ratón. Devuelve si hay que redibujar."""
    RATON.update(region=region, x=float(x), y=float(y), t=time.time())
    return cambio_compacta()


def cambio_compacta():
    """¿Alguna tarjeta tiene que pasar de compacta a abierta (o al revés)? (el vigilante lo pregunta)."""
    cambio = False
    for clave in list(RECTAS):
        forma = compacta(clave)
        if ULTIMA_FORMA.get(clave) != forma:
            ULTIMA_FORMA[clave] = forma
            cambio = True
    return cambio


def _segundos_sin_novedad():
    a = sesion.actividad()
    r = sesion.SESION["revision"]
    pieza = r.pieza_actual if r is not None else None
    pista = sesion.SESION["pista"]
    clave = (a.id if a is not None else "", sesion.estado(), r.llenas if r is not None else 0,
             pieza.estado if pieza is not None else "", pieza.motivo if pieza is not None else "",
             pista.nivel if pista is not None else 0, sesion.mensaje(), demo.activa(), sesion.SESION["mirame"])
    if clave != NOVEDAD["clave"]:
        NOVEDAD.update(clave=clave, t=time.time())
    return time.time() - NOVEDAD["t"]


def compacta(clave_region):
    """¿La tarjeta va en una línea? Solo mientras trabaja, sin novedades y con el ratón lejos."""
    p = ajustes.prefs()
    if p is not None and not getattr(p, "tarjeta_compacta", True):
        return False
    if sesion.estado() != sesion.TRABAJANDO or sesion.SESION["mirame"] or demo.activa():
        return False
    if _segundos_sin_novedad() < REPOSO:
        return False
    recta = RECTAS.get(clave_region)
    if recta is not None and RATON["region"] == clave_region and time.time() - RATON["t"] < 2.0:
        x0, y0, x1, y1 = recta
        if x0 - CERCA <= RATON["x"] <= x1 + CERCA and y0 - CERCA <= RATON["y"] <= y1 + CERCA:
            return False
    return True


def animaciones():
    p = ajustes.prefs()
    return p is None or getattr(p, "animaciones", True)


def _suave(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _con_alfa(color, alfa):
    return (*color[:3], color[3] * alfa if len(color) > 3 else alfa)


def botones():
    """[(texto, acción, activo)] según el estado de la sesión (máximo tres)."""
    from ... import fichas

    if fichas.visible() is not None:
        return fichas.botones()  # motor 6.1: la ficha de una herramienta ocupa el lugar de la tarjeta
    a = sesion.actividad()
    st = sesion.estado()
    if a is None:
        return []
    if st == sesion.PRESENTANDO:
        return [("Empezar", "empezar_actividad", True)]  # la ficha se cerró sin «Entendido»
    if st == sesion.MIRANDO:
        return [("Repetir", "repetir_demo", True), ("Ahora tú", "ahora_tu", True)]
    if sesion.SESION["mirame"]:
        return [("Ya entendí", "cerrar_demo", True)]
    if st == sesion.PAUSA:
        return [("Seguir", "seguir", True)]
    if st == sesion.LOGRADA and sesion.SESION["volver"]:
        # Motor 6: la etapa que mandó la plataforma se cumplió; lo que sigue es allá, no aquí.
        from ... import plataforma

        if plataforma.viva():  # motor 6.1: la lección ya avanzó sola en el navegador
            return [("Otra vez", "otra_vez", True)]
        return [("Ir a la plataforma", "volver_plataforma", True), ("Otra vez", "otra_vez", True)]
    if st == sesion.LOGRADA:
        if a.tipo == taller.PROYECTO:
            return [("Siguiente", "siguiente", True), ("Ver mi isla", "isla", True)]
        if a.tipo == taller.MIRA:
            return [("Hazlo tú", "siguiente", True), ("Verla otra vez", "otra_vez", True)]
        return [("Siguiente", "siguiente", True), ("Otra vez", "otra_vez", True)]
    salida = []
    nombre, puede = sesion.siguiente_pista()
    if nombre:
        espera = sesion.espera_teclas()
        texto = f"¿{nombre}?" if nombre != "Mírame" else "Mírame"
        if not puede and espera > 0:
            texto = f"¿Cómo? {int(espera) + 1} s"
        salida.append((texto, "pista", puede))
    salida.append(("Pausa", "pausa", True))
    if not sesion.SESION["proyecto"]:
        salida.append(("Ahora no" if a.tipo == taller.REPASO else "Saltar", "saltar", True))
    return salida[:MAX_BOTONES]


def _linea_pieza():
    """(texto, color) de lo que dice el molde o la pista, o (None, None)."""
    pista = sesion.SESION["pista"]
    aviso = sesion.mensaje()
    if aviso:
        return aviso, hud.NEON
    if pista is not None and pista.texto:
        return pista.texto, (0.85, 0.75, 1.0, 1.0)
    pieza = sesion.pieza_actual()
    if pieza is not None and pieza.mensaje:
        return pieza.mensaje, COLOR_ESTADO.get(pieza.estado, TEXTO)
    reporte = sesion.SESION["reporte"]
    if reporte is not None and not reporte.completed:
        pendiente = next((r for r in reporte.results if not r.passed and r.message), None)
        if pendiente is not None:
            return pendiente.message, COLOR_ESTADO["vacia"]
    # Motor 6.1: las primeras veces, una línea que recuerda para qué sirve la herramienta (se retira sola).
    from ... import fichas

    recuerda = fichas.recordatorio(sesion.actividad())
    if recuerda:
        return recuerda, (0.80, 0.74, 0.95, 1.0)
    return None, None


def _linea_accion():
    """Motor 6.2: «Te toca: Extruir · Estás haciendo: Mover» cuando la luz lo pide (nunca las teclas).

    Devuelve (te_toca, haciendo, coincide) o None. Con la luz media o plena el
    alumno ve qué herramienta pide la actividad y qué está usando ahora: en
    verde si es la que toca, en ámbar si es otra.
    """
    from .. import acompanar

    luz = acompanar.luz()
    if luz is None or not luz.accion or sesion.estado() != sesion.TRABAJANDO:
        return None
    toca = acompanar.te_toca()
    ahora = acompanar.haciendo()
    if not toca and ahora is None:
        return None
    return toca, (ahora[0] if ahora else ""), bool(ahora and ahora[1])


def _teclas_visibles():
    pista = sesion.SESION["pista"]
    if pista is not None and pista.nivel >= ayudas.COMO and pista.teclas:
        return list(pista.teclas)
    return []


def _fase_de(hid):
    plan = sesion.SESION["plan"]
    for h in (plan.habilidades if plan is not None else ()):
        if h.id == hid:
            return h
    return None


def _boton(shader, x, y, ancho, alto, texto, tam, escala, activo, principal, hover, acento):
    fondo = (*acento[:3], 0.95) if principal else (0.18, 0.17, 0.22, 0.95)
    if hover and activo:
        fondo = (*[min(1.0, c + 0.12) for c in fondo[:3]], fondo[3])
    if not activo:
        fondo = (0.16, 0.16, 0.19, 0.8)
    hud._panel(shader, x, y, ancho, alto, fondo, 6 * escala)
    color = hud.OSCURO if principal and activo else (TEXTO if activo else SUAVE)
    hud._texto(x + (ancho - hud._ancho(texto, tam)) / 2, y + (alto - tam) / 2 + 2 * escala, texto, tam, color)


def _region_base(contexto, escala):
    """Abajo al centro, encima del panel «Ajustar última operación» si está abierto."""
    _x, y = hud._origen(contexto, 16 * escala, escala)
    return y


def _dibujar_volver(contexto, region, clave):
    """Motor 6.2: la pastilla «Volver a mi práctica» abajo al centro (navegar.py)."""
    from ... import navegar

    escala = contexto.preferences.system.ui_scale or 1.0
    tam, tam_chico = int(13 * escala), int(10 * escala)
    texto = navegar.texto_boton() + "  ›"
    aviso = "Tu práctica sigue en otra escena"
    ancho = max(hud._ancho(texto, tam), hud._ancho(aviso, tam_chico)) + 40 * escala
    if ancho > region.width - 24 * escala:
        return
    alto_boton = 30 * escala
    alto = alto_boton + tam_chico + 26 * escala
    x = (region.width - ancho) / 2
    y = _region_base(contexto, escala)
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    respira = 0.5 + 0.5 * math.sin(time.time() * 2.4) if animaciones() else 1.0
    borde = (*hud.NEON[:3], 0.55 + 0.45 * respira)
    hud._tarjeta(shader, x, y, ancho, alto, FONDO, borde, escala, radio=12.0)
    hud._texto(x + (ancho - hud._ancho(aviso, tam_chico)) / 2, y + alto - 10 * escala - tam_chico, aviso, tam_chico,
               SUAVE)
    bx, by = x + 12 * escala, y + 10 * escala
    hover = HOVER["region"] == clave and HOVER["indice"] == 0
    _boton(shader, bx, by, ancho - 24 * escala, alto_boton, texto, tam, escala, True, True, hover, hud.NEON)
    BOTONES[clave] = [(bx, by, bx + ancho - 24 * escala, by + alto_boton, "volver_amatista", True)]
    RECTAS.pop(clave, None)
    gpu.state.blend_set("NONE")


def dibujar():
    if gpu is None:
        return
    p = ajustes.prefs()
    if p is not None and not p.mostrar_hud:
        return
    contexto = bpy.context
    hud.actualizar_idioma(contexto)
    region = contexto.region
    clave = region.as_pointer() if region is not None else 0
    BOTONES[clave] = []
    from ... import fichas
    from ...interfaz import turno

    quien = turno.de_quien(contexto) if region is not None else ""
    if quien == turno.VOLVER:
        _dibujar_volver(contexto, region, clave)
        return
    if quien not in (turno.TALLER, turno.FICHA):
        return
    if fichas.visible() is not None:
        from . import ficha

        escala = contexto.preferences.system.ui_scale or 1.0
        if ficha.dibujar(contexto, region, clave, _region_base(contexto, escala), _boton, BOTONES, HOVER):
            RECTAS.pop(clave, None)
        return
    if quien != turno.TALLER:
        return
    a = sesion.actividad()
    st = sesion.estado()
    escala = contexto.preferences.system.ui_scale or 1.0
    ancho = min(ANCHO * escala, region.width - 32 * escala)
    if ancho < 220 * escala:
        return
    relleno = 14 * escala
    ancho_texto = ancho - 2 * relleno
    tam, tam_grande, tam_chico = int(12 * escala), int(15 * escala), int(10 * escala)
    acento = COLOR_TIPO.get(a.tipo, hud.NEON)
    if st == sesion.LOGRADA:
        acento = hud.VERDE
    elif st == sesion.PAUSA:
        acento = hud.NARANJA

    # --- Qué dice ---
    paso_demo = demo.paso_actual() if demo.activa() else None
    if st == sesion.MIRANDO or sesion.SESION["mirame"]:
        chip = "MIRA"
        texto = (paso_demo.texto if paso_demo is not None and paso_demo.texto else a.pide)
        linea, color_linea = (None, None)
        teclas = list(paso_demo.teclas) if paso_demo is not None else []
    elif st == sesion.LOGRADA:
        chip = "¡LO LOGRASTE!"
        texto = sesion.frase_logro()
        linea, color_linea = (None, None)
        teclas = []
    elif st == sesion.PAUSA:
        chip = "EN PAUSA"
        texto = a.pide
        linea, color_linea = ("Tu trabajo está a salvo. Sigue cuando quieras.", SUAVE)
        teclas = []
    else:
        chip = NOMBRE_TIPO.get(a.tipo, a.nombre_tipo.upper())
        texto = a.pide
        linea, color_linea = _linea_pieza()
        teclas = _teclas_visibles()
    contador = f"{a.numero} de {a.de}" if a.de > 1 and st != sesion.LOGRADA else ""
    lineas_texto = hud._partir(texto, tam_grande, ancho_texto, 2)
    lineas_linea = hud._partir(linea, tam, ancho_texto - 12 * escala, 2) if linea else []
    accion = _linea_accion() if st == sesion.TRABAJANDO and not sesion.SESION["mirame"] else None
    lista = botones()
    chica = compacta(clave)
    if chica:
        # Referencia, no estorbo: una línea (lo que dice el molde o lo que pide) y los botones.
        lineas_texto = hud._partir(linea or texto, tam_grande, ancho_texto, 1)
        lineas_linea, teclas = [], []
        accion = None

    alto = relleno + tam_chico + 10 * escala  # cabecera
    alto += len(lineas_texto) * (tam_grande + 6 * escala)
    alto += len(lineas_linea) * (tam + 5 * escala) + (6 * escala if lineas_linea else 0)
    alto += (tam + 14 * escala) if teclas and not demo.activa() else 0
    alto += (tam_chico + 12 * escala) if accion else 0
    alto += 30 * escala + relleno  # fila de botones

    entra = _suave((time.time() - sesion.SESION["entrada"]) / ENTRADA) if animaciones() else 1.0
    x = (region.width - ancho) / 2
    y = _region_base(contexto, escala) - (1 - entra) * 16 * escala
    alfa = max(0.15, entra) * (0.8 if chica else 1.0)
    RECTAS[clave] = (x, y, x + ancho, y + alto)

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    borde = acento
    if st == sesion.LOGRADA and animaciones():
        brillo = max(0.0, 1.0 - (time.time() - sesion.SESION["logro_en"]) / 0.5)
        borde = (*[min(1.0, c + 0.25 * brillo) for c in acento[:3]], 1.0)
    hud._tarjeta(shader, x, y, ancho, alto, _con_alfa(FONDO, alfa), _con_alfa(borde, alfa), escala, radio=10.0)

    # Cabecera: el paso del ciclo (chip de color), la habilidad y el número de variación.
    cy = y + alto - relleno - tam_chico
    ancho_chip = hud._ancho(chip, tam_chico) + 12 * escala
    hud._panel(shader, x + relleno, cy - 4 * escala, ancho_chip, tam_chico + 8 * escala, _con_alfa(acento, alfa), 4 * escala)
    hud._texto(x + relleno + 6 * escala, cy, chip, tam_chico, hud.OSCURO)
    titulo = hud._recortar(a.titulo, tam, ancho_texto - ancho_chip - 70 * escala)
    hud._texto(x + relleno + ancho_chip + 8 * escala, cy, titulo, tam, _con_alfa(SUAVE, alfa))
    if contador:
        hud._texto(x + ancho - relleno - hud._ancho(contador, tam_chico), cy, contador, tam_chico, _con_alfa(SUAVE, alfa))
    cy -= 10 * escala

    for texto_linea in lineas_texto:
        cy -= tam_grande + 6 * escala
        hud._texto(x + relleno, cy + 4 * escala, texto_linea, tam_grande, _con_alfa(TEXTO, alfa))

    if lineas_linea:
        cy -= 6 * escala
        for i, texto_linea in enumerate(lineas_linea):
            cy -= tam + 5 * escala
            if i == 0:
                hud._punto(shader, x + relleno + 4 * escala, cy + tam * 0.4, 4 * escala, _con_alfa(color_linea, alfa))
            hud._texto(x + relleno + 14 * escala, cy + 2 * escala, texto_linea, tam, _con_alfa(color_linea, alfa))

    if teclas and not demo.activa():
        cy -= tam + 14 * escala
        tx = x + relleno
        for i, tecla in enumerate(teclas[:6]):
            if i:
                hud._texto(tx + 2 * escala, cy + 4 * escala, "›", tam, SUAVE)
                tx += 12 * escala
            tx += hud._tecla(shader, tx, cy + 4 * escala, tecla, tam_chico, escala) + 2 * escala

    if accion:
        # Motor 6.2: qué toca y qué estás haciendo (la luz del acompañamiento lo enciende).
        toca, haciendo_ahora, coincide = accion
        cy -= tam_chico + 12 * escala
        tx = x + relleno
        if toca:
            etiqueta = f"Te toca: {toca}"
            hud._punto(shader, tx + 4 * escala, cy + tam_chico * 0.45, 4 * escala, _con_alfa(hud.NEON, alfa))
            hud._texto(tx + 12 * escala, cy, etiqueta, tam_chico, _con_alfa(TEXTO, alfa))
            tx += hud._ancho(etiqueta, tam_chico) + 28 * escala
        if haciendo_ahora:
            color = hud.VERDE if coincide else COLOR_ESTADO["vacia"]
            etiqueta = f"Estás haciendo: {haciendo_ahora}" + ("  ✓" if coincide else "")
            hud._punto(shader, tx + 4 * escala, cy + tam_chico * 0.45, 4 * escala, _con_alfa(color, alfa))
            hud._texto(tx + 12 * escala, cy, hud._recortar(etiqueta, tam_chico, x + ancho - relleno - tx - 12 * escala),
                       tam_chico, _con_alfa(color, alfa))

    # Pie: avance (piezas o demostración) y los botones.
    fila_y = y + relleno
    alto_boton = 26 * escala
    if st == sesion.MIRANDO or sesion.SESION["mirame"]:
        hud._barra(shader, x + relleno, fila_y + alto_boton / 2 - 3 * escala, 120 * escala, 6 * escala, demo.avance(),
                   acento)
    elif st == sesion.LOGRADA and a.habilidad:
        h = _fase_de(a.habilidad)
        if h is not None:
            hud._barra(shader, x + relleno, fila_y + alto_boton / 2 - 3 * escala, 90 * escala, 6 * escala, h.p,
                       hud.VERDE)
            hud._texto(x + relleno + 98 * escala, fila_y + alto_boton / 2 - tam_chico / 2, FASE.get(h.fase, ""),
                       tam_chico, SUAVE)
    else:
        r = sesion.SESION["revision"]
        if r is not None and r.total:
            px = x + relleno + 5 * escala
            for pieza in r.piezas[:12]:
                color = COLOR_ESTADO.get(pieza.estado, SUAVE) if pieza.estado != "vacia" else (0.4, 0.4, 0.46, 1.0)
                hud._punto(shader, px, fila_y + alto_boton / 2, 4 * escala, color)
                px += 12 * escala
            leyenda = f"{r.llenas} de {r.total} piezas"
            hud._texto(px + 4 * escala, fila_y + alto_boton / 2 - tam_chico / 2, leyenda, tam_chico, SUAVE)

    bx = x + ancho - relleno
    rects = []
    for i, (texto_boton, accion, activo) in enumerate(reversed(lista)):
        indice = len(lista) - 1 - i
        ancho_boton = max(hud._ancho(texto_boton, tam) + 22 * escala, 74 * escala)
        bx -= ancho_boton
        principal = indice == 0
        hover = HOVER["region"] == clave and HOVER["indice"] == indice
        _boton(shader, bx, fila_y, ancho_boton, alto_boton, texto_boton, tam, escala, activo, principal, hover, acento)
        rects.append((indice, (bx, fila_y, bx + ancho_boton, fila_y + alto_boton, accion, activo)))
        bx -= 8 * escala
    BOTONES[clave] = [r for _i, r in sorted(rects)]

    # Mira: las teclas grandes encima de la tarjeta (screencast).
    if demo.activa() and paso_demo is not None and paso_demo.teclas:
        tam_tecla = int(20 * escala)
        anchos = [max(hud._ancho(_motor.terminos.tecla(t), tam_tecla) + 10 * escala, 18 * escala) for t in paso_demo.teclas]
        total = sum(anchos) + 22 * escala * (len(anchos) - 1)
        tx = (region.width - total) / 2
        ty = y + alto + 26 * escala
        for i, tecla in enumerate(paso_demo.teclas):
            if i:
                hud._texto(tx + 4 * escala, ty, "›", tam_tecla, SUAVE)
                tx += 22 * escala
            tx += hud._tecla(shader, tx, ty, tecla, tam_tecla, escala)
    gpu.state.blend_set("NONE")


def boton_en(region, x, y):
    """El índice del botón bajo (x, y) en la región, o -1."""
    clave = region.as_pointer() if region is not None else 0
    for i, (x0, y0, x1, y1, _accion, _activo) in enumerate(BOTONES.get(clave, ())):
        if x0 <= x <= x1 and y0 <= y <= y1:
            return i
    return -1


def accion_de(region, indice):
    clave = region.as_pointer() if region is not None else 0
    lista = BOTONES.get(clave) or []
    if 0 <= indice < len(lista):
        _x0, _y0, _x1, _y1, accion, activo = lista[indice]
        return accion, activo
    # El clic llegó a otra región (o antes de dibujar): la primera que tenga ese botón.
    for otra in BOTONES.values():
        if 0 <= indice < len(otra):
            return otra[indice][4], otra[indice][5]
    return None, False


def pulsar(region, x, y):
    """Para pruebas sin ratón: el botón en (x, y) de la región."""
    indice = boton_en(region, x, y)
    return accion_de(region, indice) if indice >= 0 else (None, False)


__all__ = ["BOTONES", "HOVER", "MAX_BOTONES", "accion_de", "boton_en", "botones", "compacta", "dibujar", "pulsar",
           "raton"]
