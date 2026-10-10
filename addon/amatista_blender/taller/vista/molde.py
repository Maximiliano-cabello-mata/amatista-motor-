"""El molde: cada pieza del modelo, translúcida, en su lugar de la vista 3D.

No crea objetos en la escena del alumno: se dibuja con gpu (POST_VIEW) y
el revisor nunca lo ve. Cada pieza tiene el color de su estado:

- azul: todavía vacía;
- ámbar (respira): la que toca ahora;
- verde: una pieza del alumno la llena;
- coral: hay algo, pero no es eso (otra forma, girada, de otro tamaño).

En «Hazlo tú» con piezas de inicio solo se dibuja la **marca**: la huella
de cada pieza en el suelo, sin volumen (dónde va, no cómo es).
"""
import math
import time

import bpy
from mathutils import Euler, Matrix, Vector

try:
    import gpu
    from gpu_extras.batch import batch_for_shader
except ImportError:  # Blender sin GPU (modo background)
    gpu = batch_for_shader = None

AZUL = (0.36, 0.62, 1.0)
AMBAR = (1.0, 0.70, 0.22)
VERDE = (0.35, 0.84, 0.55)
CORAL = (1.0, 0.45, 0.40)
COLOR_ESTADO = {"vacia": AZUL, "llena": VERDE, "casi": CORAL, "equivocada": CORAL}
LADOS = 24

_CACHE = {"clave": None, "formas": []}


