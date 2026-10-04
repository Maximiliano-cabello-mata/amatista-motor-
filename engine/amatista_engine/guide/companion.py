"""El acompañante: mira cómo evoluciona la escena y decide cuándo hablar.

La etapa 1 solo respondía cuando el alumno pedía una pista. El acompañante
observa cada evaluación y propone intervenciones:

    paso_logrado       un objetivo pasó a cumplirse («¡Listo! Hazla delgada»)
    nuevo_paso         empieza un paso nuevo: qué hay que hacer y por qué
    mejorando          un número se acercó al rango pedido («¡Vas mejor!»)
    retroceso          algo que estaba bien dejó de estarlo
    ofrecer_ayuda      lleva varios intentos o mucho tiempo en el mismo paso
    practica_completa  terminó la práctica
    pausa              un vigilante detuvo el progreso (motor v3): qué pasó y cómo arreglarlo
    reanuda            el vigilante volvió a cumplirse: el progreso sigue

No dibuja nada ni conoce Blender: el add-on decide si cada intervención es
un aviso que se desvanece o un diálogo (Intervention.dialog). El estado es
un dict de tipos simples para poder guardarlo o enviarlo.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..models import EvaluationReport, PracticeDefinition, ValidationResult
from .models import (
    MEJORANDO,
    NUEVO_PASO,
    OFRECER_AYUDA,
    PASO_LOGRADO,
    PAUSA,
    REANUDA,
    PRACTICA_COMPLETA,
    RETROCESO,
    Intervention,
)

# Cuánto debe acercarse un número para decir «¡vas mejor!» (fracción de la distancia anterior).
MEJORA_MINIMA = 0.15


def distance(result: Optional[ValidationResult]) -> Optional[float]:
    """Qué tan lejos está un objetivo de cumplirse (0 = cumplido; None = no medible)."""
    if result is None or result.passed is None:
        return None
    if result.passed:
        return 0.0
    d = result.details
    fallos = d.get("failed") or []
    if fallos and isinstance(fallos[0].get("value"), (int, float)):
        valor = float(fallos[0]["value"])
        minimo = float(d.get("min", -math.inf)) if not isinstance(d.get("expected"), dict) else float(
            d["expected"].get("min") or -math.inf
        )
        maximo = float(d.get("max", math.inf)) if not isinstance(d.get("expected"), dict) else float(
            d["expected"].get("max") or math.inf
        )
        if valor < minimo:
            return minimo - valor
        if valor > maximo:
            return valor - maximo
        return 0.0
    esperado = d.get("expected")
    encontrado = d.get("found")
    if isinstance(encontrado, int):
        if isinstance(esperado, int):
            return float(abs(esperado - encontrado))
        if isinstance(esperado, dict):
            minimo, maximo = esperado.get("min"), esperado.get("max")
            if minimo is not None and encontrado < minimo:
                return float(minimo - encontrado)
            if maximo is not None and encontrado > maximo:
                return float(encontrado - maximo)
    return None


class Companion:
    def __init__(
        self,
        help_after_tries: int = 4,
        help_after_seconds: float = 120.0,
        state: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.help_after_tries = help_after_tries
        self.help_after_seconds = help_after_seconds
        self.state: Dict[str, Any] = state if state is not None else {}

    def reset(self) -> None:
        self.state.clear()

    def _iniciar_paso(self, target_id: Optional[str], now: float, report: EvaluationReport) -> None:
        self.state["current"] = target_id
        self.state["since"] = now
        self.state["tries"] = 0
        self.state["best"] = distance(report.result(target_id)) if target_id else None

    def observe(self, practice: PracticeDefinition, report: EvaluationReport, now: float) -> List[Intervention]:
        s = self.state
        primera = "passed" not in s
        aprobados_antes = set(s.get("passed", []))
        aprobados = {r.target_id for r in report.results if r.passed is True}
        s["passed"] = sorted(aprobados)
        vistos = set(s.get("seen", []))
        ofrecidos = set(s.get("offered", []))
        salida: List[Intervention] = []

        def titulo(tid: Optional[str]) -> str:
            t = practice.target(tid) if tid else None
            return (t.title or t.id) if t else ""

        if not primera:
            for tid in sorted(aprobados - aprobados_antes, key=lambda x: [t.id for t in practice.targets].index(x)):
                t = practice.target(tid)
                texto = (t.messages.get("pass") if t else "") or report.result(tid).message
                salida.append(Intervention(PASO_LOGRADO, tid, f"¡Listo! {titulo(tid)}", texto))
            for tid in sorted(aprobados_antes - aprobados):
                r = report.result(tid)
                if r is not None:
                    salida.append(
                        Intervention(RETROCESO, tid, f"Ojo: «{titulo(tid)}» ya no se cumple", r.message)
                    )

        pausa_antes = s.get("paused")
        if report.paused_by != pausa_antes:
            s["paused"] = report.paused_by
            if report.paused_by:
                guard = practice.guard(report.paused_by)
                r = next((g for g in report.guards if g.target_id == report.paused_by), None)
                salida.append(Intervention(
                    PAUSA, report.paused_by, f"Progreso en pausa: {(guard.title if guard else '') or report.paused_by}",
                    (guard.messages.get("fail") if guard else "") or (r.message if r else ""),
                ))
            elif pausa_antes and not primera:
                salida.append(Intervention(REANUDA, pausa_antes, "¡Arreglado! Sigue tu práctica", ""))

        if report.completed and not s.get("done"):
            s["done"] = True
            if not primera:
                salida.append(
                    Intervention(PRACTICA_COMPLETA, None, "¡Práctica completada!",
                                 practice.completion or "Terminaste todos los pasos.")
                )
        elif not report.completed:
            s["done"] = False

        actual = report.current_target_id
        if actual != s.get("current"):
            self._iniciar_paso(actual, now, report)
            objetivo = practice.target(actual) if actual else None
            if objetivo is not None and actual not in vistos and not (report.completed and objetivo.optional):
                vistos.add(actual)
                porque = (objetivo.guide.why if objetivo.guide and objetivo.guide.why else objetivo.tip)
                salida.append(
                    Intervention(NUEVO_PASO, actual, f"Paso {report.step_number}: {titulo(actual)}",
                                 porque or report.result(actual).message)
                )
        elif actual is not None and not report.completed:
            s["tries"] = int(s.get("tries", 0)) + 1
            dist = distance(report.result(actual))
            mejor = s.get("best")
            if dist is not None and mejor is not None and dist < mejor * (1 - MEJORA_MINIMA):
                s["best"] = dist
                s["tries"] = 0
                salida.append(Intervention(MEJORANDO, actual, "¡Vas mejor!", report.result(actual).message))
            elif dist is not None and mejor is None:
                s["best"] = dist
            atascado = s["tries"] >= self.help_after_tries or (
                s["tries"] >= 1 and now - float(s.get("since", now)) >= self.help_after_seconds
            )
            if atascado and actual not in ofrecidos:
                ofrecidos.add(actual)
                salida.append(
                    Intervention(OFRECER_AYUDA, actual, "¿Te ayudo con este paso?",
                                 f"Llevas un rato en «{titulo(actual)}». Puedo mostrarte qué hacer, "
                                 f"darte una pista o dejarte intentarlo a tu manera.")
                )

        s["seen"] = sorted(vistos)
        s["offered"] = sorted(ofrecidos)
        return salida
