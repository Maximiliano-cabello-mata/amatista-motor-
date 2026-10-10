"""Malla, modificadores y materiales."""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from ..terminos import MODIFICADORES, nombre_modificador
from .base import count_message, count_ok, count_rule, describe, result, select, selector, text


def _contar_geometria(target: TargetDefinition, scene: SceneState, campo: str, nombre: str) -> ValidationResult:
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type == "MESH"]
    minimo, maximo = count_rule(target, default_min=1)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay mallas «{que}».", {"selector": sel})
    fallan = []
    for obj in objetos:
        valor = getattr(obj, campo)
        if valor is None or not count_ok(valor, minimo, maximo):
            fallan.append({"object": obj.name, "value": valor})
    mensaje = (
        f"«{que}» tiene la cantidad de {nombre} esperada."
        if not fallan
        else count_message(fallan[0]["value"] or 0, minimo, maximo, f"{nombre} en «{fallan[0]['object']}»")
    )
    return result(
        target, not fallan, mensaje, {"selector": sel, "expected": {"min": minimo, "max": maximo}, "failed": fallan}
    )


def vertex_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _contar_geometria(target, scene, "vertices", "vértices")


def face_count(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    return _contar_geometria(target, scene, "faces", "caras")


def modifier_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Todos los objetos seleccionados tienen el modificador (BEVEL, MIRROR...)."""
    modificador = text(target, "modifier", required=True).upper()
    sel = selector(target)
    objetos = select(scene, sel)
    que = describe(sel)
    sin = [o.name for o in objetos if modificador not in o.modifiers]
    nombre = nombre_modificador(modificador)
    return result(
        target,
        bool(objetos) and not sin,
        f"«{que}» ya tiene el modificador {nombre}."
        if objetos and not sin
        else (f"No hay objetos «{que}»." if not objetos else f"Agrega el modificador {nombre} a «{sin[0]}»."),
        {"selector": sel, "modifier": modificador, "missing": sin},
    )


def material_exists(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Los objetos seleccionados tienen material (o uno con params.material en el nombre)."""
    nombre = text(target, "material")
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type in ("MESH", "CURVE", "SURFACE", "META", "FONT")]
    que = describe(sel)

    def tiene(obj) -> bool:
        if not obj.materials:
            return False
        return not nombre or any(nombre.lower() in m.lower() for m in obj.materials)

    sin = [o.name for o in objetos if not tiene(o)]
    return result(
        target,
        bool(objetos) and not sin,
        f"«{que}» ya tiene material."
        if objetos and not sin
        else (f"No hay objetos «{que}»." if not objetos else f"Asigna un material a «{sin[0]}»."),
        {"selector": sel, "material": nombre or None, "missing": sin},
    )



# --- Motor v3: salud de la malla y modificadores con ajustes -----------------------------


