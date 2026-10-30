"""Motor 6: la plataforma marca la etapa, la demostración es la de la actividad y el molde tiene cordura."""
import pytest

from amatista_engine.cli import PRACTICAS
from amatista_engine.taller import (
    actividad_por_id,
    etapas,
    leer_catalogo,
    linea_de_tiempo,
    marcar_demo,
    pasos_de_actividad,
    pieza_de_revision,
    registrar_intento,
    revisar_molde,
)
from amatista_engine.testing import Escena

TALLER = "blender.bp.m1"
AHORA = 1_800_000_000.0


@pytest.fixture(scope="module")
def catalogo():
    return leer_catalogo(PRACTICAS / "habilidades.json")


def _objetos(pasos):
    return {p[a].get("nombre") for p in pasos for a in ("agregar", "duplicar") if a in p}


# --- La demostración de ESTA actividad ------------------------------------------------------------


def test_mirame_hace_el_cono_que_pide_la_actividad_y_no_la_caja_generica(catalogo):
    h = catalogo.habilidad("bl-agregar-primitivas")
    a = actividad_por_id(catalogo, TALLER, "conmigo:bl-agregar-primitivas:cono")
    pasos = pasos_de_actividad(h.demo, a.molde or a.piezas, a.inicio)
    assert _objetos(pasos) == {"Cono"}
    assert "Caja" not in _objetos(pasos) and "Lata" not in _objetos(pasos)
    agregar = next(p["agregar"] for p in pasos if "agregar" in p)
    assert agregar["primitiva"] == "cone"
    linea = linea_de_tiempo(pasos, h.titulo)
    assert linea.pasos and "Cono" in linea.pasos[0].teclas


def test_arregla_esta_escena_cambia_la_forma_equivocada(catalogo):
    h = catalogo.habilidad("bl-agregar-primitivas")
    a = actividad_por_id(catalogo, TALLER, "conmigo:bl-agregar-primitivas:cambia")
    pasos = pasos_de_actividad(h.demo, a.molde or a.piezas, a.inicio)
    acciones = [next(k for k in p if k not in ("texto", "teclas", "segundos")) for p in pasos]
    assert acciones[:3] == ["agregar", "borrar", "agregar"]
    assert pasos[2]["agregar"]["primitiva"] == "cylinder"


def test_el_gesto_de_la_habilidad_se_ve_sobre_la_pieza(catalogo):
    h = catalogo.habilidad("bl-escalar-eje")
    a = actividad_por_id(catalogo, TALLER, "conmigo:bl-escalar-eje:tabla")
    pasos = pasos_de_actividad(h.demo, a.molde or a.piezas, a.inicio)
    agregar = pasos[0]["agregar"]
    assert agregar["medidas"] == [2.0, 2.0, 2.0]  # aparece con su tamaño de base…
    escalar = next(p["escalar"] for p in pasos if "escalar" in p)
    assert escalar["medidas"] == [3.0, 1.0, 0.2]  # …y se estira hasta el molde
    assert _objetos(pasos) == {"Tabla"}


def test_sin_piezas_queda_la_demostracion_de_la_habilidad():
    demo = ({"agregar": {"primitiva": "cube", "nombre": "Caja"}}, {"material": {"objeto": "Caja"}})
    assert pasos_de_actividad(demo, ()) == demo


def test_los_pasos_sin_forma_usan_una_pieza_de_la_actividad():
    demo = ({"agregar": {"primitiva": "cube", "nombre": "Caja"}}, {"modificador": {"objeto": "Caja", "tipo": "MIRROR"}})
    pasos = pasos_de_actividad(demo, ({"primitive": "cube", "name": "Ala", "size": [2, 2, 2], "location": [0, 0, 0]},))
    assert pasos[-1]["modificador"]["objeto"] == "Ala"


def test_la_pieza_del_proyecto_se_vuelve_molde_para_su_demostracion():
    e = Escena().construir()
    r = revisar_molde([{"primitive": "cylinder", "name": "Rueda", "size": [0.7, 0.7, 0.2], "location": [1, 0, 0.35],
                        "rotation": [90, 0, 0]}], e)
    pieza = pieza_de_revision(r.pieza_actual)
    assert pieza["primitive"] == "cylinder" and pieza["name"] == "Rueda" and pieza["rotation"] == [90, 0, 0]


