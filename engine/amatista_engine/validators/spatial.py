"""Relaciones entre objetos: apoyados en el suelo y en contacto (motor v3).

Las relaciones se revisan con las cajas envolventes en el mundo (bbox): son
aproximadas a propósito; una rueda que toca el vagón «por la caja» cuenta
como unida, que es lo que un principiante ve en la vista 3D.
"""
from __future__ import annotations

from ..models import SceneObject, SceneState, TargetDefinition, ValidationResult
from .base import describe, number, result, select, selector, text


def grounded(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """La parte más baja de cada objeto queda a la altura params.height (0 = suelo)."""
    sel = selector(target)
    objetos = select(scene, sel)
    altura = number(target, "height", 0.0)
    tolerancia = number(target, "tolerance", 0.05)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay «{que}» para apoyar.", {"selector": sel})
    fallan = []
    for obj in objetos:
        base = obj.caja()[0][2]
        if abs(base - altura) > tolerancia:
            fallan.append({"object": obj.name, "value": round(base, 3), "reason": "flota" if base > altura else "hundido"})
    if not fallan:
        mensaje = f"«{que}» queda apoyado en el suelo."
    else:
        f = fallan[0]
        mensaje = (
            f"«{f['object']}» {'flota' if f['reason'] == 'flota' else 'se hunde'}: su base está en "
            f"Z = {f['value']:.2f} y debe quedar en {altura:g}."
        )
    return result(
        target, not fallan, mensaje, {"selector": sel, "height": altura, "tolerance": tolerancia, "failed": fallan}
    )


def _separacion(a: SceneObject, b: SceneObject) -> float:
    """Distancia entre dos cajas (0 si se tocan o se cruzan)."""
    (amin, amax), (bmin, bmax) = a.caja(), b.caja()
    huecos = [max(bmin[i] - amax[i], amin[i] - bmax[i], 0.0) for i in range(3)]
    return sum(h * h for h in huecos) ** 0.5


def _referencias(target: TargetDefinition, scene: SceneState):
    rol = text(target, "reference_role")
    nombre = text(target, "reference")
    primitiva = text(target, "reference_primitive")
    if not (rol or nombre or primitiva):
        raise ValueError(f"{target.validator} requiere reference_role, reference o reference_primitive")
    sel = {}
    if rol:
        sel["role"] = rol
    if nombre:
        sel["name"] = nombre
    if primitiva:
        sel["primitive"] = primitiva
    return sel, select(scene, sel)


def touching(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Cada objeto seleccionado toca (o casi) al menos un objeto de referencia."""
    sel = selector(target)
    objetos = select(scene, sel)
    sel_ref, referencias = _referencias(target, scene)
    tolerancia = number(target, "tolerance", 0.05)
    que, ref = describe(sel), describe(sel_ref)
    if not objetos or not referencias:
        falta = que if not objetos else ref
        return result(target, False, f"Todavía falta «{falta}» para revisar si están unidos.", {"selector": sel})
    sueltos = []
    for obj in objetos:
        otros = [r for r in referencias if r.name != obj.name]
        distancia = min((_separacion(obj, r) for r in otros), default=float("inf"))
        if distancia > tolerancia:
            sueltos.append({"object": obj.name, "value": round(distancia, 3) if distancia != float("inf") else None})
    if not sueltos:
        mensaje = f"Todas las piezas «{que}» tocan «{ref}»."
    else:
        mensaje = f"«{sueltos[0]['object']}» está separado de «{ref}»: acércalo con G hasta que se toquen."
    return result(target, not sueltos, mensaje, {"selector": sel, "reference": sel_ref, "failed": sueltos})


def on_top(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Cada objeto descansa ENCIMA de un objeto de referencia (motor 3.3): un techo sobre su casa.

    spatial.touching acepta un techo pegado al costado; aquí la base del objeto
    queda cerca de la parte de arriba de la referencia (±tolerance, relativa a la
    altura del objeto) y su centro cae sobre ella, no al lado.
    """
    sel = selector(target)
    objetos = select(scene, sel)
    sel_ref, referencias = _referencias(target, scene)
    tolerancia = number(target, "tolerance", 0.25)
    que, ref = describe(sel), describe(sel_ref)
    if not objetos or not referencias:
        falta = que if not objetos else ref
        return result(target, False, f"Todavía falta «{falta}» para revisar qué va encima.", {"selector": sel})
    fallan = []
    for obj in objetos:
        (omin, omax) = obj.caja()
        alto = max(omax[2] - omin[2], 0.01)
        centro = ((omin[0] + omax[0]) / 2, (omin[1] + omax[1]) / 2)
        mejor = None
        for r in referencias:
            if r.name == obj.name:
                continue
            rmin, rmax = r.caja()
            margen = 0.1 * max(rmax[0] - rmin[0], rmax[1] - rmin[1])
            encima = all(rmin[i] - margen <= centro[i] <= rmax[i] + margen for i in range(2))
            hueco = omin[2] - rmax[2]
            if encima and abs(hueco) <= tolerancia * alto + 0.02:
                mejor = None
                break
            razon = "lado" if not encima else ("flota" if hueco > 0 else "hundido")
            if mejor is None or (encima and mejor["reason"] == "lado"):
                mejor = {"object": obj.name, "reason": razon, "value": round(hueco, 2)}
        else:
            if mejor:
                fallan.append(mejor)
    if not fallan:
        mensaje = f"Cada «{que}» descansa encima de «{ref}»."
    else:
        f = fallan[0]
        mensaje = {
            "lado": f"«{f['object']}» está al lado de «{ref}», no encima: muévelo con G hasta que quede arriba.",
            "flota": f"«{f['object']}» flota {f['value']:.2f} m sobre «{ref}»: bájalo con G Z hasta que se apoye.",
            "hundido": f"«{f['object']}» se hunde en «{ref}»: súbelo con G Z hasta que se apoye arriba.",
        }[f["reason"]]
    return result(target, not fallan, mensaje, {"selector": sel, "reference": sel_ref, "failed": fallan})