def no_duplicates(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Ninguna malla tiene vértices encimados (los deja «E» y luego cancelar).

    Pensado como vigilante (guard): si falla, el motor pausa el progreso y
    ofrece «Fusionar › Por distancia».
    """
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type == "MESH"]
    maximo = int(target.params.get("max", 0))
    sucias = [
        {"object": o.name, "value": o.duplicate_vertices}
        for o in objetos
        if o.duplicate_vertices is not None and o.duplicate_vertices > maximo
    ]
    if not sucias:
        return result(target, True, "La malla está limpia: no hay vértices encimados.", {"selector": sel})
    s = sucias[0]
    return result(
        target,
        False,
        f"«{s['object']}» tiene {s['value']} vértices encimados (pasa al extruir con E y cancelar). "
        "Fusiónalos por distancia.",
        {"selector": sel, "failed": sucias},
    )


def one_side(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """La malla base vive de un solo lado del eje (el espejo dibuja el otro).

    params.axis (default x), params.side (negative | positive | any) y
    params.tolerance: cuántos vértices pueden quedar del otro lado.
    """
    sel = selector(target)
    objetos = [o for o in select(scene, sel) if o.object_type == "MESH"]
    eje = str(target.params.get("axis", "x")).lower()
    if eje not in "xyz" or len(eje) != 1:
        raise ValueError("mesh.one_side requiere axis x, y o z")
    lado = str(target.params.get("side", "any")).lower()
    tolerancia = int(target.params.get("tolerance", 0))
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay mallas «{que}».", {"selector": sel})
    fallan = []
    for obj in objetos:
        if obj.side_counts is None:
            continue
        negativos, positivos = obj.side_counts["xyz".index(eje)]
        if lado == "negative":
            sobra = positivos
        elif lado == "positive":
            sobra = negativos
        else:
            sobra = min(negativos, positivos)
        if sobra > tolerancia:
            fallan.append({"object": obj.name, "value": sobra})
    if not fallan:
        return result(target, True, f"Modelaste solo una mitad de «{que}»: el espejo hace el resto.", {"selector": sel})
    return result(
        target,
        False,
        f"«{fallan[0]['object']}» tiene {fallan[0]['value']} vértices del otro lado del eje {eje.upper()}: "
        "borra esa mitad y deja que el modificador Espejo la dibuje.",
        {"selector": sel, "axis": eje, "failed": fallan},
    )


# Nombre del modificador para el alumno (uno solo para todo el motor: terminos.py).
NOMBRES_MODIFICADOR = MODIFICADORES


def modifier_configured(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Modificador con sus ajustes: eje del espejo, niveles de subdivisión, encendido.

    params: modifier (MIRROR, SUBSURF, BEVEL...), axis (x, y o z; solo
    MIRROR), only_axis (true: ningún otro eje activo), min_levels / max_levels
    (SUBSURF) y enabled (default true: visible en la vista 3D).
    """
    tipo = text(target, "modifier", required=True).upper()
    sel = selector(target)
    objetos = select(scene, sel)
    eje = str(target.params.get("axis", "") or "").lower()
    solo_eje = bool(target.params.get("only_axis", False))
    min_niveles = target.params.get("min_levels")
    max_niveles = target.params.get("max_levels")
    encendido = bool(target.params.get("enabled", True))
    que = describe(sel)
    nombre = NOMBRES_MODIFICADOR.get(tipo, tipo)
    if not objetos:
        return result(target, False, f"No hay objetos «{que}».", {"selector": sel})
    for obj in objetos:
        m = obj.modifier(tipo)
        if m is None:
            if tipo in obj.modifiers and not obj.modifier_details:
                continue  # foto de un add-on anterior: solo se sabe que existe
            return result(target, False, f"Agrega el modificador {nombre} a «{obj.name}» (llave inglesa › Agregar).",
                          {"selector": sel, "missing": obj.name, "reason": "missing"})
        if encendido and not m.enabled:
            return result(target, False, f"El modificador {nombre} de «{obj.name}» está apagado: enciende su ojo.",
                          {"selector": sel, "object": obj.name, "reason": "disabled"})
        if eje:
            indice = "xyz".index(eje)
            if not m.axes[indice]:
                return result(target, False, f"Activa el eje {eje.upper()} del espejo de «{obj.name}».",
                              {"selector": sel, "object": obj.name, "reason": "axis", "axis": eje})
            if solo_eje and sum(m.axes) > 1:
                return result(target, False, f"El espejo de «{obj.name}» debe usar solo el eje {eje.upper()}.",
                              {"selector": sel, "object": obj.name, "reason": "extra_axis", "axis": eje})
        if min_niveles is not None and (m.levels or 0) < int(min_niveles):
            return result(target, False, f"Sube los niveles de {nombre} de «{obj.name}» a {int(min_niveles)} o más.",
                          {"selector": sel, "object": obj.name, "reason": "levels", "value": m.levels})
        if max_niveles is not None and (m.levels or 0) > int(max_niveles):
            return result(target, False, f"Baja los niveles de {nombre} de «{obj.name}» a {int(max_niveles)} o menos "
                          "(más niveles = más lento).",
                          {"selector": sel, "object": obj.name, "reason": "levels", "value": m.levels})
    return result(target, True, f"El modificador {nombre} de «{que}» está bien configurado.", {"selector": sel})
