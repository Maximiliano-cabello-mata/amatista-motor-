"""Fichas de herramientas para novatos (motor 6.1, engine/amatista_engine/taller/fichas.py)."""
import json
from pathlib import Path

from amatista_engine.taller import fichas as F
from amatista_engine.taller import cargar_catalogo
from amatista_engine.taller.modelo import ACOMPANADA, DOMINADA, NUEVA, SOLA
from amatista_engine.tools.registry import ToolRegistry

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO = RAIZ / "practices" / "blender" / "fichas.json"
DATOS = json.loads(ARCHIVO.read_text(encoding="utf-8"))
FICHAS = F.cargar_fichas()


def test_el_archivo_es_valido_y_usa_ids_del_catalogo():
    validas = [t.id for t in ToolRegistry.default().all()]
    assert F.revisar(DATOS, validas) == []


def test_cada_herramienta_de_un_taller_tiene_ficha():
    catalogo = cargar_catalogo(json.loads((RAIZ / "practices" / "blender" / "habilidades.json").read_text(encoding="utf-8")))
    faltan = {hid for t in catalogo.talleres for h in t.habilidades
              for hid in catalogo.habilidad(h).herramientas if hid not in FICHAS}
    assert faltan == set()


def test_cada_ficha_vive_en_una_zona_de_blender():
    for fid in FICHAS.ids():
        zona = FICHAS.zona_de(fid)
        assert zona is not None and zona.que_es, fid


def test_reconoce_lo_que_el_alumno_toca_en_blender():
    assert FICHAS.por_blender("builtin.scale").id == "transform.scale"
    assert FICHAS.por_blender("TRANSFORM_OT_translate").id == "transform.move"
    assert FICHAS.por_blender("OBJECT_OT_modifier_add", "MIRROR").id == "modifier.mirror"
    assert FICHAS.por_blender("OBJECT_OT_modifier_add", "ARRAY").id == "modifier.array"
    assert FICHAS.por_blender("OBJECT_OT_modifier_add", "OCEAN") is None
    assert FICHAS.por_blender("") is None


def test_el_andamio_se_retira_con_el_uso():
    assert F.andamio(0) == F.PRESENTAR
    assert F.andamio(1, fase=NUEVA) == F.RECORDAR
    assert F.andamio(2, fase=ACOMPANADA) == F.RECORDAR
    assert F.andamio(1, fase=SOLA) == F.NADA  # ya le sale: no se le recuerda
    assert F.andamio(F.VECES_RECORDAR, fase=NUEVA) == F.NADA
    assert F.andamio(0, conocida=True) == F.NADA  # «Ya la conozco»
    assert F.andamio(0, fase=DOMINADA) == F.PRESENTAR  # nunca la vio: se presenta igual


def test_presenta_solo_las_nuevas_y_pocas():
    herramientas = ["mesh.edit", "mesh.extrude", "select.box", "transform.move"]
    assert F.por_presentar(FICHAS, herramientas, {}) == ["mesh.edit", "mesh.extrude"]
    assert F.por_presentar(FICHAS, herramientas, {"mesh.edit": 1}) == ["mesh.extrude", "select.box"]
    assert F.por_presentar(FICHAS, herramientas, {"mesh.edit": 1}, conocidas=["mesh.extrude"]) == \
        ["select.box", "transform.move"]
    todas = {h: 5 for h in herramientas}
    assert F.por_presentar(FICHAS, herramientas, todas) == []
    assert F.por_presentar(FICHAS, ["no.existe"], {}) == []


def test_recordatorio_en_una_linea():
    linea = F.recordatorio(FICHAS, ["transform.scale"], {"transform.scale": 1})
    assert linea.startswith("Escalar (S): ")
    assert F.recordatorio(FICHAS, ["transform.scale"], {"transform.scale": 9}) == ""


def test_modo_curioso():
    assert F.curioso_activo("auto", 0)
    assert not F.curioso_activo("auto", F.HABILIDADES_PRINCIPIANTE)
    assert F.curioso_activo("siempre", 500)
    assert not F.curioso_activo("nunca", 0)
    assert F.explicar_curioso(FICHAS, "builtin.rotate", "", {}).id == "transform.rotate"
    assert F.explicar_curioso(FICHAS, "builtin.rotate", "", {"transform.rotate": F.VECES_CURIOSO}) is None
    assert F.explicar_curioso(FICHAS, "builtin.rotate", "", {}, conocidas=["transform.rotate"]) is None


def test_lectura_tolerante():
    assert len(F.leer_fichas(None)) == 0
    assert len(F.leer_fichas({"fichas": [{"id": "x"}, "nada", {"id": "y", "nombre": "Y"}]})) == 1
    assert len(F.cargar_fichas(RAIZ / "no-existe.json")) == 0
    assert F.revisar({"schema": "otra"}) != []
    malo = {"schema": F.SCHEMA, "zonas": [], "fichas": [{"id": "a", "nombre": "A", "como": ["uno"]}]}
    errores = F.revisar(malo)
    assert any("zona" in e for e in errores) and any("como" in e for e in errores)
