"""Motor 3.5: el ejemplo resuelto de cada práctica y la revisión autónoma contra él (ejemplo/)."""
import copy
import json
from pathlib import Path

import pytest

from amatista_engine import create_default_engine
from amatista_engine.ejemplo import ASPECTOS, aspectos_del_ejemplo, describir, escena_esperada, lo_que_pide
from amatista_engine.errors import InvalidPracticeError
from amatista_engine.guide.coach import build_guidance
from amatista_engine.practice import dump_practice, load_practice, parse_practice
from amatista_engine.practice.loader import pieza_como_dict
from amatista_engine.testing import Escena

PRACTICAS = sorted((Path(__file__).resolve().parents[2] / "practices/blender").glob("*/*/practica.json"))
MOTOR = create_default_engine()


def _partes(practica):
    return [pieza_como_dict(p) for p in practica.reference.compared] if practica.reference else []


def practica_simple(pasos, check=None, nivel=2):
    """Una práctica mínima: agregar una malla y el ejemplo."""
    ejemplo = {"title": "Prueba", "steps": pasos}
    if check:
        ejemplo["check"] = check
    return parse_practice({
        "schema": "amatista.practice/2", "id": "prueba.ejemplo", "title": "Prueba", "level": nivel,
        "targets": [{"id": "malla", "title": "Una malla", "validator": "object.exists", "params": {"type": "MESH"},
                     "weight": 10}],
        "example": ejemplo,
    })


def revisar(practica, escena):
    return MOTOR.evaluate(practica, escena).result(practica.targets[-1].id)


def lista(resultado):
    return {i["texto"]: i for i in resultado.details["checklist"]}


# --- Cada práctica tiene su ejemplo y el ejemplo la completa ------------------------------------


@pytest.mark.parametrize("ruta", PRACTICAS, ids=lambda r: f"{r.parent.parent.name}/{r.parent.name}")
def test_el_ejemplo_completa_su_practica(ruta):
    """Lo que propone la plataforma (el ejemplo) es lo que revisa el motor: el ejemplo pasa cada paso."""
    practica = load_practice(ruta)
    assert practica.example is not None, "toda práctica trae su ejemplo resuelto"
    assert practica.targets[-1].validator == "example.matches"
    reporte = MOTOR.evaluate(practica, escena_esperada(practica.example.steps, _partes(practica)))
    fallas = [(r.target_id, r.message) for r in reporte.results if not r.passed]
    assert reporte.completed and not fallas, fallas
    assert reporte.result(practica.targets[-1].id).details["score"] == 1.0


@pytest.mark.parametrize("ruta", PRACTICAS, ids=lambda r: f"{r.parent.parent.name}/{r.parent.name}")
def test_una_escena_vacia_no_coincide(ruta):
    practica = load_practice(ruta)
    r = revisar(practica, Escena().construir())
    assert not r.passed and r.details["checklist"]
    assert all(i["consejo"] for i in r.details["checklist"] if not i["ok"]), "cada punto pendiente dice cómo hacerlo"


@pytest.mark.parametrize("ruta", PRACTICAS, ids=lambda r: f"{r.parent.parent.name}/{r.parent.name}")
def test_el_ejemplo_se_lee_como_instrucciones(ruta):
    practica = load_practice(ruta)
    textos = describir(practica.example.steps, _partes(practica))
    assert len(textos) == len(practica.example.steps)
    assert all(t.endswith(".") and len(t) > 15 for t in textos)


def test_el_objetivo_del_ejemplo_no_se_exporta_y_vuelve_igual():
    practica = load_practice(PRACTICAS[0])
    datos = dump_practice(practica)
    assert "ejemplo" not in [t["id"] for t in datos["targets"]]
    assert datos["example"]["steps"] == list(practica.example.steps)
    otra = parse_practice(json.loads(json.dumps(datos)))
    assert [t.id for t in otra.targets] == [t.id for t in practica.targets]
    assert otra.targets[-1].params == practica.targets[-1].params


