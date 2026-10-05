"""Temática por práctica (amatista_blender/temas.py), sin Blender.

temas.py no importa bpy: se carga directo del archivo para no ejecutar el
__init__ del add-on (que sí lo necesita).
"""
import importlib.util
import json
from pathlib import Path

import pytest

ADDON = Path(__file__).resolve().parents[1]
RAIZ = ADDON.parent


def _cargar_modulo():
    spec = importlib.util.spec_from_file_location("amatista_temas", ADDON / "amatista_blender" / "temas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


temas = _cargar_modulo()
JSON = json.loads((RAIZ / "practices" / "blender" / "temas.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _limpio():
    temas.cargar(recargar=True)
    temas.ESTADO["extra"] = 0
    yield
    temas.cargar(recargar=True)


def test_en_el_repositorio_lee_practices_blender():
    assert temas.ruta_temas() == RAIZ / "practices" / "blender" / "temas.json"
    assert temas.cargar()["temas"].keys() == JSON["temas"].keys()


def test_paquete_construido_lee_practicas_temas(tmp_path):
    (tmp_path / "temas.json").write_text(json.dumps(JSON), encoding="utf-8")
    assert temas.ruta_temas(tmp_path) == tmp_path / "temas.json"


def test_tema_del_tren_es_el_taller():
    t = temas.tema_de_practica("blender.bp.m1.tren")
    assert t["id"] == "taller"
    assert t["nombre"] == "El taller de juguetes"
    assert t["mascota"]["nombre"] == "Tuerca"
    assert t["jefe"]["nombre"]
    assert temas.tema_de_practica("blender.bp.m1.explora")["id"] == "taller"


@pytest.mark.parametrize("prefijo, esperado", sorted(JSON["practicas"].items()))
def test_cada_prefijo_lleva_a_su_tema(prefijo, esperado):
    assert temas.tema_de_practica(prefijo + ".lo-que-sea")["id"] == esperado


def test_prefijo_exacto_y_no_parcial():
    # «blender.bp.m10» no es del módulo 1.
    assert temas.id_tema("blender.bp.m10.algo") == temas.TEMA_POR_DEFECTO
    assert temas.id_tema("blender.bp.m1") == "taller"


def test_modulo_de_la_plataforma():
    assert temas.id_tema("mod_bpi_002") == "cine"


@pytest.mark.parametrize("pid", ["blender.n1.mesa", "", None, "otra.cosa"])
def test_sin_tema_usa_el_cristal(pid):
    t = temas.tema_de_practica(pid)
    assert t["id"] == "cristal"
    assert t["mascota"]["nombre"] == "Ami"


def test_sin_archivo_hay_respaldo(tmp_path):
    temas.cargar(tmp_path / "no-existe.json", recargar=True)
    t = temas.tema_de_practica("blender.bp.m1.tren")
    assert t["id"] == "cristal" and t["colores"]["acento"].startswith("#")
    assert temas.mensaje_mascota(t, 0)[0] == "hola"


def test_cada_tema_tiene_lo_necesario_y_su_mascota_en_pixeles():
    for tid in JSON["temas"]:
        t = temas.tema(tid)
        for clave in ("acento", "suave", "cielo", "suelo"):
            assert len(temas.hex_a_rgb(t["colores"][clave])) == 3
        assert t["mascota"]["nombre"] and t["jefe"]["nombre"]
        dibujo = temas.pixeles(tid)
        assert tid in temas.PIXELES
        assert len(dibujo) == 10 and all(len(f) == 10 and set(f) <= set("asow.") for f in dibujo)


def test_colores():
    assert temas.color_rgba("#FF0000") == (1.0, 0.0, 0.0, 1.0)
    assert temas.color_rgba("#F00", 0.5) == (1.0, 0.0, 0.0, 0.5)
    r, g, b, a = temas.color_rgba("#808080", lineal=True)
    assert abs(r - 0.2158) < 0.001 and r == g == b and a == 1.0
    assert temas.color_rgba("raro") == (0.5, 0.5, 0.5, 1.0)
    assert temas.mezclar((0, 0, 0, 1), (1, 1, 1, 1), 0.5) == (0.5, 0.5, 0.5, 1.0)


def test_mensajes_de_la_mascota_dan_la_vuelta():
    t = temas.tema("taller")
    lista = temas.mensajes_mascota(t)
    m = t["mascota"]
    assert lista[0] == ("hola", m["hola"])
    assert lista[1] == ("consejo", m["consejos"][0]) and lista[2] == ("dato", m["datos"][0])
    assert len(lista) == 1 + len(m["consejos"]) + len(m["datos"])
    assert temas.mensaje_mascota(t, len(lista)) == lista[0]
    assert temas.mensaje_mascota(t, 3) == temas.mensaje_mascota(t, 3)


def test_indice_cambia_cada_periodo_y_se_adelanta():
    assert temas.indice_actual(0) == temas.indice_actual(11.9)
    assert temas.indice_actual(12.0) == temas.indice_actual(0) + 1
    temas.siguiente_mensaje()
    assert temas.indice_actual(0) == 1


def test_voz_de_la_mascota():
    assert temas.voz(temas.tema("taller"), "Listo.") == "Tuerca: Listo."
    assert temas.voz({}, "Listo.") == "Listo."
