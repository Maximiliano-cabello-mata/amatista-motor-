"""Núcleo del motor: evalúa una práctica contra una escena.

No conoce Blender, interfaz, API, usuarios ni base de datos. Los tres modos
(Author, Preview y Student) llaman a este mismo evaluate(): lo único que
cambia es cuánto detalle muestra la interfaz.
"""
from __future__ import annotations

from typing import Optional

from .models import EvaluationReport, PracticeDefinition, SceneState, ValidationResult
from .pedagogy.graph import statuses
from .pedagogy.progress import calculate_progress
from .registry import ValidatorRegistry
from .tools.registry import ToolRegistry


class AmatistaEngine:
    """Núcleo del motor.

    No conoce Blender, interfaz, API, usuarios ni base de datos.
    """

    def __init__(self, registry: ValidatorRegistry, tools: Optional[ToolRegistry] = None) -> None:
        self.registry = registry
        self.tools = tools

    def _validar(self, target, scene: SceneState) -> ValidationResult:
        validator = self.registry.get(target.validator)
        if validator is None:
            return ValidationResult(
                target_id=target.id,
                validator=target.validator,
                passed=None,
                message="Esta práctica necesita una versión más reciente de Amatista Engine.",
                details={"reason": "unknown_validator"},
            )
        try:
            result = validator(target, scene)
        except Exception as exc:  # una práctica mal escrita nunca rompe Blender
            return ValidationResult(
                target_id=target.id,
                validator=target.validator,
                passed=None,
                message=f"Error interno del validador: {exc}",
                details={"reason": "validator_error"},
            )
        # Mensaje personalizado del autor (sección 15): gana sobre el generado.
        propio = target.messages.get("pass" if result.passed else "fail")
        if propio:
            result = ValidationResult(
                target_id=result.target_id,
                validator=result.validator,
                passed=result.passed,
                message=propio,
                details={**result.details, "generated_message": result.message},
            )
        return result

    def evaluate(self, practice: PracticeDefinition, scene: SceneState) -> EvaluationReport:
        results = tuple(self._validar(target, scene) for target in practice.targets)
        by_id = {result.target_id: result for result in results}
        progress = calculate_progress(practice.targets, by_id)
        obligatorios = [t for t in practice.targets if not t.optional]
        completed = bool(obligatorios) and all(by_id[t.id].passed is True for t in obligatorios)
        pasos, actual = statuses(practice.targets, by_id)

        usados = self.tools.detect_used(scene) if self.tools else ()
        avisos = self.tools.warnings(practice, usados) if self.tools else ()

        return EvaluationReport(
            practice_id=practice.id,
            practice_title=practice.title,
            progress=progress,
            completed=completed,
            results=results,
            steps=pasos,
            current_target_id=actual,
            tool_warnings=avisos,
            tools_used=usados,
            needs_update=any(r.details.get("reason") == "unknown_validator" for r in results),
        )

    def guide(self, practice: PracticeDefinition, scene: SceneState, report: Optional[EvaluationReport] = None):
        """Guía del paso actual (etapa 2): qué hacer, con qué teclas y qué mirar."""
        from .guide import build_guidance

        return build_guidance(practice, scene, report or self.evaluate(practice, scene))

    def evaluate_target(self, practice: PracticeDefinition, scene: SceneState, target_id: str) -> ValidationResult:
        """Solo un objetivo (el depurador del modo desarrollador)."""
        target = practice.target(target_id)
        if target is None:
            raise KeyError(target_id)
        return self._validar(target, scene)

    def targets_for_event(self, practice: PracticeDefinition, event: str):
        """Objetivos que un evento invalida (sección 16: no reevaluar todo)."""
        afectados = []
        for target in practice.targets:
            spec = self.registry.spec(target.validator)
            if spec is None or event in spec.watch:
                afectados.append(target.id)
        return tuple(afectados)
