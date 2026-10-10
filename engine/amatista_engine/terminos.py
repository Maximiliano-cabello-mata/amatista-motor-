"""Términos de Blender que muestra el motor, en un solo lugar (motor 3.5).

Los validadores, las instrucciones del ejemplo (ejemplo/pasos.py), la
revisión contra el ejemplo y la guía usan estos nombres para que el alumno
lea siempre lo mismo que dicen las prácticas.
"""
from __future__ import annotations

# Nombre de cada modificador (los que usan las prácticas: «Array», «Bisel», «Subdivisión de superficie»…).
MODIFICADORES = {
    "MIRROR": "Espejo",
    "SUBSURF": "Subdivisión de superficie",
    "BEVEL": "Bisel",
    "SOLIDIFY": "Solidificar",
    "ARRAY": "Array",
    "BOOLEAN": "Booleano",
    "DECIMATE": "Diezmar",
    "WEIGHTED_NORMAL": "Normales ponderadas",
}


def nombre_modificador(tipo: str) -> str:
    tipo = str(tipo or "").upper()
    return MODIFICADORES.get(tipo, tipo.capitalize())
