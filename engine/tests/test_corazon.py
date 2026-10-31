"""Corazón Amatista (amatista.corazon/1): contrato, señales que no caducan, andamio, extensiones y ramas."""
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from amatista_engine import corazon, create_default_engine
from amatista_engine.cli import PRACTICAS
from amatista_engine.corazon import andamiaje, contrato as c, extensiones, perfiles, ramas, senales
from amatista_engine.corazon.adaptador import AdaptadorBase, Capacidades
from amatista_engine.corazon.conformidad import revisar_adaptador
from amatista_engine.corazon.perfiles.aframe import escena_desde_foto
from amatista_engine.corazon.simulado import AdaptadorSimulado
from amatista_engine.guion import guion_de_practica
from amatista_engine.models import SceneObject, SceneState, ValidationResult
from amatista_engine.practice import load_practice

TREN = PRACTICAS / "principiante" / "m1-tren" / "practica.json"
RAMAS = Path(__file__).resolve().parents[2] / "practices" / "ramas"
BLENDER = perfiles.perfil("blender")


class Reporte:
    def __init__(self, ids, pasados=(), completo=False, mensajes=None):
        mensajes = mensajes or {}
        self.results = tuple(ValidationResult(t, "x", t in pasados, mensajes.get(t, f"falta {t}")) for t in ids)
        self.completed = completo
        self.paused_by = None
        self.guards = ()


@pytest.fixture(scope="module")
def tren():
    return load_practice(TREN)


@pytest.fixture
def ids(tren):
    return tuple(p.id for p in guion_de_practica(tren).pasos)


def _director(tren, adaptador=None, **kw):
    adaptador = adaptador or AdaptadorSimulado(BLENDER)
    return corazon.Director(tren, BLENDER, adaptador.capacidades(), **kw), adaptador


# --- Contrato y perfiles ------------------------------------------------------------------------


def test_el_contrato_tiene_version_y_el_corazon_no_importa_bpy():
    assert corazon.CONTRATO == "amatista.corazon/1" and corazon.VERSION.startswith("1.")
    carpeta = Path(corazon.__file__).parent
    for archivo in carpeta.rglob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+bpy\b", archivo.read_text(encoding="utf-8"), re.M), archivo


def test_cada_perfil_ubica_las_herramientas_base():
    todos = perfiles.todos()
    assert {"blender", "aframe", "maya", "3dsmax"} <= set(todos)
    for nombre, p in todos.items():
        assert not p.faltan(), (nombre, p.faltan())
        for h, lugar in p.lugares.items():
            assert lugar.herramienta == h and lugar.lugar and lugar.tipo in c.TIPOS_LUGAR, (nombre, h)
    assert todos["maya"].estado == todos["3dsmax"].estado == "borrador"


def test_el_perfil_de_blender_es_la_tabla_del_guion():
    from amatista_engine.guion import donde

    assert set(BLENDER.lugares) == set(donde.TABLA)
    for clave, d in donde.TABLA.items():  # las mismas frases que el motor 7: una sola fuente
        for idioma in ("es", "en"):
            assert BLENDER.frase(BLENDER.lugar(clave), idioma) == donde.frase(d, idioma), (clave, idioma)
    assert BLENDER.frase(BLENDER.lugar("object.add"), "es", "cylinder").startswith("Agregar › Malla › Cilindro")
    assert "Add (Agregar)" in BLENDER.frase(BLENDER.lugar("object.add"), "en", "cylinder")
    assert BLENDER.lugar("modifier.bevel") is BLENDER.lugar("modifier")  # cae a la raíz


def test_ninguna_frase_de_ningun_perfil_dice_que_algo_brilla():
    for p in perfiles.todos().values():
        for lugar in p.lugares.values():
            assert not re.search(r"brilla|ilumina", p.frase(lugar), re.I), (p.software, lugar.herramienta)


