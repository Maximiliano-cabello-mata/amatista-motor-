"""Luces, cámara y render (motor v3, módulo 5 del plan de estudios).

light.three_point reconoce la iluminación de tres puntos SIN pedir roles:
mira desde la cámara hacia el modelo y busca una luz delante a cada lado
(principal y relleno) y una detrás (contraluz).
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from ..models import SceneObject, SceneState, TargetDefinition, ValidationResult
from .base import describe, number, result, select, selector, text


def _camara(scene: SceneState) -> Optional[SceneObject]:
    if scene.active_camera:
        cam = scene.object_by_name(scene.active_camera)
        if cam is not None:
            return cam
    return next((o for o in scene.objects if o.object_type == "CAMERA"), None)


def _centro(objetos) -> Tuple[float, float, float]:
    minimos = [o.caja()[0] for o in objetos]
    maximos = [o.caja()[1] for o in objetos]
    return tuple((min(m[i] for m in minimos) + max(m[i] for m in maximos)) / 2.0 for i in range(3))


def _sujeto(target: TargetDefinition, scene: SceneState):
    sel = selector(target)
    objetos = select(scene, sel) if sel else tuple(o for o in scene.objects if o.object_type == "MESH")
    return sel, objetos


def forward_from_euler(rotation) -> Tuple[float, float, float]:
    """Hacia dónde mira una cámara con rotación Euler XYZ (si la foto no trae «forward»)."""
    a, b, c = rotation
    v = (0.0, 0.0, -1.0)
    # Rx
    v = (v[0], v[1] * math.cos(a) - v[2] * math.sin(a), v[1] * math.sin(a) + v[2] * math.cos(a))
    # Ry
    v = (v[0] * math.cos(b) + v[2] * math.sin(b), v[1], -v[0] * math.sin(b) + v[2] * math.cos(b))
    # Rz
    v = (v[0] * math.cos(c) - v[1] * math.sin(c), v[0] * math.sin(c) + v[1] * math.cos(c), v[2])
    return v


def camera_active(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    cam = scene.object_by_name(scene.active_camera) if scene.active_camera else None
    if cam is not None:
        return result(target, True, f"«{cam.name}» es la cámara activa de la escena.", {"camera": cam.name})
    hay = any(o.object_type == "CAMERA" for o in scene.objects)
    mensaje = (
        "Hay una cámara, pero no está activa: selecciónala y pulsa Ctrl+0 (cero del teclado numérico)."
        if hay
        else "Agrega una cámara: Shift+A › Cámara."
    )
    return result(target, False, mensaje, {"camera": None})


def camera_frames(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """El modelo (selector o todas las mallas) queda dentro de lo que ve la cámara."""
    cam = _camara(scene)
    sel, objetos = _sujeto(target, scene)
    que = describe(sel) if sel else "tu modelo"
    if cam is None:
        return result(target, False, "Todavía no hay cámara: Shift+A › Cámara.", {"reason": "no_camera"})
    if not objetos:
        return result(target, False, f"No hay {que} para encuadrar.", {"reason": "no_subject"})
    centro = _centro(objetos)
    hacia = cam.forward or forward_from_euler(cam.rotation)
    d = tuple(centro[i] - cam.location[i] for i in range(3))
    largo = math.sqrt(sum(x * x for x in d)) or 1e-6
    coseno = sum(d[i] * hacia[i] for i in range(3)) / largo
    angulo = math.degrees(math.acos(max(-1.0, min(1.0, coseno))))
    limite = math.degrees((cam.camera_angle or 0.6911) / 2.0) * number(target, "margin", 1.0)
    ok = angulo <= limite
    mensaje = (
        f"La cámara «{cam.name}» encuadra {que}."
        if ok
        else f"La cámara no está mirando a {que} (se desvía {angulo:.0f}°). Pulsa 0 del teclado numérico para "
        "ver por la cámara y muévela con G y R."
    )
    return result(target, ok, mensaje, {"camera": cam.name, "angle": round(angulo, 1), "limit": round(limite, 1)})


def three_point(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Principal y relleno delante del modelo (uno a cada lado) y contraluz detrás.

    params: el selector del modelo (o todas las mallas), fill_weaker (default
    true: el relleno debe ser más suave que la principal si son del mismo tipo).
    """
    cam = _camara(scene)
    sel, objetos = _sujeto(target, scene)
    luces = [o for o in scene.objects if o.object_type == "LIGHT"]
    if cam is None:
        return result(target, False, "Primero coloca la cámara: las tres luces se ubican mirando desde ella.",
                      {"reason": "no_camera"})
    if not objetos:
        return result(target, False, "No hay modelo que iluminar.", {"reason": "no_subject"})
    if len(luces) < 3:
        return result(target, False, f"Hay {len(luces)} de 3 luces. Agrega más con Shift+A › Luz.",
                      {"reason": "count", "found": len(luces)})
    centro = _centro(objetos)
    cx, cy = cam.location[0] - centro[0], cam.location[1] - centro[1]
    norma = math.hypot(cx, cy) or 1e-6
    cx, cy = cx / norma, cy / norma
    delante_izq, delante_der, detras = [], [], []
    for luz in luces:
        vx, vy = luz.location[0] - centro[0], luz.location[1] - centro[1]
        frente = vx * cx + vy * cy
        lado = cx * vy - cy * vx  # z del producto cruz: + izquierda de la cámara
        if frente < 0:
            detras.append(luz)
        elif lado > 0.05:
            delante_izq.append(luz)
        elif lado < -0.05:
            delante_der.append(luz)
    faltan = []
    if not (delante_izq and delante_der):
        faltan.append("una luz delante a cada lado del modelo (principal y relleno)")
    if not detras:
        faltan.append("una luz detrás del modelo, del lado contrario a la cámara (contraluz)")
    detalles = {
        "front_left": [l.name for l in delante_izq],
        "front_right": [l.name for l in delante_der],
        "back": [l.name for l in detras],
    }
    if faltan:
        return result(target, False, "Falta " + " y ".join(faltan) + ".", {**detalles, "reason": "layout"})
    if bool(target.params.get("fill_weaker", True)):
        frontales = sorted(delante_izq + delante_der, key=lambda l: l.light_energy or 0.0, reverse=True)
        principal = frontales[0]
        rellenos = [l for l in (delante_der if principal in delante_izq else delante_izq)
                    if l.light_type == principal.light_type]
        if rellenos and all((r.light_energy or 0) >= (principal.light_energy or 0) for r in rellenos):
            return result(
                target, False,
                f"Las luces delanteras tienen la misma fuerza. Baja la potencia del relleno «{rellenos[0].name}» "
                f"(por ejemplo, a la mitad de «{principal.name}»).",
                {**detalles, "reason": "fill", "key": principal.name},
            )
        detalles["key"] = principal.name
    return result(target, True, "¡Iluminación de tres puntos lista: principal, relleno y contraluz!", detalles)


def render_engine(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    motor = text(target, "engine") or "EEVEE"
    ok = motor.upper() in (scene.render_engine or "").upper()
    nombre = {"EEVEE": "EEVEE", "CYCLES": "Cycles", "WORKBENCH": "Workbench"}.get(motor.upper(), motor)
    return result(
        target,
        ok,
        f"El motor de render es {nombre}." if ok else f"Cambia el motor de render a {nombre} (Propiedades › Render).",
        {"engine": scene.render_engine, "expected": motor},
    )


def render_done(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    minimo = int(target.params.get("min", 1))
    ok = scene.renders >= minimo
    return result(
        target,
        ok,
        "¡Tu primera imagen está lista!" if ok else "Pulsa F12 para hacer el render final.",
        {"renders": scene.renders, "min": minimo},
    )
