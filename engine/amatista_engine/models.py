"""Datos del motor: escena normalizada, práctica, resultados y reporte.

Todo son dataclasses inmutables de Python puro (sin bpy): el mismo código
corre dentro de Blender, en las pruebas y en el servidor FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

Vector = Tuple[float, float, float]


@dataclass(frozen=True)
class SceneObject:
    """Un objeto de la escena tal como lo entiende Amatista.

    bbox_min y bbox_max son la caja envolvente en coordenadas del mundo. Si
    no se capturaron (pruebas, versiones viejas del add-on) se calculan con
    location ± dimensions / 2, que vale para primitivas con el origen al centro.
    """

    name: str
    object_type: str
    roles: Tuple[str, ...] = ()
    location: Vector = (0.0, 0.0, 0.0)
    rotation: Vector = (0.0, 0.0, 0.0)  # radianes (Euler XYZ)
    scale: Vector = (1.0, 1.0, 1.0)
    dimensions: Vector = (0.0, 0.0, 0.0)
    modifiers: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()
    materials: Tuple[str, ...] = ()
    collections: Tuple[str, ...] = ()
    vertices: Optional[int] = None
    faces: Optional[int] = None
    bbox_min: Optional[Vector] = None
    bbox_max: Optional[Vector] = None
    parent: Optional[str] = None

    @property
    def role(self) -> Optional[str]:
        return self.roles[0] if self.roles else None

    def caja(self) -> Tuple[Vector, Vector]:
        """(mínimo, máximo) de la caja envolvente en el mundo."""
        if self.bbox_min is not None and self.bbox_max is not None:
            return self.bbox_min, self.bbox_max
        medio = tuple(d / 2.0 for d in self.dimensions)
        return (
            tuple(c - m for c, m in zip(self.location, medio)),
            tuple(c + m for c, m in zip(self.location, medio)),
        )


@dataclass(frozen=True)
class SceneState:
    blender_version: str
    file_path: str
    file_saved: bool
    objects: Tuple[SceneObject, ...] = ()
    mode: str = "OBJECT"

    def objects_with_role(self, role: str) -> Tuple[SceneObject, ...]:
        return tuple(obj for obj in self.objects if role in obj.roles)

    def object_by_name(self, name: str) -> Optional[SceneObject]:
        return next((obj for obj in self.objects if obj.name == name), None)

    @property
    def file_name(self) -> str:
        return self.file_path.replace("\\", "/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Hint:
    level: int
    text: str


@dataclass(frozen=True)
class GuideStepDefinition:
    """Micro paso escrito por el autor: texto y teclas («S», «Z», «0.1»)."""

    text: str
    keys: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetGuide:
    """Bloque opcional «guide» de un objetivo (etapa 2 del motor).

    why: por qué importa el paso (lo muestra la tarjeta guía).
    steps: micro pasos; si faltan, el motor los genera según el validador.
    """

    why: str = ""
    steps: Tuple[GuideStepDefinition, ...] = ()


@dataclass(frozen=True)
class TargetDefinition:
    id: str
    validator: str
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    title: str = ""
    requires: Tuple[str, ...] = ()
    tip: str = ""
    hints: Tuple[Hint, ...] = ()
    messages: Dict[str, str] = field(default_factory=dict)
    optional: bool = False
    guide: Optional[TargetGuide] = None


@dataclass(frozen=True)
class RoleDefinition:
    id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class PracticeDefinition:
    schema: str
    id: str
    title: str
    level: int
    targets: Tuple[TargetDefinition, ...]
    version: int = 1
    description: str = ""
    intro: str = ""
    completion: str = ""
    estimated_minutes: Optional[int] = None
    blender_min: Optional[str] = None
    skills: Tuple[str, ...] = ()
    roles: Tuple[RoleDefinition, ...] = ()
    tags: Tuple[str, ...] = ()
    allowed_tools: Tuple[str, ...] = ()
    warn_tools: Tuple[str, ...] = ()

    def target(self, target_id: str) -> Optional[TargetDefinition]:
        return next((t for t in self.targets if t.id == target_id), None)

    def role_label(self, role_id: str) -> str:
        rol = next((r for r in self.roles if r.id == role_id), None)
        return rol.label if rol else role_id


@dataclass(frozen=True)
class ValidationResult:
    target_id: str
    validator: str
    passed: Optional[bool]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# Estado de cada objetivo en el recorrido del alumno (pedagogy/graph.py).
COMPLETADO = "completado"
ACTUAL = "actual"
PENDIENTE = "pendiente"
BLOQUEADO = "bloqueado"
DESCONOCIDO = "desconocido"


@dataclass(frozen=True)
class TargetStatus:
    target_id: str
    title: str
    status: str
    passed: Optional[bool]
    message: str
    weight: float
    optional: bool = False
    hints_available: int = 0


@dataclass(frozen=True)
class ToolWarning:
    tool_id: str
    tool_name: str
    level: int
    message: str


@dataclass(frozen=True)
class EvaluationReport:
    practice_id: str
    practice_title: str
    progress: float
    completed: bool
    results: Tuple[ValidationResult, ...]
    steps: Tuple[TargetStatus, ...] = ()
    current_target_id: Optional[str] = None
    tool_warnings: Tuple[ToolWarning, ...] = ()
    tools_used: Tuple[str, ...] = ()
    needs_update: bool = False

    def result(self, target_id: str) -> Optional[ValidationResult]:
        return next((r for r in self.results if r.target_id == target_id), None)

    @property
    def step_number(self) -> int:
        """Número (1..n) del objetivo actual; n+1 si ya no queda ninguno."""
        for indice, paso in enumerate(self.steps, start=1):
            if paso.target_id == self.current_target_id:
                return indice
        return len(self.steps) + 1 if self.steps else 0
