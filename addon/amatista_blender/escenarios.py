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
    # La Nave de ESTA escena (cada práctica tiene la suya): una de otra escena no se toca.
    modelo = escena.objects.get("Nave") or nave_basica(escena)
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


# --- Ambiente del tema (add-on 3.2) ------------------------------------------------------
#
# Al abrir una práctica, el fondo de la vista 3D toma el color «cielo» del tema
# del módulo. Solo se toca World.color (y, en las vistas en modo Sólido, que el
# fondo use el del mundo): nunca se agregan ni quitan objetos, porque los
# validadores del motor los cuentan. La foto de la escena no incluye el mundo.

CIELO_PREVIO = "amatista_cielo_previo"  # [r, g, b] de World.color antes del tema
MUNDO_CREADO = "amatista_mundo_creado"  # nombre del mundo que creó Amatista (no había ninguno)
NOMBRE_MUNDO = "Amatista · Cielo"
_FONDOS_PREVIOS = {}  # puntero de la vista 3D → background_type anterior (solo en esta sesión)


def _vistas_3d():
    if bpy.app.background:
        return
    for ventana in bpy.context.window_manager.windows:
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                for espacio in area.spaces:
                    if espacio.type == "VIEW_3D":
                        yield espacio


def _fondo_del_mundo(encender):
    """Las vistas 3D en Sólido muestran World.color solo con el fondo «World»."""
    try:
        if encender:
            for espacio in _vistas_3d():
                clave = espacio.as_pointer()
                if clave not in _FONDOS_PREVIOS:
                    _FONDOS_PREVIOS[clave] = espacio.shading.background_type
                espacio.shading.background_type = "WORLD"
        else:
            for espacio in _vistas_3d():
                previo = _FONDOS_PREVIOS.get(espacio.as_pointer())
                if previo is not None:
                    espacio.shading.background_type = previo
            _FONDOS_PREVIOS.clear()
    except (AttributeError, TypeError, RuntimeError, ReferenceError) as error:
        print(f"[Amatista] No se pudo cambiar el fondo de la vista 3D: {error}")


def aplicar_ambiente(escena, practica_id):
    """Pinta el cielo de la vista 3D con el tema de la práctica. Devuelve el tema."""
    from . import temas

    tema = temas.tema_de_practica(practica_id)
    if escena is None:
        return tema
    mundo = escena.world
    if mundo is None:
        mundo = bpy.data.worlds.new(NOMBRE_MUNDO)
        escena.world = mundo
        escena[MUNDO_CREADO] = mundo.name
    if CIELO_PREVIO not in escena and MUNDO_CREADO not in escena:
        escena[CIELO_PREVIO] = [float(c) for c in mundo.color]
    mundo.color = temas.color_rgba(tema["colores"]["cielo"], lineal=True)[:3]
    _fondo_del_mundo(True)
    return tema


def restaurar_ambiente(escena):
    """Deja el mundo como estaba antes del tema (al cerrar la práctica o desactivar el add-on)."""
    if escena is None:
        return
    creado = escena.get(MUNDO_CREADO)
    if creado:
        mundo = bpy.data.worlds.get(creado)
        if escena.world is not None and escena.world == mundo:
            escena.world = None
        if mundo is not None and mundo.users == 0:
            bpy.data.worlds.remove(mundo)
        del escena[MUNDO_CREADO]
    previo = escena.get(CIELO_PREVIO)
    if previo is not None:
        if escena.world is not None:
            escena.world.color = tuple(previo)[:3]
        del escena[CIELO_PREVIO]


def restaurar_todo():
    for escena in list(bpy.data.scenes):
        try:
            restaurar_ambiente(escena)
        except (AttributeError, TypeError, RuntimeError, ReferenceError) as error:
            print(f"[Amatista] No se pudo restaurar el mundo de «{escena.name}»: {error}")
    _fondo_del_mundo(False)
