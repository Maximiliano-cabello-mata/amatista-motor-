"""Fábricas del motor listo para usar: registro de validadores incluidos + motor con herramientas por defecto."""
from .engine import AmatistaEngine
from .registry import ValidatorRegistry
from .tools.registry import ToolRegistry
from .validators.builtin import register_builtin_validators


def create_default_registry() -> ValidatorRegistry:
    """Registro de validadores con todos los incluidos (validators.builtin)."""
    registry = ValidatorRegistry()
    register_builtin_validators(registry)
    return registry


def create_default_engine() -> AmatistaEngine:
    """AmatistaEngine con el registro por defecto y ToolRegistry.default()."""
    return AmatistaEngine(create_default_registry(), ToolRegistry.default())
