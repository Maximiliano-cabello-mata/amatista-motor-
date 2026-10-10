"""La mesa de trabajo del taller: una escena propia, limpia en cada actividad.

Las actividades del taller son cortas (1 a 3 minutos) y cada una empieza
como la pide la habilidad: vacía o con las piezas de «arregla esta escena»
(``inicio.objetos``). Todas pasan en la misma escena, «Amatista · Taller»,
que se vacía al empezar la siguiente: el trabajo del alumno en sus
proyectos vive en las escenas de cada práctica y nunca se toca.

Las piezas se arman con bmesh (sin operadores: funciona desde un
temporizador o una orden de la plataforma) y su malla se llama como la
primitiva («Cube», «Cylinder»…), igual que si el alumno la agregara con
Shift + A: así el motor las reconoce igual.
"""
import math

import bpy

try:
    import bmesh
except ImportError:  # pragma: no cover - bmesh siempre viene con Blender
    bmesh = None

from mathutils import Euler, Vector

NOMBRE = "Amatista · Taller"
MARCA = "amatista_taller"  # la escena del taller (y los objetos que puso el taller al empezar)
DATOS = {"cube": "Cube", "cylinder": "Cylinder", "sphere": "Sphere", "uv_sphere": "Sphere", "icosphere": "Icosphere",
         "cone": "Cone", "plane": "Plane", "torus": "Torus"}


def es_del_taller(sc):
    return bool(sc is not None and sc.get(MARCA))


def _ventanas(context):
    ventana = getattr(context, "window", None) or getattr(bpy.context, "window", None)
    if ventana is not None:
        return [ventana]
    return list(getattr(bpy.context.window_manager, "windows", ()) or ())


def _a_modo_objeto():
    obj = getattr(bpy.context, "active_object", None)
    if obj is not None and getattr(obj, "mode", "OBJECT") != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(f"[Amatista] No se pudo volver a Modo Objeto: {error}")


def escena_del_taller(context=None, cambiar=True):
    """La escena del taller (se crea si no existe) y, si se pide, se muestra en la ventana."""
    context = context or bpy.context
    sc = next((s for s in bpy.data.scenes if es_del_taller(s)), None)
    if sc is None:
        actual = getattr(context, "scene", None) or bpy.context.scene
        sc = bpy.data.scenes.new(NOMBRE)
        sc[MARCA] = 1
        if actual is not None:
            sc.unit_settings.system = actual.unit_settings.system
    if cambiar:
        for ventana in _ventanas(context)[:1]:
            if ventana.scene != sc:
                _a_modo_objeto()
                ventana.scene = sc
    return sc


def vaciar(sc):
    """Borra lo de la actividad anterior (solo en la escena del taller)."""
    if not es_del_taller(sc):
        raise ValueError("Solo se vacía la escena del taller")
    mallas, otros = set(), set()
    for obj in list(sc.objects):
        if obj.type == "MESH" and obj.data is not None:
            mallas.add(obj.data)
        elif obj.type in ("LIGHT", "CAMERA") and obj.data is not None:
            otros.add(obj.data)
        if len(obj.users_scene) <= 1:
            bpy.data.objects.remove(obj, do_unlink=True)
        else:
            sc.collection.objects.unlink(obj)
    for malla in mallas:
        if malla.users == 0:
            bpy.data.meshes.remove(malla)
    for dato in otros:
        if dato.users == 0:
            (bpy.data.lights if isinstance(dato, bpy.types.Light) else bpy.data.cameras).remove(dato)
    sc["amatista_renders"] = 0


def _malla(primitiva, medidas=(1.0, 1.0, 1.0), corrida=(0.0, 0.0, 0.0), duplicada=False):
    """La malla de la primitiva con sus medidas reales (como recién modelada), corrida respecto a su origen."""
    malla = bpy.data.meshes.new(DATOS.get(primitiva, "Cube"))
    if bmesh is None:
        return malla
    bm = bmesh.new()
    try:
        if primitiva in ("cylinder", "cone"):
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=0.5,
                                  radius2=0.0 if primitiva == "cone" else 0.5, depth=1.0)
        elif primitiva in ("sphere", "uv_sphere"):
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.5)
        elif primitiva == "icosphere":
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
        elif primitiva == "plane":
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        else:
            bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector(medidas), verts=bm.verts)
        if any(corrida):
            bmesh.ops.translate(bm, vec=Vector(corrida), verts=bm.verts)
        if duplicada:  # «arregla esta malla»: cada punto queda dos veces (como al cancelar una extrusión)
            bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))
        bm.to_mesh(malla)
    finally:
        bm.free()
    malla.update()
    return malla


