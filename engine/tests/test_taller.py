"""Amatista Taller (motor 5): el modelo del alumno, el plan del ciclo, el molde, las pistas y la demostración.

Las pruebas del catálogo completo (todas las habilidades de los 9 módulos)
están en test_taller_catalogo.py; aquí va el comportamiento del núcleo con
el módulo 1 de Principiante.
"""
import json
from dataclasses import replace

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.practice import compile_practice
from amatista_engine.practice.loader import parse_practice
from amatista_engine.taller import (
    ACOMPANADA,
    COMO,
    CON_QUE,
    CONMIGO,
    DOMINADA,
    MIRA,
    MIRAME,
    NUEVA,
    PROYECTO,
    QUE,
    RETO,
    SOLA,
    TU,
    actividad_de_prueba,
    actividad_de_repaso,
    actividad_por_id,
    cargar_catalogo,
    dominio,
    estado_desde_dict,
    fase,
    leer_catalogo,
    linea_de_tiempo,
    pedir_pista,
    pista_para,
    planear,
    practica_de_actividad,
    registrar_intento,
    revisar_molde,
    revisar_proyecto,
)
from amatista_engine.taller.ayudas import atascado, avance, deshizo, escalera_para, fallo
from amatista_engine.taller.demo import MAXIMO
from amatista_engine.taller.habilidades import ErrorCatalogo, ParametrosBKT
from amatista_engine.taller.modelo import DIA, marcar_demo
from amatista_engine.taller.molde import CASI, EQUIVOCADA, LLENA, VACIA
from amatista_engine.testing import Escena

CATALOGO = PRACTICAS / "habilidades.json"
TALLER = "blender.bp.m1"
AHORA = 1_800_000_000.0
TREN = PRACTICAS / "principiante/m1-tren/practica.json"


@pytest.fixture(scope="module")
def catalogo():
    return leer_catalogo(CATALOGO)


@pytest.fixture(scope="module")
def motor():
    return create_default_engine()


def escena_de(piezas, mover=None):
    """Una escena armada pieza por pieza (mover: {indice: (dx, dy, dz)})."""
    e = Escena()
    for i, p in enumerate(piezas):
        loc = list(p.get("location", (0, 0, 0)))
        for k, d in enumerate((mover or {}).get(i, (0, 0, 0))):
            loc[k] += d
        e.malla(p["primitive"], p.get("name", ""), dims=p["size"], loc=loc, rot=p.get("rotation"))
    return e.construir()


# --- El catálogo -------------------------------------------------------------------------------


def test_el_catalogo_carga_con_el_taller_del_modulo_1(catalogo):
    taller = catalogo.taller(TALLER)
    assert taller is not None and taller.proyecto == "blender.bp.m1.tren"
    assert catalogo.taller_de_modulo("blender_principiante", 1).id == TALLER
    assert catalogo.taller_de_proyecto("blender.bp.m1.tren").id == TALLER
    # El orden respeta los requisitos: agregar antes que mover, mover antes que escalar.
    orden = catalogo.orden(taller.habilidades)
    assert orden.index("bl-agregar-primitivas") < orden.index("bl-mover") < orden.index("bl-escalar-eje")


def test_el_catalogo_rechaza_frases_largas_y_ciclos():
    base = json.loads(CATALOGO.read_text(encoding="utf-8"))
    largo = json.loads(json.dumps(base))
    largo["habilidades"][0]["que"] = " ".join(["un"] * 30)
    with pytest.raises(ErrorCatalogo, match="palabras"):
        cargar_catalogo(largo)
    ciclo = json.loads(json.dumps(base))
    ciclo["habilidades"][0]["requiere"] = ["bl-mover"]  # bl-mover ya requiere agregar
    with pytest.raises(ErrorCatalogo):
        cargar_catalogo(ciclo)


# --- El modelo del alumno ----------------------------------------------------------------------


def test_dos_aciertos_con_molde_llevan_a_hacerlo_solo(catalogo):
    h = catalogo.habilidad("bl-escalar-eje")
    d = None
    fases = []
    for i in range(4):
        d = registrar_intento(d, h.bkt, True, 0, AHORA + i, molde=True, tipo=CONMIGO)
        fases.append(fase(d.p))
    assert fases[0] in (NUEVA, ACOMPANADA)
    assert SOLA in fases[:3]  # con dos o tres aciertos ya toca «Hazlo tú»


