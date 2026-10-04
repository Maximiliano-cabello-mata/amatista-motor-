"""Adaptador Blender -> Amatista SceneState.

Este archivo se ejecuta únicamente dentro de Blender. Lee la escena una vez
y entrega datos normales de Python; el resto del motor no importa bpy.
"""

from ..models import SceneObject, SceneState
from . import tagger


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


def capture_object(obj):
    rol = tagger.get_role(obj)
    datos = getattr(obj, "data", None)
    es_malla = obj.type == "MESH" and datos is not None
    caja_min, caja_max = _caja_mundo(obj)
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
        materials=tuple(s.material.name for s in getattr(obj, "material_slots", ()) if s.material),
        collections=tuple(c.name for c in obj.users_collection),
        vertices=len(datos.vertices) if es_malla else None,
        faces=len(datos.polygons) if es_malla else None,
        bbox_min=tuple(float(v) for v in caja_min) if caja_min else None,
        bbox_max=tuple(float(v) for v in caja_max) if caja_max else None,
        parent=obj.parent.name if obj.parent else None,
    )


def capture_scene(scene=None):
    import bpy

    scene = scene or bpy.context.scene
    objects = tuple(capture_object(obj) for obj in scene.objects if not tagger.is_ignored(obj))
    file_path = bpy.data.filepath or ""
    return SceneState(
        blender_version=bpy.app.version_string,
        file_path=file_path,
        file_saved=bool(file_path) and not bpy.data.is_dirty,
        objects=objects,
        mode=getattr(bpy.context, "mode", "OBJECT") or "OBJECT",
    )
