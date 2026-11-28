"""Registro de validadores: las capacidades reutilizables del motor.

Cada validador se registra una sola vez con su función y una descripción
(ValidatorSpec) que usan el compilador (¿existe? ¿qué parámetros pide?), el
constructor de objetivos del modo desarrollador (plantillas con etiquetas en
español) y el observador de eventos (qué cambios lo invalidan).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from .models import SceneState, TargetDefinition, ValidationResult

ValidatorFunction = Callable[[TargetDefinition, SceneState], ValidationResult]

# Eventos que puede observar el add-on (blender/events en el add-on).
EVENTOS = ("OBJECT_ADDED", "OBJECT_TRANSFORM", "OBJECT_MODIFIER", "OBJECT_DATA", "FILE_SAVED", "ROLE_CHANGED")


@dataclass(frozen=True)
class ParamSpec:
    """Un parámetro de un validador.

    kind: role, text, int, float, axis, modifier, object_type, collection.
    """

    name: str
    kind: str
    label: str
    required: bool = False
    default: Any = None


@dataclass(frozen=True)
class ValidatorSpec:
    """Ficha de un validador registrado: función, textos para el autor, categoría, parámetros y eventos que lo disparan.

    ``watch`` son los eventos de Blender que obligan a reevaluarlo y ``selects``
    indica si el validador elige objetos (lo usa la ayuda para resaltarlos).
    """
    id: str
    function: ValidatorFunction
    label: str = ""
    description: str = ""
    category: str = "general"
    params: Tuple[ParamSpec, ...] = ()
    watch: Tuple[str, ...] = EVENTOS
    # Selectores de objetos aceptados (role, name, name_prefix, type, tag).
    selects: bool = False

    def param(self, name: str) -> Optional[ParamSpec]:
        """Ficha del parámetro con ese nombre, o None si el validador no lo declara."""
        return next((p for p in self.params if p.name == name), None)


@dataclass
class ValidatorRegistry:
    """Registro de capacidades reutilizables del motor."""

    _specs: Dict[str, ValidatorSpec] = field(default_factory=dict)

    def register(
        self,
        validator_id: str,
        function: ValidatorFunction,
        *,
        label: str = "",
        description: str = "",
        category: str = "general",
        params: Iterable[ParamSpec] = (),
        watch: Iterable[str] = EVENTOS,
        selects: bool = False,
    ) -> None:
        """Registra un validador nuevo bajo ``validator_id`` con su ficha descriptiva.

        Raises:
            ValueError: si el id está vacío o ya estaba registrado.
        """
        if not validator_id:
            raise ValueError("validator_id no puede estar vacío")
        if validator_id in self._specs:
            raise ValueError(f"Validador duplicado: {validator_id}")
        self._specs[validator_id] = ValidatorSpec(
            id=validator_id,
            function=function,
            label=label or validator_id,
            description=description,
            category=category,
            params=tuple(params),
            watch=tuple(watch),
            selects=selects,
        )

    def get(self, validator_id: str) -> Optional[ValidatorFunction]:
        """Función del validador con ese id, o None si no está registrado."""
        spec = self._specs.get(validator_id)
        return spec.function if spec else None

    def spec(self, validator_id: str) -> Optional[ValidatorSpec]:
        """Ficha completa (ValidatorSpec) del validador, o None si no existe."""
        return self._specs.get(validator_id)

    def specs(self) -> Tuple[ValidatorSpec, ...]:
        """Todas las fichas registradas, ordenadas por id (las usa el catálogo para autores y la API)."""
        return tuple(self._specs[i] for i in sorted(self._specs))

    def ids(self) -> Iterable[str]:
        """Ids de todos los validadores registrados, en orden alfabético."""
        return tuple(sorted(self._specs))

    def __contains__(self, validator_id: str) -> bool:
        """Permite ``"mesh.vertices" in registro`` para saber si un validador existe."""
        return validator_id in self._specs
