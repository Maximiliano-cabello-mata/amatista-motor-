"""Archivo, colecciones, cámara y luces."""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import count_message, count_ok, count_rule, result, text


def file_saved(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    if scene.file_saved:
        mensaje = "El archivo está guardado."
    elif scene.file_path:
        mensaje = "Hay cambios sin guardar: pulsa Ctrl+S."
    else:
        mensaje = "Guarda el archivo (Archivo › Guardar como) antes de continuar."
    return result(target, scene.file_saved, mensaje, {"file_path": scene.file_path})


def file_named(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """El .blend se llama como pide la práctica (params.contains, sin mayúsculas)."""
    contiene = text(target, "contains", required=True).lower()
    nombre = scene.file_name
    ok = bool(nombre) and contiene in nombre.lower()
    return result(
        target,
        ok,
        f"El archivo se llama «{nombre}»." if ok else f"Guarda el archivo con un nombre que incluya «{contiene}».",
        {"file_name": nombre, "contains": contiene},
    )


def collection_contains(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    coleccion = text(target, "collection", required=True)
    rol = text(target, "role")
    minimo, maximo = count_rule(target, default_min=1)
    dentro = [o for o in scene.objects if coleccion in o.collections and (not rol or rol in o.roles)]
    que = f"«{rol}» en la colección «{coleccion}»" if rol else f"objetos en la colección «{coleccion}»"
    return result(
        target,
        count_ok(len(dentro), minimo, maximo),
        count_message(len(dentro), minimo, maximo, que),
        {"collection": coleccion, "role": rol or None, "found": len(dentro), "objects": [o.name for o in dentro]},
    )


def _por_tipo(target: TargetDefinition, scene: SceneState, tipo: str, nombre: str) -> ValidationResult:
    minimo, maximo = count_rule(target, default_min=1)
    objetos = [o for o in scene.objects if o.object_type == tipo]
    return result(
        target,
        count_ok(len(objetos), minimo, maximo),
        count_message(len(objetos), minimo, maximo, nombre),
        {"type": tipo, "found": len(objetos), "objects": [o.name for o in objetos]},
    )


def camera_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _por_tipo(target, scene, "CAMERA", "cámaras")


def light_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _por_tipo(target, scene, "LIGHT", "luces")
