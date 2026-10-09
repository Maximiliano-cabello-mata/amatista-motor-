"""Motor 3.4, modo enfocado: cada práctica muestra solo sus herramientas, con «¿Cómo se usa?»."""
import json

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.practice.loader import parse_practice
from amatista_engine.tools import ToolRegistry

ACCIONES = {"tool", "operator", "menu", "panel", "tab"}


@pytest.fixture(scope="module")
def herramientas():
    return ToolRegistry.default()


def practicas():
    for ruta in sorted(PRACTICAS.glob("**/practica.json")):
        yield ruta.parent.name, parse_practice(json.loads(ruta.read_text(encoding="utf-8")))


@pytest.mark.parametrize("nombre,practica", list(practicas()))
def test_cada_herramienta_de_una_practica_se_explica(herramientas, nombre, practica):
    for tool in herramientas.for_practice(practica):
        assert tool.howto and len(tool.howto) >= 2, (nombre, tool.id)
        assert tool.mistake, (nombre, tool.id)
        assert set(tool.action) & ACCIONES, (nombre, tool.id)
    assert [t.id for t in herramientas.for_practice(practica)] == [
        i for i in practica.allowed_tools if i in herramientas]


def test_herramientas_del_paso_por_teclas_y_por_texto(herramientas):
    practica = parse_practice(json.loads((PRACTICAS / "principiante/m1-tren/practica.json").read_text(encoding="utf-8")))
    assert [t.id for t in herramientas.for_step(practica, [("S", "X")])] == ["transform.scale"]
    assert [t.id for t in herramientas.for_step(practica, [("Shift", "D")])] == ["object.duplicate"]
    assert [t.id for t in herramientas.for_step(practica, text="Shift+A › Malla › Cubo y luego G")] == [
        "object.add", "transform.move"]
    # «1.6» es un número que se escribe, no la vista de frente; y la D de Shift+D no es otra tecla.
    assert herramientas.for_step(practica, text="Escribe 1.6 y Enter") == ()
    assert herramientas.for_step(practica, [("Clic",)]) == ()


def test_la_herramienta_se_puede_mandar_a_la_plataforma(herramientas):
    datos = herramientas.get("transform.move").as_dict()
    assert datos["keys"] == ["G"] and datos["action"] == {"tool": "builtin.move"} and datos["howto"]
    json.dumps(datos)


def test_el_motor_trae_el_catalogo_completo():
    assert create_default_engine().tools.get("object.add").action == {"menu": "VIEW3D_MT_add"}
