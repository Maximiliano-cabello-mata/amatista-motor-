"""Escena ⇄ JSON compacto para enviarla al servidor.

El add-on manda esta «foto» (nombres, tipos, roles, medidas y la silueta;
nunca la malla ni el .blend) y el servidor vuelve a evaluar la práctica con el mismo motor:
el progreso que se guarda en Oracle lo calcula Amatista, no el cliente.

Claves cortas por objeto (las del motor v3 son opcionales):

    n t l d r rot s m g mat c v f b p     nombre, tipo, ubicación, medidas…  (v1)
    dn                                   nombre de los datos («Cylinder.001»)
    md  [{t, n, ax, lv, on}]             modificadores con sus ajustes
    mt  [{n, c, me, ro, tr, a}]          materiales (Principled BSDF)
    mu  [nombres]                        materiales que pintan caras
    lt  {t, e}                           luz: tipo y potencia
    ca  ángulo                           cámara: campo de visión (radianes)
    fw  [x, y, z]                        hacia dónde mira (cámara o luz)
    dv  entero                           vértices encimados
    sd  [[-, +], [-, +], [-, +]]         vértices a cada lado de cada eje local
    an  [{p, i, k: [[fotograma, valor]]}] fotogramas clave
    si  {e, l, w: [[ancho, grueso]]}     silueta de la malla (motor 3.5): eje, largo y rebanadas

y de la escena: activo, seleccion, camara, motor_render, renders, fotogramas.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence

from .errors import InvalidPracticeError
from .models import AnimationChannel, MaterialInfo, ModifierInfo, SceneObject, SceneState, Silhouette

MAX_OBJETOS = 500
MAX_LISTA = 32
MAX_NOMBRE = 120
MAX_CANALES = 12
MAX_CLAVES = 120
MAX_REBANADAS = 64  # rebanadas de la silueta de una malla (motor 3.5)
RUTAS_ANIMACION = ("location", "rotation_euler", "scale")


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
        _extras_v3(o, item)
        objetos.append(item)
    datos = {
        "blender": scene.blender_version,
        "archivo": scene.file_name,
        "guardado": scene.file_saved,
        "modo": scene.mode,
        "objetos": objetos,
    }
    if scene.active_object:
        datos["activo"] = scene.active_object
    if scene.selected:
        datos["seleccion"] = list(scene.selected[:MAX_LISTA])
    if scene.active_camera:
        datos["camara"] = scene.active_camera
    if scene.render_engine:
        datos["motor_render"] = scene.render_engine
    if scene.renders:
        datos["renders"] = scene.renders
    if tuple(scene.frame_range) != (1, 250):
        datos["fotogramas"] = list(scene.frame_range)
    return datos


def _r(valor: float) -> float:
    return round(float(valor), 4)


def _extras_v3(o: SceneObject, item: Dict[str, Any]) -> None:
    if o.data_name:
        item["dn"] = o.data_name
    if o.modifier_details:
        item["md"] = [
            {k: v for k, v in (("t", m.type), ("n", m.name), ("ax", [int(a) for a in m.axes]),
                               ("lv", m.levels), ("on", int(m.enabled))) if v not in (None, "")}
            for m in o.modifier_details[:MAX_LISTA]
        ]
    if o.material_details:
        item["mt"] = [
            {"n": m.name, "c": [_r(c) for c in m.base_color], "me": _r(m.metallic), "ro": _r(m.roughness),
             "tr": _r(m.transmission), "a": _r(m.alpha)}
            for m in o.material_details[:MAX_LISTA]
        ]
    if o.materials_used is not None:
        item["mu"] = list(o.materials_used[:MAX_LISTA])
    if o.light_type:
        item["lt"] = {"t": o.light_type, "e": _r(o.light_energy or 0.0)}
    if o.camera_angle is not None:
        item["ca"] = _r(o.camera_angle)
    if o.forward is not None:
        item["fw"] = _vector(o.forward)
    if o.duplicate_vertices is not None:
        item["dv"] = o.duplicate_vertices
    if o.side_counts is not None:
        item["sd"] = [list(par) for par in o.side_counts]
    if o.silhouette is not None:
        item["si"] = {"e": o.silhouette.eje, "l": _r(o.silhouette.largo),
                      "w": [[_r(a), _r(b)] for a, b in o.silhouette.anchos[:MAX_REBANADAS]]}
    if o.animation:
        item["an"] = [
            {"p": c.path, "i": c.index, "k": [[_r(f), _r(v)] for f, v in c.keys[:MAX_CLAVES]]}
            for c in o.animation[:MAX_CANALES]
        ]


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


def _numero(valor, defecto: float) -> float:
    if valor is None:
        return defecto
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(float(valor)):
        raise InvalidPracticeError("Número inválido en la escena")
    return float(valor)


def _entero(valor) -> Optional[int]:
    return int(valor) if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0 else None


def _lista_dicts(valor, maximo: int) -> list:
    if not valor:
        return []
    if not isinstance(valor, list) or not all(isinstance(x, dict) for x in valor):
        raise InvalidPracticeError("Lista inválida en la escena")
    return valor[:maximo]


def _modificadores(valor) -> tuple:
    salida = []
    for m in _lista_dicts(valor, MAX_LISTA):
        ejes = m.get("ax") or [0, 0, 0]
        if not isinstance(ejes, list) or len(ejes) != 3:
            raise InvalidPracticeError("Ejes inválidos en un modificador")
        salida.append(ModifierInfo(
            type=str(m.get("t", ""))[:30].upper(),
            name=str(m.get("n", ""))[:MAX_NOMBRE],
            axes=tuple(bool(a) for a in ejes),
            levels=_entero(m.get("lv")),
            enabled=bool(m.get("on", 1)),
        ))
    return tuple(salida)


def _materiales(valor) -> tuple:
    salida = []
    for m in _lista_dicts(valor, MAX_LISTA):
        color = m.get("c") or [0.8, 0.8, 0.8, 1.0]
        if not isinstance(color, list) or len(color) not in (3, 4):
            raise InvalidPracticeError("Color inválido en un material")
        color = [_numero(c, 0.0) for c in color] + ([1.0] if len(color) == 3 else [])
        salida.append(MaterialInfo(
            name=str(m.get("n", ""))[:MAX_NOMBRE],
            base_color=tuple(color),
            metallic=_numero(m.get("me"), 0.0),
            roughness=_numero(m.get("ro"), 0.5),
            transmission=_numero(m.get("tr"), 0.0),
            alpha=_numero(m.get("a"), 1.0),
        ))
    return tuple(salida)


def _animacion(valor) -> tuple:
    canales = []
    for c in _lista_dicts(valor, MAX_CANALES):
        ruta = str(c.get("p", ""))
        indice = c.get("i")
        if ruta not in RUTAS_ANIMACION or _entero(indice) is None or indice > 2:
            raise InvalidPracticeError("Canal de animación inválido")
        claves = c.get("k") or []
        if not isinstance(claves, list):
            raise InvalidPracticeError("Fotogramas inválidos")
        pares = []
        for par in claves[:MAX_CLAVES]:
            if not isinstance(par, list) or len(par) != 2:
                raise InvalidPracticeError("Fotograma inválido")
            pares.append((_numero(par[0], 0.0), _numero(par[1], 0.0)))
        canales.append(AnimationChannel(ruta, int(indice), tuple(sorted(pares))))
    return tuple(canales)


def _silueta(valor) -> Optional[Silhouette]:
    """La silueta de la malla (motor 3.5); si viene rota, se ignora."""
    if not isinstance(valor, dict):
        return None
    try:
        eje = int(valor.get("e", 2))
        largo = float(valor.get("l", 0.0))
        anchos = tuple((max(0.0, float(a)), max(0.0, float(b))) for a, b in list(valor.get("w") or [])[:MAX_REBANADAS])
    except (TypeError, ValueError):
        return None
    if eje not in (0, 1, 2) or not 0 < largo < 1e6 or len(anchos) < 4:
        return None
    if not all(math.isfinite(a) and math.isfinite(b) and a < 1e6 and b < 1e6 for a, b in anchos):
        return None
    return Silhouette(eje, largo, anchos)


def _lados(valor):
    if valor is None:
        return None
    if not isinstance(valor, list) or len(valor) != 3:
        raise InvalidPracticeError("Lados inválidos en la escena")
    lados = []
    for par in valor:
        if not isinstance(par, list) or len(par) != 2 or any(_entero(n) is None for n in par):
            raise InvalidPracticeError("Lados inválidos en la escena")
        lados.append((int(par[0]), int(par[1])))
    return tuple(lados)


def _luz(valor):
    if not valor:
        return None, None
    if not isinstance(valor, dict):
        raise InvalidPracticeError("Luz inválida en la escena")
    return str(valor.get("t", "POINT"))[:10].upper(), _numero(valor.get("e"), 0.0)


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
        tipo_luz, energia = _luz(crudo.get("lt"))
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
                data_name=str(crudo["dn"])[:MAX_NOMBRE] if crudo.get("dn") else None,
                modifier_details=_modificadores(crudo.get("md")),
                material_details=_materiales(crudo.get("mt")),
                materials_used=_textos(crudo.get("mu")) if "mu" in crudo else None,
                light_type=tipo_luz,
                light_energy=energia,
                camera_angle=_numero(crudo["ca"], 0.0) if crudo.get("ca") is not None else None,
                forward=_tupla_vector(crudo.get("fw"), None),
                duplicate_vertices=_entero(crudo.get("dv")),
                side_counts=_lados(crudo.get("sd")),
                animation=_animacion(crudo.get("an")),
                silhouette=_silueta(crudo.get("si")),
            )
        )
    archivo = str(data.get("archivo") or "")[:255]
    return SceneState(
        blender_version=str(data.get("blender") or "")[:20],
        file_path=archivo,
        file_saved=bool(data.get("guardado")),
        objects=tuple(objetos),
        mode=str(data.get("modo") or "OBJECT")[:20],
        active_object=str(data["activo"])[:MAX_NOMBRE] if data.get("activo") else None,
        selected=_textos(data.get("seleccion")),
        active_camera=str(data["camara"])[:MAX_NOMBRE] if data.get("camara") else None,
        render_engine=str(data.get("motor_render") or "")[:40],
        renders=_entero(data.get("renders")) or 0,
        frame_range=_rango_fotogramas(data.get("fotogramas")),
    )


def _rango_fotogramas(valor):
    if not valor:
        return (1, 250)
    if not isinstance(valor, list) or len(valor) != 2 or not all(isinstance(v, int) for v in valor):
        raise InvalidPracticeError("Rango de fotogramas inválido")
    return (int(valor[0]), int(valor[1]))
