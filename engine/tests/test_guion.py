"""Motor 7 · Guion: los pasos de cada proyecto, el avance por resultado y pistas que no mienten."""
import re
from pathlib import Path

import pytest

from amatista_engine import create_default_engine, guion
from amatista_engine.cli import PRACTICAS
from amatista_engine.guion import donde
from amatista_engine.models import ValidationResult
from amatista_engine.practice import load_practice

PROYECTOS = sorted(PRACTICAS.rglob("practica.json"))
TREN = PRACTICAS / "principiante" / "m1-tren" / "practica.json"
from amatista_engine.guion.pasos import DICE_QUE_HACER as VERBO


class _Reporte:
    def __init__(self, pasados, completo=False, mensajes=None):
        mensajes = mensajes or {}
        self.results = tuple(ValidationResult(t, "x", t in pasados, mensajes.get(t, f"falta {t}")) for t in ALL)
        self.completed = completo
        self.paused_by = None
        self.guards = ()


ALL = ()


@pytest.fixture(scope="module")
def tren():
    return load_practice(TREN)


def test_el_tren_tiene_un_paso_por_objetivo_en_orden(tren):
    g = guion.guion_de_practica(tren)
    ids = [p.id for p in g.pasos]
    assert ids[0] == "vagones" and ids[-1] == "guardar" and "guardado" not in ids  # opcional: no es un paso
    for p in g.pasos:
        t = next(x for x in tren.targets if x.id == p.id)
        for r in t.requires:
            assert ids.index(r) < ids.index(p.id), f"{p.id} va antes de {r}"


def test_cada_paso_de_cada_proyecto_dice_que_hacer(tren):
    for ruta in PROYECTOS:
        g = guion.guion_de_practica(load_practice(ruta))
        assert g.pasos, ruta
        for p in g.pasos:
            assert VERBO.search(p.haz), f"{ruta.parent.name}/{p.id}: «{p.haz}» no dice qué hacer"
            assert not re.search(r"\bbrilla\b", p.haz, re.I)


def test_cada_herramienta_de_un_paso_tiene_lugar_real():
    for ruta in PROYECTOS:
        for p in guion.guion_de_practica(load_practice(ruta)).pasos:
            if p.herramienta:
                assert donde.de(p.herramienta) is not None, f"{ruta.parent.name}/{p.id}: {p.herramienta} sin lugar"


def test_ninguna_frase_de_lugar_dice_que_algo_brilla():
    for d in donde.todas():
        texto = donde.frase(d, "es") + donde.frase(d, "en")
        assert not re.search(r"brilla|ilumina|resalta", texto, re.I), d.herramienta
    assert "izquierda" not in donde.frase(donde.de("object.add"))  # Agregar es un menú de la cabecera
    assert "arriba de todo" in donde.frase(donde.de("file.save"))
    assert "Add (Agregar) › Mesh (Malla) › Cylinder (Cilindro)" in donde.frase(donde.de("object.add"), "en", "cylinder")


def test_avanza_por_el_resultado_en_cualquier_orden(tren):
    global ALL
    g = guion.guion_de_practica(tren)
    ALL = tuple(p.id for p in g.pasos)
    a = guion.avanzar(g, _Reporte(set()))
    assert a.actual == "vagones" and a.hechos == 0 and not a.completo
    # El alumno hizo las ruedas y la chimenea antes de estirar los vagones: todo eso cuenta.
    hechos = {"vagones", "ruedas", "ruedas-de-pie", "chimenea"}
    b = guion.avanzar(g, _Reporte(hechos), a)
    assert b.actual == "vagones-largos" and b.hechos == 4 and set(b.recien) == hechos
    assert b.por_que == "falta vagones-largos"  # el mensaje de ESE paso, no de otra pieza
    # Todo menos guardar: el paso que toca es guardar, y la pista habla de guardar.
    casi = set(ALL) - {"guardar"}
    c = guion.avanzar(g, _Reporte(casi), b)
    assert c.actual == "guardar"
    p = guion.pista(g, c, guion.DONDE, "es")
    assert "Archivo › Guardar como" in p.texto and "izquierda" not in p.texto and p.herramienta == "file.save"
    # El reporte completo termina la práctica en ese instante.
    d = guion.avanzar(g, _Reporte(set(ALL), completo=True), c)
    assert d.completo and d.actual is None and d.progreso == 100.0
    # Deshacer una pieza la vuelve a pedir (nada queda «hecho» por recuerdo).
    e = guion.avanzar(g, _Reporte(casi - {"ruedas"}), c)
    assert e.actual == "ruedas" and "ruedas" in e.deshechos


def test_las_pistas_son_del_paso_que_toca(tren):
    g = guion.guion_de_practica(tren)
    a = guion.avanzar(g, _Reporte({"vagones"}, mensajes={"vagones-largos": "«Cube» mide en X 1.1 veces su ancho"}))
    assert guion.pista(g, a, guion.QUE_FALTA).texto.startswith("«Cube» mide")
    assert "Escalar" in guion.pista(g, a, guion.DONDE).texto
    como = guion.pista(g, a, guion.COMO)
    assert "S" in como.texto and "X" in como.texto


def test_el_tren_real_avanza_con_el_motor(tren):
    from amatista_engine.testing import Escena

    motor = create_default_engine()
    g = guion.guion_de_practica(tren)
    a = guion.avanzar(g, motor.evaluate(tren, Escena().construir()))
    assert a.actual == "vagones" and a.hechos == 0


def test_el_tip_de_los_vagones_dice_lo_que_se_revisa(tren):
    t = next(x for x in tren.targets if x.id == "vagones-largos")
    assert "ancho" in t.tip  # se compara el largo con el ancho, no con la altura


def test_version():
    assert guion.VERSION.startswith("7.")


def test_todos_los_proyectos_se_cargan():
    assert len(PROYECTOS) == 9 and all(isinstance(p, Path) for p in PROYECTOS)
