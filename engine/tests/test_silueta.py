"""Motor 3.5: la silueta de una malla (figures/silueta.py) y figure.silhouette.

La espada del módulo 2 es UNA malla: Amatista la corta en rebanadas y dice,
parte por parte, qué está bien y qué falta.
"""
import copy
import json
import time
from pathlib import Path

import pytest

from amatista_engine import create_default_engine
from amatista_engine.figures.silueta import (
    comparar_siluetas,
    lista_de_revision,
    malla_de_pieza,
    partes_del_modelo,
    silueta_de_malla,
    silueta_de_piezas,
)
from amatista_engine.models import SceneObject, SceneState, TargetDefinition
from amatista_engine.practice import parse_practice
from amatista_engine.snapshot import scene_from_dict, scene_to_dict
from amatista_engine.testing import Escena
from amatista_engine.validators.silhouette import silhouette

ESPADA = Path(__file__).resolve().parents[2] / "practices/blender/principiante/m2-espada/practica.json"


@pytest.fixture(scope="module")
def practica():
    return parse_practice(json.loads(ESPADA.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def piezas(practica):
    return [{"name": p.name, "primitive": p.primitive, "size": list(p.size), "location": list(p.location),
             "rotation": list(p.rotation), "segments": p.segments} for p in practica.reference.compared]


@pytest.fixture(scope="module")
def modelo(piezas):
    return partes_del_modelo(piezas)


def revisar(piezas_alumno, modelo, exigencia="proporcion"):
    silueta, partes = modelo
    return comparar_siluetas(silueta_de_piezas(piezas_alumno), silueta, partes, exigencia)


def estado(revision, parte):
    return next(i["estado"] for i in lista_de_revision(revision) if i["texto"] == parte)


# --- Medir ------------------------------------------------------------------------------


def test_un_cubo_se_mide_en_su_eje_mas_largo():
    puntos, aristas = malla_de_pieza("cube", (0.4, 0.2, 3.0), (5, 5, 1.5))
    s = silueta_de_malla(puntos, aristas, 8)
    assert s.eje == 2 and s.largo == pytest.approx(3.0)
    assert all(a == pytest.approx(0.4) and b == pytest.approx(0.2) for a, b in s.anchos)


def test_un_cono_se_afila():
    puntos, aristas = malla_de_pieza("cone", (1.0, 1.0, 4.0), segmentos=16)
    s = silueta_de_malla(puntos, aristas, 8)
    assert s.anchos[0][0] > 0.8 and s.anchos[-1][0] < 0.2


def test_las_partes_del_modelo_van_en_orden(modelo):
    _, partes = modelo
    assert [p.nombre for p in partes] == ["Pomo", "Mango", "Guarda", "Hoja", "Punta"]
    assert partes[0].desde == 0 and partes[-1].hasta == pytest.approx(1.0)
    assert partes[3].hasta - partes[3].desde > 0.5  # la hoja es más de la mitad de la espada


# --- Comparar ---------------------------------------------------------------------------


def test_la_espada_del_modelo_esta_completa(piezas, modelo):
    r = revisar(piezas, modelo)
    assert not r.criticas and not r.fuera and r.puntaje > 0.85
    assert all(i["estado"] == "Bien" for i in lista_de_revision(r))


def test_sin_guarda_falta_la_guarda_en_todos_los_niveles(piezas, modelo):
    sin_guarda = copy.deepcopy(piezas)
    sin_guarda[2]["size"] = [0.2, 0.2, 0.18]
    for exigencia in ("forma", "proporcion", "exacta"):
        r = revisar(sin_guarda, modelo, exigencia)
        assert {c["parte"] for c in r.criticas} == {"Guarda"}, exigencia
    item = next(i for i in lista_de_revision(r) if i["texto"] == "Guarda")
    assert item["estado"] == "Falta" and "Ctrl + R" in item["consejo"] and "(S, X)" in item["consejo"]


def test_una_punta_cuadrada_no_se_afila(piezas, modelo):
    cuadrada = copy.deepcopy(piezas)
    cuadrada[4]["primitive"] = "cube"
    r = revisar(cuadrada, modelo)
    assert [c["tipo"] for c in r.criticas] == ["afilar"]
    assert estado(r, "Punta") == "No se afila" and estado(r, "Hoja") == "Bien"


def test_al_reves_o_acostada_sigue_siendo_espada(piezas, modelo):
    al_reves = copy.deepcopy(piezas)
    for p in al_reves:
        p["location"][2] = -p["location"][2]
        p["rotation"] = [180, 0, 0]
    r = revisar(al_reves, modelo)
    assert r.invertida and not r.criticas and not r.fuera
    acostada = copy.deepcopy(piezas)
    for p in acostada:
        p["location"] = [p["location"][2], 0, 0]
        p["rotation"] = [0, 90, 0]
    r = revisar(acostada, modelo)
    assert not r.criticas and not r.fuera and r.ejes["largo"] == "X"


def test_sin_pomo_pasa_y_se_sugiere_como_detalle(piezas, modelo):
    r = revisar([p for p in piezas if p["name"] != "Pomo"], modelo)
    assert not r.criticas and not r.fuera
    item = next(i for i in lista_de_revision(r) if i["texto"] == "Pomo")
    assert item["ok"] and item["estado"] == "Detalle" and "sobresale" in item["consejo"]


def test_la_exigencia_sube_con_el_nivel(piezas, modelo):
    corta = copy.deepcopy(piezas)
    corta[3]["size"][2] = 1.3  # hoja a la mitad
    corta[3]["location"][2] = 1.82
    corta[4]["location"][2] = 2.7
    assert not revisar(corta, modelo, "forma").fuera
    r = revisar(corta, modelo, "exacta")
    assert any(f["parte"] == "Hoja" and f["problema"] == "largo" for f in r.fuera)
    assert "más corta" in next(i["consejo"] for i in lista_de_revision(r) if i["texto"] == "Hoja")


def test_es_rapida_para_revisar_en_vivo(piezas, modelo):
    alumno = silueta_de_piezas(piezas)
    inicio = time.perf_counter()
    for _ in range(5):
        comparar_siluetas(alumno, *modelo, "proporcion")
    assert (time.perf_counter() - inicio) / 5 < 0.06


# --- El validador y la práctica ----------------------------------------------------------


def objetivo(piezas, nivel=2):
    return TargetDefinition(id="silueta", validator="figure.silhouette",
                            params={"type": "MESH", "parts": piezas, "level": nivel, "title": "Espada low-poly"})


def escena_con(silueta):
    return SceneState("5.0.1", "", False, objects=(SceneObject("Espada", "MESH", dimensions=(1, 1, 4), vertices=40, faces=38,
                                           silhouette=silueta),))


def test_el_validador_da_la_lista_del_instructor(piezas):
    r = silhouette(objetivo(piezas), escena_con(silueta_de_piezas(piezas)))
    assert r.passed and "Amatista reconoce tu figura" in r.message
    assert [i["texto"] for i in r.details["checklist"]] == ["Pomo", "Mango", "Guarda", "Hoja", "Punta"]


def test_sin_malla_pide_un_cubo(piezas):
    r = silhouette(objetivo(piezas), SceneState("5.0.1", "", False, objects=()))
    assert not r.passed and "Shift + A" in r.message and len(r.details["checklist"]) == 5


def test_una_foto_vieja_sin_silueta_no_bloquea(piezas):
    r = silhouette(objetivo(piezas), escena_con(None))
    assert r.passed and r.details["no_silhouette"]


def test_en_el_nivel_5_cuenta_el_tamano(piezas):
    grande = [{**p, "size": [m * 2 for m in p["size"]], "location": [m * 2 for m in p["location"]]} for p in piezas]
    r = silhouette(objetivo(piezas, nivel=5), escena_con(silueta_de_piezas(grande)))
    assert not r.passed and "redúcela" in r.message
    assert silhouette(objetivo(piezas, nivel=2), escena_con(silueta_de_piezas(grande))).passed


def test_la_silueta_viaja_en_la_foto(piezas):
    escena = escena_con(silueta_de_piezas(piezas))
    llegada = scene_from_dict(json.loads(json.dumps(scene_to_dict(escena)))).objects[0].silhouette
    assert llegada.eje == 2 and len(llegada.anchos) == 32
    assert scene_from_dict({"objetos": [{"n": "x", "si": {"e": 7, "l": 1, "w": [[1, 1]] * 8}}]}).objects[0].silhouette is None
    assert scene_from_dict({"objetos": [{"n": "x", "si": {"e": 2, "l": 1, "w": "nada"}}]}).objects[0].silhouette is None


def test_la_practica_de_la_espada_sigue_una_ruta(practica):
    assert [t.id for t in practica.targets] == ["malla", "alargar", "silueta", "low-poly", "guardar"]
    assert not practica.roles  # nada de «asígnale el rol»: se modela
    motor = create_default_engine()
    hecha = Escena().referencia(practica.reference.parts, vertices=48, caras=46).guardado("mi_espada.blend").construir()
    assert motor.evaluate(practica, hecha).completed
    barra = Escena().referencia(practica.reference.parts, cambiar={"Guarda": [0.2, 0.7, 1]}, vertices=40).construir()
    reporte = motor.evaluate(practica, barra)
    assert reporte.current_target_id == "silueta" and "Guarda" in reporte.result("silueta").message
