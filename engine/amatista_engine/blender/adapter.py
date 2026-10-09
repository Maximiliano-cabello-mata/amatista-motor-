"""Adaptador Blender -> Amatista SceneState.

Este archivo se ejecuta únicamente dentro de Blender. Lee la escena una vez
y entrega datos normales de Python; el resto del motor no importa bpy.

Motor v3: además de medidas y roles captura los ajustes de los
modificadores, los valores del Principled BSDF, luces y cámaras (hacia dónde
miran), los fotogramas clave, los vértices encimados (lo que deja «E» y
luego cancelar), de qué primitiva salió cada malla y cuántos renders se
hicieron. Motor 3.5: la silueta de las mallas chicas (figures/silueta.py).
Funciona en Blender 4.2 a 5.x (la API de acciones cambió en 4.4 y
en 5.0).
"""

from ..models import AnimationChannel, MaterialInfo, ModifierInfo, SceneObject, SceneState
from . import tagger

# Mallas más grandes no se revisan vértice por vértice (sería lento en cada cambio).
MAX_VERTICES_SALUD = 50000
MAX_VERTICES_SILUETA = 20000  # la silueta (motor 3.5) es para modelos low-poly
DISTANCIA_ENCIMADOS = 1e-4
RUTAS_ANIMACION = ("location", "rotation_euler", "scale")
MAX_CLAVES = 120
PROP_RENDERS = "amatista_renders"


def _caja_mundo(obj):
    """Caja envolvente en coordenadas del mundo (min, max)."""
    try:
        puntos = [obj.matrix_world @ _vector(c) for c in obj.bound_box]
    except Exception:  # objetos sin caja (algunos vacíos)
        return None, None
    minimo = tuple(min(p[i] for p in puntos) for i in range(3))
    maximo = tuple(max(p[i] for p in puntos) for i in range(3))
    return minimo, maximo


def _vector(coordenadas):
    from mathutils import Vector

    return Vector(coordenadas)


def _malla_viva(obj):
    """(vértices como tuplas, índices de material de las caras, aristas) de la malla.

    En modo Edición la malla del objeto no se actualiza hasta salir: se lee
    con bmesh para ver lo que el alumno tiene delante.
    """
    datos = obj.data
    if obj.mode == "EDIT":
        try:
            import bmesh

            bm = bmesh.from_edit_mesh(datos)
            bm.verts.index_update()
            return ([tuple(v.co) for v in bm.verts], [f.material_index for f in bm.faces],
                    [(e.verts[0].index, e.verts[1].index) for e in bm.edges])
        except Exception:  # noqa: BLE001
            pass
    return ([tuple(v.co) for v in datos.vertices], [p.material_index for p in datos.polygons],
            [tuple(e.vertices) for e in datos.edges])


def _silueta(obj, vertices, aristas):
    """Silueta en el mundo (motor 3.5): solo mallas chicas, para revisar en vivo sin trabarse."""
    if not aristas or len(vertices) > MAX_VERTICES_SILUETA:
        return None
    from ..figures.silueta import silueta_de_malla

    matriz = obj.matrix_world
    try:
        mundo = [tuple(matriz @ _vector(co)) for co in vertices]
        return silueta_de_malla(mundo, aristas)
    except Exception:  # noqa: BLE001 - una malla rara no rompe la foto
        return None


def _encimados(vertices):
    """Cuántos vértices sobran: los que tienen otro anterior a menos de
    DISTANCIA_ENCIMADOS (lo que quitaría «Fusionar › Por distancia»)."""
    if len(vertices) < 2 or len(vertices) > MAX_VERTICES_SALUD:
        return 0 if len(vertices) < 2 else None
    from mathutils import kdtree

    arbol = kdtree.KDTree(len(vertices))
    for i, co in enumerate(vertices):
        arbol.insert(co, i)
    arbol.balance()
    return sum(
        1 for i, co in enumerate(vertices) if any(j < i for _, j, _ in arbol.find_range(co, DISTANCIA_ENCIMADOS))
    )


def _lados(vertices):
    lados = []
    for eje in range(3):
        negativos = sum(1 for co in vertices if co[eje] < -DISTANCIA_ENCIMADOS)
        positivos = sum(1 for co in vertices if co[eje] > DISTANCIA_ENCIMADOS)
        lados.append((negativos, positivos))
    return tuple(lados)


def _modificadores(obj):
    detalles = []
    for m in getattr(obj, "modifiers", ()):
        ejes = (False, False, False)
        niveles = None
        if m.type == "MIRROR":
            ejes = tuple(bool(e) for e in m.use_axis)
        elif m.type == "SUBSURF":
            niveles = int(m.levels)
        detalles.append(ModifierInfo(m.type, m.name, ejes, niveles, bool(m.show_viewport)))
    return tuple(detalles)


def _entrada(nodo, nombres, defecto):
    for nombre in nombres:
        socket = nodo.inputs.get(nombre)
        if socket is not None and hasattr(socket, "default_value"):
            return socket.default_value
    return defecto


