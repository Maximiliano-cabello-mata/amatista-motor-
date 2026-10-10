"""taller.molde: las piezas del molde están llenas (motor 5, Amatista Taller).

Lo usan las prácticas que el taller genera al vuelo para «Hazlo conmigo»,
«Hazlo tú», los retos y los repasos (taller/actividades.py). Con
``mode: "molde"`` el alumno construye dentro del molde (importan lugar y
tamaño, con la holgura de su nivel); con ``mode: "libre"`` la figura se
acomoda sola al modelo y solo importan la forma, las proporciones y cómo se
acomodan las piezas. El detalle (qué pieza está llena, casi, equivocada o
vacía, y por qué) queda en ``details`` para que el add-on pinte el molde.
"""
from __future__ import annotations

from ..models import SceneState, TargetDefinition, ValidationResult
from .base import result


def molde(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    from ..taller.molde import revisar_molde

    piezas = target.params.get("parts") or []
    if not isinstance(piezas, list) or not piezas:
        raise ValueError("taller.molde requiere params.parts (las piezas del molde)")
    modo = str(target.params.get("mode") or "molde")
    if modo not in ("molde", "libre"):
        raise ValueError("taller.molde: params.mode debe ser molde o libre")
    nivel = int(target.params.get("level") or 1)
    revision = revisar_molde(piezas, scene, modo, nivel, target.params.get("labels") or {})
    if revision.completa:
        mensaje = "Cada pieza está en su lugar." if modo == "molde" else "Amatista reconoce tu figura."
    else:
        mensaje = revision.mensaje or "Todavía faltan piezas."
    return result(target, revision.completa, mensaje, {"molde": revision.a_dict()})
