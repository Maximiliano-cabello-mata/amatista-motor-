"""Motor 3.3: la figura tiene sentido (figure.resembles y dimension.approx).

Una figura parecida al modelo pasa aunque las medidas sean a mano (±25 %),
esté más grande, más chica, girada o en espejo. Una figura sin sentido no
pasa aunque cada pieza por separado cumpla: ruedas en el techo, de un solo
lado o acostadas, vagones apilados, piezas regadas o una pieza gigante.
"""
import json
import random
from dataclasses import replace

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.models import TargetDefinition
from amatista_engine.practice import compile_practice
from amatista_engine.practice.loader import dump_practice, parse_practice
from amatista_engine.testing import Escena

TREN = PRACTICAS / "principiante/m1-tren/practica.json"


@pytest.fixture(scope="module")
def tren():
    return parse_practice(json.loads(TREN.read_text(encoding="utf-8")))


def evaluar(tren, piezas, **kw):
    motor = create_default_engine()
    funcion = motor.registry.get("figure.resembles")
    return funcion(tren.target("figura"), Escena().referencia(piezas, **kw).construir())


def test_la_practica_lleva_las_piezas_del_modelo(tren):
    params = tren.target("figura").params
    assert len(params["parts"]) == 11  # el suelo solo decora la imagen
    assert params["tolerance"] == 0.35 and params["labels"]["rueda"] == "Rueda"
    # Al volver a escribir la práctica, las piezas quedan solo en «reference».
    datos = dump_practice(tren)
    figura = next(t for t in datos["targets"] if t["id"] == "figura")
    assert figura["params"] == {} and len(datos["reference"]["parts"]) == 12
    assert parse_practice(datos).target("figura").params == params


@pytest.mark.parametrize("semilla", range(1, 9))
def test_medidas_a_mano_pasan(tren, semilla):
    assert evaluar(tren, tren.reference.parts, variacion=0.25, semilla=semilla).passed


@pytest.mark.parametrize("escala,giro", [(1, 0), (2, 90), (0.6, 180), (1.4, 270)])
def test_mas_grande_mas_chica_o_girada_pasa(tren, escala, giro):
    assert evaluar(tren, tren.reference.parts, escala=escala, giro=giro).passed


def test_demasiado_grande_pide_escalar(tren):
    r = evaluar(tren, tren.reference.parts, escala=4)
    assert not r.passed and "redúcela" in r.message


def _cambiar(piezas, rol, **cambios):
    return [replace(p, **cambios(p) if callable(cambios) else cambios) if p.role == rol else p for p in piezas]


def test_figuras_sin_sentido_no_pasan(tren):
    P = tren.reference.parts
    techo = [replace(p, location=(p.location[0], p.location[1], 1.8)) if p.role == "rueda" else p for p in P]
    acostadas = [replace(p, rotation=(0, 0, 0)) if p.role == "rueda" else p for p in P]
    apilados = [replace(p, location=(0, 0, 0.9 if p.name == "Locomotora" else 2.0)) if p.role == "vagon" else p for p in P]
    gigante = [replace(p, size=(0.4, 0.4, 2.5), location=(1.9, 0, 2.7)) if p.role == "chimenea" else p for p in P]
    azar = random.Random(3)
    regadas = [replace(p, location=(azar.uniform(-4, 4), azar.uniform(-4, 4), azar.uniform(0, 3))) for p in P]
    casos = {
        "techo": (techo, "más abajo"),
        "acostadas": (acostadas, "girada"),
        "apilados": (apilados, "más abajo"),
        "gigante": (gigante, "demasiado alta"),
        "regadas": (regadas, ""),
    }
    for nombre, (piezas, texto) in casos.items():
        r = evaluar(tren, piezas)
        assert not r.passed, nombre
        assert texto in r.message, (nombre, r.message)


def test_falta_un_tipo_de_pieza_o_los_roles(tren):
    r = evaluar(tren, tren.reference.parts, sin=["chimenea"])
    assert not r.passed and "Falta «Chimenea»" in r.message
    r = evaluar(tren, tren.reference.parts, roles=False)
    assert not r.passed and "Asigna los roles" in r.message


def test_menos_ruedas_que_el_modelo(tren):
    ruedas = [p for p in tren.reference.parts if p.role == "rueda"]
    cuatro = [p for p in tren.reference.parts if p.role != "rueda"] + ruedas[:4]
    r = evaluar(tren, cuatro)
    assert not r.passed and "tiene 8" in r.message


def test_la_referencia_se_revisa_al_compilar():
    motor = create_default_engine()
    datos = json.loads(TREN.read_text(encoding="utf-8"))
    datos["reference"]["parts"][0]["primitive"] = "tetera"
    datos["reference"]["tolerance"] = 3
    resultado = compile_practice(datos, motor.registry, motor.tools)
    assert not resultado.ok
    assert any("primitive" in e for e in resultado.errors) and any("tolerance" in e for e in resultado.errors)
    sin_modelo = json.loads(TREN.read_text(encoding="utf-8"))
    del sin_modelo["reference"]
    assert any("necesita 'reference'" in e for e in compile_practice(sin_modelo, motor.registry, motor.tools).errors)


def test_medida_aproximada():
    motor = create_default_engine()
    funcion = motor.registry.get("dimension.approx")
    escena = Escena().esfera("Bola", dims=(2.3, 2.3, 2.3), loc=(0, 0, 1.15)).construir()
    cerca = TargetDefinition(id="a", validator="dimension.approx", params={"primitive": "sphere", "value": 2})
    assert funcion(cerca, escena).passed
    lejos = TargetDefinition(id="b", validator="dimension.approx", params={"primitive": "sphere", "value": 4})
    r = funcion(lejos, escena)
    assert not r.passed and "cerca de 4 m" in r.message