def _material(mat):
    nodo = None
    arbol = getattr(mat, "node_tree", None)
    if arbol is not None and getattr(mat, "use_nodes", True):
        nodo = next((n for n in arbol.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if nodo is None:
        color = tuple(mat.diffuse_color)
        return MaterialInfo(mat.name, tuple(float(c) for c in color), float(mat.metallic), float(mat.roughness),
                            0.0, float(color[3]) if len(color) > 3 else 1.0)
    color = tuple(float(c) for c in _entrada(nodo, ("Base Color",), (0.8, 0.8, 0.8, 1.0)))
    return MaterialInfo(
        mat.name,
        color if len(color) == 4 else color + (1.0,),
        float(_entrada(nodo, ("Metallic",), 0.0)),
        float(_entrada(nodo, ("Roughness",), 0.5)),
        float(_entrada(nodo, ("Transmission Weight", "Transmission"), 0.0)),
        float(_entrada(nodo, ("Alpha",), 1.0)),
    )


def _fcurves(obj):
    """Curvas de animación del objeto en cualquier versión de Blender 4.2+."""
    ad = getattr(obj, "animation_data", None)
    accion = getattr(ad, "action", None) if ad else None
    if accion is None:
        return []
    try:
        curvas = accion.fcurves  # hasta 4.x (en 4.4+ es la vista heredada)
        return list(curvas)
    except AttributeError:
        pass
    ranura = getattr(ad, "action_slot", None)
    try:  # 4.4+ con acciones por capas y ranuras
        from bpy_extras import anim_utils

        bolsa = anim_utils.action_get_channelbag_for_slot(accion, ranura)
        if bolsa is not None:
            return list(bolsa.fcurves)
    except (ImportError, AttributeError):
        pass
    for capa in getattr(accion, "layers", ()):
        for tira in capa.strips:
            try:
                bolsa = tira.channelbag(ranura)
            except (AttributeError, TypeError):
                bolsa = None
            if bolsa is not None:
                return list(bolsa.fcurves)
    return []


def _animacion(obj):
    canales = []
    for curva in _fcurves(obj):
        if curva.data_path not in RUTAS_ANIMACION or curva.array_index > 2:
            continue
        claves = tuple(
            (float(k.co[0]), float(k.co[1])) for k in list(curva.keyframe_points)[:MAX_CLAVES]
        )
        canales.append(AnimationChannel(curva.data_path, int(curva.array_index), claves))
    return tuple(sorted(canales, key=lambda c: (c.path, c.index)))


def _hacia_donde(obj):
    from mathutils import Vector

    v = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    if v.length:
        v.normalize()
    return tuple(float(c) for c in v)


def capture_object(obj):
    rol = tagger.get_role(obj)
    datos = getattr(obj, "data", None)
    es_malla = obj.type == "MESH" and datos is not None
    caja_min, caja_max = _caja_mundo(obj)
    vertices = indices_material = aristas = None
    if es_malla:
        vertices, indices_material, aristas = _malla_viva(obj)
    slots = [s.material.name if s.material else None for s in getattr(obj, "material_slots", ())]
    usados = None
    if es_malla:
        usados = tuple(sorted({slots[i] for i in set(indices_material) if i < len(slots) and slots[i]}))
    luz = obj.type == "LIGHT" and datos is not None
    camara = obj.type == "CAMERA" and datos is not None
    return SceneObject(
        name=obj.name,
        object_type=obj.type,
        roles=(rol,) if rol else (),
        location=tuple(float(v) for v in obj.matrix_world.translation),
        rotation=tuple(float(v) for v in obj.rotation_euler),
        scale=tuple(float(v) for v in obj.scale),
        dimensions=tuple(float(v) for v in obj.dimensions),
        modifiers=tuple(modifier.type for modifier in getattr(obj, "modifiers", ())),
        tags=tagger.get_tags(obj),
        materials=tuple(s for s in slots if s),
        collections=tuple(c.name for c in obj.users_collection),
        vertices=len(vertices) if es_malla else None,
        faces=len(indices_material) if es_malla else None,
        bbox_min=tuple(float(v) for v in caja_min) if caja_min else None,
        bbox_max=tuple(float(v) for v in caja_max) if caja_max else None,
        parent=obj.parent.name if obj.parent else None,
        data_name=datos.name if datos is not None and hasattr(datos, "name") else None,
        modifier_details=_modificadores(obj),
        material_details=tuple(
            _material(s.material) for s in getattr(obj, "material_slots", ()) if s.material
        ),
        materials_used=usados,
        light_type=datos.type if luz else None,
        light_energy=float(getattr(datos, "energy", 0.0)) if luz else None,
        camera_angle=float(datos.angle) if camara else None,
        forward=_hacia_donde(obj) if (luz or camara) else None,
        duplicate_vertices=_encimados(vertices) if es_malla else None,
        side_counts=_lados(vertices) if es_malla and len(vertices) <= MAX_VERTICES_SALUD else None,
        animation=_animacion(obj),
        silhouette=_silueta(obj, vertices, aristas) if es_malla else None,
    )


def capture_scene(scene=None):
    import bpy

    scene = scene or bpy.context.scene
    objects = tuple(capture_object(obj) for obj in scene.objects if not tagger.is_ignored(obj))
    file_path = bpy.data.filepath or ""
    capa = getattr(bpy.context, "view_layer", None)
    activo = capa.objects.active if capa is not None else None
    seleccion = tuple(o.name for o in scene.objects if o.select_get(view_layer=capa)) if capa is not None else ()
    return SceneState(
        blender_version=bpy.app.version_string,
        file_path=file_path,
        file_saved=bool(file_path) and not bpy.data.is_dirty,
        objects=objects,
        mode=getattr(bpy.context, "mode", "OBJECT") or "OBJECT",
        active_object=activo.name if activo is not None else None,
        selected=seleccion[:32],
        active_camera=scene.camera.name if scene.camera else None,
        render_engine=scene.render.engine,
        renders=int(scene.get(PROP_RENDERS, 0) or 0),
        frame_range=(int(scene.frame_start), int(scene.frame_end)),
    )
