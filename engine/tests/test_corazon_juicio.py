"""Juicio del Corazón: comparar la escena con el ejemplo, pieza por pieza, y decidir una indicación."""
import json
from pathlib import Path

import pytest

import amatista_engine
from amatista_engine.corazon import juicio
from amatista_engine.corazon.juicio import AGREGAR, AJUSTAR_TAMANO, BIEN, FALTA, GIRADA, GIRAR, SEGUIR, TAMANO, juzgar
from amatista_engine.practice import parse_practice
from amatista_engine.testing import Escena

RAIZ = Path(__file__).resolve().parents[2]
PRACTICAS = sorted(p.parent for p in (RAIZ / "practices" / "blender").rglob("practica.json"))
TREN = RAIZ / "practices" / "blender" / "principiante" / "m1-tren"


def leer(carpeta: Path):
    return parse_practice(json.loads((carpeta / "practica.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def motor():
    return amatista_engine.create_default_engine()


@pytest.fixture(scope="module")
def tren():
    return leer(TREN)


def juicio_de(motor, practica, escena: Escena):
    estado = escena.construir()
    return juzgar(practica, estado, motor.evaluate(practica, estado))


def test_escena_vacia_pide_la_primera_pieza_con_medidas(motor, tren):
    j = juicio_de(motor, tren, Escena())
    assert j.avance == (0, 11)
    assert j.decision.accion == AGREGAR and j.decision.grupo == "vagon"
    assert "2.2 × 1.2 × 1.1 m" in j.decision.texto and "cubo" in j.decision.texto


def test_las_medidas_se_piden_en_la_escala_del_alumno(motor, tren):
    # Una locomotora al doble de tamaño: la rueda «debería medir» el doble que en el ejemplo.
    e = Escena()
    e.cubo("Cube", dims=[4.4, 2.4, 2.2], loc=[2.5, 0, 1.8])
    e.cubo("Cube.001", dims=[4.0, 2.4, 2.0], loc=[-2.3, 0, 1.7])
    e.cilindro("Cylinder", dims=[1.4, 1.4, 0.9], loc=[0, 4, 0.7], rot=[90, 0, 0])  # de pie pero gruesa
    j = juicio_de(motor, tren, e)
    assert j.diferencia.escala == pytest.approx(2.0, abs=0.15)
    assert j.decision.accion == AJUSTAR_TAMANO and j.decision.objeto == "Cylinder"
    assert "mide 0.9 m en Y" in j.decision.texto and "0.4 m" in j.decision.texto and "S y luego Y" in j.decision.texto


def test_distingue_girar_de_escalar(motor, tren):
    e = Escena()
    e.cubo("Cube", dims=[2.2, 1.2, 1.1], loc=[1.25, 0, 0.9])
    e.cubo("Cube.001", dims=[2.0, 1.2, 1.0], loc=[-1.15, 0, 0.85])
    e.cilindro("Cylinder", dims=[0.7, 0.7, 0.2], loc=[0, 3, 0.1])  # bien de medidas, acostada
    j = juicio_de(motor, tren, e)
    rueda = next(p for p in j.diferencia.piezas if p.objeto == "Cylinder")
    assert rueda.estado == GIRADA
    assert j.decision.accion == GIRAR and "Gírala con R" in j.decision.texto


def test_corrige_lo_que_existe_antes_de_pedir_mas(motor, tren):
    # Una rueda mal hecha y faltan siete: primero se arregla esa, para no duplicar el error.
    e = Escena()
    e.cubo("Cube", dims=[2.2, 1.2, 1.1], loc=[1.25, 0, 0.9])
    e.cubo("Cube.001", dims=[2.0, 1.2, 1.0], loc=[-1.15, 0, 0.85])
    e.cilindro("Cylinder", dims=[0.7, 0.7, 0.5], loc=[0.65, 0.85, 0.35], rot=[90, 0, 0])
    j = juicio_de(motor, tren, e)
    assert j.diferencia.faltan("rueda") == 7
    assert j.decision.accion == AJUSTAR_TAMANO


def test_cuenta_lo_que_llevas(motor, tren):
    e = Escena().referencia(tren.reference.parts, sin=("chimenea",), roles=False)
    for nombre in [o.name for o in e._objetos if o.primitive == "cylinder"][:3]:
        e.quitar(nombre)
    j = juicio_de(motor, tren, e)
    assert j.decision.accion == AGREGAR
    assert j.decision.grupo in ("rueda", "chimenea")
    assert j.diferencia.faltan("rueda") == 3 and j.diferencia.con_estado(FALTA)


def test_con_las_piezas_bien_cede_la_palabra_al_motor(motor, tren):
    e = Escena().referencia(tren.reference.parts, roles=False)
    estado = e.construir()
    reporte = motor.evaluate(tren, estado)
    j = juzgar(tren, estado, reporte)
    assert j.avance == (11, 11)
    assert j.decision.accion == SEGUIR and j.decision.texto == reporte.result(reporte.current_target_id).message


def test_figura_girada_un_cuarto_de_vuelta(motor, tren):
    j = juicio_de(motor, tren, Escena().referencia(tren.reference.parts, roles=False, giro=90))
    assert j.diferencia.girada is True
    assert j.avance == (11, 11)


def test_las_piezas_unidas_no_se_juzgan_aqui():
    espada = leer(RAIZ / "practices" / "blender" / "principiante" / "m2-espada")
    assert juicio.plano_de(espada) is None
    assert juzgar(espada, Escena().construir()) is None


@pytest.mark.parametrize("carpeta", PRACTICAS, ids=lambda c: c.name)
def test_el_ejemplo_bien_hecho_no_recibe_correcciones(motor, carpeta):
    """En toda práctica: el ejemplo, a varios tamaños y hecho a mano, no debe generar ni una corrección."""
    practica = leer(carpeta)
    if juicio.plano_de(practica) is None:
        pytest.skip("sin piezas sueltas que comparar")
    piezas = practica.reference.parts
    casos = [("exacto", {}), ("mitad", {"escala": 0.5}), ("doble", {"escala": 2.0}), ("girado", {"giro": 90})]
    casos += [(f"a mano {s}", {"variacion": 0.10, "semilla": s}) for s in (1, 2, 3)]
    for nombre, opciones in casos:
        estado = Escena().referencia(piezas, **opciones).construir()
        j = juzgar(practica, estado, motor.evaluate(practica, estado))
        mal = [(p.esperada, p.estado, p.ajuste) for p in j.diferencia.piezas if p.estado != BIEN]
        assert not mal, f"{practica.id} ({nombre}): {mal}"


@pytest.mark.parametrize("carpeta", PRACTICAS, ids=lambda c: c.name)
def test_armando_pieza_por_pieza_solo_pide_agregar(motor, carpeta):
    """Mientras el alumno agrega piezas correctas, el juicio nunca le pide corregir una que está bien."""
    practica = leer(carpeta)
    if juicio.plano_de(practica) is None:
        pytest.skip("sin piezas sueltas que comparar")
    piezas = list(practica.reference.compared)
    for k in range(1, len(piezas)):
        estado = Escena().referencia(piezas[:k]).construir()
        j = juzgar(practica, estado, motor.evaluate(practica, estado))
        assert j.decision.accion == AGREGAR, f"{practica.id} con {k} piezas: {j.decision}"
        assert not j.diferencia.con_estado(TAMANO) and not j.diferencia.con_estado(GIRADA)


# --- El juicio dentro del turno (Director) ---------------------------------------------------


def _director_real(tren):
    from amatista_engine.corazon import perfiles
    from amatista_engine.corazon.director import Director
    from amatista_engine.corazon.simulado import AdaptadorSimulado

    adaptador = AdaptadorSimulado(perfiles.perfil("blender"))
    return Director(tren, adaptador.perfil, adaptador.capacidades()), adaptador


def _turno(motor, tren, director, adaptador, escena: Escena, ahora: float = 1.0):
    estado = escena.construir()
    return director.ciclo(adaptador, motor.evaluate(tren, estado), ahora, escena=estado)


def test_el_turno_trae_la_correccion_de_una_pieza_con_medidas(motor, tren):
    director, adaptador = _director_real(tren)
    e = Escena()
    e.cubo("Cube", dims=[2.2, 1.2, 1.1], loc=[1.25, 0, 0.9])
    e.cubo("Cube.001", dims=[2.0, 1.2, 1.0], loc=[-1.15, 0, 0.85])
    e.cilindro("Cylinder", dims=[0.7, 0.7, 0.5], loc=[0.65, 0.85, 0.35], rot=[90, 0, 0])  # rueda gruesa
    t = _turno(motor, tren, director, adaptador, e)
    assert t.revision_objeto == "Cylinder"
    assert "0.5 m" in t.revision and "0.2 m" in t.revision
    assert t.piezas == (2, 11)
    assert t.como_dict()["revision"] == t.revision  # viaja en el turno, como todo lo demás


def test_el_turno_no_pide_agregar_piezas_eso_lo_dice_el_paso(motor, tren):
    # Dos vagones bien y nada más: el juicio «agregaría» la chimenea, pero el paso del guion
    # pide las ruedas. El turno no repite ni contradice al paso: la revisión queda vacía.
    director, adaptador = _director_real(tren)
    e = Escena()
    e.cubo("Cube", dims=[2.2, 1.2, 1.1], loc=[1.25, 0, 0.9])
    e.cubo("Cube.001", dims=[2.0, 1.2, 1.0], loc=[-1.15, 0, 0.85])
    t = _turno(motor, tren, director, adaptador, e)
    assert t.revision == "" and t.revision_objeto == ""
    assert t.piezas == (2, 11)
    assert t.haz  # el paso sigue mandando


def test_sin_escena_el_turno_es_el_de_siempre(motor, tren):
    director, adaptador = _director_real(tren)
    estado = Escena().construir()
    t = director.ciclo(adaptador, motor.evaluate(tren, estado), 1.0)
    assert t.revision == "" and t.piezas == (0, 0)


def test_un_fallo_del_juicio_no_rompe_el_turno(motor, tren, monkeypatch):
    from amatista_engine.corazon import juicio as modulo

    def romper(*_a, **_k):
        raise RuntimeError("fallo a propósito")

    monkeypatch.setattr(modulo, "juzgar", romper)
    director, adaptador = _director_real(tren)
    e = Escena()
    e.cubo("Cube", dims=[2, 2, 2], loc=[0, 0, 1])
    t = _turno(motor, tren, director, adaptador, e)
    assert t.revision == "" and t.haz


def test_practica_de_una_sola_malla_no_trae_revision(motor):
    from amatista_engine.corazon import perfiles
    from amatista_engine.corazon.director import Director
    from amatista_engine.corazon.simulado import AdaptadorSimulado

    espada = leer(RAIZ / "practices" / "blender" / "principiante" / "m2-espada")
    adaptador = AdaptadorSimulado(perfiles.perfil("blender"))
    director = Director(espada, adaptador.perfil, adaptador.capacidades())
    estado = Escena().cubo("Cube", dims=[0.3, 0.1, 2.6], loc=[0, 0, 1.3]).construir()
    t = director.ciclo(adaptador, motor.evaluate(espada, estado), 1.0, escena=estado)
    assert t.revision == "" and t.piezas == (0, 0)


def test_una_pieza_irreconocible_no_falta_hay_que_corregirla(motor, tren):
    # Encontrado dentro de Blender: una rueda al triple de grosor ya no se reconoce como rueda.
    # No hay que decir «te falta una rueda» teniendo ocho cilindros: hay que decir cuál corregir.
    e = Escena().referencia(tren.reference.parts, roles=False)
    ruedas = [o.name for o in e._objetos if o.primitive == "cylinder" and o.dimensions[2] < 0.3]
    gorda = ruedas[0]
    obj = e._obj(gorda)
    e.quitar(gorda)
    e.cilindro(gorda, dims=[0.7, 0.7, 0.6], loc=list(obj.location), rot=[90, 0, 0])
    j = juicio_de(motor, tren, e)
    assert not j.diferencia.con_estado(FALTA)
    assert j.avance == (10, 11)
    assert j.decision.accion == AJUSTAR_TAMANO and j.decision.objeto == gorda
    assert "0.6 m" in j.decision.texto and "0.2 m" in j.decision.texto
