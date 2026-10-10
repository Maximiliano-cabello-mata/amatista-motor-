"""Motor 4: la ruta del alumno, las medidas amables y el instructor sin decimales."""
import json
from dataclasses import replace

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.models import TargetDefinition
from amatista_engine.practice.loader import dump_practice, parse_practice
from amatista_engine.ruta import (
    ACTUAL,
    ADELANTADA,
    HECHA,
    SIGUIENTE,
    YA_LO_TENIAS,
    ajustar,
    ajustar_parametros,
    frase_amable,
    holgura,
    logro,
    ruta_a_dict,
    titulo_parte,
)
from amatista_engine.testing import Escena

TREN = PRACTICAS / "principiante/m1-tren/practica.json"


@pytest.fixture(scope="module")
def tren():
    return parse_practice(json.loads(TREN.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def motor():
    return create_default_engine()


def _ruta(motor, practica, escena, **extra):
    reporte = motor.evaluate(practica, escena)
    guia = motor.guide(practica, escena, reporte)
    return motor.route(practica, reporte, guia, **extra), reporte


def todas_las_practicas():
    return sorted(PRACTICAS.glob("*/*/practica.json"))


# --- La ruta --------------------------------------------------------------------------------


def test_escena_vacia_una_sola_mision_actual(motor, tren):
    ruta, reporte = _ruta(motor, tren, Escena().construir())
    assert ruta.actual == 0 and ruta.mision.id == "vagones"
    assert [m.estado for m in ruta.misiones].count(ACTUAL) == 1
    assert all(m.estado == SIGUIENTE for m in ruta.misiones[1:])
    assert ruta.hechas == 0 and not ruta.completada
    assert ruta.mision.pasos and len(ruta.mision.pasos) <= 3, "la misión actual dice cómo hacerlo, en pocos pasos"
    assert ruta.mision.mensaje


def test_partes_automaticas_sin_stage(motor):
    practica = parse_practice({
        "schema": "amatista.practice/2", "id": "prueba.partes", "title": "Partes", "level": 1,
        "targets": [
            {"id": "cubo", "validator": "object.count", "params": {"primitive": "cube", "min": 1}},
            {"id": "plano", "validator": "shape.thinnest_axis", "params": {"primitive": "cube", "axis": "z"},
             "requires": ["cubo"]},
            {"id": "esfera", "validator": "object.count", "params": {"primitive": "sphere", "min": 1}},
            {"id": "suelo", "validator": "spatial.grounded", "params": {"primitive": "sphere"}},
            {"id": "cubo-suelo", "validator": "spatial.grounded", "params": {"primitive": "cube"}},
            {"id": "guardar", "validator": "file.named", "params": {"contains": "x"}},
        ],
    })
    ruta, _ = _ruta(motor, practica, Escena().construir())
    # «plano» sola en «Dale forma» se une a la parte de antes; guardar cierra la ruta.
    assert [(p.titulo, p.desde, p.hasta) for p in ruta.partes] == [
        ("Arma las piezas", 1, 3), ("Acomoda las piezas", 4, 5), ("Guarda y muestra", 6, 6)]


def test_los_opcionales_no_son_misiones(motor, tren):
    ruta, _ = _ruta(motor, tren, Escena().construir())
    assert "guardado" not in [m.id for m in ruta.misiones]


def test_partes_con_nombre_y_en_orden(motor, tren):
    ruta, _ = _ruta(motor, tren, Escena().construir())
    titulos = [p.titulo for p in ruta.partes]
    assert titulos == ["La locomotora y el vagón", "Las ruedas", "Arma el tren", "Revisa y guarda"]
    # Cada misión cae dentro de su parte.
    for m in ruta.misiones:
        p = ruta.partes[m.parte]
        assert p.desde <= m.numero <= p.hasta


def test_herramientas_de_la_mision_iluminadas(motor, tren):
    ruta, _ = _ruta(motor, tren, Escena().construir())
    assert "object.add" in ruta.mision.herramientas, ruta.mision.herramientas
    # El cinturón de herramientas tiene las de la práctica, primero las de la ruta.
    assert set(ruta.mision.herramientas) <= set(ruta.herramientas)
    assert set(tren.allowed_tools) <= set(ruta.herramientas)


def test_avanza_y_celebra(motor, tren):
    vacia = Escena().construir()
    antes, _ = _ruta(motor, tren, vacia)
    dos = Escena().malla("cube", dims=(2.2, 1.2, 1.1), loc=(1.2, 0, 0.6)).malla(
        "cube", dims=(2.0, 1.2, 1.0), loc=(-1.2, 0, 0.5)).construir()
    ruta, _ = _ruta(motor, tren, dos, previous=antes.mision.id)
    assert ruta.misiones[0].estado == HECHA
    assert ruta.mision.id != "vagones"
    assert ruta.celebracion.endswith("¡Y sin pistas!")
    con_pista, _ = _ruta(motor, tren, dos, previous="vagones", hints={"vagones": 1})
    assert "sin pistas" not in con_pista.celebracion


def test_lo_hecho_antes_queda_adelantado(motor):
    practica = parse_practice({
        "schema": "amatista.practice/2", "id": "prueba.ruta", "title": "Ruta", "level": 1,
        "targets": [
            {"id": "cubo", "title": "Un cubo", "validator": "object.count", "params": {"primitive": "cube", "min": 1}},
            {"id": "esfera", "title": "Una esfera", "validator": "object.count",
             "params": {"primitive": "sphere", "min": 1}},
            {"id": "guardar", "title": "Guarda", "validator": "file.named", "params": {"contains": "ruta"},
             "stage": "Al final"},
        ],
    })
    escena = replace(Escena().malla("sphere").construir(), file_path="/tmp/ruta.blend", file_saved=True)
    ruta, _ = _ruta(motor, practica, escena)
    estados = {m.id: m.estado for m in ruta.misiones}
    assert estados == {"cubo": ACTUAL, "esfera": ADELANTADA, "guardar": ADELANTADA}
    assert ruta.misiones[1].mensaje == YA_LO_TENIAS
    assert ruta.partes[-1].titulo == "Al final", "«stage» nombra la parte"
    assert ruta.hechas == 2


def test_practica_completa(motor):
    practica = parse_practice({
        "schema": "amatista.practice/2", "id": "prueba.fin", "title": "Fin", "level": 1,
        "targets": [{"id": "cubo", "validator": "object.count", "params": {"primitive": "cube", "min": 1}}],
    })
    ruta, reporte = _ruta(motor, practica, Escena().malla("cube").construir())
    assert reporte.completed and ruta.completada and ruta.mision is None and ruta.hechas == ruta.total == 1


def test_ruta_a_dict_es_json(motor, tren):
    ruta, _ = _ruta(motor, tren, Escena().construir())
    datos = json.loads(json.dumps(ruta_a_dict(ruta)))
    assert datos["actual"]["numero"] == 1 and datos["total"] == ruta.total
    assert datos["actual"]["parte"] == "La locomotora y el vagón"


@pytest.mark.parametrize("ruta_json", todas_las_practicas(), ids=lambda p: p.parent.name)
def test_toda_practica_tiene_ruta_clara(motor, ruta_json):
    """Cada práctica del plan: ruta con partes con nombre y una misión actual que dice qué hacer."""
    practica = parse_practice(json.loads(ruta_json.read_text(encoding="utf-8")))
    ruta, _ = _ruta(motor, practica, Escena().construir())
    assert ruta.total >= 2
    titulos = [p.titulo for p in ruta.partes]
    assert "Tu práctica" not in titulos, [titulo_parte(t) for t in practica.targets]
    assert len(titulos) == len(set(titulos)), f"{practica.id}: la ruta vuelve a una parte ya terminada {titulos}"
    assert len(titulos) <= 5
    assert ruta.mision is not None and ruta.mision.objetivo, f"{practica.id}: la primera misión no dice qué hacer"
    assert all(len(m.pasos) <= 3 for m in ruta.misiones)


# --- Medidas amables ---------------------------------------------------------------------------


def test_holgura_por_nivel():
    assert holgura(1) > holgura(2) > holgura(3) > holgura(4) == holgura(5) == 1.0


def test_tolerancias_se_aflojan_sin_perder_sentido():
    p = ajustar_parametros("spatial.grounded", {"role": "rueda", "tolerance": 0.15}, 1)
    assert 0.15 < p["tolerance"] <= 0.25
    assert ajustar_parametros("spatial.grounded", {"role": "rueda"}, 1)["tolerance"] == 0.1
    assert ajustar_parametros("spatial.on_top", {"role": "techo"}, 2)["tolerance"] > 0.25
    prop = ajustar_parametros("shape.proportion", {"axis": "x", "min_ratio": 1.3}, 1)
    assert 1.0 < prop["min_ratio"] < 1.3, "más largo sigue siendo más largo"
    delgada = ajustar_parametros("shape.thinnest_axis", {"axis": "z", "max_ratio": 0.5}, 1)
    assert 0.5 < delgada["max_ratio"] <= 0.7, "delgada sigue siendo delgada"


def test_niveles_altos_y_exact_no_cambian():
    params = {"tolerance": 0.05}
    assert ajustar_parametros("spatial.grounded", params, 4) is params
    exacto = {"tolerance": 0.05, "exact": True}
    assert ajustar_parametros("spatial.grounded", exacto, 1) is exacto
    t = TargetDefinition("x", "file.saved")
    assert ajustar(t, 1) is t


def test_logic_any_afloja_sus_opciones(tren):
    t = ajustar(tren.target("vagones-largos"), 1)
    assert all(o["params"]["min_ratio"] < 1.3 for o in t.params["options"])
    assert tren.target("vagones-largos").params["options"][0]["params"]["min_ratio"] == 1.3, "el original no cambia"


def test_rueda_casi_en_el_suelo_cuenta_en_nivel_1(motor, tren):
    """0.2 sobre el suelo no se ve como «flotando» en un tren de juguete; 0.6 sí."""
    t = tren.target("ruedas-al-suelo")
    casi = Escena().malla("cylinder", dims=(0.7, 0.2, 0.7), loc=(0, 0.7, 0.35 + 0.2), rol="rueda").construir()
    lejos = Escena().malla("cylinder", dims=(0.7, 0.2, 0.7), loc=(0, 0.7, 0.35 + 0.6), rol="rueda").construir()
    assert motor.registry.get(t.validator)(t, casi).passed is False, "el autor pidió 0.15"
    assert motor._validar(t, casi, tren).passed is True
    assert motor._validar(t, lejos, tren).passed is False


# --- El instructor sin decimales -------------------------------------------------------------------


def test_frase_amable_sin_numeros(motor, tren):
    t = tren.target("ruedas-al-suelo")
    lejos = Escena().malla("cylinder", dims=(0.7, 0.2, 0.7), loc=(0, 0.7, 1.2), rol="rueda").construir()
    r = motor._validar(t, lejos, tren)
    frase = frase_amable(tren, t, r, 1)
    assert "flota" in frase and not any(c.isdigit() for c in frase.replace("(1)", ""))
    assert frase_amable(tren, t, r, 4) == "", "en los niveles 4 y 5 las medidas son parte de lo que se aprende"


def test_logros_varian():
    assert len({logro(n) for n in range(1, 8)}) == 7


def test_stage_se_exporta(tren):
    datos = json.loads(TREN.read_text(encoding="utf-8"))
    datos["targets"][0]["stage"] = "Las piezas"
    practica = parse_practice(datos)
    assert practica.targets[0].stage == "Las piezas" and "stage" not in practica.targets[0].params
    assert dump_practice(practica)["targets"][0]["stage"] == "Las piezas"