def test_acertar_con_las_teclas_a_la_vista_no_prueba_que_sepa(catalogo):
    h = catalogo.habilidad("bl-mover")
    sin_ayuda = registrar_intento(None, h.bkt, True, 0, AHORA)
    con_teclas = registrar_intento(None, h.bkt, True, COMO, AHORA)
    con_demo = registrar_intento(None, h.bkt, True, MIRAME, AHORA)
    con_pista = registrar_intento(None, h.bkt, True, QUE, AHORA)
    assert sin_ayuda.p > con_pista.p > con_teclas.p
    assert con_teclas.p == pytest.approx(con_demo.p)
    assert con_teclas.sin_ayuda == 0 and sin_ayuda.sin_ayuda == 1


def test_lo_que_no_se_practica_se_olvida(catalogo):
    h = catalogo.habilidad("bl-rotar")
    d = None
    for i in range(6):
        d = registrar_intento(d, h.bkt, True, 0, AHORA + i)
    hoy = dominio(d, h.bkt, AHORA + 10)
    en_un_mes = dominio(d, h.bkt, AHORA + 30 * DIA)
    assert hoy > en_un_mes > h.bkt.L0


def test_las_cajas_de_repaso(catalogo):
    h = catalogo.habilidad("bl-mover")
    d = None
    t = AHORA
    while d is None or fase(d.p) != DOMINADA:
        d = registrar_intento(d, h.bkt, True, 0, t)
        t += 60
    assert d.caja == 1 and d.proximo == pytest.approx(t - 60 + DIA)  # recién dominada: repaso mañana
    d = registrar_intento(d, h.bkt, True, 0, d.proximo + 5, tipo="repaso")
    assert d.caja == 2
    d = registrar_intento(d, h.bkt, False, 0, d.proximo + 5, tipo="repaso")
    assert d.caja == 1  # un repaso fallido vuelve a la primera caja


def test_camino_rapido_dos_pruebas_sin_ayuda(catalogo):
    h = catalogo.habilidad("bl-escalar-eje")
    d = registrar_intento(None, h.bkt, True, 0, AHORA, tipo="prueba")
    assert d.p < 0.9
    d = registrar_intento(d, h.bkt, True, 0, AHORA + 60, tipo="prueba")
    assert d.p >= 0.9 and fase(d.p) in (SOLA, DOMINADA)


def test_el_estado_guardado_ignora_lo_que_no_entiende():
    estado = estado_desde_dict({"bl-mover": {"p": 0.5, "intentos": 2, "basura": 1}, "x": "no", 3: {}})
    assert list(estado) == ["bl-mover"] and estado["bl-mover"].intentos == 2
    assert estado_desde_dict(None) == {}


# --- El plan -----------------------------------------------------------------------------------


def test_un_alumno_nuevo_empieza_mirando_la_primera_habilidad(catalogo):
    plan = planear(catalogo, TALLER, {}, AHORA)
    assert plan.actual.tipo == MIRA and plan.actual.habilidad == "bl-agregar-primitivas"
    assert plan.puede_probar and not plan.proyecto_abierto
    datos = plan.a_dict()
    assert datos["actual"]["nombre_tipo"] == "Mira" and datos["total"] == 6


def test_despues_de_mirar_viene_hazlo_conmigo_y_luego_hazlo_tu(catalogo):
    h = catalogo.habilidad("bl-agregar-primitivas")
    estado = {h.id: marcar_demo(None, h.bkt)}
    plan = planear(catalogo, TALLER, estado, AHORA)
    assert plan.actual.tipo == CONMIGO and plan.actual.habilidad == h.id
    assert plan.actual.molde and plan.actual.dibujo == "molde"
    d = estado[h.id]
    t = AHORA
    while fase(dominio(d, h.bkt, t)) in (NUEVA, ACOMPANADA):
        d = registrar_intento(d, h.bkt, True, 0, t, molde=True)
        t += 60
    plan = planear(catalogo, TALLER, {h.id: d}, t)
    # Ya sale sola, pero falta hacerla una vez sin ayuda: «Hazlo tú», sin molde ni teclas.
    assert plan.actual.habilidad == h.id and plan.actual.tipo == TU
    assert plan.actual.teclas == "ocultas" and plan.actual.techo == CON_QUE and not plan.actual.molde
    d = registrar_intento(d, h.bkt, True, 0, t + 60, tipo=TU)
    plan = planear(catalogo, TALLER, {h.id: d}, t + 120)
    # Lista: ahora toca mirar la siguiente.
    assert plan.actual.habilidad == "bl-mover" and plan.actual.tipo == MIRA
    assert plan.habilidades[0].lista


