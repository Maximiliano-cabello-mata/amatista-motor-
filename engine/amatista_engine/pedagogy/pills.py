"""Píldoras de teoría (motor v3): qué idea mostrar y cuándo.

El plan de estudios pide que la teoría no llegue como texto largo sino
como «pequeñas píldoras visuales que aparecen solo cuando el estudiante
necesita usar una herramienta». Cada píldora declara su disparador
(practice/2 › pills[].trigger) y esta función decide cuáles tocan ahora,
en orden de urgencia:

    guard > target > mode > tool > selection > start > complete

`seen` son las píldoras que el alumno ya cerró (las de once=true no
vuelven). El add-on muestra la primera como tarjeta y dibuja su visual
(ejes, teclas, pestaña de Propiedades) sobre la vista 3D.
"""
from __future__ import annotations

from typing import Iterable, Tuple

from ..models import EvaluationReport, PillDefinition, PracticeDefinition, SceneState

PRIORIDAD = {"guard": 0, "target": 1, "mode": 2, "tool": 3, "selection": 4, "start": 5, "complete": 6}


def _toca(p: PillDefinition, scene: SceneState, report: EvaluationReport, tools_used) -> bool:
    t = p.trigger
    if t.on == "start":
        return not report.completed
    if t.on == "target":
        return report.current_target_id == t.target and not report.paused
    if t.on == "guard":
        return report.paused_by == t.target
    if t.on == "mode":
        return (scene.mode or "").upper().startswith(t.mode)
    if t.on == "selection":
        return bool(scene.selected or scene.active_object)
    if t.on == "tool":
        return t.tool in tools_used
    if t.on == "complete":
        return report.completed
    return False


def pills_for(
    practice: PracticeDefinition,
    scene: SceneState,
    report: EvaluationReport,
    seen: Iterable[str] = (),
    tools_used: Iterable[str] = (),
) -> Tuple[PillDefinition, ...]:
    vistas = set(seen)
    usados = set(tools_used)
    tocan = [
        (PRIORIDAD.get(p.trigger.on, 9), i, p)
        for i, p in enumerate(practice.pills)
        if not (p.once and p.id in vistas) and _toca(p, scene, report, usados)
    ]
    return tuple(p for _, _, p in sorted(tocan, key=lambda x: (x[0], x[1])))


def pill_to_dict(p: PillDefinition) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "text": p.text,
        "keys": list(p.keys),
        "visual": p.visual,
        "trigger": p.trigger.on,
        "check": None
        if p.check is None
        else {"question": p.check.question, "options": list(p.check.options), "answer": p.check.answer},
    }