def _cubo():
    v = [Vector((x, y, z)) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
    caras = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = [t for a, b, c, d in caras for t in ((a, b, c), (a, c, d))]
    aristas = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return v, tris, aristas


def _cilindro(arriba=0.5):
    """Cilindro (o cono si arriba=0) de radio 0.5 y alto 1."""
    v, tris, aristas = [], [], []
    for i in range(LADOS):
        a = 2 * math.pi * i / LADOS
        v.append(Vector((0.5 * math.cos(a), 0.5 * math.sin(a), -0.5)))
        v.append(Vector((arriba * math.cos(a), arriba * math.sin(a), 0.5)))
    abajo_c, arriba_c = len(v), len(v) + 1
    v += [Vector((0, 0, -0.5)), Vector((0, 0, 0.5))]
    for i in range(LADOS):
        j = (i + 1) % LADOS
        a0, a1, b0, b1 = 2 * i, 2 * i + 1, 2 * j, 2 * j + 1
        tris += [(a0, b0, b1), (a0, b1, a1), (abajo_c, b0, a0), (arriba_c, a1, b1)]
        aristas += [(a0, b0), (a1, b1)]
        if i % 6 == 0:
            aristas.append((a0, a1))
    return v, tris, aristas


def _esfera():
    v, tris, aristas = [], [], []
    filas, cols = 10, LADOS
    for r in range(filas + 1):
        fi = math.pi * r / filas
        for c in range(cols):
            te = 2 * math.pi * c / cols
            v.append(Vector((0.5 * math.sin(fi) * math.cos(te), 0.5 * math.sin(fi) * math.sin(te), 0.5 * math.cos(fi))))
    for r in range(filas):
        for c in range(cols):
            a, b = r * cols + c, r * cols + (c + 1) % cols
            d, e = a + cols, b + cols
            tris += [(a, b, e), (a, e, d)]
            if r == filas // 2:
                aristas.append((a, b))  # el ecuador
            if c % 6 == 0:
                aristas.append((a, d))  # cuatro meridianos
    return v, tris, aristas


def _plano():
    v = [Vector((x, y, 0.0)) for x in (-0.5, 0.5) for y in (-0.5, 0.5)]
    return v, [(0, 1, 3), (0, 3, 2)], [(0, 1), (1, 3), (3, 2), (2, 0)]


FORMAS = {
    "cube": _cubo(), "cylinder": _cilindro(), "cone": _cilindro(0.0), "sphere": _esfera(), "uv_sphere": _esfera(),
    "icosphere": _esfera(), "plane": _plano(), "torus": _cilindro(),
}


def matriz(pieza):
    medidas = [max(0.001, float(v)) for v in (pieza.get("size") or (2, 2, 2))]
    giro = Euler([math.radians(float(g)) for g in (pieza.get("rotation") or (0, 0, 0))], "XYZ")
    loc = Vector([float(v) for v in (pieza.get("location") or (0, 0, 0))])
    return Matrix.Translation(loc) @ giro.to_matrix().to_4x4() @ Matrix.Diagonal((*medidas, 1.0))


def puntos(pieza):
    """(vértices en el mundo, triángulos, aristas) de la pieza."""
    v, tris, aristas = FORMAS.get(str(pieza.get("primitive") or "cube"), FORMAS["cube"])
    m = matriz(pieza)
    return [m @ p for p in v], tris, aristas


def huella(pieza):
    """El contorno de la pieza en el suelo (la «marca»), a la altura de su base."""
    mundo, _tris, _aristas = puntos(pieza)
    base = min(p.z for p in mundo) + 0.004
    primitiva = str(pieza.get("primitive") or "cube")
    if primitiva in ("cylinder", "cone", "sphere", "uv_sphere", "icosphere"):
        xs, ys = [p.x for p in mundo], [p.y for p in mundo]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        rx, ry = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
        contorno = [Vector((cx + rx * math.cos(2 * math.pi * i / LADOS), cy + ry * math.sin(2 * math.pi * i / LADOS),
                            base)) for i in range(LADOS)]
    else:
        xs, ys = [p.x for p in mundo], [p.y for p in mundo]
        contorno = [Vector((min(xs), min(ys), base)), Vector((max(xs), min(ys), base)),
                    Vector((max(xs), max(ys), base)), Vector((min(xs), max(ys), base))]
    centro = sum(contorno, Vector()) / len(contorno)
    tris = [(len(contorno), i, (i + 1) % len(contorno)) for i in range(len(contorno))]
    return contorno + [centro], tris, [(i, (i + 1) % len(contorno)) for i in range(len(contorno))]


def _formas(piezas, marca):
    clave = (id(piezas), len(piezas), marca)
    if _CACHE["clave"] != clave:
        _CACHE["formas"] = [huella(p) if marca else puntos(p) for p in piezas]
        _CACHE["clave"] = clave
    return _CACHE["formas"]


def _pulso():
    return 0.5 + 0.5 * math.sin(time.time() * 3.2)


def _shader_lineas():
    try:
        shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
        region = bpy.context.region
        shader.uniform_float("viewportSize", (region.width, region.height))
        shader.uniform_float("lineWidth", 2.0)
        return shader
    except (ValueError, AttributeError, TypeError):
        return gpu.shader.from_builtin("UNIFORM_COLOR")


def dibujar(piezas, estados, actual, marca=False, reducir_movimiento=False):
    """Dibuja el molde. estados: un estado por pieza (vacia, llena, casi, equivocada); actual: índice o None."""
    if gpu is None or not piezas:
        return
    formas = _formas(piezas, marca)
    relleno = gpu.shader.from_builtin("UNIFORM_COLOR")
    lineas = _shader_lineas()
    gpu.state.blend_set("ALPHA")
    gpu.state.depth_mask_set(False)
    pulso = 1.0 if reducir_movimiento else _pulso()
    for i, (mundo, tris, aristas) in enumerate(formas):
        estado = estados[i] if i < len(estados) else "vacia"
        color = AMBAR if i == actual and estado != "llena" else COLOR_ESTADO.get(estado, AZUL)
        alfa_cara = 0.10 if estado == "llena" else (0.16 + 0.12 * pulso if i == actual else 0.13)
        alfa_linea = 0.45 if estado == "llena" else (0.6 + 0.35 * pulso if i == actual else 0.55)
        # Las caras, sin tapar lo del alumno: se ven a través de lo que está delante.
        gpu.state.depth_test_set("LESS_EQUAL")
        batch = batch_for_shader(relleno, "TRIS", {"pos": mundo}, indices=tris)
        relleno.uniform_float("color", (*color, alfa_cara))
        batch.draw(relleno)
        # Las aristas, siempre visibles (un poco más tenues detrás de los objetos).
        gpu.state.depth_test_set("NONE")
        segmentos = [mundo[k] for arista in aristas for k in arista]
        batch = batch_for_shader(lineas, "LINES", {"pos": segmentos})
        lineas.uniform_float("color", (*color, alfa_linea * 0.55))
        batch.draw(lineas)
        gpu.state.depth_test_set("LESS_EQUAL")
        lineas.uniform_float("color", (*color, alfa_linea))
        batch.draw(lineas)
    gpu.state.depth_test_set("NONE")
    gpu.state.depth_mask_set(True)
    gpu.state.blend_set("NONE")
