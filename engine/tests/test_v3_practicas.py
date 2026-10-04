"""Plan de estudios v3: las 6 prácticas compilan, sus casos de prueba pasan y cursos.json cuadra."""
import json
from pathlib import Path

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import CURSOS, PRACTICAS, comprobar_caso, revisar_plan
from amatista_engine.curriculum import load_curriculum
from amatista_engine.practice import compile_practice

CARPETAS = sorted(p.parent for p in PRACTICAS.rglob("practica.json"))


def _leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def test_hay_seis_practicas_del_plan():
    assert len(CARPETAS) == 6
    ids = {_leer(c / "practica.json")["id"] for c in CARPETAS}
    assert ids == set(load_curriculum(_leer(CURSOS)).practices())


@pytest.mark.parametrize("carpeta", CARPETAS, ids=lambda c: c.name)
def test_practica_compila_sin_errores_ni_avisos(carpeta):
    motor = create_default_engine()
    resultado = compile_practice(_leer(carpeta / "practica.json"), motor.registry, motor.tools)
    assert resultado.ok, resultado.errors
    assert not resultado.warnings, resultado.warnings
    assert resultado.practice.pills, "cada práctica del plan trae su teoría en píldoras"


@pytest.mark.parametrize("carpeta", CARPETAS, ids=lambda c: c.name)
def test_casos_de_prueba(carpeta):
    motor = create_default_engine()
    practica = compile_practice(_leer(carpeta / "practica.json"), motor.registry, motor.tools).practice
    casos = _leer(carpeta / "pruebas.json")["casos"]
    assert any(c.get("espera", {}).get("completada") for c in casos), "falta el caso con la solución"
    for caso in casos:
        assert comprobar_caso(motor, practica, caso) == [], caso["nombre"]


def test_cursos_json_coincide_con_las_practicas():
    plan = load_curriculum(_leer(CURSOS))
    assert revisar_plan(plan) == []
    assert [c.difficulty for c in plan.courses] == ["principiante", "principiante_intermedio", "intermedio", "avanzado"]
    assert [c.status for c in plan.courses[2:]] == ["proximamente", "proximamente"]


def test_repasos_apuntan_a_pildoras_con_pregunta_de_practicas_anteriores():
    motor = create_default_engine()
    practicas = {}
    for c in CARPETAS:
        p = compile_practice(_leer(c / "practica.json"), motor.registry, motor.tools).practice
        practicas[p.id] = p
    orden = list(load_curriculum(_leer(CURSOS)).practices())
    for pid, p in practicas.items():
        for ref in p.review:
            origen, _, pildora = ref.partition("#")
            assert orden.index(origen) < orden.index(pid), ref
            assert practicas[origen].pill(pildora) is not None, ref
