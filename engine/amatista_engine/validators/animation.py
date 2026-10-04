"""Animación con fotogramas clave (motor v3, módulo 6 del plan de estudios)."""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import describe, number, result, select, selector, text

PROPIEDADES = {"location": "posición", "rotation_euler": "rotación", "scale": "escala"}
ALIAS = {"location": "location", "posicion": "location", "rotation": "rotation_euler",
         "rotation_euler": "rotation_euler", "rotacion": "rotation_euler", "scale": "scale", "escala": "scale"}


def _propiedad(target: TargetDefinition) -> str:
    valor = str(target.params.get("property", "location")).lower()
    if valor not in ALIAS:
        raise ValueError("property debe ser location, rotation_euler o scale")
    return ALIAS[valor]


def _eje(target: TargetDefinition, defecto: str = "z") -> int:
    eje = str(target.params.get("axis", defecto)).lower()
    if eje not in ("x", "y", "z"):
        raise ValueError("axis debe ser x, y o z")
    return "xyz".index(eje)


def keyframes(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Cada objeto tiene al menos `min` fotogramas clave en property[axis]."""
    sel = selector(target)
    objetos = select(scene, sel)
    propiedad, indice = _propiedad(target), _eje(target)
    minimo = int(target.params.get("min", 2))
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay «{que}» para animar.", {"selector": sel})
    fallan = []
    for obj in objetos:
        canal = obj.channel(propiedad, indice)
        cuantos = len(canal.keys) if canal else 0
        if cuantos < minimo:
            fallan.append({"object": obj.name, "value": cuantos})
    eje = "XYZ"[indice]
    if not fallan:
        nombres = ", ".join(f"«{o.name}»" for o in objetos)
        mensaje = f"{nombres} ya tiene sus fotogramas clave de {PROPIEDADES[propiedad]} en {eje}."
    else:
        mensaje = (
            f"«{fallan[0]['object']}» tiene {fallan[0]['value']} de {minimo} fotogramas clave de "
            f"{PROPIEDADES[propiedad]} en {eje}. Cambia de fotograma, mueve el objeto y pulsa I."
        )
    return result(target, not fallan, mensaje, {"selector": sel, "property": propiedad, "axis": eje, "failed": fallan})


def varies(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Los valores de property[axis] cambian a lo largo de la línea de tiempo.

    params: min_delta (lo mínimo entre el valor más alto y el más bajo),
    low_max (el valor más bajo llega a este o menos: «toca el suelo»),
    high_min (el más alto llega a este o más), ground (true: el valor más
    bajo de location z deja la pelota tocando el suelo, es decir, a su radio
    más una tolerancia; vale con el origen al centro, como en las primitivas)
    y bounce (true: hay un valle, un fotograma más bajo que uno anterior y
    uno posterior: cae y vuelve a subir).
    """
    sel = selector(target)
    objetos = select(scene, sel)
    propiedad, indice = _propiedad(target), _eje(target)
    delta = number(target, "min_delta", 0.0)
    bajo = target.params.get("low_max")
    alto = target.params.get("high_min")
    rebote = bool(target.params.get("bounce", False))
    suelo = bool(target.params.get("ground", False))
    tolerancia = number(target, "tolerance", 0.15)
    que = describe(sel)
    eje = "XYZ"[indice]
    if not objetos:
        return result(target, False, f"No hay «{que}» para animar.", {"selector": sel})
    for obj in objetos:
        canal = obj.channel(propiedad, indice)
        valores = canal.values if canal else ()
        if len(valores) < 2:
            return result(target, False, f"«{obj.name}» todavía no tiene animación de {PROPIEDADES[propiedad]} en {eje}.",
                          {"selector": sel, "object": obj.name, "reason": "keys"})
        if max(valores) - min(valores) < delta:
            return result(
                target, False,
                f"La {PROPIEDADES[propiedad]} de «{obj.name}» en {eje} casi no cambia "
                f"({max(valores) - min(valores):.2f}); haz que cambie al menos {delta:g}.",
                {"selector": sel, "object": obj.name, "reason": "delta"},
            )
        if bajo is not None and min(valores) > float(bajo):
            return result(
                target, False,
                f"En su punto más bajo, «{obj.name}» queda en {min(valores):.2f}: debe llegar a {float(bajo):g} o menos.",
                {"selector": sel, "object": obj.name, "reason": "low"},
            )
        if suelo:
            # El radio sale del ancho (X/Y): la altura cambia si la pelota se aplasta en ese fotograma.
            radio = min(obj.dimensions[0], obj.dimensions[1]) / 2.0 if obj.dimensions[0] and obj.dimensions[1] \
                else obj.dimensions[2] / 2.0
            if min(valores) > radio + tolerancia:
                return result(
                    target, False,
                    f"«{obj.name}» nunca toca el suelo: en su punto más bajo su centro está en {min(valores):.2f} "
                    f"y debería bajar a {radio:.2f} (su radio).",
                    {"selector": sel, "object": obj.name, "reason": "low"},
                )
        if alto is not None and max(valores) < float(alto):
            return result(
                target, False,
                f"En su punto más alto, «{obj.name}» queda en {max(valores):.2f}: debe llegar a {float(alto):g} o más.",
                {"selector": sel, "object": obj.name, "reason": "high"},
            )
        if rebote and not any(
            valores[i] < valores[i - 1] and valores[i] < valores[i + 1] for i in range(1, len(valores) - 1)
        ):
            return result(
                target, False,
                f"«{obj.name}» baja pero no vuelve a subir: agrega un fotograma clave más alto después del golpe.",
                {"selector": sel, "object": obj.name, "reason": "bounce"},
            )
    nombres = ", ".join(f"«{o.name}»" for o in objetos)
    if rebote and suelo:
        mensaje = f"¡Bien! {nombres} cae, toca el suelo y vuelve a subir."
    elif rebote:
        mensaje = f"¡Bien! {nombres} baja y vuelve a subir."
    elif bajo is not None:
        mensaje = f"¡Bien! La {PROPIEDADES[propiedad]} en {eje} de {nombres} baja a {float(bajo):g} o menos."
    else:
        mensaje = f"¡Bien! La {PROPIEDADES[propiedad]} en {eje} de {nombres} cambia como se pedía."
    return result(target, True, mensaje,
                  {"selector": sel, "property": propiedad, "axis": eje})