def test_un_paso_del_autor_revisa_un_aspecto():
    datos = dump_practice(practica_simple([{"esfera": {"nombre": "Bola"}},
                                           {"material": {"objeto": "Bola", "nombre": "Oro", "metal": 1}}]))
    datos["targets"].append({"id": "metal", "title": "Pinta de metal", "validator": "example.matches",
                             "params": {"aspects": ["materiales"]}, "weight": 10})
    practica = parse_practice(datos)
    assert [t.id for t in practica.targets] == ["malla", "metal", "ejemplo"]  # el de todo se agrega igual
    r = revisar(practica, Escena().esfera("Bola").construir())
    assert [a["id"] for a in MOTOR.evaluate(practica, Escena().esfera("Bola").construir()).result("metal")
            .details["aspects"]] == ["materiales"]
    assert not r.passed


def test_ejemplos_mal_escritos():
    with pytest.raises(InvalidPracticeError, match="paso desconocido"):
        practica_simple([{"volar": {}}])
    with pytest.raises(InvalidPracticeError, match="example.check"):
        practica_simple([{"cubo": {}}], check=["sonido"])
    with pytest.raises(InvalidPracticeError, match="no se puede armar"):
        practica_simple([{"material": {"objeto": "Nadie", "nombre": "x"}}])
    with pytest.raises(InvalidPracticeError, match="«referencia» necesita"):
        practica_simple([{"referencia": {}}])


def test_aspectos_segun_lo_que_tiene_el_ejemplo():
    pasos = [{"cubo": {"nombre": "Caja", "vertices": 20}}, {"modificador": {"objeto": "Caja", "tipo": "BEVEL"}},
             {"luz": {"tipo": "AREA"}}, {"camara": {}}, {"motor": "CYCLES"}, {"renders": 1},
             {"guardado": {"archivo": "mi_caja.blend"}}]
    esperada = escena_esperada(pasos)
    assert aspectos_del_ejemplo(esperada, lo_que_pide(pasos)) == [
        "figura", "malla", "modificadores", "luces", "camara", "render", "archivo"]
    assert set(ASPECTOS) >= set(aspectos_del_ejemplo(esperada, lo_que_pide(pasos)))


# --- Cada aspecto ----------------------------------------------------------------------------


def test_materiales_metal_vidrio_y_que_se_distingan():
    practica = practica_simple([
        {"cubo": {"nombre": "Nave"}},
        {"material": {"objeto": "Nave", "nombre": "Casco", "metal": 1, "rugosidad": 0.2}},
        {"material": {"objeto": "Nave", "nombre": "Cabina", "transmision": 0.95, "rugosidad": 0.05}},
    ], check=["materiales"])
    sin_vidrio = (Escena().cubo("Mi nave").material("Mi nave", "A", metal=1, rugosidad=0.1)
                  .material("Mi nave", "B", rugosidad=0.1).construir())
    r = revisar(practica, sin_vidrio)
    assert not r.passed
    items = lista(r)
    assert items["«Casco»: metálico, pulido"]["ok"]
    assert not items["«Cabina»: vidrio, pulido"]["ok"] and "Transmisión" in items["«Cabina»: vidrio, pulido"]["consejo"]
    bien = (Escena().cubo("Mi nave").material("Mi nave", "A", metal=0.9, rugosidad=0.25)
            .material("Mi nave", "B", transmision=1, rugosidad=0.0).construir())
    assert revisar(practica, bien).passed


def test_un_material_no_sirve_para_dos():
    practica = practica_simple([
        {"cubo": {"nombre": "A"}}, {"material": {"objeto": "A", "nombre": "Uno", "color": [1, 0, 0]}},
        {"material": {"objeto": "A", "nombre": "Dos", "color": [0, 0, 1]}},
    ], check=["materiales"])
    r = revisar(practica, Escena().cubo("A").material("A", "Rojo", color=(1, 0, 0)).construir())
    assert not r.passed and sum(1 for i in r.details["checklist"] if i["ok"]) == 1


