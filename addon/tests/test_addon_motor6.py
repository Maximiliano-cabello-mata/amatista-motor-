"""Motor 6 en el add-on, sin Blender: la etapa en el enlace, Blender Amatista y la autosanación.

protocolo.py no importa bpy. saneamiento.py sí, pero sus reglas (qué copia
gana, qué es una copia de Amatista) son Python puro: se carga con un bpy
de mentira. Lo que necesita Blender de verdad está en en_blender.py.
"""
import importlib.util
import sys
import types
from pathlib import Path

ADDON = Path(__file__).resolve().parents[1] / "amatista_blender"


def _cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, ADDON / archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


protocolo = _cargar("amatista_protocolo_m6", "protocolo.py")


def _saneamiento():
    falso = types.ModuleType("bpy")
    falso.app = types.SimpleNamespace(driver_namespace={}, handlers=types.SimpleNamespace(), timers=None)
    anterior = sys.modules.get("bpy")
    sys.modules["bpy"] = falso
    try:
        return _cargar("amatista_saneamiento_m6", "saneamiento.py"), falso
    finally:
        if anterior is None:
            del sys.modules["bpy"]
        else:
            sys.modules["bpy"] = anterior


# --- La etapa viaja en el enlace -------------------------------------------------------------------


def test_el_enlace_lleva_la_etapa_de_la_leccion():
    orden = protocolo.orden_de_url(
        "amatista://taller/blender.bp.m1?etapa=exploracion&habilidades=bl-agregar-primitivas,bl-mover&leccion=bp1_blender")
    assert orden == {"tipo": "taller_abrir", "datos": {
        "taller": "blender.bp.m1", "etapa": "exploracion", "habilidades": ["bl-agregar-primitivas", "bl-mover"],
        "leccion": "bp1_blender"}}


def test_la_etapa_nunca_acepta_rutas_ni_etapas_inventadas():
    orden = protocolo.orden_de_url("amatista://taller/blender.bp.m1?etapa=todo&habilidades=../../x&leccion=/etc/passwd")
    assert orden == {"tipo": "taller_abrir", "datos": {"taller": "blender.bp.m1"}}
    orden = protocolo.orden_de_url("amatista://taller/blender.bp.m1?etapa=exploracion&habilidades=a,b,c,d,e,../x")
    assert orden["datos"]["habilidades"] == ["a", "b", "c", "d"]


# --- Blender Amatista ------------------------------------------------------------------------------


def test_el_enlace_abre_blender_amatista():
    assert "--app-template amatista -- --amatista" in protocolo.comando_linux("/opt/blender/blender", {})
    assert "--app-template amatista" in protocolo.guion_mac("/Applications/Blender.app/Contents/MacOS/Blender")


def test_el_acceso_directo_de_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(protocolo.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    ok, texto = protocolo.crear_lanzador("/opt/blender 4.2/blender", "/x/logo.png")
    assert ok, texto
    contenido = (tmp_path / "applications" / protocolo.DESKTOP_LANZADOR).read_text(encoding="utf-8")
    assert "Name=Blender Amatista" in contenido
    assert "Exec='/opt/blender 4.2/blender' --app-template amatista %f" in contenido
    assert "Icon=/x/logo.png" in contenido


def test_el_acceso_directo_de_windows_escapa_las_comillas():
    guion = protocolo.guion_lanzador_windows("C:/Program Files/Blender's/blender.exe", "C:/Menu/Blender Amatista.lnk")
    assert "Blender''s" in guion and "--app-template amatista" in guion


def test_el_acceso_directo_nunca_lanza():
    assert protocolo.crear_lanzador("") == (False, "No sé dónde está Blender.")


def test_la_plantilla_trae_su_pantalla_de_inicio():
    carpeta = ADDON / "plantilla_amatista"
    for nombre in ("__init__.py", "splash.png", "splash_2x.png"):
        assert (carpeta / nombre).is_file(), nombre
    assert (carpeta / "splash.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# --- Autosanación ----------------------------------------------------------------------------------


def test_reconoce_las_copias_de_amatista():
    s, _bpy = _saneamiento()
    assert s.es_amatista("amatista_blender")
    assert s.es_amatista("bl_ext.user_default.amatista")
    assert s.es_amatista("bl_ext.blender_org.amatista")
    assert s.es_amatista("amatista_blender_5_3")
    assert not s.es_amatista("node_wrangler")
    assert not s.es_amatista("bl_ext.user_default.amatistas_de_otro", {"name": "Otra cosa"})


def test_gana_la_version_mas_nueva_y_a_igual_version_la_extension():
    s, _bpy = _saneamiento()
    ext, clasico = "bl_ext.user_default.amatista", "amatista_blender"
    assert s.gana((6, 0, 0), (5, 4, 0), ext, clasico)
    assert s.gana((6, 0, 0), (5, 4, 0), clasico, ext)
    assert not s.gana((5, 4, 0), (6, 0, 0), ext, clasico)
    assert s.gana((6, 0, 0), (6, 0, 0), ext, clasico)
    assert not s.gana((6, 0, 0), (6, 0, 0), clasico, ext)


def test_la_duena_del_dibujo():
    s, falso = _saneamiento()
    assert s.soy_duena()  # nadie la tomó todavía
    falso.app.driver_namespace[s.CLAVE_DUENA] = "otra_copia"
    assert not s.soy_duena()
    s.tomar()
    assert s.soy_duena()
