"""Los primeros pasos en Blender (amatista_blender/recorrido_pasos.py), sin Blender.

recorrido_pasos.py no importa bpy: se carga directo del archivo para no ejecutar
el __init__ del add-on. Lo que manda al latido debe caber en
backend/api/enlace.py › RecorridoVivo.
"""
import importlib.util
from pathlib import Path

ADDON = Path(__file__).resolve().parents[1]


def _cargar_modulo():
    spec = importlib.util.spec_from_file_location(
        "amatista_recorrido_pasos", ADDON / "amatista_blender" / "recorrido_pasos.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


pasos = _cargar_modulo()
COMPROBACIONES = {"ninguna", "barra", "cuenta", "orbitar", "elegir", "mover"}


def test_diez_paradas_con_id_unico():
    ids = [p["id"] for p in pasos.PASOS]
    assert pasos.TOTAL == len(ids) == 10
    assert len(set(ids)) == len(ids)
    assert ids[0] == "hola" and ids[-1] == "listo"


def test_cada_parada_dice_que_hacer_y_cabe_en_el_servidor():
    for p in pasos.PASOS:
        assert p["comprobar"] in COMPROBACIONES, p["id"]
        assert p["titulo"] and len(p["titulo"]) <= 60
        assert p["texto"] and len(p["texto"]) <= 300
        assert p["hacer"] and len(p["hacer"]) <= 160
        assert len(p["teclas"]) <= 6


def test_mover_no_se_sale():
    assert pasos.mover(0, -1) == 0
    assert pasos.mover(pasos.ULTIMO, 1) == pasos.ULTIMO
    assert pasos.mover(3, 1) == 4


def test_las_paradas_que_se_comprueban_esperan_a_estar_hechas():
    indice = {p["id"]: i for i, p in enumerate(pasos.PASOS)}
    assert pasos.puede_seguir(indice["hola"], set())
    assert not pasos.puede_seguir(indice["mover"], set())
    assert pasos.puede_seguir(indice["mover"], {"mover"})
    # La cuenta es opcional: se puede vincular después.
    assert pasos.puede_seguir(indice["cuenta"], set())


def test_estado_publico_para_el_latido():
    estado = pasos.estado_publico(4, {"barra", "orbitar"}, activo=True, hecho=False)
    assert estado["activo"] and not estado["hecho"]
    assert (estado["paso"], estado["total"]) == (4, 10)
    assert estado["titulo"] == pasos.PASOS[4]["titulo"]
    ok = [p["ok"] for p in estado["pasos"]]
    assert ok[0] is True  # «hola» ya pasó y solo explicaba
    assert ok[1] is True and ok[3] is True  # comprobadas
    assert ok[2] is False  # la cuenta sin vincular
    assert not any(ok[4:])
    assert len(estado["pasos"]) <= 12


def test_terminado_marca_todo():
    estado = pasos.estado_publico(99, set(), activo=False, hecho=True)
    assert estado["paso"] == pasos.ULTIMO
    assert all(p["ok"] for p in estado["pasos"])
