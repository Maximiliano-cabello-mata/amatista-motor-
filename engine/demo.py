"""Demostración del motor sin Blender: python engine/demo.py"""
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
REPO = ENGINE.parent
sys.path.insert(0, str(ENGINE))

from amatista_engine import create_default_engine  # noqa: E402
from amatista_engine.models import SceneObject, SceneState  # noqa: E402
from amatista_engine.practice import load_practice  # noqa: E402

practice = load_practice(REPO / "practices" / "archivo" / "v2" / "mesa.json")


def pata(nombre, x, y):
    return SceneObject(nombre, "MESH", roles=("pata",), location=(x, y, 0.375), dimensions=(0.1, 0.1, 0.75))


scene = SceneState(
    blender_version="5.1-demo",
    file_path="mesa.blend",
    file_saved=True,
    objects=(
        SceneObject("Cubierta", "MESH", roles=("cubierta",), location=(0, 0, 0.8), dimensions=(2.0, 1.0, 0.1)),
        pata("Pata01", -0.9, -0.4),
        pata("Pata02", 0.9, -0.4),
        pata("Pata03", -0.9, 0.4),
    ),
)

engine = create_default_engine()
report = engine.evaluate(practice, scene)

print(f"Práctica: {report.practice_title}")
print(f"Progreso: {report.progress}%")
print(f"Completada: {report.completed}")
print(f"Paso actual: {report.step_number} de {len(report.steps)}")
print()

ICONOS = {"completado": "✓", "actual": "▶", "pendiente": "·", "bloqueado": "🔒", "desconocido": "?"}
for paso in report.steps:
    print(f"{ICONOS[paso.status]} {paso.title}: {paso.message}")
