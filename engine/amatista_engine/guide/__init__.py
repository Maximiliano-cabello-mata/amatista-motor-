"""Etapa 2 del motor: guía paso a paso y acompañamiento.

    guia = build_guidance(practica, escena, reporte)   # qué hacer ahora
    avisos = Companion().observe(practica, reporte, t)  # cuándo decirlo

Documentación: docs/motor/referencia/07_guia_y_acompanamiento.md.
"""
from .coach import ENTRENADORES, build_guidance, guide_target, objetivo_amable
from .companion import Companion, distance
from .models import (
    GuideAction,
    GuideInstruction,
    Guidance,
    Highlight,
    Intervention,
    VisualCue,
    guidance_to_dict,
)

__all__ = [
    "ENTRENADORES",
    "Companion",
    "GuideAction",
    "GuideInstruction",
    "Guidance",
    "Highlight",
    "Intervention",
    "VisualCue",
    "build_guidance",
    "distance",
    "guidance_to_dict",
    "guide_target",
    "objetivo_amable",
]
