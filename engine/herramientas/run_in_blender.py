"""Prueba manual dentro de Blender.

1. Ajusta PROJECT_ROOT.
2. Abre este archivo desde Blender > Scripting.
3. Ejecuta Run Script.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\ruta\a\amatista_engine_starter")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from amatista_engine import create_default_engine
from amatista_engine.blender.adapter import capture_scene
from amatista_engine.practice import load_practice

practice = load_practice(
    PROJECT_ROOT / "practices" / "sandbox" / "table.json"
)

scene = capture_scene()

engine = create_default_engine()
report = engine.evaluate(practice, scene)

print("=" * 60)
print("AMATISTA ENGINE")
print(f"Blender: {scene.blender_version}")
print(f"Práctica: {report.practice_title}")
print(f"Progreso: {report.progress}%")
print(f"Completada: {report.completed}")
print("-" * 60)

for result in report.results:
    icon = "OK" if result.passed else "FAIL" if result.passed is False else "?"
    print(f"[{icon}] {result.target_id}: {result.message}")

print("=" * 60)
