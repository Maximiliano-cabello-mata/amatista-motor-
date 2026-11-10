"""El alumno no debe sentir que retrocede: progreso, pasos, reconocimiento de piezas y mensajes.

Casos del tren reproducidos el 10 de noviembre de 2026 (docs/auditoria-practicas.md).
"""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "engine" / "herramientas"))

import amatista_engine  # noqa: E402
import auditar  # noqa: E402
from amatista_engine.models import TargetDefinition, ValidationResult  # noqa: E402
from amatista_engine.pedagogy.progress import avance_parcial, calculate_progress, desbloqueados  # noqa: E402
from amatista_engine.practice import parse_practice  # noqa: E402
from amatista_engine.testing import Escena  # noqa: E402

TREN = RAIZ / "practices" / "blender" / "principiante" / "m1-tren"
RUEDAS = [(0.65, 0.7), (1.85, 0.7), (0.65, -0.7), (1.85, -0.7), (-1.65, 0.7), (-0.65, 0.7), (-1.65, -0.7), (-0.65, -0.7)]


@pytest.fixture(scope="module")
def motor():
    return amatista_engine.create_default_engine()


@pytest.fixture(scope="module")
def tren():
    return parse_practice(json.loads((TREN / "practica.json").read_text(encoding="utf-8")))


def vagones() -> Escena:
    e = Escena()
    e.cubo("Cube", dims=[2.2, 1.2, 1.1], loc=[1.25, 0, 0.9])
    e.cubo("Cube.001", dims=[2.0, 1.2, 1.0], loc=[-1.15, 0, 0.85])
    return e


def rueda(e: Escena, i: int, grosor: float = 0.2, **kw) -> Escena:
    x, y = RUEDAS[i]
    opciones = {"dims": [0.7, 0.7, grosor], "loc": [x, y, 0.35], "rot": [90, 0, 0]}
    opciones.update(kw)
    return e.cilindro(f"Cylinder.{i:03d}", **opciones)


def test_el_progreso_sube_con_cada_rueda(motor, tren):
    e = vagones()
    anterior = motor.evaluate(tren, e.construir()).progress
    for i in range(8):
        rueda(e, i)
        actual = motor.evaluate(tren, e.construir()).progress
        assert actual > anterior, f"la rueda {i + 1} no movió el progreso ({anterior} → {actual})"
        anterior = actual


def test_la_octava_rueda_acostada_no_hace_retroceder(motor, tren):
    e = vagones()
    for i in range(7):
        rueda(e, i)
    antes = motor.evaluate(tren, e.construir())
    # La octava recién aplanada: todavía acostada y lejos del tren.
    e.cilindro("Cylinder.007", dims=[0.7, 0.7, 0.2], loc=[0, 3, 0.1])
    despues = motor.evaluate(tren, e.construir())
    assert despues.progress >= antes.progress
    assert despues.current_target_id == "ruedas-de-pie"
    hechos = lambda r: {p.target_id for p in r.steps if p.status == "completado"}  # noqa: E731
    assert hechos(antes) <= hechos(despues), "se desmarcó un paso que ya estaba hecho"


def test_un_paso_no_se_marca_hecho_antes_que_su_requisito(motor, tren):
    e = vagones()
    rueda(e, 0)
    reporte = motor.evaluate(tren, e.construir())
    estados = {p.target_id: p.status for p in reporte.steps}
    assert reporte.result("ruedas-de-pie").passed is True  # se cumple en vacío con una rueda
    assert estados["ruedas-de-pie"] == "bloqueado"  # pero no se muestra hecho: faltan ruedas
    assert estados["ruedas"] == "actual"


def test_una_rueda_gruesa_sigue_siendo_rueda(motor, tren):
    e = vagones()
    for i in range(8):
        rueda(e, i, grosor=0.45)
    roles = dict(motor.evaluate(tren, e.construir()).inferred_roles)
    assert [roles.get(f"Cylinder.{i:03d}") for i in range(8)] == ["rueda"] * 8


def test_la_chimenea_sigue_siendo_chimenea(motor, tren):
    e = vagones()
    e.cilindro("Cylinder", dims=[0.4, 0.4, 0.7], loc=[1.9, 0, 1.8])
    assert dict(motor.evaluate(tren, e.construir()).inferred_roles)["Cylinder"] == "chimenea"


