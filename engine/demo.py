"""Demostración del motor sin Blender: python engine/demo.py"""
import sys
from dataclasses import replace
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
REPO = ENGINE.parent
sys.path.insert(0, str(ENGINE))

from amatista_engine import create_default_engine  # noqa: E402
from amatista_engine.ejemplo import escena_esperada  # noqa: E402
from amatista_engine.practice import load_practice  # noqa: E402
from amatista_engine.practice.loader import pieza_como_dict  # noqa: E402

# Práctica vigente: el tren de juguete (Principiante, módulo 1).
practice = load_practice(REPO / "practices" / "blender" / "principiante" / "m1-tren" / "practica.json")

# La escena que deja su ejemplo resuelto, sin el último objeto: un alumno a mitad de camino.
partes = [pieza_como_dict(p) for p in practice.reference.compared] if practice.reference else []
completa = escena_esperada(practice.example.steps, partes)
scene = replace(completa, objects=completa.objects[:-1])

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
