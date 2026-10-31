"""Motor 6.2: el termómetro de ánimo y la luz que se enciende sola según el dominio."""
from amatista_engine.taller import ACOMPANADA, DOMINADA, NUEVA, SOLA
from amatista_engine.taller import acompanamiento as ac


def test_tranquilo_al_empezar():
    s = ac.senales_nuevas(0.0)
    animo = ac.leer_animo(s, 5.0)
    assert animo.nivel == ac.TRANQUILO
    assert animo.razones == ()


def test_tres_fallos_llevan_a_atorado():
    s = ac.senales_nuevas(0.0)
    for _ in range(3):
        s = ac.fallo(s)
    assert ac.leer_animo(s, 10.0).nivel == ac.ATORADO


def test_rafaga_de_clics_y_la_misma_operacion_frustran():
    s = ac.senales_nuevas(0.0)
    for i in range(20):
        s = s.con_operacion(1.0 + i * 0.5, "transform.translate")
    animo = ac.leer_animo(s, 12.0)
    assert animo.nivel in (ac.ATORADO, ac.FRUSTRADO)
    assert "muchos clics en poco tiempo" in animo.razones
    assert "la misma operación una y otra vez" in animo.razones


def test_la_rafaga_vieja_no_cuenta():
    s = ac.senales_nuevas(0.0)
    for i in range(20):
        s = s.con_operacion(1.0 + i * 0.2, "transform.resize")
    assert ac.leer_animo(s, 50.0).razones.count("muchos clics en poco tiempo") == 0


def test_avanzar_calma():
    s = ac.senales_nuevas(0.0)
    for _ in range(3):
        s = ac.fallo(s)
    s = ac.deshizo(ac.deshizo(ac.deshizo(s)))
    assert ac.leer_animo(s, 10.0).nivel in (ac.ATORADO, ac.FRUSTRADO)
    s = ac.avanzo(s, 11.0)
    assert ac.leer_animo(s, 12.0).indice < ac.NIVELES_ANIMO.index(ac.ATORADO)


def test_mucho_rato_sin_avanzar_es_atorado():
    s = ac.senales_nuevas(0.0)
    assert ac.leer_animo(s, 50.0).nivel == ac.DUDA
    assert ac.leer_animo(s, 120.0).nivel == ac.ATORADO


def test_al_principio_todo_encendido():
    luz = ac.luz_para(NUEVA, 0.0)
    assert luz.nivel == ac.PLENA
    assert luz.pieza and luz.herramienta and luz.accion


def test_con_el_curso_se_vuelve_serio():
    temprano = ac.luz_para(ACOMPANADA, 0.1)
    tarde = ac.luz_para(ACOMPANADA, 0.9)
    assert temprano.nivel > tarde.nivel
    assert tarde.nivel == ac.TENUE  # sigue señalando la pieza: nunca a oscuras en algo que no domina
    assert ac.luz_para(DOMINADA, 0.0).nivel == ac.APAGADA


def test_lo_que_no_domina_se_sigue_senalando():
    tarde = ac.luz_para(ACOMPANADA, 0.95, debil=True)
    assert tarde.nivel >= ac.MEDIA
    assert tarde.pieza and tarde.accion
    assert ac.luz_para(ACOMPANADA, 0.95, ac.Animo(ac.DUDA, 0.3), debil=True).herramienta


def test_la_frustracion_sube_la_luz_y_ofrece_pista():
    animo = ac.Animo(ac.FRUSTRADO, 0.9, ("3 intentos sin salir",))
    luz = ac.luz_para(SOLA, 0.6, animo)
    assert luz.nivel > ac.luz_para(SOLA, 0.6).nivel
    assert luz.ofrecer_pista
    assert luz.frase


def test_en_un_reto_la_luz_no_pasa_de_tenue():
    animo = ac.Animo(ac.FRUSTRADO, 0.9)
    luz = ac.luz_para(NUEVA, 0.0, animo, reto=True)
    assert luz.nivel == ac.TENUE
    assert not luz.herramienta and not luz.accion
    assert luz.ofrecer_pista


def test_madurez_y_debiles():
    assert ac.madurez([]) == 0.0
    assert ac.madurez([DOMINADA, DOMINADA]) == 1.0
    assert 0 < ac.madurez([NUEVA, SOLA]) < 1
    fases = {"extruir": NUEVA, "mover": DOMINADA, "escalar": ACOMPANADA}
    assert ac.debiles(fases, {"extruir": 4, "escalar": 1, "mover": 9}) == ("extruir",)