def test_la_foto_del_motor_web_es_una_escena_del_corazon():
    escena = escena_desde_foto({"objetos": {"caja": {"x": 1, "y": 0.5, "z": 2, "tocado": True}},
                                "zonas": {"meta": {"x": 0, "z": 0, "radio": 1.5}}})
    caja = next(o for o in escena.objects if o.name == "caja")
    meta = next(o for o in escena.objects if o.name == "meta")
    assert caja.location == (1.0, -2.0, 0.5) and "tocado" in caja.tags  # z arriba, como Blender
    assert meta.object_type == "EMPTY" and meta.dimensions[0] == 3.0 and "zona" in meta.tags


# --- Señales -------------------------------------------------------------------------------------


def test_la_senal_cae_a_decir_si_el_programa_no_sabe_hacerla():
    lugar = BLENDER.lugar("transform.move")
    solo_texto = Capacidades("blender")
    s = senales.elegir(lugar, BLENDER, solo_texto, a_pedido=True)
    assert s.tipo == c.DECIR and not s.texto_hecho and "barra de herramientas" in s.texto_base
    s = senales.elegir(lugar, BLENDER, Capacidades("blender", senales=frozenset({c.ELEGIR_HERRAMIENTA})), a_pedido=False)
    assert s.tipo == c.ELEGIR_HERRAMIENTA and "Te dejé elegida «Mover»" in s.texto_hecho


def test_un_menu_no_se_abre_solo():
    todo = Capacidades("blender", senales=frozenset(c.TIPOS_SENAL))
    agregar = BLENDER.lugar("object.add")
    assert senales.elegir(agregar, BLENDER, todo, a_pedido=False).tipo == c.DECIR
    assert senales.elegir(agregar, BLENDER, todo, a_pedido=True).tipo == c.ABRIR_MENU


def test_solo_se_dice_lo_que_el_programa_confirmo():
    s = senales.elegir(BLENDER.lugar("transform.scale"), BLENDER,
                       Capacidades("blender", senales=frozenset({c.ELEGIR_HERRAMIENTA})), a_pedido=True)
    e = senales.iniciar(s, 0)
    assert "Te dejé" not in e.texto  # propuesta: todavía no se hizo
    fallida = senales.tras_ejecutar(e, c.ResultadoSenal(False, "sin barra"), 1)
    assert fallida.estado == c.FALLIDA and "Te dejé" not in fallida.texto and fallida.se_puede_repetir
    vigente = senales.tras_ejecutar(e, c.ResultadoSenal(True), 1)
    assert vigente.estado == c.VIGENTE and "Te dejé elegida «Escalar»" in vigente.texto


def test_la_senal_no_caduca_por_reloj_solo_si_deja_de_ser_verdad():
    s = senales.elegir(BLENDER.lugar("transform.move"), BLENDER,
                       Capacidades("blender", senales=frozenset({c.ELEGIR_HERRAMIENTA})), a_pedido=True)
    e = senales.tras_ejecutar(senales.iniciar(s, 0), c.ResultadoSenal(True), 0)
    una_hora = senales.revisar(e, True, 3600)
    assert una_hora.estado == c.VIGENTE  # sigue elegida: sigue diciéndose
    perdida = senales.revisar(una_hora, False, 3601)
    assert perdida.estado == c.PERDIDA and "otra herramienta" in perdida.texto and perdida.se_puede_repetir


# --- Andamio -------------------------------------------------------------------------------------


def test_el_andamio_se_retira_con_el_uso_y_vuelve_con_los_tropiezos():
    h = andamiaje.Historial()
    pasos = []
    for _ in range(5):
        pasos.append(andamiaje.escalon(h.uso("transform.move"), 0))
        andamiaje.registrar(h, "transform.move", con_ayuda=False, ahora=0)
    assert pasos == ["mostrar", "senalar", "senalar", "recordar", "recordar"]
    assert andamiaje.escalon(h.uso("transform.move"), 0) == "reto"
    andamiaje.tropezar(h, "transform.move", 0)
    assert andamiaje.escalon(h.uso("transform.move"), 0) == "recordar"
    andamiaje.registrar(h, "transform.move", con_ayuda=True, ahora=0)  # con ayuda no sube ni borra tropiezos
    assert andamiaje.escalon(h.uso("transform.move"), 0) == "recordar"


