"""Motor 3.4: el motor reconoce la figura (figure.recognize y roles deducidos).

- Sin roles: el motor deduce qué es cada pieza por su forma.
- Con sentido: ruedas en el suelo y a los dos lados, chimenea encima, nada flotando.
- Por nivel: en el 1 basta la forma; en el 4 y 5 cuentan las medidas reales.
- Libertad creativa: los adornos no restan.
- Identifica: si la figura es otra (una mesa), lo dice.
"""
import json
import random
from dataclasses import replace

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.figures import PERFILES, biblioteca, identificar, inferir_roles, perfil_para
from amatista_engine.practice.loader import dump_practice, parse_practice, pieza_como_dict
from amatista_engine.testing import Escena

TREN = PRACTICAS / "principiante/m1-tren/practica.json"


@pytest.fixture(scope="module")
def tren():
    return parse_practice(json.loads(TREN.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def motor():
    return create_default_engine()


def objetivo(tren, nivel=None, **params):
    base = tren.target("figura")
    return replace(base, params={**base.params, **({"level": nivel} if nivel else {}), **params})


def evaluar(motor, tren, escena, nivel=None, **params):
    return motor.registry.get("figure.recognize")(objetivo(tren, nivel, **params), escena)


def piezas_sin_sentido(tren):
    P = tren.reference.parts
    azar = random.Random(3)
    return {
        "ruedas en el techo": [replace(p, location=(p.location[0], p.location[1], 1.8)) if p.role == "rueda" else p for p in P],
        "ruedas acostadas": [replace(p, rotation=(0, 0, 0)) if p.role == "rueda" else p for p in P],
        "vagones apilados": [replace(p, location=(0, 0, 0.9 if p.name == "Locomotora" else 2.0)) if p.role == "vagon" else p
                             for p in P],
        "piezas regadas": [replace(p, location=(azar.uniform(-4, 4), azar.uniform(-4, 4), azar.uniform(0, 3))) for p in P],
        "ruedas de un lado": [replace(p, location=(p.location[0], 0.7, p.location[2])) if p.role == "rueda" else p for p in P],
        "chimenea flotando": [replace(p, location=(1.9, 0, 2.6)) if p.role == "chimenea" else p for p in P],
    }


def test_la_practica_usa_el_reconocedor_con_su_nivel(tren):
    params = tren.target("figura").params
    assert tren.target("figura").validator == "figure.recognize"
    assert params["level"] == 1 and params["title"] == "Tren de juguete" and len(params["parts"]) == 11
    # Al volver a escribir la práctica, lo inyectado no se guarda en el objetivo.
    datos = dump_practice(tren)
    assert next(t for t in datos["targets"] if t["id"] == "figura")["params"] == {}
    assert parse_practice(datos).target("figura").params == params


@pytest.mark.parametrize("nivel,perfil", [(1, "forma"), (2, "proporcion"), (3, "cercana"), (4, "medidas"), (5, "exacta")])
def test_exigencia_por_nivel(nivel, perfil):
    assert perfil_para(nivel).id == perfil
    assert perfil_para(1, "exacta").id == "exacta"  # la práctica puede fijarla
    tolerancias = [PERFILES[p].tolerancia for p in ("forma", "proporcion", "cercana", "medidas", "exacta")]
    assert tolerancias == sorted(tolerancias, reverse=True)


@pytest.mark.parametrize("roles", [True, False])
@pytest.mark.parametrize("nivel", [1, 2, 3])
def test_el_tren_a_mano_se_reconoce_con_o_sin_roles(motor, tren, roles, nivel):
    for semilla in range(1, 5):
        escena = Escena().referencia(tren.reference.parts, roles=roles, variacion=0.25, semilla=semilla).construir()
        r = evaluar(motor, tren, escena, nivel)
        assert r.passed, (semilla, r.message)
        assert "reconoce tu figura" in r.message


@pytest.mark.parametrize("nivel", [1, 2, 3, 4, 5])
def test_figuras_sin_sentido_no_pasan_en_ningun_nivel(motor, tren, nivel):
    for nombre, piezas in piezas_sin_sentido(tren).items():
        for roles in (True, False):
            r = evaluar(motor, tren, Escena().referencia(piezas, roles=roles).construir(), nivel)
            assert not r.passed, (nombre, roles, r.message)


def test_los_mensajes_dicen_que_no_tiene_sentido(motor, tren):
    casos = piezas_sin_sentido(tren)
    esperados = {
        "ruedas en el techo": "suelo",
        "vagones apilados": "encima",
        "ruedas de un lado": "dos lados",
        "chimenea flotando": "encima",
        "ruedas acostadas": "girada",
    }
    for nombre, texto in esperados.items():
        r = evaluar(motor, tren, Escena().referencia(casos[nombre], roles=False).construir(), 1)
        assert texto in r.message, (nombre, r.message)


def test_una_pieza_flotando_se_nombra(motor, tren):
    escena = Escena().referencia(tren.reference.parts, roles=False)
    escena.malla("cylinder", "Humo", dims=(0.3, 0.3, 0.6), loc=(1.9, 0, 3.4))
    r = evaluar(motor, tren, escena.construir(), 1)
    assert r.details["failed_relations"]


def test_en_el_nivel_1_la_forma_basta(motor, tren):
    # Una chimenea exagerada sigue siendo un tren reconocible para quien empieza…
    P = [replace(p, size=(0.4, 0.4, 2.5), location=(1.9, 0, 2.7)) if p.role == "chimenea" else p
         for p in tren.reference.parts]
    escena = Escena().referencia(P).construir()
    assert evaluar(motor, tren, escena, 1).passed
    # …pero desde el nivel 2 la proporción cuenta.
    assert not evaluar(motor, tren, escena, 2).passed


def test_niveles_4_y_5_piden_el_tamano_real(motor, tren):
    grande = Escena().referencia(tren.reference.parts, escala=1.6).construir()
    assert evaluar(motor, tren, grande, 3).passed
    for nivel in (4, 5):
        r = evaluar(motor, tren, grande, nivel)
        assert not r.passed and "medidas cuentan" in r.message
    exacto = Escena().referencia(tren.reference.parts).construir()
    assert evaluar(motor, tren, exacto, 5).passed
    # A mano (±25 %) alcanza en el 3, no en el 5.
    a_mano = Escena().referencia(tren.reference.parts, variacion=0.25, semilla=2).construir()
    assert evaluar(motor, tren, a_mano, 3).passed and not evaluar(motor, tren, a_mano, 5).passed


def test_los_adornos_no_restan(motor, tren):
    escena = Escena().referencia(tren.reference.parts, roles=False)
    escena.malla("sphere", "Faro", dims=(0.3, 0.3, 0.3), loc=(2.4, 0, 1.0))
    escena.malla("cone", "Bandera", dims=(0.2, 0.2, 0.4), loc=(-1.15, 0, 1.55))
    r = evaluar(motor, tren, escena.construir(), 1)
    assert r.passed and r.details["decorations"] == 2 and "adorno" in r.message
    assert "Faro" not in r.details["inferred_roles"]


def test_deduce_los_roles_por_la_forma(tren):
    partes = [pieza_como_dict(p) for p in tren.reference.compared]
    escena = (Escena().cubo("Cubo", dims=(2, 1.1, 1)).cilindro("Rueda?", dims=(0.7, 0.7, 0.2), rot=(90, 0, 0))
              .cilindro("Tubo", dims=(0.4, 0.4, 0.8)).construir())
    assert inferir_roles(partes, escena.objects) == {"Cubo": "vagon", "Rueda?": "rueda", "Tubo": "chimenea"}
    # Los roles que puso el alumno se respetan.
    con_rol = Escena().cilindro("Mi rueda", dims=(0.4, 0.4, 0.8), rol="rueda").construir()
    assert inferir_roles(partes, con_rol.objects) == {}


def test_el_motor_ya_no_pide_roles(motor, tren):
    """Los pasos «Dos vagones», «Ocho ruedas»… se cumplen sin tocar la pestaña Amatista."""
    escena = Escena().referencia(tren.reference.parts, roles=False).guardado("/tmp/mi_tren.blend").construir()
    reporte = motor.evaluate(tren, escena)
    assert reporte.completed, [r.message for r in reporte.results if not r.passed]
    deducidos = dict(reporte.inferred_roles)
    assert list(deducidos.values()).count("rueda") == 8 and list(deducidos.values()).count("vagon") == 2


def test_identifica_otra_figura(motor, tren):
    mesa = next(f for f in biblioteca() if f["id"] == "mesa")
    escena = Escena().referencia(mesa["parts"], roles=False).construir()
    r = evaluar(motor, tren, escena, 1)
    assert not r.passed and "se parece más a «Mesa»" in r.message
    assert identificar(escena, biblioteca())[0]["id"] == "mesa"


@pytest.mark.parametrize("figura", [f["id"] for f in biblioteca()])
def test_cada_figura_de_la_biblioteca_se_reconoce_a_si_misma(figura):
    datos = next(f for f in biblioteca() if f["id"] == figura)
    escena = Escena().referencia(datos["parts"], roles=False, variacion=0.15, semilla=4).construir()
    assert identificar(escena, biblioteca())[0]["id"] == figura


def test_escena_vacia(motor, tren):
    r = evaluar(motor, tren, Escena().construir(), 1)
    assert not r.passed and "piezas" in r.message
