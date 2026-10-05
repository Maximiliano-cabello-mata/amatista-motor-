"""Plano del modelo de referencia en SVG (motor 3.3), sin Blender.

Dibuja la figura de «reference» en tres vistas, como las teclas del teclado
numérico de Blender: de frente (1), de lado (3) y desde arriba (7), con las
medidas generales APROXIMADAS y la holgura que acepta figure.resembles.
Lo escribe engine/herramientas/referencias.py junto a la imagen renderizada
(plano.svg en la carpeta de cada práctica) y lo muestran el add-on y la
plataforma en «Así se debe ver».
"""
from __future__ import annotations

from html import escape
from typing import Dict, List, Sequence, Tuple

from ..models import ReferenceModel, ReferencePart
from ..validators.figure import caja_de_pieza

ANCHO, ALTO = 960, 400
PANEL = 300
VISTAS = (("De frente (1)", 0, 2), ("De lado (3)", 1, 2), ("Desde arriba (7)", 0, 1))
FONDO, LINEA, TEXTO, SUAVE = "#0f2747", "#cfe3ff", "#eaf3ff", "#5b7fb0"


def _caja(p: ReferencePart):
    return caja_de_pieza({"size": p.size, "location": p.location, "rotation": p.rotation})


def _numero(valor: float) -> str:
    return f"{valor:.1f}".rstrip("0").rstrip(".") if valor < 10 else f"{valor:.0f}"


def _figura(p: ReferencePart, x0, y0, x1, y1, eje_h: int, eje_v: int, color: str, extra: str) -> str:
    ancho, alto = x1 - x0, y1 - y0
    girada = any(abs(a) > 1 for a in p.rotation)
    if p.primitive in ("sphere", "icosphere"):
        return (f'<ellipse cx="{x0 + ancho / 2:.1f}" cy="{y0 + alto / 2:.1f}" rx="{ancho / 2:.1f}" '
                f'ry="{alto / 2:.1f}" fill="{color}" {extra}/>')
    if p.primitive == "cone" and not girada and eje_v == 2:
        return (f'<polygon points="{x0:.1f},{y1:.1f} {x1:.1f},{y1:.1f} {x0 + ancho / 2:.1f},{y0:.1f}" '
                f'fill="{color}" {extra}/>')
    redondo = p.primitive in ("cylinder", "cone", "torus")
    # Un cilindro visto por su eje es un círculo (las ruedas desde el frente o el lado).
    if redondo and abs(ancho - alto) < 0.08 * max(ancho, alto, 1e-6) and (girada or eje_v != 2):
        return (f'<ellipse cx="{x0 + ancho / 2:.1f}" cy="{y0 + alto / 2:.1f}" rx="{ancho / 2:.1f}" '
                f'ry="{alto / 2:.1f}" fill="{color}" {extra}/>')
    radio = min(ancho, alto) * (0.25 if redondo else 0.06)
    return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{max(ancho, 0.8):.1f}" height="{max(alto, 0.8):.1f}" '
            f'rx="{radio:.1f}" fill="{color}" {extra}/>')