def test_lo_que_no_se_usa_en_una_semana_baja_un_escalon():
    u = andamiaje.Uso(solos=5, ultimo=1)
    assert andamiaje.escalon(u, 3 * andamiaje.DIA) == "reto"
    assert andamiaje.escalon(u, 8 * andamiaje.DIA) == "recordar"


def test_el_historial_se_guarda_y_se_lee():
    h = andamiaje.Historial()
    andamiaje.registrar(h, "object.add", con_ayuda=False, ahora=10)
    datos = json.loads(json.dumps(h.como_dict()))
    assert andamiaje.Historial.desde_dict(datos).uso("object.add").solos == 1
    assert andamiaje.Historial.desde_dict("basura").usos == {}
    assert andamiaje.desde_fases({"transform.move": "sola"}).uso("transform.move").solos == 3


# --- Director ------------------------------------------------------------------------------------


def test_el_director_senala_solo_la_primera_vez_y_lo_comprueba(tren, ids):
    d, programa = _director(tren)
    t = d.ciclo(programa, Reporte(ids), 0)
    assert t.modo == c.TRABAJANDO and t.numero == 1 and t.nivel == "mostrar"
    assert t.donde and "Agregar" in t.donde  # dónde está, siempre
    # Agregar es un menú: no se abre solo; la señal es decir dónde está.
    assert t.senal is not None and t.senal.senal.tipo == c.DECIR
    # Los vagones están: el paso de estirarlos usa Escalar y la barra sí se elige sola.
    t = d.ciclo(programa, Reporte(ids, {"vagones", "ruedas", "ruedas-de-pie", "chimenea"}), 1)
    assert t.paso_id == "vagones-largos" and t.senal.estado == c.VIGENTE
    assert programa.activa == "builtin.scale" and "Te dejé elegida «Escalar»" in t.senal.texto
    programa.elegir_otra("builtin.move")  # el alumno cambia de herramienta
    t = d.ciclo(programa, None, 2)
    assert t.senal.estado == c.PERDIDA and "Escalar" in t.senal.texto and t.senal.se_puede_repetir
    d.repetir_senal(3)
    t = d.ciclo(programa, None, 3)
    assert t.senal.estado == c.VIGENTE and programa.activa == "builtin.scale"


def test_la_senal_del_paso_anterior_no_se_arrastra(tren, ids):
    d, programa = _director(tren)
    d.ciclo(programa, Reporte(ids, {"vagones", "ruedas", "ruedas-de-pie", "chimenea"}), 0)
    assert d.senal is not None and d.senal.senal.herramienta == "transform.scale"
    t = d.ciclo(programa, Reporte(ids, {"vagones", "ruedas", "ruedas-de-pie", "chimenea", "vagones-largos"}), 1)
    assert t.paso_id != "vagones-largos"
    assert t.senal is None or t.senal.senal.herramienta == t.herramienta


def test_quien_ya_sabe_no_recibe_la_senal_sola(tren, ids):
    h = andamiaje.Historial({"transform.scale": andamiaje.Uso(solos=5, ultimo=0)})
    d, programa = _director(tren, historial=h)
    t = d.ciclo(programa, Reporte(ids, {"vagones", "ruedas", "ruedas-de-pie", "chimenea"}), 0)
    assert t.nivel == "reto" and t.senal is None and t.donde == "" and programa.activa == ""
    assert not t.sugerir_pista
    t = d.ciclo(programa, None, 200)
    assert t.sugerir_pista  # lleva rato: se ofrece la pista, no se impone


