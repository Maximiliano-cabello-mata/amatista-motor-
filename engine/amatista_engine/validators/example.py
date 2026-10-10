"""example.matches: la escena del alumno contra el ejemplo resuelto de la práctica (motor 3.5).

El cargador agrega este objetivo al final de toda práctica con «example» y
le inyecta los pasos del ejemplo, las piezas de «reference», el nivel y los
aspectos que se revisan. Un autor también puede usarlo en medio de la ruta
para un solo aspecto: {"validator": "example.matches", "params": {"aspects": ["materiales"]}}.
El detalle está en amatista_engine/ejemplo/.
"""
from __future__ import annotations

from typing import Any, Dict

from ..ejemplo import escena_esperada, lo_que_pide, revisar_ejemplo
from ..figures.reconocer import perfil_para
from ..models import SceneState, TargetDefinition, ValidationResult
from .base import number, result, text


def matches(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    pasos = target.params.get("steps")
    if not isinstance(pasos, list) or not pasos:
        raise ValueError("example.matches necesita los pasos del ejemplo («example» en la práctica)")
    partes = target.params.get("parts") or []
    nivel = int(number(target, "level", 1))
    perfil = perfil_para(nivel, text(target, "strictness") or "")
    esperada = escena_esperada(pasos, partes)
    aspectos = target.params.get("aspects") or target.params.get("check") or None
    if aspectos is not None and (not isinstance(aspectos, list) or not all(isinstance(a, str) for a in aspectos)):
        raise ValueError("example.matches: «aspects» debe ser una lista de aspectos (figura, materiales…)")
    revision = revisar_ejemplo(
        esperada, scene, perfil, nivel, lo_que_pide(pasos), aspectos, partes,
        [str(g) for g in target.params.get("flexible") or []], dict(target.params.get("labels") or {}),
        text(target, "title"),
    )
    lista = revision.lista
    detalles: Dict[str, Any] = {
        "score": round(revision.puntaje, 3), "checklist": lista, "level": nivel, "strictness": perfil.id,
        "aspects": [{"id": a.id, "nombre": a.nombre, "ok": a.aprobado} for a in revision.aspectos],
    }
    hechos = sum(1 for i in lista if i["ok"])
    if revision.aprobada:
        detalles_extra = [i for i in lista if i["estado"] == "Detalle" and i["consejo"]]
        mensaje = f"Tu práctica coincide con el ejemplo ({hechos} de {len(lista)})."
        if detalles_extra:
            mensaje += f" Un detalle: {detalles_extra[0]['consejo']}"
        return result(target, True, mensaje, detalles)
    if not revision.aspectos:
        return result(target, False, "No hay nada del ejemplo que revisar en este paso: los aspectos pedidos no "
                                     "están en el ejemplo resuelto (avisa a quien escribió la práctica).", detalles)
    pendiente = revision.pendientes[0]
    consejo = pendiente["consejo"] or f"Compara «{pendiente['texto']}» con el ejemplo."
    faltan = sum(1 for a in revision.aspectos if not a.aprobado)
    return result(target, False, f"{pendiente['aspecto']}: {consejo} (Coincide {hechos} de {len(lista)}"
                                 f"{'' if faltan == 1 else f'; {faltan} aspectos por revisar'}.)", detalles)
