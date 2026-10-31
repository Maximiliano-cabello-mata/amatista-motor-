"""La ficha de una herramienta en la vista 3D (motor 6.1).

Ocupa el lugar de la tarjeta del taller (una sola cosa a la vez) y se lee como
una lección corta, no como un aviso:

    ╭──────────────────────────────────────────────────────────╮
    │ HERRAMIENTA NUEVA · 1 de 2                               │
    │ Escalar                                       [S]        │
    │ Hacer un objeto más grande, más chico, más alto…         │  ← para qué sirve
    │ Como estirar o aplastar plastilina…                      │  ← la comparación
    │ ● En la barra de herramientas (el cuadro con flechas)…   │  ← dónde está (y brilla)
    │ 1 Elige el objeto.   2 Presiona S…                       │  ← «¿Cómo se usa?» abierto
    │ Ojo: Escalar con S solo cuando querías…                  │  ← el error típico
    │              [Entendido] [¿Cómo se usa?] [Ya la conozco] │
    ╰──────────────────────────────────────────────────────────╯

Los botones se tocan igual que los de la tarjeta (sus rectángulos van a
tarjeta.BOTONES y los atrapa el mismo grupo de gizmos).
"""
import time

try:
    import gpu
except ImportError:  # Blender sin GPU (modo background)
    gpu = None

from ... import fichas
from ...interfaz import hud

ANCHO = 600
COLOR = (0.75, 0.52, 1.0, 1.0)
COLOR_CURIOSO = (0.30, 0.82, 0.86, 1.0)
ANALOGIA = (0.80, 0.74, 0.95, 1.0)
OJO = (1.0, 0.70, 0.22, 1.0)


def lineas(f, ancho_texto, tam, tam_grande):
    """[(texto, tamaño, color, sangría, viñeta)] de la ficha, ya partidas al ancho (sin GPU: se prueba)."""
    salida = []
    for texto in hud._partir(f.para_que, tam_grande, ancho_texto, 2):
        salida.append((texto, tam_grande, hud.TEXTO, 0, ""))
    if f.analogia:
        for texto in hud._partir(f.analogia, tam, ancho_texto, 2):
            salida.append((texto, tam, ANALOGIA, 0, ""))
    if f.donde:
        for i, texto in enumerate(hud._partir(f.donde, tam, ancho_texto - 14, 2)):
            salida.append((texto, tam, hud.NEON, 14, "●" if i == 0 else ""))
    if fichas.ESTADO["abierta"]:
        for n, paso in enumerate(f.como[:5], 1):
            for i, texto in enumerate(hud._partir(paso, tam, ancho_texto - 22, 2)):
                salida.append((texto, tam, hud.TEXTO, 22, str(n) if i == 0 else ""))
        if f.error:
            for texto in hud._partir(f"Ojo: {f.error}", tam, ancho_texto, 2):
                salida.append((texto, tam, OJO, 0, ""))
    return salida


def dibujar(contexto, region, clave, base_y, boton, botones_salida, hover):
    """Dibuja la ficha visible. boton(...) es el dibujante de botones de la tarjeta."""
    f = fichas.visible()
    if gpu is None or f is None:
        return False
    escala = contexto.preferences.system.ui_scale or 1.0
    ancho = min(ANCHO * escala, region.width - 32 * escala)
    if ancho < 240 * escala:
        return False
    relleno = 16 * escala
    ancho_texto = ancho - 2 * relleno
    tam, tam_grande, tam_chico, tam_titulo = int(12 * escala), int(14 * escala), int(10 * escala), int(19 * escala)
    acento = COLOR_CURIOSO if fichas.modo() == fichas.CURIOSO else COLOR
    cuerpo = lineas(f, ancho_texto, tam, tam_grande)
    lista = fichas.botones()

    alto = relleno + tam_chico + 10 * escala + tam_titulo + 12 * escala
    alto += sum(t + 6 * escala for _x, t, _c, _s, _v in cuerpo)
    alto += 30 * escala + relleno + 6 * escala
    x = (region.width - ancho) / 2
    y = base_y
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    hud._tarjeta(shader, x, y, ancho, alto, (0.075, 0.065, 0.10, 0.96), acento, escala, radio=10.0)

    cy = y + alto - relleno - tam_chico
    chip = fichas.chip()
    ancho_chip = hud._ancho(chip, tam_chico) + 12 * escala
    hud._panel(shader, x + relleno, cy - 4 * escala, ancho_chip, tam_chico + 8 * escala, acento, 4 * escala)
    hud._texto(x + relleno + 6 * escala, cy, chip, tam_chico, hud.OSCURO)
    if f.ingles:
        ingles = hud._recortar(f"En inglés: {f.ingles}", tam_chico, ancho_texto - ancho_chip - 20 * escala)
        hud._texto(x + ancho - relleno - hud._ancho(ingles, tam_chico), cy, ingles, tam_chico, hud.TEXTO_SUAVE)
    cy -= 12 * escala + tam_titulo
    hud._texto(x + relleno, cy + 2 * escala, f.nombre, tam_titulo, hud.TEXTO)
    tx = x + relleno + hud._ancho(f.nombre, tam_titulo) + 12 * escala
    for i, tecla in enumerate(f.teclas[:3]):
        if i:
            hud._texto(tx, cy + 4 * escala, "·", tam, hud.TEXTO_SUAVE)
            tx += 10 * escala
        tx += hud._tecla(shader, tx, cy + 4 * escala, tecla, tam_chico, escala) + 4 * escala

    for texto, t, color, sangria, vineta in cuerpo:
        cy -= t + 6 * escala
        if vineta == "●":
            hud._punto(shader, x + relleno + 4 * escala, cy + t * 0.4, 4 * escala, color)
        elif vineta:
            hud._texto(x + relleno, cy + 2 * escala, vineta, t, acento)
        hud._texto(x + relleno + sangria * escala, cy + 2 * escala, texto, t, color)

    fila_y = y + relleno
    alto_boton = 26 * escala
    bx = x + ancho - relleno
    rects = []
    for i, (texto_boton, accion, activo) in enumerate(reversed(lista)):
        indice = len(lista) - 1 - i
        ancho_boton = max(hud._ancho(texto_boton, tam) + 22 * escala, 74 * escala)
        bx -= ancho_boton
        encima = hover["region"] == clave and hover["indice"] == indice
        boton(shader, bx, fila_y, ancho_boton, alto_boton, texto_boton, tam, escala, activo, indice == 0, encima, acento)
        rects.append((indice, (bx, fila_y, bx + ancho_boton, fila_y + alto_boton, accion, activo)))
        bx -= 8 * escala
    botones_salida[clave] = [r for _i, r in sorted(rects)]
    if fichas.modo() == fichas.CURIOSO:
        queda = max(0.0, fichas.ESTADO["hasta"] - time.time())
        total = fichas.DURA_ABIERTA if fichas.ESTADO["abierta"] else fichas.DURA_CURIOSO
        hud._barra(shader, x + relleno, fila_y + alto_boton / 2 - 2 * escala, 80 * escala, 4 * escala,
                   queda / total if total else 0.0, acento)
    gpu.state.blend_set("NONE")
    return True


__all__ = ["dibujar", "lineas"]