def test_las_pistas_son_del_paso_que_toca_y_marcan_ayuda(tren, ids):
    d, programa = _director(tren)
    programa.escena = SceneState(blender_version="", file_path="", file_saved=False,
                                 objects=(SceneObject("Cylinder.003", "MESH"),))
    hechos = {"vagones", "vagones-largos"}
    d.ciclo(programa, Reporte(ids, hechos, mensajes={"ruedas": "«Cylinder.003» está separado de «Vagón»"}), 0)
    p1 = d.pedir_pista(1, nivel=1)
    assert p1.titulo == "¿Qué falta?" and "Cylinder.003" in p1.texto
    d.ciclo(programa, None, 1)
    assert d.senal.senal.tipo == c.SELECCIONAR and programa.escena.selected == ("Cylinder.003",)
    assert "Lo dejé seleccionado" in d.turno(1).senal.texto
    p2 = d.pedir_pista(2, nivel=2)
    assert p2.titulo == "¿Dónde está?" and "Agregar" in p2.texto
    p3 = d.pedir_pista(3, nivel=3)
    assert p3.titulo == "¿Cómo se hace?"
    d.observar(Reporte(ids, hechos | {"ruedas"}), 5)
    assert d.historial.uso("object.add").ayudados == 1 and d.historial.uso("object.add").solos == 0


def test_terminar_y_deshacer(tren, ids):
    d, programa = _director(tren)
    t = d.ciclo(programa, Reporte(ids, set(ids), completo=True), 0)
    assert t.modo == c.TERMINADO and t.completo and t.ultimo.startswith("¡Terminado!")
    t = d.ciclo(programa, Reporte(ids, set(ids) - {"chimenea"}), 1)
    assert t.modo == c.TRABAJANDO and t.paso_id == "chimenea" and "Se deshizo" in t.ultimo
    assert d.historial.uso(d.guion.paso("chimenea").herramienta).tropiezos == 1


def test_el_ultimo_aviso_no_desaparece_solo(tren, ids):
    d, programa = _director(tren)
    d.ciclo(programa, Reporte(ids), 0)
    d.ciclo(programa, Reporte(ids, {"vagones"}), 1)
    assert d.turno(1).ultimo.startswith("Listo") and d.turno(10_000).ultimo == d.turno(1).ultimo


def test_el_turno_se_vuelve_json(tren, ids):
    d, programa = _director(tren)
    t = d.ciclo(programa, Reporte(ids), 0)
    datos = json.loads(json.dumps(t.como_dict(), ensure_ascii=False))
    assert datos["contrato"] == "amatista.corazon/1" and datos["senal"]["tipo"] == "decir" and datos["pasos"]


def test_con_el_motor_de_verdad(tren):
    d, programa = _director(tren)
    reporte = create_default_engine().evaluate(tren, programa.capturar())
    t = d.ciclo(programa, reporte, 0)
    assert t.numero == 1 and t.total == d.guion.total and not t.completo


# --- Extensiones ---------------------------------------------------------------------------------


def test_una_extension_cambia_el_comportamiento_sin_tocar_el_corazon(tren, ids):
    vistos = []
    ext = corazon.Extension("mia", aporta={
        "observadores": [lambda ev, turno: vistos.append(ev.tipo)],
        "turno": [lambda t: replace(t, haz=t.haz + " (rama de prueba)")],
        "pasos": [lambda p, practica: replace(p, titulo=p.titulo.upper())],
    })
    exts = corazon.Extensiones()
    exts.instalar(ext)
    d, programa = _director(tren, extensiones=exts)
    t = d.ciclo(programa, Reporte(ids), 0)
    assert t.haz.endswith("(rama de prueba)") and d.guion.pasos[0].titulo.isupper()
    d.ciclo(programa, Reporte(ids, {"vagones"}), 1)
    assert c.PRACTICA_ABIERTA in vistos and c.PASO_HECHO in vistos


def test_una_extension_que_falla_no_rompe_nada(tren, ids):
    def rompe(*_):
        raise RuntimeError("ups")

    exts = corazon.Extensiones()
    exts.instalar(corazon.Extension("rota", aporta={"turno": [rompe], "andamio": [rompe], "observadores": [rompe]}))
    d, programa = _director(tren, extensiones=exts)
    t = d.ciclo(programa, Reporte(ids), 0)
    assert t.numero == 1 and any("rota › turno" in e for e in exts.errores)


def test_las_extensiones_piden_el_contrato_correcto():
    exts = corazon.Extensiones()
    with pytest.raises(extensiones.ErrorExtension, match="corazon/2"):
        exts.instalar(corazon.Extension("futura", requiere="2"))
    with pytest.raises(extensiones.ErrorExtension, match="no existen"):
        exts.instalar(corazon.Extension("rara", aporta={"magia": []}))
    exts.instalar(corazon.Extension("a"))
    with pytest.raises(extensiones.ErrorExtension, match="ya está"):
        exts.instalar(corazon.Extension("a"))