def test_animacion_claves_y_recorrido():
    practica = practica_simple([
        {"esfera": {"nombre": "Pelota", "loc": [0, 0, 4]}},
        {"animar": {"objeto": "Pelota", "propiedad": "location", "eje": "z", "claves": [[1, 4], [12, 0], [24, 4]]}},
    ], check=["animacion"], nivel=3)
    poco = Escena().esfera("Bola").animar("Bola", "location", "z", [[1, 4], [12, 3.5], [24, 4]]).construir()
    r = revisar(practica, poco)
    assert not r.passed and "muy poco" in r.message
    dos = Escena().esfera("Bola").animar("Bola", "location", "z", [[1, 4], [24, 0]]).construir()
    assert "faltan claves" in revisar(practica, dos).message
    bien = Escena().esfera("Bola").animar("Bola", "location", "z", [[1, 5], [10, 0.2], [20, 5], [30, 0]]).construir()
    assert revisar(practica, bien).passed


def test_luces_el_tipo_es_sugerencia_en_los_primeros_niveles():
    pasos = [{"cubo": {}}, {"luz": {"tipo": "AREA"}}, {"luz": {"tipo": "SPOT", "nombre": "Foco"}}]
    con_puntuales = Escena().cubo().luz("L1", "POINT").luz("L2", "POINT").construir()
    facil = revisar(practica_simple(pasos, ["luces"], nivel=2), con_puntuales)
    assert facil.passed and "Un detalle" in facil.message
    assert any(i["estado"] == "Detalle" for i in facil.details["checklist"])
    assert not revisar(practica_simple(pasos, ["luces"], nivel=3), con_puntuales).passed


def test_camara_que_mira_al_modelo():
    practica = practica_simple([{"cubo": {}}, {"camara": {"loc": [0, -8, 2]}}], check=["camara"])
    de_espaldas = Escena().cubo().camara(loc=(0, -8, 2), mira_a=(0, -20, 2)).construir()
    r = revisar(practica, de_espaldas)
    assert not r.passed and "Se desvía" in r.message
    assert revisar(practica, Escena().cubo().camara(loc=(5, 5, 3)).construir()).passed


def test_modificadores_espejo_y_niveles():
    practica = practica_simple([{"cubo": {"nombre": "N"}}, {"modificador": {"objeto": "N", "tipo": "MIRROR"}},
                                {"modificador": {"objeto": "N", "tipo": "SUBSURF", "niveles": 2}}],
                               check=["modificadores"])
    mal = (Escena().cubo("X").modificador("X", "MIRROR", ejes=(False, True, False))
           .modificador("X", "SUBSURF", niveles=1).construir())
    r = revisar(practica, mal)
    assert not r.passed and "revisa sus ajustes" in r.message
    bien = Escena().cubo("X").modificador("X", "MIRROR").modificador("X", "SUBSURF", niveles=3).construir()
    assert revisar(practica, bien).passed


def test_colecciones_con_nombre_libre_hasta_el_nivel_3():
    pasos = [{"cubo": {"nombre": "A"}}, {"cubo": {"nombre": "B"}},
             {"coleccion": {"nombre": "Casas", "objetos": ["A", "B"]}}]
    otra = Escena().cubo("A", coleccion="Pueblo").cubo("B", coleccion="Pueblo").construir()
    assert revisar(practica_simple(pasos, ["colecciones"], nivel=3), otra).passed
    assert not revisar(practica_simple(pasos, ["colecciones"], nivel=4), otra).passed


def test_archivo_lleva_la_palabra_del_ejemplo():
    practica = practica_simple([{"cubo": {}}, {"guardado": {"archivo": "mi_tren.blend"}}], check=["archivo"])
    assert revisar(practica, Escena().cubo().guardado("/casa/tren_rojo.blend").construir()).passed
    r = revisar(practica, Escena().cubo().guardado("casa.blend").construir())
    assert not r.passed and "debe llevar «tren»" in r.message


