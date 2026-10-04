"""Genera los íconos PNG del add-on con la identidad de Amatista.

Sin dependencias (solo zlib): polígonos rellenos con antialiasing por
supermuestreo. Colores de docs/arquitectura/2026-09-28_identidad_visual_interfaz.txt.

    python addon/herramientas/generar_iconos.py
"""
import math
import struct
import zlib
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "amatista_blender" / "iconos"
TAM = 64
MUESTRAS = 4

AMATISTA = (155, 89, 182)
AMATISTA_CLARO = (195, 155, 211)
AMATISTA_OSCURO = (91, 44, 111)
NEON = (0, 229, 255)
GRIS = (120, 120, 128)
GRIS_CLARO = (170, 170, 178)
BLANCO = (245, 245, 250)
NARANJA = (245, 121, 42)
VERDE = (88, 214, 141)


def lienzo():
    return [[(0, 0, 0, 0) for _ in range(TAM)] for _ in range(TAM)]


def dentro(px, py, puntos):
    resultado = False
    j = len(puntos) - 1
    for i in range(len(puntos)):
        xi, yi = puntos[i]
        xj, yj = puntos[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
            resultado = not resultado
        j = i
    return resultado


def mezclar(fondo, color, alfa):
    r, g, b, a = fondo
    fa = a / 255.0
    na = alfa + fa * (1 - alfa)
    if na <= 0:
        return (0, 0, 0, 0)
    canal = lambda c, f: int((c * alfa + f * fa * (1 - alfa)) / na)  # noqa: E731
    return (canal(color[0], r), canal(color[1], g), canal(color[2], b), int(na * 255))


def poligono(img, puntos, color, opacidad=1.0):
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    for y in range(max(0, int(min(ys)) - 1), min(TAM, int(max(ys)) + 2)):
        for x in range(max(0, int(min(xs)) - 1), min(TAM, int(max(xs)) + 2)):
            cubiertas = sum(
                dentro(x + (i + 0.5) / MUESTRAS, y + (j + 0.5) / MUESTRAS, puntos)
                for i in range(MUESTRAS)
                for j in range(MUESTRAS)
            )
            if cubiertas:
                img[y][x] = mezclar(img[y][x], color, opacidad * cubiertas / MUESTRAS**2)


def circulo(img, cx, cy, radio, color, opacidad=1.0, lados=48):
    poligono(
        img,
        [(cx + radio * math.cos(2 * math.pi * k / lados), cy + radio * math.sin(2 * math.pi * k / lados)) for k in range(lados)],
        color,
        opacidad,
    )


def anillo(img, cx, cy, radio, grosor, color, lados=48):
    exterior = [(cx + radio * math.cos(2 * math.pi * k / lados), cy + radio * math.sin(2 * math.pi * k / lados)) for k in range(lados)]
    interior = [
        (cx + (radio - grosor) * math.cos(2 * math.pi * k / lados), cy + (radio - grosor) * math.sin(2 * math.pi * k / lados))
        for k in range(lados)
    ]
    for k in range(lados):
        poligono(img, [exterior[k], exterior[(k + 1) % lados], interior[(k + 1) % lados], interior[k]], color)


def linea(img, a, b, grosor, color):
    dx, dy = b[0] - a[0], b[1] - a[1]
    largo = math.hypot(dx, dy) or 1
    nx, ny = -dy / largo * grosor / 2, dx / largo * grosor / 2
    poligono(img, [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], color)


def gema(img, cx, cy, escala, base, claro, oscuro, filo=None):
    """Cristal de amatista low poly de seis caras (el logo de la PWA)."""
    s = escala
    arriba = (cx, cy - 26 * s)
    abajo = (cx, cy + 26 * s)
    izq_a, der_a = (cx - 18 * s, cy - 10 * s), (cx + 18 * s, cy - 10 * s)
    izq_b, der_b = (cx - 18 * s, cy + 10 * s), (cx + 18 * s, cy + 10 * s)
    centro = (cx + 2 * s, cy - 2 * s)
    poligono(img, [arriba, izq_a, centro], claro)
    poligono(img, [arriba, centro, der_a], base)
    poligono(img, [izq_a, izq_b, centro], base)
    poligono(img, [centro, der_a, der_b], oscuro)
    poligono(img, [izq_b, abajo, centro], oscuro)
    poligono(img, [centro, abajo, der_b], base)
    if filo:
        for a, b in ((arriba, der_a), (der_a, der_b), (der_b, abajo)):
            linea(img, a, b, 2.2 * s, filo)


def check(img, color, cx=32, cy=33, s=1.0):
    linea(img, (cx - 12 * s, cy), (cx - 3 * s, cy + 9 * s), 6 * s, color)
    linea(img, (cx - 4 * s, cy + 9 * s), (cx + 13 * s, cy - 10 * s), 6 * s, color)


def png(img, ruta):
    filas = b"".join(b"\x00" + bytes(c for px in fila for c in px) for fila in img)

    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)

    contenido = (
        b"\x89PNG\r\n\x1a\n"
        + bloque(b"IHDR", struct.pack(">IIBBBBB", TAM, TAM, 8, 6, 0, 0, 0))
        + bloque(b"IDAT", zlib.compress(filas, 9))
        + bloque(b"IEND", b"")
    )
    ruta.write_bytes(contenido)