def crear_pieza(sc, pieza, nombre=""):
    """Una pieza del formato del motor ({primitive, size, location, rotation°}) como objeto real.

    Como si el alumno la hubiera modelado: la malla tiene sus medidas y la
    escala queda en 1. Extras de «inicio»: ``escalada`` (estirada con S, la
    escala sin aplicar), ``origen`` (el origen en otro punto: media nave
    para el Espejo) y ``duplicada`` (puntos encimados para limpiar).
    """
    primitiva = str(pieza.get("primitive") or "cube")
    nombre = nombre or str(pieza.get("name") or DATOS.get(primitiva, "Cube"))
    medidas = [float(v) for v in (pieza.get("size") or (2.0, 2.0, 2.0))]
    if primitiva == "plane":
        medidas[2] = 1.0
    lugar = Vector([float(v) for v in (pieza.get("location") or (0.0, 0.0, 0.0))])
    giro = Euler([math.radians(float(g)) for g in (pieza.get("rotation") or (0.0, 0.0, 0.0))], "XYZ")
    escalada = bool(pieza.get("escalada"))
    origen = Vector([float(v) for v in pieza["origen"]]) if pieza.get("origen") is not None else lugar
    corrida = giro.to_matrix().inverted() @ (lugar - origen)  # del origen al centro, en coordenadas de la pieza
    if escalada:
        corrida = Vector([c / m if m else 0.0 for c, m in zip(corrida, medidas)])
    malla = _malla(primitiva, (1.0, 1.0, 1.0) if escalada else medidas, tuple(corrida), bool(pieza.get("duplicada")))
    obj = bpy.data.objects.new(nombre, malla)
    sc.collection.objects.link(obj)
    if escalada:
        obj.scale = medidas
    obj.location = origen
    obj.rotation_euler = giro
    return obj


def _mirar(obj, punto):
    obj.rotation_euler = (Vector(punto) - obj.location).to_track_quat("-Z", "Y").to_euler()


def crear_luz(sc, datos):
    """Una luz de inicio ({tipo: luz, name, light_type, location, mira, energia})."""
    nombre = str(datos.get("name") or "Luz")
    luz = bpy.data.lights.new(nombre, str(datos.get("light_type") or "AREA").upper())
    luz.energy = float(datos.get("energia") or (3.0 if luz.type == "SUN" else 500.0))
    obj = bpy.data.objects.new(nombre, luz)
    sc.collection.objects.link(obj)
    obj.location = [float(v) for v in (datos.get("location") or (3.0, -3.0, 4.0))]
    _mirar(obj, datos.get("mira") or (0.0, 0.0, 0.0))
    return obj


def crear_camara(sc, datos):
    """Una cámara de inicio ({tipo: camara, name, location, mira}); queda como la cámara de la escena."""
    nombre = str(datos.get("name") or "Camara")
    obj = bpy.data.objects.new(nombre, bpy.data.cameras.new(nombre))
    sc.collection.objects.link(obj)
    obj.location = [float(v) for v in (datos.get("location") or (6.0, -6.0, 4.0))]
    _mirar(obj, datos.get("mira") or (0.0, 0.0, 0.0))
    sc.camera = obj
    return obj


def preparar(context, actividad):
    """La escena lista para la actividad: limpia, con sus piezas de inicio y el cursor en el centro."""
    sc = escena_del_taller(context)
    vaciar(sc)
    if sc.amatista.practica_json:  # nunca es la escena de una práctica del paquete
        sc.amatista.practica_json = ""
        sc.amatista.practica_id = ""
    for pieza in actividad.inicio:
        tipo = str(pieza.get("tipo") or "")
        obj = crear_luz(sc, pieza) if tipo == "luz" else crear_camara(sc, pieza) if tipo == "camara" else crear_pieza(sc, pieza)
        obj[MARCA] = 1
    sc.cursor.location = (0.0, 0.0, 0.0)
    sc.cursor.rotation_euler = (0.0, 0.0, 0.0)
    for obj in sc.objects:
        obj.select_set(False)
    capa = getattr(bpy.context, "view_layer", None)
    mallas = [o for o in sc.objects if o.type == "MESH"]
    if capa is not None and mallas:
        try:
            capa.objects.active = mallas[0]
        except (AttributeError, RuntimeError, ReferenceError):
            pass
    sc.view_layers[0].update()  # las matrices al día: la primera revisión ve las piezas donde están
    return sc


def caja_de(piezas):
    """(centro, radio) que abarca las piezas: para encuadrar la vista."""
    if not piezas:
        return Vector((0.0, 0.0, 1.0)), 4.0
    minimo = Vector((1e9, 1e9, 1e9))
    maximo = Vector((-1e9, -1e9, -1e9))
    for p in piezas:
        centro = Vector([float(v) for v in (p.get("location") or (0, 0, 0))])
        medio = max(float(v) for v in (p.get("size") or (2, 2, 2))) / 2
        for i in range(3):
            minimo[i] = min(minimo[i], centro[i] - medio)
            maximo[i] = max(maximo[i], centro[i] + medio)
    return (minimo + maximo) / 2, max(1.5, (maximo - minimo).length / 2)


def encuadrar(context, piezas):
    """Mira la actividad desde un ángulo cómodo (de frente y un poco desde arriba)."""
    centro, radio = caja_de(piezas)
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for espacio in area.spaces:
                if espacio.type == "VIEW_3D" and espacio.region_3d is not None:
                    r3d = espacio.region_3d
                    r3d.view_location = centro
                    r3d.view_distance = radio * 3.2
                    r3d.view_rotation = Euler((math.radians(62), 0.0, math.radians(32)), "XYZ").to_quaternion()
                    if r3d.view_perspective == "CAMERA":
                        r3d.view_perspective = "PERSP"
            area.tag_redraw()
