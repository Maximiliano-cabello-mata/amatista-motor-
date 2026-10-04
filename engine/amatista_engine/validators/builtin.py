"""Catálogo de validadores incluidos en el motor.

Cada uno se registra con su etiqueta en español, sus parámetros y los
eventos que lo invalidan. El constructor de objetivos del modo
desarrollador muestra estas etiquetas como plantillas («Cantidad por rol»,
«Dimensión»...). Agregar una capacidad nueva = una función + un registro
aquí; ninguna práctica necesita código propio.
"""
from __future__ import annotations

from ..registry import ParamSpec as P
from ..registry import ValidatorRegistry
from . import mesh, objects, scene, transforms

# Parámetros comunes del selector de objetos (validators/base.py).
SELECTOR = (
    P("role", "role", "Rol"),
    P("name", "text", "Nombre exacto"),
    P("name_prefix", "text", "Nombre empieza con"),
    P("type", "object_type", "Tipo de objeto"),
)
CANTIDAD = (
    P("equals", "int", "Exactamente"),
    P("min", "int", "Mínimo"),
    P("max", "int", "Máximo"),
)
RANGO = (P("axis", "axis", "Eje", default="z"), P("min", "float", "Mínimo"), P("max", "float", "Máximo"))

TRANSFORMACION = ("OBJECT_TRANSFORM", "OBJECT_ADDED", "ROLE_CHANGED")


def register_builtin_validators(registry: ValidatorRegistry) -> None:
    r = registry.register
    # --- Objetos y roles ---
    r(
        "object.exists", objects.object_exists, label="Objeto existe", category="objetos",
        description="Hay al menos un objeto que cumple el selector.",
        params=SELECTOR, watch=("OBJECT_ADDED", "ROLE_CHANGED"), selects=True,
    )
    r(
        "object.count", objects.object_count, label="Cantidad de objetos", category="objetos",
        description="Cuenta los objetos que cumplen el selector.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_ADDED", "ROLE_CHANGED"), selects=True,
    )
    r(
        "role.exists", objects.role_exists, label="Rol asignado", category="roles",
        description="Algún objeto tiene el rol educativo.",
        params=(P("role", "role", "Rol", required=True),), watch=("OBJECT_ADDED", "ROLE_CHANGED"),
    )
    r(
        "role.count", objects.role_count, label="Cantidad por rol", category="roles",
        description="Cantidad de objetos con un rol (exactamente, mínimo o máximo).",
        params=(P("role", "role", "Rol", required=True),) + CANTIDAD, watch=("OBJECT_ADDED", "ROLE_CHANGED"),
    )
    # --- Transformaciones ---
    r(
        "dimension.range", transforms.dimension_range, label="Dimensión", category="transformaciones",
        description="La medida en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    r(
        "object.position", transforms.object_position, label="Posición", category="transformaciones",
        description="La ubicación en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION, selects=True,
    )
    r(
        "object.rotation", transforms.object_rotation, label="Rotación", category="transformaciones",
        description="El giro (en grados) en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION, selects=True,
    )
    r(
        "transform.scale_applied", transforms.scale_applied, label="Escala aplicada", category="transformaciones",
        description="La escala del objeto es 1 en los tres ejes (Ctrl+A › Escala).",
        params=SELECTOR, watch=TRANSFORMACION, selects=True,
    )
    r(
        "spatial.below", transforms.below, label="Debajo de", category="relaciones",
        description="Los objetos quedan debajo de otro (por ejemplo, patas bajo la cubierta).",
        params=SELECTOR + (
            P("reference_role", "role", "Rol de referencia", required=True),
            P("tolerance", "float", "Tolerancia", default=0.02),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Malla, modificadores y materiales ---
    r(
        "mesh.vertex_count", mesh.vertex_count, label="Vértices", category="malla",
        description="Cantidad de vértices de la malla.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "mesh.face_count", mesh.face_count, label="Caras", category="malla",
        description="Cantidad de caras de la malla.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "modifier.exists", mesh.modifier_exists, label="Modificador", category="malla",
        description="Los objetos tienen un modificador (BEVEL, MIRROR, ARRAY...).",
        params=SELECTOR + (P("modifier", "modifier", "Modificador", required=True),),
        watch=("OBJECT_MODIFIER",), selects=True,
    )
    r(
        "material.exists", mesh.material_exists, label="Material", category="materiales",
        description="Los objetos tienen material asignado.",
        params=SELECTOR + (P("material", "text", "Nombre del material contiene"),),
        watch=("OBJECT_DATA",), selects=True,
    )
    # --- Escena y archivo ---
    r(
        "collection.contains", scene.collection_contains, label="Colección", category="organización",
        description="Una colección contiene objetos (opcionalmente de un rol).",
        params=(P("collection", "collection", "Colección", required=True), P("role", "role", "Rol")) + CANTIDAD,
        watch=("OBJECT_ADDED", "OBJECT_DATA", "ROLE_CHANGED"),
    )
    r(
        "scene.camera_exists", scene.camera_exists, label="Cámara", category="escena",
        description="La escena tiene cámara.", params=CANTIDAD, watch=("OBJECT_ADDED",),
    )
    r(
        "scene.light_exists", scene.light_exists, label="Luz", category="escena",
        description="La escena tiene luces.", params=CANTIDAD, watch=("OBJECT_ADDED",),
    )
    r(
        "file.saved", scene.file_saved, label="Archivo guardado", category="archivo",
        description="El .blend está guardado y sin cambios pendientes.", watch=("FILE_SAVED", "OBJECT_DATA"),
    )
    r(
        "file.named", scene.file_named, label="Nombre del archivo", category="archivo",
        description="El nombre del .blend incluye un texto.",
        params=(P("contains", "text", "Contiene", required=True),), watch=("FILE_SAVED",),
    )


# Compatibilidad con el prototipo v0.1 (importaba estas funciones de aquí).
file_saved = scene.file_saved
object_exists = objects.object_exists
role_count = objects.role_count
dimension_range = transforms.dimension_range