def test_con_todas_listas_se_abre_el_proyecto_y_despues_el_reto(catalogo):
    taller = catalogo.taller(TALLER)
    solas = {hid: replace(registrar_intento(None, catalogo.habilidad(hid).bkt, True, 0, AHORA, molde=True), p=0.8)
             for hid in taller.habilidades}
    plan = planear(catalogo, TALLER, solas, AHORA)
    # Todas salen solas: el proyecto ya se puede hacer, aunque el plan sugiere antes un «Hazlo tú».
    assert plan.proyecto_abierto and plan.actual.tipo == TU
    listo = {hid: replace(d, sin_ayuda=1) for hid, d in solas.items()}
    assert planear(catalogo, TALLER, listo, AHORA).actual.tipo == PROYECTO
    dominado = {hid: replace(d, p=0.97) for hid, d in listo.items()}
    plan = planear(catalogo, TALLER, dominado, AHORA)
    assert plan.actual.tipo == PROYECTO and plan.actual.practica_id == "blender.bp.m1.tren"
    plan = planear(catalogo, TALLER, dominado, AHORA, completadas=["blender.bp.m1.tren"])
    assert plan.proyecto_hecho and plan.actual.tipo == RETO
    plan = planear(catalogo, TALLER, dominado, AHORA, completadas=["blender.bp.m1.tren", f"reto:{TALLER}"])
    assert plan.completo and plan.actual is None


def test_el_alumno_elige_que_practicar(catalogo):
    plan = planear(catalogo, TALLER, {}, AHORA, elegida="bl-rotar")
    assert plan.actual.habilidad == "bl-rotar"


def test_las_actividades_se_vuelven_a_armar_por_su_id(catalogo):
    plan = planear(catalogo, TALLER, {}, AHORA)
    for a in (plan.actual,) + plan.siguientes:
        assert actividad_por_id(catalogo, TALLER, a.id).id == a.id
    assert actividad_por_id(catalogo, TALLER, f"proyecto:{TALLER}").tipo == PROYECTO
    assert actividad_por_id(catalogo, TALLER, "conmigo:bl-mover:no-existe") is None
    assert actividad_por_id(catalogo, TALLER, "basura") is None


def test_repasos_vencidos_no_bloquean(catalogo):
    h = catalogo.habilidad("bl-mover")
    d = replace(registrar_intento(None, h.bkt, True, 0, AHORA), p=0.97, caja=1, proximo=AHORA + DIA)
    plan = planear(catalogo, TALLER, {h.id: d}, AHORA + 2 * DIA)
    assert plan.repasos == (h.id,)
    assert plan.actual.tipo != "repaso"  # se ofrece aparte
    repaso = actividad_de_repaso(catalogo, TALLER, h.id)
    assert repaso.teclas == "ocultas" and repaso.techo == QUE and repaso.modo == "molde"  # al-suelo: libre false


# --- La práctica generada ----------------------------------------------------------------------


def _compilar(datos):
    practica = parse_practice(datos)
    resultado = compile_practice(practica)
    assert resultado.ok, resultado.errors
    return resultado.practice


def test_la_variacion_se_revisa_con_el_molde(catalogo, motor):
    a = actividad_por_id(catalogo, TALLER, "conmigo:bl-escalar-eje:tabla")
    datos = practica_de_actividad(catalogo, a)
    assert datos["id"] == "taller.bl-escalar-eje.tabla.conmigo"
    assert datos["targets"][0]["validator"] == "taller.molde"
    practica = _compilar(datos)
    assert motor.evaluate(practica, escena_de(a.piezas)).completed
    assert not motor.evaluate(practica, Escena().inicial().construir()).completed


def test_arreglar_la_escena_no_pasa_al_empezar(catalogo, motor):
    a = actividad_por_id(catalogo, TALLER, "tu:bl-mover:baja")
    assert a.inicio and a.modo == "molde" and a.dibujo == "marca"
    practica = _compilar(practica_de_actividad(catalogo, a))
    assert not motor.evaluate(practica, escena_de(a.inicio)).completed
    assert motor.evaluate(practica, escena_de(a.piezas)).completed