def test_rescate_tras_tropiezos_vuelve_a_mostrar(tren, ids):
    exts = corazon.Extensiones()
    exts.instalar(extensiones.crear("rescate-tras-tropiezos"))
    h = andamiaje.Historial({"object.add": andamiaje.Uso(solos=9)})
    d, _ = _director(tren, extensiones=exts, historial=h)
    assert d.escalon("object.add") == "reto"
    d.tropiezos_seguidos = 3
    assert d.escalon("object.add") == "mostrar"


def test_vistas_espaciales_agrega_una_cuarta_pista(tren, ids):
    exts = corazon.Extensiones()
    exts.instalar(extensiones.crear("vistas-espaciales"))
    d, programa = _director(tren, extensiones=exts)
    t = d.ciclo(programa, Reporte(ids, {"vagones", "ruedas", "ruedas-de-pie", "chimenea"}), 0)
    assert "¿Desde otro ángulo?" in t.pistas
    p = d.pedir_pista(0, 4)
    assert p.titulo == "¿Desde otro ángulo?" and "7" in p.texto


# --- Ramas ---------------------------------------------------------------------------------------


def test_las_ramas_del_repositorio_estan_bien():
    todas = ramas.cargar_ramas(RAMAS)
    assert {"blender-principiante", "blender-reto", "aframe-web"} <= set(todas)
    assert ramas.revisar(todas) == ()


def test_una_rama_hereda_y_quita(tren, ids):
    todas = ramas.cargar_ramas(RAMAS)
    reto = ramas.resolver(todas["blender-reto"], todas)
    assert reto.software == "blender" and reto.senal_sola is False
    assert "rescate-tras-tropiezos" in reto.extensiones and "vistas-espaciales" not in reto.extensiones
    d = ramas.crear_director(tren, todas["blender-reto"], adaptador=AdaptadorSimulado(BLENDER), todas=todas)
    t = d.ciclo(AdaptadorSimulado(BLENDER), Reporte(ids), 0)
    assert t.nivel == "reto" and t.senal is None


def test_una_rama_mal_escrita_se_explica():
    with pytest.raises(ramas.ErrorRama, match="formato"):
        ramas.rama_desde_dict({"id": "x"})
    with pytest.raises(ramas.ErrorRama, match="andamio no tiene"):
        ramas.rama_desde_dict({"formato": ramas.FORMATO, "id": "x", "andamio": {"magia": 1}})
    a = ramas.rama_desde_dict({"formato": ramas.FORMATO, "id": "a", "hereda": "b", "software": "blender"})
    b = ramas.rama_desde_dict({"formato": ramas.FORMATO, "id": "b", "hereda": "a"})
    assert any("círculo" in p for p in ramas.revisar({"a": a, "b": b}))
    z = ramas.rama_desde_dict({"formato": ramas.FORMATO, "id": "z", "software": "zbrush", "extensiones": ["nada"]})
    problemas = ramas.revisar({"z": z})
    assert any("nada" in p for p in problemas) and any("zbrush" in p for p in problemas)


# --- Conformidad ---------------------------------------------------------------------------------


def test_el_adaptador_simulado_cumple_el_contrato():
    for p in perfiles.todos().values():
        assert revisar_adaptador(AdaptadorSimulado(p)) == [], p.software


def test_la_conformidad_encuentra_un_adaptador_mentiroso():
    class Mentiroso(AdaptadorBase):
        def capacidades(self):
            return Capacidades("blender", senales=frozenset({c.DECIR, c.ELEGIR_HERRAMIENTA}))

        def ejecutar(self, senal):
            return c.ResultadoSenal(True)  # dice que todo lo hizo

    problemas = revisar_adaptador(Mentiroso(BLENDER))
    assert any("sin saber hacerla" in p for p in problemas)
    assert any("comprobar() dice que no" in p for p in problemas)