def plano_svg(referencia: ReferenceModel, titulo: str = "", etiquetas: Dict[str, str] = None) -> str:
    """El SVG del plano (texto). etiquetas: {rol: nombre para el alumno}."""
    etiquetas = etiquetas or {}
    piezas = [p for p in referencia.parts if p.primitive != "plane"]
    comparadas = [p for p in piezas if p.compare] or piezas
    if not piezas:
        return ""
    cajas = {id(p): _caja(p) for p in piezas}
    minimo = [min(cajas[id(p)][0][i] for p in comparadas) for i in range(3)]
    maximo = [max(cajas[id(p)][1][i] for p in comparadas) for i in range(3)]
    tolerancia = round(referencia.tolerance * 100)
    salida: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="{ANCHO}" height="{ALTO}" '
        f'font-family="system-ui, sans-serif" role="img" aria-label="Plano de {escape(titulo or referencia.title)}">',
        f'<rect width="{ANCHO}" height="{ALTO}" rx="18" fill="{FONDO}"/>',
        '<defs><pattern id="cuadricula" width="20" height="20" patternUnits="userSpaceOnUse">'
        f'<path d="M20 0H0V20" fill="none" stroke="{SUAVE}" stroke-opacity=".35" stroke-width=".6"/></pattern></defs>',
        f'<rect x="12" y="12" width="{ANCHO - 24}" height="{ALTO - 24}" rx="12" fill="url(#cuadricula)"/>',
        f'<text x="28" y="44" fill="{TEXTO}" font-size="20" font-weight="700">Plano: {escape(titulo or referencia.title)}</text>',
    ]
    for n, (nombre, eje_h, eje_v) in enumerate(VISTAS):
        ox = 28 + n * (PANEL + 12)
        oy = 70
        lado_h = max(maximo[eje_h] - minimo[eje_h], 1e-6)
        lado_v = max(maximo[eje_v] - minimo[eje_v], 1e-6)
        escala = min((PANEL - 60) / lado_h, (PANEL - 110) / lado_v)
        cx = ox + PANEL / 2 - (minimo[eje_h] + lado_h / 2) * escala
        cy = oy + 30 + (PANEL - 110) / 2 + (minimo[eje_v] + lado_v / 2) * escala
        salida.append(f'<rect x="{ox}" y="{oy}" width="{PANEL}" height="{PANEL - 30}" rx="10" fill="none" '
                      f'stroke="{SUAVE}" stroke-dasharray="4 4"/>')
        salida.append(f'<text x="{ox + 12}" y="{oy + 22}" fill="{TEXTO}" font-size="14" font-weight="600">{nombre}</text>')
        # De frente y de lado: lo de atrás se dibuja primero; desde arriba: lo de abajo primero.
        profundidad = 2 if eje_v == 1 else (1 if eje_h == 0 else 0)
        signo = 1 if eje_v == 1 else -1
        orden = sorted(piezas, key=lambda p: signo * -(cajas[id(p)][0][profundidad] + cajas[id(p)][1][profundidad]))
        for p in orden:
            (a, b) = cajas[id(p)]
            x0, x1 = cx + a[eje_h] * escala, cx + b[eje_h] * escala
            y0, y1 = cy - b[eje_v] * escala, cy - a[eje_v] * escala
            color = p.color or "#9b7bff"
            extra = (f'fill-opacity=".55" stroke="{LINEA}" stroke-width="1.4"' if p.compare
                     else f'fill-opacity=".15" stroke="{SUAVE}" stroke-dasharray="3 3"')
            salida.append(_figura(p, x0, y0, x1, y1, eje_h, eje_v, color, extra))
        # Cotas generales (aproximadas)
        bx0, bx1 = cx + minimo[eje_h] * escala, cx + maximo[eje_h] * escala
        by0, by1 = cy - maximo[eje_v] * escala, cy - minimo[eje_v] * escala
        abajo = by1 + 22
        salida.append(f'<path d="M{bx0:.1f} {abajo:.1f}H{bx1:.1f}M{bx0:.1f} {abajo - 5:.1f}v10M{bx1:.1f} {abajo - 5:.1f}v10" '
                      f'stroke="{LINEA}" stroke-width="1.2"/>')
        salida.append(f'<text x="{(bx0 + bx1) / 2:.1f}" y="{abajo + 16:.1f}" fill="{TEXTO}" font-size="13" '
                      f'text-anchor="middle">≈ {_numero(lado_h)} m</text>')
        izquierda = bx0 - 16
        salida.append(f'<path d="M{izquierda:.1f} {by0:.1f}V{by1:.1f}M{izquierda - 5:.1f} {by0:.1f}h10M{izquierda - 5:.1f} {by1:.1f}h10" '
                      f'stroke="{LINEA}" stroke-width="1.2"/>')
        salida.append(f'<text x="{izquierda - 8:.1f}" y="{(by0 + by1) / 2:.1f}" fill="{TEXTO}" font-size="13" '
                      f'text-anchor="middle" transform="rotate(-90 {izquierda - 8:.1f} {(by0 + by1) / 2:.1f})">'
                      f'≈ {_numero(lado_v)} m</text>')
    # Piezas por grupo y holgura
    grupos: Dict[str, int] = {}
    for p in comparadas:
        grupos[p.group] = grupos.get(p.group, 0) + (0 if p.join and any(
            q.join == p.join and q is not p and comparadas.index(q) < comparadas.index(p) for q in comparadas) else 1)
    nombres = {"cube": "cubo", "cylinder": "cilindro", "sphere": "esfera", "icosphere": "icoesfera",
               "cone": "cono", "torus": "dona"}
    lista = " · ".join(f"{n} × {etiquetas.get(g) or nombres.get(g, g)}" for g, n in grupos.items() if n)
    salida.append(f'<text x="28" y="{ALTO - 40}" fill="{TEXTO}" font-size="14">Piezas: {escape(lista)}</text>')
    salida.append(f'<text x="28" y="{ALTO - 20}" fill="{LINEA}" font-size="13">Medidas aproximadas: ±{tolerancia} % está bien. '
                  'Tu figura puede ser más grande o más chica y estar girada; lo que cuenta es que se vea así.</text>')
    salida.append("</svg>")
    return "\n".join(salida) + "\n"


def medidas_generales(referencia: ReferenceModel) -> Tuple[float, float, float]:
    piezas = [p for p in referencia.parts if p.compare and p.primitive != "plane"]
    cajas = [_caja(p) for p in piezas]
    if not cajas:
        return (0.0, 0.0, 0.0)
    return tuple(round(max(c[1][i] for c in cajas) - min(c[0][i] for c in cajas), 2) for i in range(3))


__all__: Sequence[str] = ("plano_svg", "medidas_generales")