def test_guardar_se_revisa_con_sus_objetivos(catalogo):
    a = actividad_por_id(catalogo, TALLER, "conmigo:bl-guardar-archivo:nombre")
    datos = practica_de_actividad(catalogo, a)
    assert [t["validator"] for t in datos["targets"]] == ["file.named", "file.saved"]
    _compilar(datos)


def test_la_prueba_rapida_es_un_reto_sin_ayuda(catalogo):
    a = actividad_de_prueba(catalogo, TALLER, "bl-escalar-eje")
    assert a.tipo == "prueba" and a.modo == "libre" and a.teclas == "ocultas" and not a.molde
    _compilar(practica_de_actividad(catalogo, a))


def test_mira_y_proyecto_no_generan_practica(catalogo):
    assert practica_de_actividad(catalogo, actividad_por_id(catalogo, TALLER, "mira:bl-mover")) is None
    assert practica_de_actividad(catalogo, actividad_por_id(catalogo, TALLER, f"proyecto:{TALLER}")) is None


# --- El molde ----------------------------------------------------------------------------------

CHIMENEA = {"primitive": "cylinder", "size": [0.4, 0.4, 0.8], "location": [1, 0, 1.4], "name": "Chimenea"}
CUERPO = {"primitive": "cube", "size": [2.5, 1.2, 1], "location": [0, 0, 0.5], "name": "Cuerpo"}
RUEDA = {"primitive": "cylinder", "size": [0.8, 0.8, 0.2], "location": [0, 0.7, 0.4], "rotation": [90, 0, 0],
         "name": "Rueda"}


def test_el_molde_dice_que_falta_sin_numeros():
    r = revisar_molde([CUERPO, CHIMENEA], escena_de([CUERPO]))
    assert [p.estado for p in r.piezas] == [LLENA, VACIA]
    assert r.pieza_actual.nombre == "Chimenea" and "cilindro" in r.pieza_actual.mensaje
    assert r.pieza_actual.teclas[0] == "Shift+A"
    assert not any(c.isdigit() for c in r.mensaje)


def test_el_molde_reconoce_la_forma_equivocada():
    cubo = dict(CHIMENEA, primitive="cube")
    r = revisar_molde([CUERPO, CHIMENEA], escena_de([CUERPO, cubo]))
    chimenea = r.piezas[1]
    assert chimenea.estado == EQUIVOCADA and chimenea.motivo == "forma" and "cubo" in chimenea.mensaje


def test_el_molde_ve_la_rueda_acostada_y_la_que_flota():
    acostada = dict(RUEDA, rotation=[0, 0, 0], location=[0, 0.7, 0.1])
    r = revisar_molde([RUEDA], escena_de([acostada]))
    assert r.piezas[0].motivo == "giro" and "de pie" in r.piezas[0].mensaje
    r = revisar_molde([RUEDA], escena_de([RUEDA], mover={0: (0, 0, 0.8)}))
    assert r.piezas[0].estado in (CASI, EQUIVOCADA) and r.piezas[0].motivo in ("flota", "lugar")


def test_una_chimenea_bajita_no_es_un_giro():
    bajita = dict(CHIMENEA, size=[0.4, 0.4, 0.25], location=[1, 0, 1.125])
    r = revisar_molde([CUERPO, CHIMENEA], escena_de([CUERPO, bajita]))
    assert r.piezas[1].motivo == "tamano" and "altura" in r.piezas[1].mensaje


def test_en_libre_la_figura_se_acomoda_donde_este():
    piezas = [CUERPO, CHIMENEA]
    corrida = escena_de(piezas, mover={0: (5, 3, 0), 1: (5, 3, 0)})
    assert not revisar_molde(piezas, corrida, "molde").completa
    assert revisar_molde(piezas, corrida, "libre").completa


def test_los_niveles_altos_piden_mas_exactitud():
    larga = dict(CUERPO, size=[3.6, 1.2, 1])
    assert revisar_molde([CUERPO], escena_de([larga]), nivel=1).completa
    assert not revisar_molde([CUERPO], escena_de([larga]), nivel=5).completa


def test_el_proyecto_del_tren_tiene_molde_y_libre(motor):
    tren = parse_practice(json.loads(TREN.read_text(encoding="utf-8")))
    exacta = Escena().referencia(tren.reference.parts).construir()
    r = revisar_proyecto(tren, exacta)
    assert r is not None and r.modo == "molde" and r.completa
    girada = Escena().referencia(tren.reference.parts, giro=90).construir()
    r = revisar_proyecto(tren, girada)
    assert r.completa  # si arma fuera del molde, se revisa la figura


