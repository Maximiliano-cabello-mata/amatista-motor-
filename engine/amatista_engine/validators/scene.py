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


MODOS = {"OBJECT": "Modo Objeto", "EDIT": "Modo Edición", "SCULPT": "Modo Escultura", "POSE": "Modo Pose"}


def scene_mode(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Blender está en un modo (params.mode: OBJECT, EDIT…). «EDIT» acepta EDIT_MESH, EDIT_CURVE…"""
    pedido = (text(target, "mode") or "OBJECT").upper()
    actual = str(scene.mode or "OBJECT").upper()
    ok = actual == pedido or actual.startswith(pedido + "_")
    nombre = MODOS.get(pedido, pedido)
    mensaje = f"Estás en {nombre}." if ok else f"Pasa a {nombre} (Tab cambia entre Modo Objeto y Modo Edición)."
    return result(target, ok, mensaje, {"mode": actual, "expected": pedido})


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


TIPOS_LUZ = {"POINT": "luces puntuales", "SUN": "soles", "SPOT": "focos", "AREA": "luces de área"}


def _por_tipo(target: TargetDefinition, scene: SceneState, tipo: str, nombre: str) -> ValidationResult:
    minimo, maximo = count_rule(target, default_min=1)
    objetos = [o for o in scene.objects if o.object_type == tipo]
    tipo_luz = str(target.params.get("light_type", "") or "").upper()
    if tipo == "LIGHT" and tipo_luz:
        if tipo_luz not in TIPOS_LUZ:
            raise ValueError("light_type debe ser POINT, SUN, SPOT o AREA")
        objetos = [o for o in objetos if (o.light_type or "").upper() == tipo_luz]
        nombre = TIPOS_LUZ[tipo_luz]
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
