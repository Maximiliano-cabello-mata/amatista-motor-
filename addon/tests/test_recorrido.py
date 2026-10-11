"""«Conoce Amatista Motor» (amatista_blender/recorrido_pasos.py), sin Blender.

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
COMPROBACIONES = {"ninguna", "barra", "cuenta", "orbitar", "acercar", "elegir", "mover", "girar", "escalar"}
USOS = {"plataforma", "guardar", "herramienta", "ayuda", "enfoque"}  # recorrido.anotar() en los operadores


def test_tres_practicas_en_orden_con_paradas_de_id_unico():
    assert pasos.ORDEN == ("pestana", "vista", "taller")
    for rid in pasos.ORDEN:
        ids = [p["id"] for p in pasos.pasos_de(rid)]
        assert 6 <= len(ids) <= 12, rid  # el servidor acepta hasta 12 paradas
        assert len(set(ids)) == len(ids), rid
        assert ids[-1] == "listo", rid


def test_cada_parada_dice_que_hacer_y_cabe_en_el_servidor():
    for rid in pasos.ORDEN:
        assert len(pasos.RECORRIDOS[rid]["nombre"]) <= 60
        for p in pasos.pasos_de(rid):
            comprobar = p["comprobar"]
            assert comprobar in COMPROBACIONES or (comprobar.startswith("uso:") and comprobar[4:] in USOS), p["id"]
            assert p["titulo"] and len(p["titulo"]) <= 60
            assert p["texto"] and len(p["texto"]) <= 300
            assert p["hacer"] and len(p["hacer"]) <= 160
            assert len(p["teclas"]) <= 6


def test_entre_las_tres_explican_todas_las_herramientas_del_addon():
    temas = {p["id"] for rid in pasos.ORDEN for p in pasos.pasos_de(rid)}
    for tema in ("barra", "cuenta", "plataforma", "leccion", "ajustes", "guardar", "orbitar", "acercar", "elegir",
                 "mover", "girar", "escalar", "herramientas", "ayuda", "enfoque", "ciclo", "tarjeta", "mira", "molde",
                 "comprobar", "pistas", "pausa", "isla", "enlace"):
        assert tema in temas, tema


def test_mover_no_se_sale():
    assert pasos.mover("vista", 0, -1) == 0
    assert pasos.mover("vista", pasos.ultimo("vista"), 1) == pasos.ultimo("vista")
    assert pasos.mover("vista", 3, 1) == 4
    assert pasos.valido("otra") == "pestana" and pasos.siguiente_de("pestana") == "vista"
    assert pasos.siguiente_de("taller") is None


def test_las_paradas_que_se_comprueban_esperan_a_estar_hechas():
    indice = {p["id"]: i for i, p in enumerate(pasos.pasos_de("vista"))}
    assert not pasos.puede_seguir("vista", indice["mover"], set())
    assert pasos.puede_seguir("vista", indice["mover"], {"mover"})
    assert not pasos.puede_seguir("vista", indice["herramientas"], set())
    indice = {p["id"]: i for i, p in enumerate(pasos.pasos_de("pestana"))}
    assert pasos.puede_seguir("pestana", indice["hola"], set())
    # La cuenta es opcional: se puede vincular después.
    assert pasos.puede_seguir("pestana", indice["cuenta"], set())


def test_hechos_se_guardan_en_orden():
    assert pasos.leer_hechos("taller, pestana,nada") == ["pestana", "taller"]
    assert pasos.escribir_hechos({"vista", "pestana"}) == "pestana,vista"
    assert pasos.leer_hechos("") == []


def test_estado_publico_para_el_latido():
    estado = pasos.estado_publico("pestana", 4, {"barra", "plataforma"}, activo=True, hechos=[])
    assert estado["id"] == "pestana" and estado["nombre"] == "Tu pestaña Amatista"
    assert estado["activo"] and not estado["hecho"] and estado["hechos"] == []
    assert (estado["paso"], estado["total"]) == (4, 8)
    assert estado["titulo"] == pasos.pasos_de("pestana")[4]["titulo"]
    ok = [p["ok"] for p in estado["pasos"]]
    assert ok[0] is True  # «hola» ya pasó y solo explicaba
    assert ok[1] is True and ok[3] is True  # comprobadas
    assert ok[2] is False  # la cuenta sin vincular
    assert not any(ok[4:])
    assert len(estado["pasos"]) <= 12


def test_terminada_marca_todo():
    estado = pasos.estado_publico("vista", 99, set(), activo=False, hechos=["pestana", "vista"])
    assert estado["hecho"] and estado["hechos"] == ["pestana", "vista"]
    assert estado["paso"] == pasos.ultimo("vista")
    assert all(p["ok"] for p in estado["pasos"])
