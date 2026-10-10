"""Forma de los objetos: qué eje es el más delgado y proporciones (motor v3).

Sirven para revisar formas sin exigir medidas exactas: «la rueda está de
pie» (su eje más delgado es horizontal) o «la espada es alargada» (mide en
Z al menos tres veces lo que mide en X o Y).

Se mide la caja en el MUNDO (como se ve en la vista 3D), no las
dimensiones locales: un cilindro girado 90° en X queda delgado en Y aunque
su «Dimensión Z» local siga siendo la pequeña.
"""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import EJES, describe, number, result, select, selector, text


def medidas_mundo(obj):
    minimo, maximo = obj.caja()
    return tuple(maximo[i] - minimo[i] for i in range(3))

NOMBRES_EJE = {"x": "X", "y": "Y", "z": "Z", "horizontal": "X o Y"}


def thinnest_axis(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """El eje más delgado de cada objeto es params.axis (x, y, z u horizontal).

    max_ratio (default 0.6): lo delgado debe medir como máximo esa fracción
    de lo más grande; así un cubo (todo igual) no cuenta como «plano».
    """
    sel = selector(target)
    objetos = select(scene, sel)
    eje = text(target, "axis") or "horizontal"
    if eje not in NOMBRES_EJE:
        raise ValueError("shape.thinnest_axis requiere axis x, y, z u horizontal")
    razon = number(target, "max_ratio", 0.6)
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay «{que}» para revisar su forma.", {"selector": sel})
    fallan = []
    for obj in objetos:
        d = medidas_mundo(obj)
        grande = max(d) or 1.0
        delgado = min(range(3), key=lambda i: d[i])
        ok_eje = delgado in ((0, 1) if eje == "horizontal" else (EJES[eje],))
        if not ok_eje or d[delgado] > razon * grande:
            fallan.append({"object": obj.name, "thinnest": "xyz"[delgado], "ratio": round(d[delgado] / grande, 3)})
    if not fallan:
        mensaje = f"La forma de «{que}» es la esperada."
    else:
        f = fallan[0]
        mensaje = (
            f"«{f['object']}» todavía no es delgado en {NOMBRES_EJE[eje]}: "
            f"su lado más delgado es {f['thinnest'].upper()}."
        )
    return result(target, not fallan, mensaje, {"selector": sel, "axis": eje, "max_ratio": razon, "failed": fallan})


def proportion(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Cada objeto mide en params.axis al menos min_ratio veces su otra medida mayor."""
    sel = selector(target)
    objetos = select(scene, sel)
    eje = (text(target, "axis") or "z").lower()
    if eje not in EJES:
        raise ValueError("shape.proportion requiere axis x, y o z")
    indice = EJES[eje]
    minimo = number(target, "min_ratio", 2.0)
    maximo = number(target, "max_ratio", float("inf"))
    que = describe(sel)
    if not objetos:
        return result(target, False, f"No hay «{que}» para revisar su proporción.", {"selector": sel})
    fallan = []
    for obj in objetos:
        d = medidas_mundo(obj)
        otros = [d[i] for i in range(3) if i != indice]
        base = max(otros) or 1e-6
        razon = d[indice] / base
        if not minimo <= razon <= maximo:
            fallan.append({"object": obj.name, "value": round(razon, 2)})
    if not fallan:
        mensaje = f"Las proporciones de «{que}» están bien."
    else:
        valor = fallan[0]["value"]
        veces = "vez" if valor == 1 else "veces"
        limite = f"como máximo {maximo:g}" if valor > maximo else f"al menos {minimo:g}"
        mensaje = f"«{fallan[0]['object']}» mide en {eje.upper()} {valor:g} {veces} su ancho; se busca {limite}."
    return result(target, not fallan, mensaje, {"selector": sel, "axis": eje, "min": minimo,
                                                 "max": None if maximo == float("inf") else maximo, "failed": fallan})