def generar():
    DESTINO.mkdir(parents=True, exist_ok=True)
    iconos = {}

    img = lienzo()
    gema(img, 32, 32, 1.15, AMATISTA, AMATISTA_CLARO, AMATISTA_OSCURO, filo=NEON)
    iconos["logo"] = img

    img = lienzo()
    circulo(img, 32, 32, 27, AMATISTA)
    check(img, BLANCO)
    iconos["completado"] = img

    img = lienzo()
    anillo(img, 32, 32, 27, 6, NEON)
    circulo(img, 32, 32, 11, NEON)
    iconos["actual"] = img

    img = lienzo()
    anillo(img, 32, 32, 26, 4, GRIS)
    iconos["pendiente"] = img

    img = lienzo()
    circulo(img, 32, 32, 27, (70, 70, 78))
    poligono(img, [(20, 30), (44, 30), (44, 48), (20, 48)], GRIS_CLARO)
    anillo(img, 32, 30, 10, 4, GRIS_CLARO)
    poligono(img, [(20, 30), (44, 30), (44, 33), (20, 33)], GRIS_CLARO)
    iconos["bloqueado"] = img

    img = lienzo()
    circulo(img, 32, 26, 17, NARANJA)
    poligono(img, [(24, 38), (40, 38), (38, 48), (26, 48)], NARANJA)
    poligono(img, [(25, 50), (39, 50), (37, 55), (27, 55)], GRIS_CLARO)
    circulo(img, 27, 21, 5, (255, 220, 170), 0.8)
    iconos["pista"] = img

    img = lienzo()
    gema(img, 32, 32, 1.15, (40, 160, 180), (120, 230, 245), (10, 90, 110), filo=BLANCO)
    iconos["autor"] = img

    img = lienzo()
    gema(img, 32, 34, 0.85, AMATISTA, AMATISTA_CLARO, AMATISTA_OSCURO)
    for k in range(8):
        angulo = 2 * math.pi * k / 8
        linea(img, (32 + 22 * math.cos(angulo), 34 + 22 * math.sin(angulo)),
              (32 + 30 * math.cos(angulo), 34 + 30 * math.sin(angulo)), 3, NEON)
    iconos["celebrar"] = img

    img = lienzo()
    circulo(img, 32, 32, 27, VERDE)
    check(img, BLANCO)
    iconos["sincronizado"] = img

    for nombre, imagen in iconos.items():
        png(imagen, DESTINO / f"{nombre}.png")
    return sorted(iconos)


if __name__ == "__main__":
    print("Íconos:", ", ".join(generar()))
