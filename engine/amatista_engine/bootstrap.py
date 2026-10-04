from .engine import AmatistaEngine
from .registry import ValidatorRegistry
from .tools.registry import ToolRegistry
from .validators.builtin import register_builtin_validators


def create_default_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    register_builtin_validators(registry)
    return registry


def create_default_engine() -> AmatistaEngine:
    return AmatistaEngine(create_default_registry(), ToolRegistry.default())
