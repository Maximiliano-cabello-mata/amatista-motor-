"""Etapa 2: guía paso a paso (coach) y acompañante (companion)."""
from amatista_engine import create_default_engine
from amatista_engine.guide import Companion, distance, guidance_to_dict
from amatista_engine.guide.coach import delta_amable, factor_amable, objetivo_amable
from amatista_engine.guide.models import (
    MEJORANDO,
    NUEVO_PASO,
    OFRECER_AYUDA,
    PASO_LOGRADO,
    PRACTICA_COMPLETA,
    RESALTE_BIEN,
    RESALTE_CANDIDATO,
    RESALTE_CORREGIR,
    RETROCESO,
)
from amatista_engine.models import SceneObject, SceneState
from amatista_engine.practice import compile_practice, dump_practice, load_practice, parse_practice

from ayudantes import MESA, cubierta, mesa_completa, pata

motor = create_default_engine()
practica = load_practice(MESA)


def escena(*objetos, guardada=False, ruta=""):
    return SceneState("5.1.1", ruta, guardada, tuple(objetos))


def cubo(nombre="Cube", roles=(), alto=2.0):
    return SceneObject(nombre, "MESH", roles=roles, location=(0, 0, alto / 2), dimensions=(2, 2, alto))


def test_numeros_redondos():
    assert objetivo_amable(0.05, 0.3) in (0.1, 0.15, 0.2, 0.25)
    assert factor_amable(2, 0.05, 0.3) == 0.1
    assert factor_amable(2, 0.4, 1.2) == 0.5
    assert factor_amable(0.1, 0.4, 1.2) == 10.0
    assert delta_amable(0.3, 1.0, 1.5) == 1.0


def test_sin_roles_propone_el_cubo_como_cubierta():
    g = motor.guide(practica, escena(cubo()))
    assert g.target_id == "cubierta" and g.step_number == 1 and g.step_total == 6
    assert "ningún objeto es «Cubierta»" in g.feedback
    assert g.highlights[0].kind == RESALTE_CANDIDATO and g.highlights[0].object_name == "Cube"
    assert g.action.kind == "assign_role" and g.action.role == "cubierta" and g.action.objects == ("Cube",)
    assert any("N" in i.keys for i in g.instructions)
    # El «por qué» lo escribió el autor en guide.why.
    assert g.why.startswith("Amatista no adivina")


def test_escena_vacia_propone_agregar_un_cubo():
    g = motor.guide(practica, escena())
    assert g.action.kind == "add_cube"
    assert g.instructions[0].keys == ("Shift", "A")


def test_cubierta_gruesa_da_teclas_y_numero_exacto():
    g = motor.guide(practica, escena(cubo(roles=("cubierta",))))
    assert g.target_id == "grosor"
    assert [i.keys for i in g.instructions][1:] == [("S", "Z"), ("0.1", "Enter")]
    assert g.action.kind == "scale" and g.action.axis == "z" and g.action.value == 0.1
    regla = g.cues[0]
    assert regla.kind == "ruler" and regla.data["current"] == 2.0 and regla.data["max"] == 0.3
    assert g.highlights[0].kind == RESALTE_CORREGIR


def test_patas_que_faltan_se_dibujan_como_fantasmas():
    g = motor.guide(practica, escena(cubierta(), pata("P1", -0.9, -0.4)))
    assert g.target_id == "patas"
    assert "Llevas 1 de 4" in g.feedback and "faltan 3" in g.feedback
    fantasmas = next(c for c in g.cues if c.kind == "ghosts")
    assert len(fantasmas.data["boxes"]) == 3  # la esquina de P1 está ocupada
    assert g.action.kind == "duplicate" and g.action.objects == ("P1",)
    bien = {h.object_name for h in g.highlights if h.kind == RESALTE_BIEN}
    assert bien == {"P1", "Cubierta"}


def test_pata_que_atraviesa_dice_cuanto_bajarla():
    base = mesa_completa().objects
    g = motor.guide(practica, escena(*base[:4], pata("P4", 0.9, 0.4, alto=1.0)))
    assert g.target_id == "debajo"
    assert g.action.kind == "move" and g.action.axis == "z" and g.action.value == -0.25
    assert {c.kind for c in g.cues} == {"plane", "arrow"}
    corregir = [h.object_name for h in g.highlights if h.kind == RESALTE_CORREGIR]
    assert corregir == ["P4"]


