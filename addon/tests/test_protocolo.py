"""El enlace amatista:// (amatista_blender/protocolo.py), sin Blender.

protocolo.py no importa bpy: se carga directo del archivo. Las direcciones las
arma frontend/src/services/lanzador.js y las órdenes deben ser las que
backend/api/enlace.py › ORDENES conoce (más «abrir», que solo abre Blender).
"""
import importlib.util
from pathlib import Path

ADDON = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("amatista_protocolo", ADDON / "amatista_blender" / "protocolo.py")
protocolo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocolo)


def test_cada_direccion_pide_su_orden():
    assert protocolo.orden_de_url("amatista://abrir") == {"tipo": "abrir", "datos": {}}
    assert protocolo.orden_de_url("amatista://") == {"tipo": "abrir", "datos": {}}
    assert protocolo.orden_de_url("amatista://practica/blender.n1.mesa") == {
        "tipo": "abrir_practica", "datos": {"practica_id": "blender.n1.mesa"}}
    assert protocolo.orden_de_url("amatista://taller/blender.bp.m1?actividad=conmigo%3Abl-mover%3Abaja") == {
        "tipo": "taller_abrir", "datos": {"taller": "blender.bp.m1", "actividad": "conmigo:bl-mover:baja"}}
    assert protocolo.orden_de_url("amatista://taller/blender.bp.m1") == {
        "tipo": "taller_abrir", "datos": {"taller": "blender.bp.m1"}}
    assert protocolo.orden_de_url("amatista://isla") == {"tipo": "isla", "datos": {}}
    assert protocolo.orden_de_url("amatista://recorrido/vista") == {
        "tipo": "recorrido", "datos": {"accion": "empezar", "recorrido": "vista"}}
    assert protocolo.orden_de_url("amatista://recorrido") == {"tipo": "recorrido", "datos": {"accion": "empezar"}}


def test_tolera_lo_que_agregan_navegadores_y_sistemas():
    # Windows y algunos navegadores agregan una barra final o cambian mayúsculas del esquema.
    assert protocolo.orden_de_url("AMATISTA://practica/blender.n1.mesa/")["datos"] == {"practica_id": "blender.n1.mesa"}
    assert protocolo.orden_de_url("amatista:practica/blender.n1.mesa")["tipo"] == "abrir_practica"
    assert protocolo.orden_de_url(" amatista://isla/ ")["tipo"] == "isla"


def test_nunca_acepta_rutas_ni_codigo():
    # Cualquier página puede pedir un amatista://: solo se eligen actividades con un id simple.
    for url in ("amatista://practica/../../etc/passwd", "amatista://practica/%2E%2E%2Fsecreto",
                "amatista://practica/a b", "amatista://practica/" + "x" * 200, "amatista://borrar/todo",
                "https://ejemplo.com/practica/x", "", None, "amatista://practica/"):
        orden = protocolo.orden_de_url(url)
        assert orden is None or orden["tipo"] == "abrir" and orden["datos"] == {}, url
    orden = protocolo.orden_de_url("amatista://taller/blender.bp.m1?actividad=../../x")
    assert orden["datos"] == {"taller": "blender.bp.m1"}
    assert protocolo.orden_de_url("amatista://recorrido/otra")["datos"] == {"accion": "empezar"}


def test_lee_la_direccion_de_los_argumentos_de_blender():
    assert protocolo.url_de_argumentos(["blender", "--", "--amatista", "amatista://isla"]) == "amatista://isla"
    assert protocolo.url_de_argumentos(["blender", "--", "--amatista=amatista://isla"]) == "amatista://isla"
    assert protocolo.url_de_argumentos(["blender", "--", "amatista://isla"]) == "amatista://isla"
    assert protocolo.url_de_argumentos(["blender", "--amatista", "amatista://isla"]) == ""  # antes de «--» es de Blender
    assert protocolo.url_de_argumentos(["blender", "archivo.blend"]) == ""
    assert protocolo.url_de_argumentos(["blender", "--", "--amatista"]) == ""


def test_linux_registra_el_esquema_con_la_ruta_de_blender(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(protocolo.subprocess, "run", lambda *a, **k: None)
    texto = protocolo._registrar_linux("/opt/blender 4.2/blender")
    archivo = tmp_path / "applications" / protocolo.DESKTOP_LINUX
    assert str(archivo) in texto
    contenido = archivo.read_text(encoding="utf-8")
    assert "Exec='/opt/blender 4.2/blender' -- --amatista %u" in contenido
    assert "MimeType=x-scheme-handler/amatista;" in contenido


def test_flatpak_y_snap_se_abren_desde_fuera_de_su_caja():
    assert protocolo.comando_linux("/app/blender/blender", {"FLATPAK_ID": "org.blender.Blender"}) == \
        "flatpak run org.blender.Blender -- --amatista %u"
    assert protocolo.comando_linux("/snap/blender/5/blender", {"SNAP": "/snap/blender/5"}).startswith("/snap/bin/blender ")


def test_el_guion_de_macos_pasa_la_direccion_entre_comillas():
    guion = protocolo.guion_mac('/Applications/Blender "4.2".app/Contents/MacOS/Blender')
    assert "on open location direccion" in guion
    assert 'quoted form of direccion' in guion
    assert '\\"4.2\\"' in guion


def test_registrar_nunca_lanza():
    assert protocolo.registrar("") == (False, "No sé dónde está Blender.")
