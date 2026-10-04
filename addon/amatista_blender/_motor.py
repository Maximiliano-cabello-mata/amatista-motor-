"""Acceso a Amatista Engine desde el add-on.

En el paquete instalado el motor viaja dentro del add-on
(amatista_blender/amatista_engine, lo copia herramientas/construir.py). Al
trabajar desde el repositorio se usa engine/ directamente.
"""
import sys
from pathlib import Path

try:
    from . import amatista_engine as engine  # paquete construido
except ImportError:  # desarrollo: <repo>/addon/amatista_blender → <repo>/engine
    _ENGINE = Path(__file__).resolve().parents[2] / "engine"
    if str(_ENGINE) not in sys.path:
        sys.path.insert(0, str(_ENGINE))
    import amatista_engine as engine  # noqa: F401

from importlib import import_module

adapter = import_module(engine.__name__ + ".blender.adapter")
tagger = import_module(engine.__name__ + ".blender.tagger")
modelos = import_module(engine.__name__ + ".models")
practica = import_module(engine.__name__ + ".practice")
pedagogia = import_module(engine.__name__ + ".pedagogy")
foto = import_module(engine.__name__ + ".snapshot")
herramientas = import_module(engine.__name__ + ".tools")
guia = import_module(engine.__name__ + ".guide")

MOTOR = engine.create_default_engine()
VERSION_MOTOR = engine.__version__
