"""Escenas de inicio de las prácticas (motor v3, practice/2 › starter).

    "starter": {"scene": "empty", "build": "estudio_foto", "from_practice": "…"}

- scene "empty": quita el cubo, la luz y la cámara de inicio de Blender
  (solo si siguen intactos: nunca borra trabajo del alumno).
- build: arma una escena preparada para la práctica (lista de abajo). Si
  la práctica dice from_practice, primero se ofrece abrir el .blend de esa
  práctica; la escena armada es el plan B para quien no lo tiene.

Todo se hace con bpy.data (sin operadores): funciona en segundo plano y no
depende de la ventana activa. Ctrl+Z deshace la preparación completa.
"""
import math

import bpy

from . import _motor

PREPARADO = "amatista_preparado"  # marca en la escena: ya se preparó para esta práctica


def _intactos():
    """El cubo, la luz y la cámara de inicio, si nadie los tocó."""
    quitar = []
    cubo = bpy.data.objects.get("Cube")
    if cubo is not None and cubo.type == "MESH" and len(cubo.data.vertices) == 8 and \
            tuple(round(v, 3) for v in cubo.dimensions) == (2.0, 2.0, 2.0) and not _motor.tagger.get_role(cubo):
        quitar.append(cubo)
    for nombre, tipo in (("Light", "LIGHT"), ("Camera", "CAMERA")):
        obj = bpy.data.objects.get(nombre)
        if obj is not None and obj.type == tipo:
            quitar.append(obj)
    return quitar


def vaciar(escena):
    for obj in _intactos():
        if obj.name in escena.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def _malla(escena, nombre, verts, caras, ubicacion=(0, 0, 0), rol=None, datos_nombre=None):
    # El nombre de los datos dice de qué primitiva salió (Sphere, Plane…): el motor lo usa.
    datos = bpy.data.meshes.new(datos_nombre or nombre)
    datos.from_pydata(verts, [], caras)
    datos.update()
    obj = bpy.data.objects.new(nombre, datos)
    obj.location = ubicacion
    escena.collection.objects.link(obj)
    if rol:
        _motor.tagger.assign_role(obj, rol)
    return obj


def _caja(ancho, largo, alto, z0=0.0):
    x, y = ancho / 2, largo / 2
    verts = [(-x, -y, z0), (x, -y, z0), (x, y, z0), (-x, y, z0),
             (-x, -y, z0 + alto), (x, -y, z0 + alto), (x, y, z0 + alto), (-x, y, z0 + alto)]
    caras = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, caras


def _piso(escena, tam=12.0):
    t = tam / 2
    return _malla(escena, "Piso", [(-t, -t, 0), (t, -t, 0), (t, t, 0), (-t, t, 0)], [(0, 1, 2, 3)], datos_nombre="Plane")


def _esfera(escena, nombre, radio, ubicacion, segmentos=24, anillos=12):
    verts = [(0, 0, radio)]
    for i in range(1, anillos):
        theta = math.pi * i / anillos
        for j in range(segmentos):
            phi = 2 * math.pi * j / segmentos
            verts.append((radio * math.sin(theta) * math.cos(phi), radio * math.sin(theta) * math.sin(phi),
                          radio * math.cos(theta)))
    verts.append((0, 0, -radio))
    caras = [(0, 1 + j, 1 + (j + 1) % segmentos) for j in range(segmentos)]
    for i in range(anillos - 2):
        a, b = 1 + i * segmentos, 1 + (i + 1) * segmentos
        caras += [(a + j, b + j, b + (j + 1) % segmentos, a + (j + 1) % segmentos) for j in range(segmentos)]
    ultimo, base = len(verts) - 1, 1 + (anillos - 2) * segmentos
    caras += [(base + (j + 1) % segmentos, base + j, ultimo) for j in range(segmentos)]
    obj = _malla(escena, nombre, verts, caras, ubicacion, datos_nombre="Sphere")
    for poligono in obj.data.polygons:
        poligono.use_smooth = True
    return obj


def _camara(escena, ubicacion, mirar=(0, 0, 0.5)):
    datos = bpy.data.cameras.new("Camara")
    obj = bpy.data.objects.new("Camara", datos)
    obj.location = ubicacion
    escena.collection.objects.link(obj)
    _mirar(obj, mirar)
    escena.camera = obj
    return obj


def _luz(escena, nombre, tipo, ubicacion, energia, mirar=(0, 0, 0.5)):
    datos = bpy.data.lights.new(nombre, tipo)
    datos.energy = energia
    obj = bpy.data.objects.new(nombre, datos)
    obj.location = ubicacion
    escena.collection.objects.link(obj)
    _mirar(obj, mirar)
    return obj


def _mirar(obj, punto):
    from mathutils import Vector

    direccion = Vector(punto) - Vector(obj.location)
    obj.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()


def nave_basica(escena):
    """Media nave con Espejo y Subdivisión (el resultado esperado del curso Principiante)."""
    verts, caras = _caja(1.0, 3.0, 0.8)
    verts = [(x - 0.5, y, z) for x, y, z in verts]  # solo el lado X negativo: el Espejo dibuja el otro
    obj = _malla(escena, "Nave", verts, caras, (0, 0, 0.6), rol="nave")
    espejo = obj.modifiers.new("Espejo", "MIRROR")
    espejo.use_clip = True
    sub = obj.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 2
    return obj


def estudio_foto(escena):
    """Modelo sobre un piso, sin luces ni cámara y con Workbench (para cambiar a EEVEE)."""
    _piso(escena)
    modelo = nave_basica(escena) if "Nave" not in bpy.data.objects else bpy.data.objects["Nave"]
    _motor.tagger.assign_role(modelo, "modelo")
    escena.render.engine = "BLENDER_WORKBENCH"
    return modelo


def pelota_y_suelo(escena):
    _piso(escena)
    pelota = _esfera(escena, "Pelota", 1.0, (0, 0, 4.0))
    _camara(escena, (0, -14, 3.5), (0, 0, 2))
    _luz(escena, "Sol", "SUN", (4, -4, 8), 3.0)
    escena.frame_start, escena.frame_end = 1, 48
    return pelota


CONSTRUCTORES = {"nave_basica": nave_basica, "estudio_foto": estudio_foto, "pelota_y_suelo": pelota_y_suelo}


def preparar(escena, practica):
    """Prepara la escena una sola vez por práctica. Devuelve el texto para el aviso o None."""
    inicio = getattr(practica, "starter", None)
    if inicio is None or escena.get(PREPARADO) == practica.id:
        return None
    hecho = []
    if inicio.scene == "empty":
        antes = len(escena.objects)
        vaciar(escena)
        if len(escena.objects) < antes:
            hecho.append("quitamos el cubo, la luz y la cámara de inicio")
    constructor = CONSTRUCTORES.get(inicio.build or "")
    if constructor is not None:
        constructor(escena)
        hecho.append("armamos la escena de la práctica")
    escena[PREPARADO] = practica.id
    if not hecho:
        return None
    return "Listo: " + " y ".join(hecho) + ". Ctrl+Z lo deshace."
