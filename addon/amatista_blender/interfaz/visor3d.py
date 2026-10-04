"""La guía dibujada DENTRO de la escena (etapa 2).

En vez de leer «la pata 4 está muy alta» en una tabla, el alumno lo ve:

- Resaltados: contorno de la caja de cada objeto del paso.
  Verde = ya cumple («✓ Pata»), naranja = hay que cambiarlo («Bájala»),
  neón tenue = candidato («¿Es la cubierta?»).
- Señales (VisualCue del motor):
  ruler   regla junto al objeto: en verde el rango pedido, en naranja lo que
          mide ahora.
  plane   plano translúcido (por ejemplo, la cara de abajo de la cubierta:
          ahí tienen que tocar las patas).
  ghosts  cajas fantasma donde falta una pieza (las patas que faltan).
  arrow   flecha hacia arriba o abajo sobre el objeto.

POST_VIEW dibuja líneas y superficies en 3D; POST_PIXEL pone las etiquetas
(pastillas de texto) proyectadas sobre la pantalla. Nada de esto modifica la
escena ni se guarda en el .blend.
"""
import bpy
from mathutils import Vector

try:
    import blf
    import gpu
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    from gpu_extras.batch import batch_for_shader
except ImportError:  # sin GPU
    blf = gpu = batch_for_shader = location_3d_to_region_2d = None

from .. import ajustes, guia

COLOR_RESALTE = {
    "bien": (0.35, 0.84, 0.55, 0.9),
    "corregir": (1.0, 0.62, 0.26, 1.0),
    "candidato": (0.0, 0.898, 1.0, 0.55),
}
NEON = (0.0, 0.898, 1.0, 1.0)
AMATISTA = (0.608, 0.349, 0.714, 1.0)
NARANJA = (1.0, 0.62, 0.26, 1.0)
VERDE = (0.35, 0.84, 0.55, 1.0)
FONDO = (0.07, 0.07, 0.08, 0.88)
TEXTO = (0.92, 0.92, 0.92, 1.0)

ARISTAS_CAJA = ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7))
CARAS_CAJA = ((0, 1, 3), (0, 3, 2), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
              (0, 2, 6), (0, 6, 4), (1, 3, 7), (1, 7, 5))


def _activo():
    """La guía se dibuja si hay práctica, guía y las preferencias lo permiten."""
    if gpu is None:
        return None
    p = ajustes.prefs()
    if p is not None and (not p.mostrar_hud or not p.resaltar_3d or p.acompanamiento == "silencioso"):
        return None
    escena = bpy.context.scene
    if escena is None or not escena.amatista.practica_json:
        return None
    return guia.guia_actual()


def caja_mundo(obj):
    """Ocho esquinas de la caja del objeto en coordenadas del mundo, en el
    orden (x, y, z) ∈ {mín, máx}³ que usan ARISTAS_CAJA y CARAS_CAJA."""
    esquinas = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs, ys, zs = ([c[i] for c in esquinas] for i in range(3))
    minimo, maximo = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
    return caja_desde(minimo, maximo)


def caja_desde(minimo, maximo):
    return [
        Vector((x, y, z))
        for x in (minimo[0], maximo[0])
        for y in (minimo[1], maximo[1])
        for z in (minimo[2], maximo[2])
    ]


def _shader_lineas():
    try:
        shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
        region = bpy.context.region
        shader.uniform_float("viewportSize", (region.width, region.height))
        shader.uniform_float("lineWidth", 2.5)
        return shader
    except (ValueError, AttributeError, TypeError):
        return gpu.shader.from_builtin("UNIFORM_COLOR")


def _lineas(shader, puntos, color):
    if not puntos:
        return
    batch = batch_for_shader(shader, "LINES", {"pos": puntos})
    shader.uniform_float("color", color)
    batch.draw(shader)


def _relleno(puntos, indices, color):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=indices)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _aristas(esquinas):
    return [esquinas[i] for arista in ARISTAS_CAJA for i in arista]


def _objeto(nombre):
    obj = bpy.data.objects.get(nombre)
    return obj if obj is not None and obj.visible_get() else None


def dibujar_escena():
    g = _activo()
    if g is None:
        return
    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("NONE")
    lineas = _shader_lineas()
    for resalte in g.highlights:
        obj = _objeto(resalte.object_name)
        if obj is not None:
            _lineas(lineas, _aristas(caja_mundo(obj)), COLOR_RESALTE.get(resalte.kind, NEON))
    for senal in g.cues:
        d = senal.data
        if senal.kind == "ghosts":
            for caja in d.get("boxes", []):
                centro, medida = Vector(caja["center"]), Vector(caja["size"]) / 2
                esquinas = caja_desde(centro - medida, centro + medida)
                _relleno(esquinas, CARAS_CAJA, (*NEON[:3], 0.12))
                _lineas(lineas, _aristas(esquinas), (*NEON[:3], 0.8))
        elif senal.kind == "plane":
            z = d["z"]
            (x0, y0), (x1, y1) = d["min_xy"], d["max_xy"]
            esquinas = [Vector((x0, y0, z)), Vector((x1, y0, z)), Vector((x1, y1, z)), Vector((x0, y1, z))]
            _relleno(esquinas, ((0, 1, 2), (0, 2, 3)), (*AMATISTA[:3], 0.22))
            _lineas(lineas, [esquinas[0], esquinas[1], esquinas[1], esquinas[2], esquinas[2], esquinas[3],
                             esquinas[3], esquinas[0]], AMATISTA)
        elif senal.kind == "ruler":
            _regla(lineas, d)
        elif senal.kind == "arrow":
            _flecha(lineas, d)
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.blend_set("NONE")


