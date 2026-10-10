"""El catálogo completo del taller (motor 5): las 33 habilidades y los 9 talleres de practices/blender/habilidades.json.

Cada variación, reto y repaso trae su «solucion» (o su molde, que ya es la
solución): aquí se arma esa escena con el constructor de pruebas y se
comprueba que la práctica generada la da por lograda, que la escena de
inicio NO (nada se logra sin hacer nada) y que el molde la reconoce pieza
por pieza. Así un error de contenido sale aquí y no frente al alumno.
"""
import json

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import CURSOS, PRACTICAS
from amatista_engine.curriculum import load_curriculum
from amatista_engine.practice import compile_practice
from amatista_engine.taller import (
    CONMIGO,
    NUEVA,
    TU,
    actividad_de_prueba,
    actividad_de_repaso,
    actividad_de_reto_final,
    leer_catalogo,
    linea_de_tiempo,
    practica_de_actividad,
    revisar_molde,
)
from amatista_engine.taller.actividades import actividad_de_habilidad
from amatista_engine.taller.demo import MAXIMO
from amatista_engine.testing import Escena, escena_desde_pasos

CRUDO = json.loads((PRACTICAS / "habilidades.json").read_text(encoding="utf-8"))
CATALOGO = leer_catalogo(PRACTICAS / "habilidades.json")
MODULOS = PRACTICAS.parents[1] / "frontend" / "src" / "data" / "modulos"
CRUDAS = {h["id"]: h for h in CRUDO["habilidades"]}


def _taller_de(hid):
    return next(t for t in CATALOGO.talleres if hid in t.habilidades)


def _casos():
    """(nombre, actividad, datos crudos con «solucion» o molde) de cada variación, reto y repaso."""
    for h in CATALOGO.habilidades.values():
        t = _taller_de(h.id)
        cruda = CRUDAS[h.id]
        for i, v in enumerate(cruda["variaciones"]):
            for tipo in (CONMIGO, TU):
                yield f"{h.id}:{v['id']}:{tipo}", actividad_de_habilidad(t, h, tipo, NUEVA, i), v
        if cruda.get("reto"):
            yield f"{h.id}:reto", actividad_de_prueba(CATALOGO, t.id, h.id), cruda["reto"]
        if cruda.get("repaso"):
            yield f"{h.id}:repaso", actividad_de_repaso(CATALOGO, t.id, h.id), cruda["repaso"]
    for t, cruda in zip(CATALOGO.talleres, CRUDO["talleres"]):
        if cruda.get("reto"):
            yield f"{t.id}:reto", actividad_de_reto_final(t), cruda["reto"]


CASOS = list(_casos())


def _inicio(datos):
    """La escena de inicio que arma el add-on (taller/escena.py), con el constructor de pruebas."""
    e = Escena()
    for o in (datos.get("inicio") or {}).get("objetos") or ():
        if o.get("tipo") == "luz":
            e.luz(o.get("name", "Luz"), o.get("light_type", "AREA"), o.get("location"), mira_a=o.get("mira"))
        elif o.get("tipo") == "camara":
            e.camara(o.get("name", "Camara"), o.get("location"), o.get("mira") or (0, 0, 0))
        else:
            mitad = ""
            if o.get("origen") is not None:
                mitad = "x+" if o["location"][0] > o["origen"][0] else "x-"
            e.malla(o["primitive"], o.get("name", ""), dims=o["size"], loc=o["location"], rot=o.get("rotation"),
                    escala=o["size"] if o.get("escalada") else None, encimados=8 if o.get("duplicada") else 0,
                    mitad=mitad)
    return e.construir()


def _solucion(datos, piezas):
    if "solucion" in datos:
        return escena_desde_pasos(datos["solucion"])
    e = Escena()
    for p in piezas:
        e.malla(p["primitive"], p.get("name", ""), dims=p["size"], loc=p.get("location"), rot=p.get("rotation"))
    return e.construir()


@pytest.fixture(scope="module")
def motor():
    return create_default_engine()


def test_nueve_talleres_uno_por_modulo_del_plan():
    plan = load_curriculum(json.loads(CURSOS.read_text(encoding="utf-8")))
    modulos = [(c.id, m.number, m.practice, m.taller) for c in plan.courses for m in c.modules]
    assert len(CATALOGO.talleres) == len(modulos) == 9
    for curso, numero, practica, taller_id in modulos:
        t = CATALOGO.taller(taller_id)
        assert t is not None and (t.curso, t.modulo, t.proyecto) == (curso, numero, practica), taller_id
        assert (PRACTICAS / "habilidades.json").exists()


def test_cada_habilidad_esta_en_un_solo_taller():
    vistas = [h for t in CATALOGO.talleres for h in t.habilidades]
    assert sorted(vistas) == sorted(CATALOGO.habilidades), "una habilidad sin taller o en dos talleres"


def test_los_repasos_vienen_de_talleres_anteriores():
    orden = [t.id for t in CATALOGO.talleres]
    for t in CATALOGO.talleres:
        for hid in t.repasa:
            assert orden.index(_taller_de(hid).id) < orden.index(t.id), f"{t.id} repasa {hid}, que viene después"


def test_cada_leccion_de_la_plataforma_tiene_su_taller():
    talleres = {t.id: t for t in CATALOGO.talleres}
    vistos = set()
    for archivo in sorted(MODULOS.glob("blender_*.json")):
        modulo = json.loads(archivo.read_text(encoding="utf-8"))["module"]
        for leccion in modulo["lessons"]:
            for bloque in leccion.get("contentBlocks", []):
                if bloque.get("type") == "blender_taller":
                    assert bloque["taller"] in talleres, f"{archivo.name}: {bloque['taller']}"
                    if bloque.get("vista") != "proyecto":
                        assert talleres[bloque["taller"]].leccion == leccion["id"], archivo.name
                    vistos.add(bloque["taller"])
    assert vistos == set(talleres), f"talleres sin lección: {set(talleres) - vistos}"


@pytest.mark.parametrize("hid", sorted(CATALOGO.habilidades))
def test_la_demostracion_cabe_en_24_segundos(hid):
    h = CATALOGO.habilidad(hid)
    linea = linea_de_tiempo(h.demo, h.titulo)
    assert linea.pasos and linea.duracion <= MAXIMO


@pytest.mark.parametrize("nombre,actividad,datos", CASOS, ids=[c[0] for c in CASOS])
def test_la_solucion_se_logra_y_el_inicio_no(nombre, actividad, datos, motor):
    assert actividad is not None, nombre
    practica_datos = practica_de_actividad(CATALOGO, actividad)
    assert practica_datos is not None, nombre
    resultado = compile_practice(practica_datos, motor.registry, motor.tools)
    assert resultado.ok, resultado.errors
    # Las pistas y la teoría de una actividad las pone el taller (escalera de pistas y la frase «que»).
    avisos = [w for w in resultado.warnings if "sin pistas" not in w and "píldoras" not in w]
    assert not avisos, avisos
    practica = resultado.practice
    piezas = list(actividad.piezas)
    assert piezas or "solucion" in datos, f"{nombre}: sin molde necesita «solucion»"

    solucion = _solucion(datos, piezas)
    reporte = motor.evaluate(practica, solucion)
    assert reporte.completed, [(r.target_id, r.message) for r in reporte.results if not r.passed]
    if piezas:
        revision = revisar_molde(piezas, solucion, actividad.modo, actividad.nivel)
        assert revision.completa, revision.mensaje

    inicio = _inicio(datos)
    assert not motor.evaluate(practica, inicio).completed, f"{nombre}: la escena de inicio ya estaba lograda"
