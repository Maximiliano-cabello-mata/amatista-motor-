"""Herramientas de autor de prácticas (motor v3). Ayuda: python engine/herramientas/practicas.py -h

    nueva        crea una práctica desde una plantilla (ensamblar, modelado, modificadores…)
    revisar      compila y revisa la pedagogía (píldoras, pistas, vigilantes)
    probar       corre los casos de pruebas.json de cada práctica
    simular      muestra paso a paso qué vería el alumno con cada escena
    validadores  catálogo de validadores (o --md para regenerar la referencia)
    plan         mapa del plan de estudios (practices/blender/cursos.json)

Documentación: docs/motor/referencia/08_practicas_v3_y_herramientas.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from amatista_engine.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