# --- Cordura del molde ------------------------------------------------------------------------------

CUBO = [{"primitive": "cube", "name": "Caja", "size": [2, 2, 2], "location": [0, 0, 1]}]


def test_un_cubo_tres_veces_mas_grande_ya_no_llena_el_molde_del_nivel_1():
    e = Escena().malla("cube", "Caja", dims=(3.4, 3.4, 3.4), loc=(0, 0, 1.7)).construir()
    assert not revisar_molde(CUBO, e, "molde", 1).completa


def test_llenar_el_molde_con_un_monton_de_piezas_no_cuenta():
    e = Escena().malla("cube", "Caja", dims=(2, 2, 2), loc=(0, 0, 1))
    for i in range(6):
        e.malla("cube", dims=(0.5, 0.5, 0.5), loc=(4 + i, 4, 0.25))
    r = revisar_molde(CUBO, e.construir(), "molde", 1)
    assert r.revuelto and not r.completa and "sobran" in r.mensaje


def test_una_malla_irreconocible_no_llena_piezas_en_los_primeros_niveles():
    e = Escena().malla("cube", "Caja", dims=(2, 2, 2), loc=(0, 0, 1), vertices=300, caras=290)
    objeto = e.construir()
    objeto = type(objeto)(**{**objeto.__dict__, "objects": tuple(
        type(o)(**{**o.__dict__, "data_name": "Blob"}) for o in objeto.objects)})
    assert not revisar_molde(CUBO, objeto, "molde", 1).completa
    assert revisar_molde(CUBO, objeto, "molde", 3).completa  # en el nivel 3 ya se une y edita


def test_la_forma_se_reconoce_por_sus_vertices_aunque_se_renombre_la_malla():
    e = Escena().malla("cube", "Caja", dims=(2, 2, 2), loc=(0, 0, 1)).construir()
    e = type(e)(**{**e.__dict__, "objects": tuple(type(o)(**{**o.__dict__, "data_name": "MiCaja"}) for o in e.objects)})
    assert revisar_molde(CUBO, e, "molde", 1).completa


# --- La plataforma marca la etapa ------------------------------------------------------------------


def test_la_exploracion_solo_pide_las_primeras_habilidades(catalogo):
    t = catalogo.taller(TALLER)
    etapa = etapas.etapa_de(t, "exploracion")
    assert etapa.habilidades == tuple(t.habilidades[:2])
    a, _plan, cumplida = etapas.siguiente(catalogo, etapa, {}, AHORA)
    assert not cumplida and a.tipo == "mira" and a.habilidad == t.habilidades[0]


def test_la_exploracion_no_acepta_habilidades_de_otro_taller(catalogo):
    t = catalogo.taller(TALLER)
    etapa = etapas.etapa_de(t, "exploracion", ["bl-extruir", "bl-rotar", "inventada"])
    assert etapa.habilidades == ("bl-rotar",)
    assert etapas.etapa_de(t, "cualquier-cosa").nombre == etapas.PRACTICA


def test_la_exploracion_se_cumple_con_mira_y_un_intento_y_no_sigue_sola(catalogo):
    t = catalogo.taller(TALLER)
    etapa = etapas.etapa_de(t, "exploracion")
    estado = {}
    for hid in etapa.habilidades:
        h = catalogo.habilidad(hid)
        estado[hid] = registrar_intento(marcar_demo(None, h.bkt), h.bkt, True, 2, AHORA, molde=True, tipo="conmigo")
    a, plan, cumplida = etapas.siguiente(catalogo, etapa, estado, AHORA)
    assert cumplida and a is None and plan is not None
    otra = actividad_por_id(catalogo, TALLER, "conmigo:bl-rotar:rueda")
    assert not etapas.permitida(etapa, otra)


def test_la_practica_es_el_taller_entero(catalogo):
    t = catalogo.taller(TALLER)
    etapa = etapas.etapa_de(t, "practica")
    a, _plan, cumplida = etapas.siguiente(catalogo, etapa, {}, AHORA)
    assert a is not None and not cumplida
    assert etapas.permitida(etapa, actividad_por_id(catalogo, TALLER, "conmigo:bl-rotar:rueda"))