def test_malla_modelada_y_media_nave():
    practica = practica_simple([{"cubo": {"nombre": "N", "vertices": 30, "mitad": "x-"}}], check=["malla"])
    r = revisar(practica, Escena().cubo("N").construir())
    assert {i["texto"]: i["ok"] for i in r.details["checklist"]} == {
        "«N» modelado en Modo Edición": False, "Solo una mitad de «N» (en X)": False}
    assert revisar(practica, Escena().cubo("N", vertices=20, mitad="x+").construir()).passed


def test_la_figura_sin_modelo_usa_las_mallas_del_ejemplo():
    pasos = [{"cubo": {"nombre": "Mesa", "dims": [2, 1, 0.1], "loc": [0, 0, 1]}},
             {"cilindro": {"nombre": "Pata", "dims": [0.1, 0.1, 1], "loc": [0.9, 0.4, 0.5]}},
             {"cilindro": {"nombre": "Pata.001", "dims": [0.1, 0.1, 1], "loc": [-0.9, -0.4, 0.5]}}]
    practica = practica_simple(pasos, ["figura"])
    sin_patas = Escena().cubo("Tabla", dims=(2, 1, 0.1), loc=(0, 0, 0.05)).construir()
    r = revisar(practica, sin_patas)
    assert not r.passed and "Cilindro" in r.message
    otra_escala = (Escena().cubo("Tabla", dims=(4, 2, 0.2), loc=(0, 0, 2))
                   .cilindro("P1", dims=(0.2, 0.2, 2), loc=(1.8, 0.8, 1))
                   .cilindro("P2", dims=(0.2, 0.2, 2), loc=(-1.8, -0.8, 1)).construir())
    assert revisar(practica, otra_escala).passed


def test_el_instructor_guia_con_el_primer_punto_pendiente():
    practica = practica_simple([{"cubo": {"nombre": "Caja"}}, {"modificador": {"objeto": "Caja", "tipo": "BEVEL"}},
                                {"guardado": {"archivo": "mi_caja.blend"}}], check=["modificadores", "archivo"])
    escena = Escena().cubo("Caja").construir()
    guia = build_guidance(practica, escena, MOTOR.evaluate(practica, escena))
    assert guia.target_id == "ejemplo"
    assert "Bisel" in guia.instructions[0].text
    assert any("archivo" in i.text for i in guia.instructions)
    assert guia.action is not None and guia.action.kind == "show_example"


def test_la_espada_hecha_a_mano_coincide_y_sin_guarda_no(tmp_path):
    practica = load_practice(next(r for r in PRACTICAS if r.parent.name == "m2-espada"))
    piezas = practica.reference.parts
    hecha = Escena().referencia(piezas, variacion=0.15, semilla=4, vertices=60).guardado("espada.blend").construir()
    assert revisar(practica, hecha).passed
    sin_guarda = Escena().referencia(piezas, cambiar={"Guarda": [0.2, 0.7, 1]}, vertices=60).construir()
    r = revisar(practica, sin_guarda)
    assert not r.passed and not lista(r)["Guarda"]["ok"]


def test_copiar_el_ejemplo_no_cambia_la_practica():
    practica = load_practice(PRACTICAS[0])
    antes = copy.deepcopy(practica.example.steps)
    escena_esperada(practica.example.steps, _partes(practica))
    assert practica.example.steps == antes


def test_ejemplo_no_aprueba_silueta_omitida():
    from dataclasses import replace

    ruta = next(p for p in PRACTICAS if p.parent.name == 'm2-espada')
    practica = load_practice(ruta)
    esperada = escena_esperada(practica.example.steps, _partes(practica))
    sin_evidencia = replace(esperada, objects=tuple(replace(o, silhouette=None) for o in esperada.objects))
    resultado = revisar(practica, sin_evidencia)
    assert not resultado.passed
    assert any(not i['ok'] and 'silueta' in i['consejo'] for i in resultado.details['checklist'])