# --- Las pistas --------------------------------------------------------------------------------


def test_la_escalera_tiene_freno_antes_de_las_teclas(catalogo):
    h = catalogo.habilidad("bl-mover")
    e = escalera_para(ACOMPANADA, AHORA)
    e, nivel, _ = pedir_pista(e, AHORA + 1)
    assert nivel == QUE
    e, nivel, _ = pedir_pista(e, AHORA + 2)
    assert nivel == CON_QUE
    e2, nivel, espera = pedir_pista(e, AHORA + 5)
    assert nivel is None and espera > 0  # «Cómo» espera 20 s de intentarlo
    e3, nivel, _ = pedir_pista(fallo(e), AHORA + 5)
    assert nivel == COMO  # o un intento fallido
    e4, nivel, _ = pedir_pista(e, AHORA + 25)
    assert nivel == COMO and pista_para(COMO, h).teclas
    _, nivel, _ = pedir_pista(e4, AHORA + 26)
    assert nivel == MIRAME and pista_para(MIRAME, h).demo


def test_una_habilidad_nueva_no_tiene_freno_y_una_sola_tiene_techo():
    e = escalera_para(NUEVA, AHORA)
    for esperado in (QUE, CON_QUE, COMO):
        e, nivel, _ = pedir_pista(e, AHORA + 1)
        assert nivel == esperado
    e = escalera_para(SOLA, AHORA)
    e, _, _ = pedir_pista(e, AHORA + 100)
    e, _, _ = pedir_pista(e, AHORA + 100)
    _, nivel, _ = pedir_pista(e, AHORA + 100)
    assert nivel is None  # «Hazlo tú» llega hasta «Con qué»
    reto = escalera_para(SOLA, AHORA, reto=True)
    reto, _, _ = pedir_pista(reto, AHORA + 100)
    assert pedir_pista(reto, AHORA + 100)[1] is None  # en un reto, solo «Qué falta»


def test_atascado_ofrece_la_siguiente_pista():
    e = escalera_para(ACOMPANADA, AHORA)
    assert not atascado(e, AHORA + 30)
    assert atascado(e, AHORA + 95)
    e = avance(e, AHORA + 95)
    assert not atascado(e, AHORA + 100)
    for _ in range(3):
        e = deshizo(e)
    assert atascado(e, AHORA + 101)


def test_la_pista_que_habla_del_modelo():
    r = revisar_molde([CUERPO, CHIMENEA], escena_de([CUERPO]))
    p = pista_para(QUE, None, r.pieza_actual)
    assert "Chimenea" in p.texto and not p.teclas


# --- La demostración ---------------------------------------------------------------------------


def test_cada_demostracion_dura_poco_y_muestra_teclas(catalogo):
    for h in catalogo.habilidades.values():
        linea = linea_de_tiempo(h.demo, h.titulo)
        assert 0 < linea.duracion <= MAXIMO, h.id
    linea = linea_de_tiempo(catalogo.habilidad("bl-rotar").demo)
    rotar = next(p for p in linea.pasos if p.accion == "rotar")
    assert rotar.teclas == ("R", "X", "90")
    assert linea.en(rotar.inicio + 0.1) is rotar and linea.en(-1) is None


def test_una_demostracion_larga_se_acelera():
    pasos = [{"mover": {"objeto": "Caja", "eje": "x", "a": [i, 0, 0]}} for i in range(30)]
    linea = linea_de_tiempo(pasos)
    assert linea.duracion == pytest.approx(MAXIMO) and len(linea.pasos) == 30


# --- El validador ------------------------------------------------------------------------------


def test_el_validador_del_molde_esta_registrado(motor):
    funcion = motor.registry.get("taller.molde")
    assert funcion is not None
    params = {"parts": [CUERPO], "mode": "molde", "level": 1}
    from amatista_engine.models import TargetDefinition

    objetivo = TargetDefinition(id="figura", title="Figura", validator="taller.molde", params=params)
    bien = funcion(objetivo, escena_de([CUERPO]))
    mal = funcion(objetivo, Escena().construir())
    assert bien.passed and "en su lugar" in bien.message
    assert not mal.passed and mal.details["molde"]["total"] == 1


def test_parametros_bkt_por_defecto():
    p = ParametrosBKT()
    assert 0 < p.L0 < 0.3 and 0 < p.G < 0.5 and 0 < p.S < 0.5
