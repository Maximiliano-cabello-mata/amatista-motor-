"""Amatista Engine: motor educativo declarativo para Blender.

El motor se programa; las prácticas se describen. Este paquete no importa
bpy (salvo amatista_engine.blender): corre igual en Blender, en pytest y en
el servidor FastAPI. Documentación: docs/motor/.
"""

from .bootstrap import create_default_engine, create_default_registry
from .engine import AmatistaEngine

__all__ = ["AmatistaEngine", "create_default_engine", "create_default_registry"]
__version__ = "0.2.0"
