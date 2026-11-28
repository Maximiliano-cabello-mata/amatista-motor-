"""direcciones.py: el token solo viaja por https:// (o http:// hacia esta misma PC). Sin bpy."""
import importlib.util
from pathlib import Path

import pytest

_RUTA = Path(__file__).resolve().parents[1] / "amatista_blender" / "direcciones.py"
_spec = importlib.util.spec_from_file_location("direcciones_prueba", _RUTA)
direcciones = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(direcciones)


@pytest.mark.parametrize("url", [
    "https://api.amatista-3dt.tech",
    "https://api.amatista-3dt.tech/api/auth/yo",
    "HTTPS://Servidor.Escuela.mx:8443",
    "http://localhost:8000",
    "http://LOCALHOST:8000/api",
    "http://127.0.0.1:8000",
    "http://127.5.6.7",
    "http://[::1]:8000",
    "http://amatista.localhost:8000",
])
def test_acepta_https_y_http_local(url):
    """Comprueba que https:// y http:// hacia esta PC se aceptan."""
    assert direcciones.revisar_servidor(url) is None


@pytest.mark.parametrize("url", [
    "http://api.amatista-3dt.tech",
    "http://192.168.1.20:8000",
    "http://10.0.0.5",
    "http://localhost.atacante.com",
    "http://127.0.0.1.nip.io",
    "http://0.0.0.0:8000",
])
def test_rechaza_http_hacia_otro_equipo(url):
    """Comprueba que http:// hacia cualquier otro equipo se rechaza con el aviso de seguridad."""
    assert direcciones.revisar_servidor(url) == direcciones.ERROR_HTTP


@pytest.mark.parametrize("url", ["", "file:///C:/secreto.txt", "ftp://servidor", "api.amatista-3dt.tech", "https://", None])
def test_rechaza_esquemas_raros_o_vacios(url):
    """Comprueba que una dirección vacía, sin esquema o con file:// / ftp:// se rechaza."""
    assert direcciones.revisar_servidor(url) == direcciones.ERROR_ESQUEMA