def _regla(lineas, d):
    """Regla junto al objeto, a lo largo del eje pedido.

    Empieza en el borde inferior del objeto en ese eje: en naranja lo que
    mide ahora y en verde el tramo [mín, máx] que se pide.
    """
    obj = _objeto(d.get("object", ""))
    if obj is None:
        return
    eje = "xyz".index(d.get("axis", "z"))
    esquinas = caja_mundo(obj)
    minimo = Vector(tuple(min(c[i] for c in esquinas) for i in range(3)))
    maximo = Vector(tuple(max(c[i] for c in esquinas) for i in range(3)))
    # La regla va a un lado: desplazada en un eje distinto del medido.
    lado = 0 if eje != 0 else 1
    base = minimo.copy()
    base[lado] = maximo[lado] + max(0.15, (maximo[lado] - minimo[lado]) * 0.15)
    direccion = Vector((0, 0, 0))
    direccion[eje] = 1.0
    actual = float(d.get("current", maximo[eje] - minimo[eje]))
    bajo = max(0.0, float(d.get("min", 0.0)))
    alto = float(d.get("max", bajo))
    if alto == float("inf"):
        alto = bajo + max(actual, 0.5)
    desde, hasta = base + direccion * bajo, base + direccion * alto
    tic = Vector((0, 0, 0))
    tic[lado] = 0.06
    _lineas(lineas, [base, base + direccion * actual, base - tic, base + tic,
                     base + direccion * actual - tic, base + direccion * actual + tic], NARANJA)
    desplaza = tic * 1.6
    _lineas(lineas, [desde + desplaza, hasta + desplaza, desde + desplaza - tic, desde + desplaza + tic,
                     hasta + desplaza - tic, hasta + desplaza + tic], VERDE)


def _flecha(lineas, d):
    obj = _objeto(d.get("object", ""))
    if obj is None:
        return
    esquinas = caja_mundo(obj)
    centro = sum(esquinas, Vector()) / 8
    alto = max(c.z for c in esquinas)
    largo = 0.5
    if d.get("direction") == "up":
        inicio, fin = Vector((centro.x, centro.y, alto + 0.1)), Vector((centro.x, centro.y, alto + 0.1 + largo))
    elif d.get("direction") == "down":
        inicio, fin = Vector((centro.x, centro.y, alto + 0.1 + largo)), Vector((centro.x, centro.y, alto + 0.1))
    else:
        inicio, fin = Vector((centro.x + largo, centro.y, alto + 0.1)), Vector((centro.x, centro.y, alto + 0.1))
    vector = (fin - inicio).normalized()
    lateral = Vector((0.0, 0.0, 1.0)).cross(vector) if abs(vector.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    punta = 0.12
    _lineas(lineas, [inicio, fin, fin, fin - vector * punta + lateral * punta * 0.6,
                     fin, fin - vector * punta - lateral * punta * 0.6], NARANJA)


# --- Etiquetas sobre la pantalla ---------------------------------------------------------


def _pastilla(x, y, texto, color, escala):
    tam = int(11 * escala)
    blf.size(0, tam)
    ancho, alto = blf.dimensions(0, texto)[0] + 14 * escala, tam + 10 * escala
    x -= ancho / 2
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    for puntos, tinte in (
        ([(x - 1, y - 1), (x + ancho + 1, y - 1), (x + ancho + 1, y + alto + 1), (x - 1, y + alto + 1)], color),
        ([(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)], FONDO),
    ):
        batch = batch_for_shader(shader, "TRIS", {"pos": puntos}, indices=((0, 1, 2), (0, 2, 3)))
        shader.uniform_float("color", tinte)
        batch.draw(shader)
    blf.color(0, *TEXTO)
    blf.position(0, x + 7 * escala, y + 6 * escala, 0)
    blf.draw(0, texto)


def dibujar_etiquetas():
    g = _activo()
    if g is None:
        return
    contexto = bpy.context
    region, vista = contexto.region, contexto.region_data
    if region is None or vista is None:
        return
    escala = contexto.preferences.system.ui_scale
    gpu.state.blend_set("ALPHA")
    for resalte in g.highlights:
        obj = _objeto(resalte.object_name)
        if obj is None or not resalte.label:
            continue
        esquinas = caja_mundo(obj)
        arriba = sum(esquinas, Vector()) / 8
        arriba.z = max(c.z for c in esquinas) + 0.05
        punto = location_3d_to_region_2d(region, vista, arriba)
        if punto is not None:
            _pastilla(punto.x, punto.y + 6 * escala, resalte.label, COLOR_RESALTE.get(resalte.kind, NEON), escala)
    for senal in g.cues:
        if not senal.label:
            continue
        ancla = _ancla(senal)
        punto = location_3d_to_region_2d(region, vista, ancla) if ancla is not None else None
        if punto is not None:
            _pastilla(punto.x, punto.y, senal.label, NARANJA if senal.kind in ("ruler", "arrow") else NEON, escala)
    gpu.state.blend_set("NONE")


def _ancla(senal):
    d = senal.data
    if senal.kind == "ghosts" and d.get("boxes"):
        caja = d["boxes"][0]
        return Vector(caja["center"]) + Vector((0, 0, caja["size"][2] / 2 + 0.1))
    if senal.kind == "plane":
        return Vector((d["max_xy"][0], d["min_xy"][1], d["z"]))
    if senal.kind in ("ruler", "arrow"):
        obj = _objeto(d.get("object", ""))
        if obj is None:
            return None
        esquinas = caja_mundo(obj)
        punto = Vector(tuple(max(c[i] for c in esquinas) for i in range(3)))
        return punto + Vector((0.2, 0, 0.6 if senal.kind == "arrow" else 0))
    return None
