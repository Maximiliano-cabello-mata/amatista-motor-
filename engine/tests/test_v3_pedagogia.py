"""Píldoras, repaso espaciado, plan de estudios y vigilantes (motor v3)."""
from amatista_engine import create_default_engine
from amatista_engine.curriculum import (BLOQUEADO, COMPLETADO, DISPONIBLE, PROXIMAMENTE, load_curriculum,
                                        next_practice, unlock_state)
from amatista_engine.guide import build_guidance
from amatista_engine.pedagogy import spaced
from amatista_engine.practice import compile_practice
from amatista_engine.testing import Escena

DIA = spaced.DIA


def _practica(**extra):
    datos = {
        "schema": "amatista.practice/2", "id": "prueba.v3", "version": 1, "title": "Prueba", "level": 2,
        "course": {"id": "blender_principiante", "module": 1}, "estimatedMinutes": 10,
        "roles": {"modelo": {"label": "Modelo"}},
        "pills": [
            {"id": "inicio", "title": "Inicio", "text": "Al empezar.", "trigger": {"on": "start"}},
            {"id": "edicion", "title": "Edición", "text": "En edición.", "trigger": {"on": "mode", "mode": "EDIT"}},
            {"id": "limpia", "title": "Limpia", "text": "Vigilante.", "trigger": {"on": "guard", "target": "limpia"},
             "once": False},
        ],
        "targets": [
            {"id": "modelo", "title": "Modelo", "validator": "role.count", "params": {"role": "modelo", "equals": 1},
             "weight": 50},
            {"id": "caras", "title": "Caras", "validator": "mesh.face_count", "params": {"role": "modelo", "min": 10},
             "weight": 50, "requires": ["modelo"]},
        ],
        "guards": [{"id": "limpia", "title": "Limpia", "validator": "mesh.no_duplicates", "params": {},
                    "fix": {"action": "merge_by_distance", "label": "Fusionar"}}],
    }
    datos.update(extra)
    motor = create_default_engine()
    resultado = compile_practice(datos, motor.registry, motor.tools)
    assert resultado.ok, resultado.errors
    return motor, resultado.practice


def test_pildoras_por_disparo_y_prioridad():
    motor, p = _practica()
    escena = Escena().cubo("M", rol="modelo").modo("EDIT_MESH").construir()
    ids = [x.id for x in motor.pills(p, escena, motor.evaluate(p, escena))]
    assert ids == ["edicion", "inicio"]
    vistas = [x.id for x in motor.pills(p, escena, motor.evaluate(p, escena), seen=["inicio"])]
    assert vistas == ["edicion"]


def test_vigilante_pausa_el_progreso_y_ofrece_arreglo():
    motor, p = _practica()
    escena = Escena().cubo("M", rol="modelo", caras=20, encimados=3).construir()
    reporte = motor.evaluate(p, escena)
    assert reporte.paused and reporte.paused_by == "limpia" and not reporte.completed
    guia = build_guidance(p, escena, reporte)
    assert guia.paused and guia.action.kind == "merge_by_distance"
    assert [x.id for x in motor.pills(p, escena, reporte)][0] == "limpia"
    limpia = Escena().cubo("M", rol="modelo", caras=20).construir()
    assert motor.evaluate(p, limpia).completed


def test_mensajes_usan_la_etiqueta_del_rol():
    motor, p = _practica()
    reporte = motor.evaluate(p, Escena().construir())
    assert "«Modelo»" in reporte.results[0].message


def test_repaso_espaciado_leitner():
    estado = spaced.introduce({}, "a#b", now=0)
    assert estado["a#b"] == {"box": 1, "due": DIA}
    assert spaced.due(estado, now=0) == []
    assert spaced.due(estado, now=DIA) == ["a#b"]
    estado = spaced.answer(estado, "a#b", True, now=DIA)
    assert estado["a#b"]["box"] == 2 and estado["a#b"]["due"] == DIA + 3 * DIA
    estado = spaced.answer(estado, "a#b", False, now=2 * DIA)
    assert estado["a#b"]["box"] == 1
    for _ in range(10):
        estado = spaced.answer(estado, "a#b", True, now=0)
    assert spaced.mastered(estado) == ["a#b"]
    assert spaced.introduce(estado, "a#b", now=99) is estado


def test_desbloqueo_del_plan():
    plan = load_curriculum({
        "schema": "amatista.curriculum/1", "route": "blender", "title": "Ruta",
        "courses": [
            {"id": "a", "title": "A", "difficulty": "principiante", "modules": [
                {"number": 1, "title": "1", "practice": "p1"}, {"number": 2, "title": "2", "practice": "p2"},
                {"number": 3, "title": "3", "practice": "p3"}]},
            {"id": "b", "title": "B", "difficulty": "principiante_intermedio", "modules": [
                {"number": 1, "title": "1", "practice": "q1"}]},
            {"id": "c", "title": "C", "difficulty": "intermedio", "status": "proximamente", "modules": [
                {"number": 1, "title": "1", "practice": "r1"}]},
        ],
    })
    estado = unlock_state(plan, ["p1"])
    assert estado == {"p1": COMPLETADO, "p2": DISPONIBLE, "p3": BLOQUEADO, "q1": DISPONIBLE, "r1": PROXIMAMENTE}
    assert next_practice(plan, ["p1"]) == "p2"
    assert next_practice(plan, ["p1", "p2", "p3", "q1"]) is None