def test_el_mensaje_de_forma_trae_medidas(motor, tren):
    e = vagones()
    for i in range(8):
        rueda(e, i, grosor=0.45)
    gruesa = motor.evaluate(tren, e.construir()).result("ruedas-de-pie")
    assert gruesa.passed is False
    assert "grues" in gruesa.message and "0.45 m" in gruesa.message and "0.7 m" in gruesa.message

    e = vagones()
    for i in range(8):
        rueda(e, i, rot=[0, 0, 0], loc=[RUEDAS[i][0], RUEDAS[i][1], 0.1])
    acostada = motor.evaluate(tren, e.construir()).result("ruedas-de-pie")
    assert acostada.passed is False
    assert "acostado" in acostada.message and "Z (0.2 m)" in acostada.message and "R" in acostada.message


def test_vagones_hundidos_no_se_culpa_a_las_ruedas(motor, tren):
    # Siguiendo las pistas al pie de la letra: cubos en el origen (medio hundidos) y ruedas en el suelo.
    e = Escena()
    e.cubo("Cube", dims=[3.2, 2, 2], loc=[0, 0, 0])
    e.cubo("Cube.001", dims=[3.2, 2, 2], loc=[3.4, 0, 0])
    for i, (x, y) in enumerate([(-1, 1.2), (1, 1.2), (-1, -1.2), (1, -1.2), (2.4, 1.2), (4.4, 1.2), (2.4, -1.2), (4.4, -1.2)]):
        e.cilindro(f"Cylinder.{i:03d}", dims=[2, 2, 0.4], loc=[x, y, 1.0], rot=[90, 0, 0])
    e.cilindro("Chim", dims=[0.6, 0.6, 1.2], loc=[4.2, 0, 1.6])
    figura = motor.evaluate(tren, e.construir()).result("figura")
    assert figura.passed is False
    assert "Vagón" in figura.message and "más abajo" in figura.message
    assert "Cylinder" not in figura.message


def _objetivo(tid, requires=(), weight=10.0):
    return TargetDefinition(id=tid, validator="x", params={}, weight=weight, requires=tuple(requires))


def _resultado(tid, passed, **detalles):
    return ValidationResult(target_id=tid, validator="x", passed=passed, message="", details=detalles)


def test_un_objetivo_no_suma_si_su_requisito_no_esta_cumplido():
    objetivos = (_objetivo("a"), _objetivo("b", ["a"]), _objetivo("c", ["b"]))
    resultados = {"a": _resultado("a", False), "b": _resultado("b", True), "c": _resultado("c", True)}
    assert desbloqueados(objetivos, resultados) == {"a"}
    assert calculate_progress(objetivos, resultados) == 0.0
    resultados["a"] = _resultado("a", True)
    assert calculate_progress(objetivos, resultados) == 100.0


def test_avance_parcial_solo_en_conteos_incompletos():
    assert avance_parcial(_resultado("a", False, found=4, expected={"min": 8, "max": None})) == 0.5
    assert avance_parcial(_resultado("a", False, found=3, expected=4)) == 0.75
    assert avance_parcial(_resultado("a", False, found=9, expected={"min": 8, "max": 8})) == 0.0  # de más
    assert avance_parcial(_resultado("a", False)) == 0.0
    assert avance_parcial(_resultado("a", True, found=8, expected={"min": 8})) == 0.0  # ya pasó: suma entero


# Tropiezos que la auditoría encuentra y todavía no se corrigen. Cada uno con su motivo:
# si aparece uno nuevo, la prueba falla; si uno de estos desaparece, también (hay que quitarlo).
CONOCIDOS = {
    # La espada es una sola malla. Al sacar la guarda (ancha) antes que la hoja, deja
    # de ser «más larga que ancha» y el paso «alargar» se desmarca. Es del diseño de
    # la práctica, no del motor: se decide con quien escribe las prácticas.
    ("blender.bp.m2.espada", "retroceso"),
}


def test_auditoria_de_todas_las_practicas(motor):
    encontrados = set()
    detalle = []
    for carpeta in auditar.carpetas(()):
        informe = auditar.auditar(carpeta, motor)
        for h in informe["hallazgos"]:
            encontrados.add((informe["practica"], h["comprobacion"]))
            detalle.append(f"{informe['practica']} [{h['comprobacion']}] {h['cuando']}: {h['dato']}")
    assert encontrados - CONOCIDOS == set(), "tropiezos nuevos:\n" + "\n".join(detalle)
    assert CONOCIDOS - encontrados == set(), "ya no ocurren (quítalos de CONOCIDOS): " + str(CONOCIDOS - encontrados)
