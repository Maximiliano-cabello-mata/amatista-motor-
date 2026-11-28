"""credencial.py: el token se guarda fuera de userpref.blend, cifrado en Windows (sin bpy)."""
import importlib.util
import sys
from pathlib import Path

import pytest

_RUTA = Path(__file__).resolve().parents[1] / "amatista_blender" / "credencial.py"
_spec = importlib.util.spec_from_file_location("credencial_prueba", _RUTA)
credencial = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(credencial)

TOKEN = "tok_abcdef0123456789-ÑANDÚ"


def test_guardar_y_leer(tmp_path):
    """Comprueba que el token guardado se recupera igual."""
    credencial.guardar(tmp_path, TOKEN)
    assert credencial.leer(tmp_path) == TOKEN


def test_sin_sesion_devuelve_vacio(tmp_path):
    """Comprueba que sin archivo, o con uno dañado, no hay sesión (no lanza)."""
    assert credencial.leer(tmp_path) == ""
    (tmp_path / credencial.ARCHIVO).write_bytes(b"basura")
    assert credencial.leer(tmp_path) == ""


def test_token_vacio_borra_la_sesion(tmp_path):
    """Comprueba que guardar '' (desvincular) borra el archivo."""
    credencial.guardar(tmp_path, TOKEN)
    credencial.guardar(tmp_path, "")
    assert not (tmp_path / credencial.ARCHIVO).exists()
    credencial.borrar(tmp_path)  # borrar dos veces no falla


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI solo existe en Windows")
def test_windows_el_archivo_va_cifrado(tmp_path):
    """Comprueba que en Windows el token no aparece en claro en el archivo."""
    credencial.guardar(tmp_path, TOKEN)
    contenido = (tmp_path / credencial.ARCHIVO).read_bytes()
    assert contenido.startswith(credencial.CABECERA_DPAPI)
    assert TOKEN.encode("utf-8") not in contenido


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI solo existe en Windows")
def test_windows_otra_entropia_no_descifra(tmp_path, monkeypatch):
    """Comprueba que el cifrado depende de la entropía de Amatista (otro programa no lo descifra sin ella)."""
    credencial.guardar(tmp_path, TOKEN)
    monkeypatch.setattr(credencial, "ENTROPIA", b"otra-app")
    assert credencial.leer(tmp_path) == ""


@pytest.mark.skipif(sys.platform == "win32", reason="en Windows se usa DPAPI")
def test_otros_sistemas_permisos_0600(tmp_path):
    """Comprueba que fuera de Windows el archivo solo lo puede leer su dueño."""
    credencial.guardar(tmp_path, TOKEN)
    assert (tmp_path / credencial.ARCHIVO).stat().st_mode & 0o777 == 0o600
