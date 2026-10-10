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

    def _validar(self, target, scene: SceneState, practice: Optional[PracticeDefinition] = None) -> ValidationResult:
        if practice is not None:
            # Motor 4: medidas amables; la forma tiene que tener sentido, los decimales no estorban.
            from .ruta.medidas import ajustar

            target = ajustar(target, practice.level)
        resultado = self._validar_crudo(target, scene)
        if practice is None or not practice.roles:
            return resultado
        # Motor v3: los mensajes nombran el rol como lo ve el alumno («Vagón», no «vagon»).
        mensaje = resultado.message
        for rol in practice.roles:
            if (target.params or {}).get("role") != rol.id and rol.id not in str((target.params or {}).get("reference_role", "")):
                continue
            if rol.label and rol.label != rol.id:
                mensaje = mensaje.replace(f"«{rol.id}»", f"«{rol.label}»")
        if mensaje == resultado.message:
            return resultado
        return ValidationResult(resultado.target_id, resultado.validator, resultado.passed, mensaje, resultado.details)

    def _validar_crudo(self, target, scene: SceneState) -> ValidationResult:
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

    def infer_roles(self, practice: PracticeDefinition, scene: SceneState):
        """Motor 3.4: roles deducidos por la forma para las mallas sin rol ({objeto: rol})."""
        referencia = practice.reference
        if not practice.infers_roles:
            return {}
        from .figures import inferir_roles
        from .practice.loader import pieza_como_dict

        partes = [pieza_como_dict(p) for p in referencia.compared if p.role]
        return inferir_roles(partes, scene.objects) if partes else {}

    def evaluate(self, practice: PracticeDefinition, scene: SceneState) -> EvaluationReport:
        # Motor 3.4: el alumno ya no tiene que poner roles; el motor reconoce cada pieza por su forma.
        deducidos = self.infer_roles(practice, scene)
        if deducidos:
            from .figures import con_roles

            scene = con_roles(scene, deducidos)
        results = tuple(self._validar(target, scene, practice) for target in practice.targets)
        by_id = {result.target_id: result for result in results}
        progress = calculate_progress(practice.targets, by_id)
        obligatorios = [t for t in practice.targets if not t.optional]
        completed = bool(obligatorios) and all(by_id[t.id].passed is True for t in obligatorios)
        pasos, actual = statuses(practice.targets, by_id)

        usados = self.tools.detect_used(scene) if self.tools else ()
        avisos = self.tools.warnings(practice, usados) if self.tools else ()

        # Motor v3: un vigilante que falla pausa el progreso (no se completa la
        # práctica hasta arreglarlo) y la guía muestra su arreglo.
        vigilancia = tuple(self._validar(guard, scene, practice) for guard in practice.guards)
        pausa = next((r.target_id for r in vigilancia if r.passed is False), None)
        if pausa is not None:
            completed = False

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
            needs_update=any(r.details.get("reason") == "unknown_validator" for r in results + vigilancia),
            guards=vigilancia,
            paused_by=pausa,
            inferred_roles=tuple(sorted(deducidos.items())),
        )

    def guide(self, practice: PracticeDefinition, scene: SceneState, report: Optional[EvaluationReport] = None):
        """Guía del paso actual (etapa 2): qué hacer, con qué teclas y qué mirar."""
        from .guide import build_guidance

        return build_guidance(practice, scene, report or self.evaluate(practice, scene))

    def route(self, practice: PracticeDefinition, report: EvaluationReport, guidance=None, hints=None,
              previous: Optional[str] = None):
        """Motor 4: la ruta del alumno (misiones en fila, la actual explicada y sus herramientas)."""
        from .ruta import construir_ruta

        return construir_ruta(practice, report, guidance, self.tools, hints, previous)

    def pills(self, practice: PracticeDefinition, scene: SceneState, report: EvaluationReport, seen=()):
        """Píldoras de teoría que tocan ahora (motor v3)."""
        from .pedagogy.pills import pills_for

        usados = report.tools_used
        return pills_for(practice, scene, report, seen=seen, tools_used=usados)

    def evaluate_target(self, practice: PracticeDefinition, scene: SceneState, target_id: str) -> ValidationResult:
        """Solo un objetivo (el depurador del modo desarrollador)."""
        target = practice.target(target_id) or practice.guard(target_id)
        if target is None:
            raise KeyError(target_id)
        return self._validar(target, scene, practice)

    def targets_for_event(self, practice: PracticeDefinition, event: str):
        """Objetivos que un evento invalida (sección 16: no reevaluar todo)."""
        afectados = []
        for target in practice.targets:
            spec = self.registry.spec(target.validator)
            if spec is None or event in spec.watch:
                afectados.append(target.id)
        return tuple(afectados)
