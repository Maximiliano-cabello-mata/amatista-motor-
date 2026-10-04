"""Evidencia de aprendizaje (secciones 18, 19 y 25).

El add-on no sube el .blend ni la escena completa: genera este resumen.
La autonomía se clasifica con los mismos nombres que HABILIDADES_ALUMNO;
el servidor nunca marca «autonoma» solo con una práctica (eso pide
variación o transferencia, rúbrica D y E).
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional

from ..models import EvaluationReport, PracticeDefinition
from .hints import NIVEL_GUIA, hints_used, max_level

CON_GUIA = "con_guia"
CON_PISTAS = "con_pistas"
AUTONOMA = "autonoma"


def classify(completed: bool, hints: Mapping[str, int], corrections: int = 0) -> Optional[str]:
    """None si no terminó; con_guia si llegó a la pista paso a paso; con_pistas
    si usó pistas o correcciones guiadas; autonoma si no usó ninguna."""
    if not completed:
        return None
    if max_level(hints) >= NIVEL_GUIA:
        return CON_GUIA
    if hints_used(hints) or corrections:
        return CON_PISTAS
    return AUTONOMA


def evidence(
    practice: PracticeDefinition,
    report: EvaluationReport,
    hints: Optional[Mapping[str, int]] = None,
    corrections: int = 0,
) -> Dict[str, object]:
    hints = dict(hints or {})
    return {
        "practice": practice.id,
        "version": practice.version,
        "progress": report.progress,
        "completed": report.completed,
        "targets": [{"id": r.target_id, "completed": r.passed is True} for r in report.results],
        "hintsUsed": hints_used(hints),
        "hintLevels": hints,
        "maxHintLevel": max_level(hints),
        "errorsCorrected": int(corrections),
        "toolsUsed": list(report.tools_used),
        "toolWarnings": [w.tool_id for w in report.tool_warnings],
        "autonomy": classify(report.completed, hints, corrections),
        "skills": list(practice.skills),
    }
