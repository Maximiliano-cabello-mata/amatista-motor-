"""Genera la pantalla de inicio de «Blender Amatista» (motor 6).

Blender muestra ``splash.png`` (501 × 250) y ``splash_2x.png`` (1002 × 500)
de la plantilla de aplicación en lugar de la suya. Fondo low poly con los
colores de Amatista (la identidad del sistema «Facetas»), la gema y el nombre.

    python addon/herramientas/generar_splash.py

Necesita Pillow (solo para generar: los PNG quedan en el repositorio).
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DESTINO = Path(__file__).resolve().parents[1] / "amatista_blender" / "plantilla_amatista"
FONDO_1 = (22, 12, 34)
FONDO_2 = (60, 26, 84)
AMATISTA = (155, 89, 182)
AMATISTA_CLARO = (195, 155, 211)
NEON = (0, 229, 255)
BLANCO = (245, 245, 250)
FUENTES = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
FUENTES_FINAS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf")


def _fuente(candidatas, tam):
    for ruta in candidatas:
        try:
            return ImageFont.truetype(ruta, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _mezcla(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def splash(ancho, alto, semilla=7):
    escala = ancho / 1002
    azar = random.Random(semilla)
    img = Image.new("RGB", (ancho, alto), FONDO_1)
    dibujo = ImageDraw.Draw(img)
    # Facetas: una malla de triángulos con un degradado de abajo a la izquierda hacia arriba a la derecha.
    paso = int(84 * escala)
    puntos = {}
    for i in range(-1, ancho // paso + 3):
        for j in range(-1, alto // paso + 3):
            puntos[i, j] = (i * paso + azar.randint(-paso // 3, paso // 3), j * paso + azar.randint(-paso // 3, paso // 3))
    for (i, j), p in puntos.items():
        derecha, abajo, diagonal = puntos.get((i + 1, j)), puntos.get((i, j + 1)), puntos.get((i + 1, j + 1))
        if not (derecha and abajo and diagonal):
            continue
        for tri in ((p, derecha, diagonal), (p, diagonal, abajo)):
            cx = sum(x for x, _ in tri) / 3 / ancho
            cy = sum(y for _, y in tri) / 3 / alto
            t = max(0.0, min(1.0, 0.65 * cx + 0.35 * (1 - cy) + azar.uniform(-0.08, 0.08)))
            dibujo.polygon(tri, fill=_mezcla(FONDO_1, FONDO_2, t), outline=_mezcla(FONDO_2, AMATISTA, 0.25))
    # La gema (el logo): un octaedro facetado con su brillo.
    cx, cy, r = int(250 * escala), alto // 2, int(118 * escala)
    brillo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    ImageDraw.Draw(brillo).ellipse((cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5), fill=(*AMATISTA, 90))
    img.paste(brillo.filter(ImageFilter.GaussianBlur(40 * escala)), (0, 0), brillo.filter(ImageFilter.GaussianBlur(40 * escala)))
    dibujo = ImageDraw.Draw(img)
    arriba, abajo, izq, der = (cx, cy - r), (cx, cy + r), (cx - int(r * 0.72), cy), (cx + int(r * 0.72), cy)
    centro = (cx + int(r * 0.12), cy - int(r * 0.1))
    caras = (
        ((arriba, izq, centro), AMATISTA_CLARO),
        ((arriba, centro, der), _mezcla(AMATISTA_CLARO, AMATISTA, 0.5)),
        ((izq, abajo, centro), AMATISTA),
        ((centro, abajo, der), _mezcla(AMATISTA, FONDO_2, 0.45)),
    )
    for tri, color in caras:
        dibujo.polygon(tri, fill=color, outline=_mezcla(color, BLANCO, 0.35))
    dibujo.line((arriba, centro, abajo), fill=_mezcla(AMATISTA_CLARO, BLANCO, 0.5), width=max(1, int(2 * escala)))
    # El nombre.
    x = int(440 * escala)
    dibujo.text((x, int(150 * escala)), "Blender", font=_fuente(FUENTES_FINAS, int(46 * escala)), fill=AMATISTA_CLARO)
    dibujo.text((x, int(200 * escala)), "Amatista", font=_fuente(FUENTES, int(92 * escala)), fill=BLANCO)
    dibujo.rectangle((x, int(318 * escala), x + int(120 * escala), int(324 * escala)), fill=NEON)
    dibujo.text((x, int(340 * escala)), "Aprende 3D paso a paso con la plataforma",
                font=_fuente(FUENTES_FINAS, int(20 * escala)), fill=_mezcla(AMATISTA_CLARO, BLANCO, 0.4))
    return img


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    splash(1002, 500).save(DESTINO / "splash_2x.png", optimize=True)
    splash(1002, 500).resize((501, 250), Image.LANCZOS).save(DESTINO / "splash.png", optimize=True)
    print(f"Pantallas de inicio en {DESTINO}")


if __name__ == "__main__":
    main()
