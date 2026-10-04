"""Escena ⇄ JSON compacto para enviarla al servidor.

El add-on manda esta «foto» (nombres, tipos, roles, medidas; nunca la malla
ni el .blend) y el servidor vuelve a evaluar la práctica con el mismo motor:
el progreso que se guarda en Oracle lo calcula Amatista, no el cliente.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence

from .errors import InvalidPracticeError
from .models import SceneObject, SceneState

MAX_OBJETOS = 500
MAX_LISTA = 32
MAX_NOMBRE = 120


def _vector(valor: Optional[Sequence[float]]):
    if valor is None:
        return None
    return [round(float(v), 5) for v in valor]


def scene_to_dict(scene: SceneState) -> Dict[str, Any]:
    objetos = []
    for o in scene.objects[:MAX_OBJETOS]:
        item: Dict[str, Any] = {"n": o.name, "t": o.object_type, "l": _vector(o.location), "d": _vector(o.dimensions)}
        if o.roles:
            item["r"] = list(o.roles)
        if any(abs(v) > 1e-9 for v in o.rotation):
            item["rot"] = _vector(o.rotation)
        if any(abs(v - 1.0) > 1e-9 for v in o.scale):
            item["s"] = _vector(o.scale)
        for clave, valor in (("m", o.modifiers), ("g", o.tags), ("mat", o.materials), ("c", o.collections)):
            if valor:
                item[clave] = list(valor)
        if o.vertices is not None:
            item["v"] = o.vertices
        if o.faces is not None:
            item["f"] = o.faces
        if o.bbox_min is not None and o.bbox_max is not None:
            item["b"] = [_vector(o.bbox_min), _vector(o.bbox_max)]
        if o.parent:
            item["p"] = o.parent
        objetos.append(item)
    return {
        "blender": scene.blender_version,
        "archivo": scene.file_name,
        "guardado": scene.file_saved,
        "modo": scene.mode,
        "objetos": objetos,
    }


def _tupla_vector(valor, defecto):
    if valor is None:
        return defecto
    if not isinstance(valor, (list, tuple)) or len(valor) != 3:
        raise InvalidPracticeError("Vector inválido en la escena")
    try:
        numeros = tuple(float(v) for v in valor)
    except (TypeError, ValueError):
        raise InvalidPracticeError("Vector inválido en la escena") from None
    if not all(math.isfinite(n) for n in numeros):
        raise InvalidPracticeError("Vector inválido en la escena")
    return numeros


def _textos(valor) -> tuple:
    if not valor:
        return ()
    if not isinstance(valor, list):
        raise InvalidPracticeError("Lista inválida en la escena")
    return tuple(str(v)[:MAX_NOMBRE] for v in valor[:MAX_LISTA])


def scene_from_dict(data: Dict[str, Any]) -> SceneState:
    """Lo inverso, con límites: lo usa el servidor con datos que vienen de afuera."""
    if not isinstance(data, dict):
        raise InvalidPracticeError("La escena debe ser un objeto")
    crudos = data.get("objetos") or []
    if not isinstance(crudos, list) or len(crudos) > MAX_OBJETOS:
        raise InvalidPracticeError(f"La escena admite como máximo {MAX_OBJETOS} objetos")
    objetos = []
    for crudo in crudos:
        if not isinstance(crudo, dict):
            raise InvalidPracticeError("Objeto inválido en la escena")
        caja = crudo.get("b")
        objetos.append(
            SceneObject(
                name=str(crudo.get("n", ""))[:MAX_NOMBRE],
                object_type=str(crudo.get("t", "MESH"))[:20].upper(),
                roles=_textos(crudo.get("r")),
                location=_tupla_vector(crudo.get("l"), (0.0, 0.0, 0.0)),
                rotation=_tupla_vector(crudo.get("rot"), (0.0, 0.0, 0.0)),
                scale=_tupla_vector(crudo.get("s"), (1.0, 1.0, 1.0)),
                dimensions=_tupla_vector(crudo.get("d"), (0.0, 0.0, 0.0)),
                modifiers=_textos(crudo.get("m")),
                tags=_textos(crudo.get("g")),
                materials=_textos(crudo.get("mat")),
                collections=_textos(crudo.get("c")),
                vertices=int(crudo["v"]) if isinstance(crudo.get("v"), int) else None,
                faces=int(crudo["f"]) if isinstance(crudo.get("f"), int) else None,
                bbox_min=_tupla_vector(caja[0], None) if isinstance(caja, list) and len(caja) == 2 else None,
                bbox_max=_tupla_vector(caja[1], None) if isinstance(caja, list) and len(caja) == 2 else None,
                parent=str(crudo["p"])[:MAX_NOMBRE] if crudo.get("p") else None,
            )
        )
    archivo = str(data.get("archivo") or "")[:255]
    return SceneState(
        blender_version=str(data.get("blender") or "")[:20],
        file_path=archivo,
        file_saved=bool(data.get("guardado")),
        objects=tuple(objetos),
        mode=str(data.get("modo") or "OBJECT")[:20],
    )