def test_guardar_y_practica_completa():
    g = motor.guide(practica, escena(*mesa_completa().objects))
    assert g.target_id == "guardar" and g.action.kind == "save"
    fin = motor.guide(practica, mesa_completa())
    assert fin.completed and fin.title == "¡Práctica completada!"
    assert fin.action is None and "color" in (fin.target_id or "")


def test_pasos_del_autor_reemplazan_los_generados():
    datos = dump_practice(practica)
    datos["targets"][1]["guide"] = {"why": "Porque sí.", "steps": ["Elige la tabla", {"text": "Aplana", "keys": ["S", "Z"]}]}
    propia = parse_practice(datos)
    g = motor.guide(propia, escena(cubo(roles=("cubierta",))))
    assert g.why == "Porque sí."
    assert [(i.text, i.keys) for i in g.instructions] == [("Elige la tabla", ()), ("Aplana", ("S", "Z"))]
    # La acción y la regla siguen siendo las calculadas.
    assert g.action.kind == "scale" and g.cues[0].kind == "ruler"


def test_guia_viaja_en_json_y_se_conserva_al_exportar():
    assert compile_practice(dump_practice(practica)).ok
    assert dump_practice(practica)["targets"][0]["guide"]["why"].startswith("Amatista")
    datos = guidance_to_dict(motor.guide(practica, escena(cubo(roles=("cubierta",)))))
    assert datos["action"]["kind"] == "scale" and datos["instructions"][1]["keys"] == ["S", "Z"]


def test_guia_mal_escrita_explica_el_error():
    datos = dump_practice(practica)
    datos["targets"][0]["guide"] = {"steps": [{"text": "x", "keys": "S"}]}
    resultado = compile_practice(datos)
    assert not resultado.ok and "keys" in resultado.errors[0]


def test_distancia_al_objetivo():
    r = motor.evaluate(practica, escena(cubo(roles=("cubierta",)))).result("grosor")
    assert round(distance(r), 2) == 1.7
    r = motor.evaluate(practica, escena(cubierta(), pata("P1", 0, 0))).result("patas")
    assert distance(r) == 3.0


def test_acompanante_celebra_avisa_y_ofrece_ayuda():
    c = Companion(help_after_tries=3)
    avisos = c.observe(practica, motor.evaluate(practica, escena(cubo())), now=0)
    assert [a.kind for a in avisos] == [NUEVO_PASO]  # al abrir: solo el primer paso

    avisos = c.observe(practica, motor.evaluate(practica, escena(cubo(roles=("cubierta",)))), now=5)
    tipos = [a.kind for a in avisos]
    assert tipos[:1] == [PASO_LOGRADO] and NUEVO_PASO in tipos
    assert avisos[0].text == "Ya tienes la cubierta de tu mesa."

    # Se acerca al rango: «¡Vas mejor!»
    avisos = c.observe(practica, motor.evaluate(practica, escena(cubo(roles=("cubierta",), alto=1.0))), now=10)
    assert [a.kind for a in avisos] == [MEJORANDO]

    # Tres cambios sin mejorar: el acompañante ofrece ayuda una sola vez.
    for t in (11, 12):
        assert c.observe(practica, motor.evaluate(practica, escena(cubo(roles=("cubierta",), alto=1.0))), now=t) == []
    avisos = c.observe(practica, motor.evaluate(practica, escena(cubo(roles=("cubierta",), alto=1.0))), now=13)
    assert [a.kind for a in avisos] == [OFRECER_AYUDA] and avisos[0].dialog
    assert c.observe(practica, motor.evaluate(practica, escena(cubo(roles=("cubierta",), alto=1.0))), now=14) == []


def test_acompanante_retroceso_y_final():
    c = Companion()
    c.observe(practica, motor.evaluate(practica, escena(*mesa_completa().objects)), now=0)
    avisos = c.observe(practica, motor.evaluate(practica, mesa_completa()), now=1)
    assert PRACTICA_COMPLETA in [a.kind for a in avisos]
    rota = escena(*mesa_completa().objects[:4], pata("P4", 0.9, 0.4, alto=1.0), guardada=True, ruta="/tmp/m.blend")
    avisos = c.observe(practica, motor.evaluate(practica, rota), now=2)
    assert RETROCESO in [a.kind for a in avisos]


def test_acompanante_por_tiempo():
    c = Companion(help_after_tries=99, help_after_seconds=60)
    e = escena(cubo(roles=("cubierta",)))
    c.observe(practica, motor.evaluate(practica, e), now=0)
    assert c.observe(practica, motor.evaluate(practica, e), now=30) == []
    assert [a.kind for a in c.observe(practica, motor.evaluate(practica, e), now=61)] == [OFRECER_AYUDA]
