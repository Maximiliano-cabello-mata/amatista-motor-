"""Palabras de Blender (amatista_blender/palabras.py y practices/blender/palabras.json), sin Blender.

palabras.py solo usa temas.py y los términos del motor: se carga dentro de un paquete de prueba
para no ejecutar el __init__ del add-on (que necesita bpy).
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

ADDON = Path(__file__).resolve().parents[1]
RAIZ = ADDON.parent
sys.path.insert(0, str(RAIZ / "engine"))
from amatista_engine import terminos  # noqa: E402


def _cargar(nombre, paquete):
    spec = importlib.util.spec_from_file_location(f"{paquete.__name__}.{nombre}", ADDON / "amatista_blender" / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    setattr(paquete, nombre, modulo)
    spec.loader.exec_module(modulo)
    return modulo


paquete = types.ModuleType("amatista_prueba_palabras")
paquete.__path__ = []
sys.modules[paquete.__name__] = paquete
paquete._motor = types.SimpleNamespace(terminos=terminos)
sys.modules[f"{paquete.__name__}._motor"] = paquete._motor
_cargar("temas", paquete)
palabras = _cargar("palabras", paquete)
JSON = json.loads((RAIZ / "practices" / "blender" / "palabras.json").read_text(encoding="utf-8"))


def test_el_glosario_es_corto_simple_y_sin_repetidos():
    lista = JSON["palabras"]
    assert 10 <= len(lista) <= 25
    assert len({p["id"] for p in lista}) == len(lista)
    for p in lista:
        assert p["termino"] and p["ingles"] and p["que_es"], p["id"]
        assert len(p["que_es"]) <= 140, p["id"]


def test_el_add_on_lo_encuentra_en_el_repositorio():
    assert [p["id"] for p in palabras.cargar(recargar=True)] == [p["id"] for p in JSON["palabras"]]


def test_con_blender_en_ingles_muestra_el_nombre_de_sus_menus():
    malla = next(p for p in JSON["palabras"] if p["id"] == "malla")
    assert palabras.titulo(malla, "es") == "Malla"
    assert palabras.titulo(malla, "en") == "Malla · Mesh"
    assert "Add (Agregar) › Mesh (Malla)" in palabras.detalle(malla, "en")
    assert "Agregar › Malla" in palabras.detalle(malla, "es")
    render = next(p for p in JSON["palabras"] if p["id"] == "render")
    assert palabras.titulo(render, "en") == "Render"
