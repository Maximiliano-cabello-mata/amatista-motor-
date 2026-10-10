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
"""
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
    a = sesion.actividad()
    st = sesion.estado()
    if a is None:
        return []
    if st == sesion.MIRANDO:
        return [("Repetir", "repetir_demo", True), ("Ahora tú", "ahora_tu", True)]
    if sesion.SESION["mirame"]:
        return [("Ya entendí", "cerrar_demo", True)]
    if st == sesion.PAUSA:
        return [("Seguir", "seguir", True)]
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
    return None, None


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


def dibujar():
    if gpu is None:
        return
    p = ajustes.prefs()
    if p is not None and not p.mostrar_hud:
        return
    contexto = bpy.context
    region = contexto.region
    clave = region.as_pointer() if region is not None else 0
    BOTONES[clave] = []
    if region is None or not sesion.cubre(contexto.scene):
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
    lista = botones()

    alto = relleno + tam_chico + 10 * escala  # cabecera
    alto += len(lineas_texto) * (tam_grande + 6 * escala)
    alto += len(lineas_linea) * (tam + 5 * escala) + (6 * escala if lineas_linea else 0)
    alto += (tam + 14 * escala) if teclas and not demo.activa() else 0
    alto += 30 * escala + relleno  # fila de botones

    entra = _suave((time.time() - sesion.SESION["entrada"]) / ENTRADA) if animaciones() else 1.0
    x = (region.width - ancho) / 2
    y = _region_base(contexto, escala) - (1 - entra) * 16 * escala
    alfa = max(0.15, entra)

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
        anchos = [max(hud._ancho(t, tam_tecla) + 10 * escala, 18 * escala) for t in paso_demo.teclas]
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


__all__ = ["BOTONES", "HOVER", "MAX_BOTONES", "accion_de", "boton_en", "botones", "dibujar", "pulsar"]
