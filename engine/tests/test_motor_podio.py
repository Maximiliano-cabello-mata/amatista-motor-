"""Contrato educativo del podio: evita aprobar posiciones o escalas incorrectas."""
import json
from dataclasses import replace
from pathlib import Path

import pytest
from amatista_engine import create_default_engine
from amatista_engine.models import SceneObject, SceneState
from amatista_engine.practice import load_practice

REPO = Path(__file__).resolve().parents[2]
motor = create_default_engine()
practica = load_practice(REPO / "practices/blender/level_1/podio.json")

def escena():
    # Valores de referencia independientes de los rangos del JSON.
    return SceneState("4.2", "mi_podio.blend", True, (
        SceneObject("A", "MESH", roles=("centro",), dimensions=(1, 1, 1.5), location=(0, 0, .75)),
        SceneObject("B", "MESH", roles=("izquierda",), dimensions=(1, 1, 1), location=(-1.1, 0, .5)),
        SceneObject("C", "MESH", roles=("derecha",), dimensions=(1, 1, .5), location=(1.1, 0, .25)),
    ))

def test_referencia_completa_y_escena_vacia():
    assert motor.evaluate(practica, escena()).completed
    assert motor.evaluate(practica, escena()).progress == 100
    assert not motor.evaluate(practica, SceneState("4.2", "", False)).completed

@pytest.mark.parametrize("indice,cambios,objetivo", [
    (0, {"location": (0, 0, 0)}, "centro_posicion_z"),
    (1, {"location": (0, 0, .5)}, "izquierda_posicion_x"),
    (2, {"dimensions": (1, 1, 1)}, "derecha_medida_z"),
    (0, {"scale": (.5, .5, .75)}, "centro_escala"),
    (1, {"roles": ("centro",)}, "izquierda"),
])
def test_errores_reales_no_completan(indice, cambios, objetivo):
    original = escena()
    objetos = list(original.objects)
    objetos[indice] = replace(objetos[indice], **cambios)
    reporte = motor.evaluate(practica, replace(original, objects=tuple(objetos)))
    assert not reporte.completed
    assert reporte.result(objetivo).passed is False

def test_no_acepta_entrega_con_cambios_sin_guardar():
    reporte = motor.evaluate(practica, replace(escena(), file_saved=False))
    assert not reporte.completed
    assert reporte.result("guardar").passed is False

def test_enlace_y_pasos_del_modulo_coinciden_con_la_practica():
    modulo = json.loads((REPO / "frontend/src/data/modulos/blender-modulo-3.json").read_text(encoding="utf-8"))["module"]
    bloques = [b for l in modulo["lessons"] for b in l.get("contentBlocks", []) if b["type"] == "blender_practice"]
    assert len(bloques) == 1
    assert bloques[0]["practica"] == practica.id
    assert bloques[0]["steps"] == [t.title for t in practica.targets if not t.optional]
    assert modulo["estado"] == "borrador"
