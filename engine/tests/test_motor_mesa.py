import json

import pytest

from amatista_engine import create_default_engine
from amatista_engine.models import ACTUAL, BLOQUEADO, COMPLETADO, SceneObject, SceneState
from amatista_engine.pedagogy import classify, evidence, next_hint
from amatista_engine.practice import compile_practice, dump_practice, load_practice, parse_practice
from amatista_engine.snapshot import scene_from_dict, scene_to_dict

from ayudantes import MESA, REPO, mesa_completa, pata

motor = create_default_engine()
practica = load_practice(MESA)


def test_mesa_completa_llega_al_100():
    reporte = motor.evaluate(practica, mesa_completa())
    assert reporte.progress == 100.0
    assert reporte.completed
    assert reporte.current_target_id == "color"  # solo queda el extra opcional


def test_mesa_vacia_empieza_por_la_cubierta():
    reporte = motor.evaluate(practica, SceneState("5.1.1", "", False, ()))
    assert reporte.progress == 0
    assert reporte.current_target_id == "cubierta"
    estados = {p.target_id: p.status for p in reporte.steps}
    assert estados["patas"] == BLOQUEADO and estados["grosor"] == BLOQUEADO


def test_tres_patas_dicen_cuantas_faltan():
    escena = mesa_completa()
    escena = SceneState(escena.blender_version, escena.file_path, True, escena.objects[:4])
    reporte = motor.evaluate(practica, escena)
    assert not reporte.completed
    assert reporte.result("patas").message == "Tienes 3/4 «pata». Falta 1."
    assert reporte.current_target_id == "patas"
    assert {p.target_id: p.status for p in reporte.steps}["cubierta"] == COMPLETADO


def test_pata_que_atraviesa_la_cubierta():
    escena = mesa_completa()
    alta = pata("P4", 0.9, 0.4, alto=1.0)
    escena = SceneState("5.1.1", "x.blend", True, escena.objects[:4] + (alta,))
    reporte = motor.evaluate(practica, escena)
    assert reporte.result("debajo").passed is False
    assert "P4" in reporte.result("debajo").message


def test_cubierta_gruesa_y_mensaje_personalizado():
    escena = mesa_completa()
    gruesa = SceneObject("Cubierta", "MESH", roles=("cubierta",), location=(0, 0, 1.0), dimensions=(2, 1, 0.5))
    reporte = motor.evaluate(practica, SceneState("5", "a.blend", True, (gruesa,) + escena.objects[1:]))
    assert reporte.result("grosor").passed is False
    assert "demasiado grande" in reporte.result("grosor").message
    assert reporte.result("cubierta").message == "Ya tienes la cubierta de tu mesa."


def test_archivo_sin_guardar():
    reporte = motor.evaluate(practica, mesa_completa(guardada=False))
    assert reporte.progress == 90.0
    assert reporte.current_target_id == "guardar"


def test_extra_opcional_no_cambia_el_progreso():
    reporte = motor.evaluate(practica, mesa_completa(materials=("Madera",)))
    assert reporte.result("color").passed and reporte.progress == 100.0


def test_herramienta_fuera_de_nivel_avisa():
    escena = mesa_completa(modifiers=("BOOLEAN",))
    reporte = motor.evaluate(practica, escena)
    assert [w.tool_id for w in reporte.tool_warnings] == ["modifier.boolean"]
    assert "Nivel 3" in reporte.tool_warnings[0].message
    assert reporte.completed  # avisar, no bloquear


def test_pistas_progresivas_y_autonomia():
    estado = {}
    primera = next_hint(practica, estado, "patas")
    segunda = next_hint(practica, estado, "patas")
    assert (primera.level, segunda.level, segunda.total) == (1, 2, 4)
    assert estado == {"patas": 2}
    reporte = motor.evaluate(practica, mesa_completa())
    assert classify(True, {}) == "autonoma"
    assert classify(True, estado) == "con_pistas"
    next_hint(practica, estado, "patas")
    assert classify(True, estado) == "con_guia"
    resumen = evidence(practica, reporte, estado)
    assert resumen["hintsUsed"] == 3 and resumen["completed"] and resumen["autonomy"] == "con_guia"


def test_la_foto_de_la_escena_viaja_al_servidor_sin_cambiar_el_resultado():
    escena = mesa_completa()
    viaje = scene_from_dict(json.loads(json.dumps(scene_to_dict(escena))))
    assert motor.evaluate(practica, viaje).progress == motor.evaluate(practica, escena).progress == 100.0


def test_todas_las_practicas_del_repositorio_compilan():
    archivos = sorted((REPO / "practices").rglob("*.json"))
    assert archivos
    for archivo in archivos:
        resultado = compile_practice(json.loads(archivo.read_text(encoding="utf-8")))
        assert resultado.ok, (archivo.name, resultado.errors)


def test_exportar_y_volver_a_leer_da_la_misma_practica():
    assert parse_practice(dump_practice(practica)) == practica


def test_eventos_solo_reevaluan_lo_afectado():
    afectados = motor.targets_for_event(practica, "FILE_SAVED")
    assert "guardar" in afectados and "patas" not in afectados


@pytest.mark.parametrize(
    "cambio, error",
    [
        (lambda d: d["targets"][0].update(validator="uv.exists"), "no existe en esta versión"),
        (lambda d: d["targets"][2]["params"].update(role="pierna"), "rol «pierna»"),
        (lambda d: d["targets"][0].update(requires=["guardar"]), "ciclo"),
        (lambda d: d["targets"][1].update(requires=["nada"]), "«nada», que no existe"),
        (lambda d: d["targets"][1]["params"].update(axis="w"), "eje"),
    ],
)
def test_el_compilador_explica_los_errores(cambio, error):
    datos = json.loads(MESA.read_text(encoding="utf-8"))
    cambio(datos)
    resultado = compile_practice(datos)
    assert not resultado.ok
    assert any(error in e for e in resultado.errors), resultado.errors
