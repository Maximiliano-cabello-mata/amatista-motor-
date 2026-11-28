# [REVISION-BUG] ``import os`` está ANTES del docstring: el texto de abajo ya no es el docstring del módulo (__doc__ es None). Mover el import debajo.
import os
"""Motor 6.2 en el add-on, sin Blender: la versión, los instaladores y sus scripts.

Lo que necesita Blender de verdad (cambio limpio, «Volver a mi práctica», el
acompañamiento) está en en_blender.py › probar_motor62.
"""
import importlib.util
import struct
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ADDON = RAIZ / "addon" / "amatista_blender"
HERRAMIENTAS = RAIZ / "addon" / "herramientas"


def _instaladores():
    """Carga herramientas/instaladores.py."""
    spec = importlib.util.spec_from_file_location("amatista_instaladores", HERRAMIENTAS / "instaladores.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_version_62():
    """Comprueba la versión del add-on en manifiesto y ajustes."""
    manifiesto = (ADDON / "blender_manifest.toml").read_text(encoding="utf-8")
    assert 'version = "7.1.0"' in manifiesto  # motor 7 (test_addon_motor7.py) sigue sobre el 6.2
    assert 'VERSION_ADDON = "7.1.0"' in (ADDON / "ajustes.py").read_text(encoding="utf-8")


def test_preparar_lleva_lo_necesario(tmp_path):
    """Comprueba que la carpeta común del instalador trae zip, scripts, licencia e icono."""
    inst = _instaladores()
    comun = inst.preparar(tmp_path / "comun")
    nombres = {p.name for p in comun.iterdir()}
    assert {f"amatista-{inst.version()}.zip", "instalar_en_blender.py", "desinstalar_en_blender.py", "LICENSE.txt",
            "amatista.ico", "amatista.png", "VERSION"} <= nombres
    ico = (comun / "amatista.ico").read_bytes()
    reservado, tipo, cuantas = struct.unpack("<HHH", ico[:6])
    assert (reservado, tipo) == (0, 1) and cuantas >= 1


def test_el_instalador_de_windows_usa_lo_que_prepara():
    """Comprueba que el .iss de Windows usa los archivos preparados y no pide administrador."""
    iss = (HERRAMIENTAS / "instalador" / "windows" / "amatista.iss").read_text(encoding="utf-8")
    for nombre in ("instalar_en_blender.py", "desinstalar_en_blender.py", "amatista.ico", "LICENSE.txt"):
        assert nombre in iss
    assert "PrivilegesRequired=lowest" in iss  # sin administrador
    assert "amatista-{#Version}.zip" in iss
    assert "Spanish.isl" in iss


def test_lanzador_linux_es_bash_valido():
    """Comprueba que el lanzador de Linux es bash válido y abre la plantilla."""
    lanzador = HERRAMIENTAS / "instalador" / "linux" / "amatista"
    if sys.platform.startswith("win"):
        pytest.skip("bash no está en Windows")
    subprocess.run(["bash", "-n", str(lanzador)], check=True)
    texto = lanzador.read_text(encoding="utf-8")
    assert "--app-template amatista" in texto and "--amatista" in texto


def test_arbol_deb(tmp_path):
    """Comprueba el árbol del paquete .deb."""
    inst = _instaladores()
    comun = inst.preparar(tmp_path / "comun")
    raiz = inst.armar_arbol_deb(comun, tmp_path / "deb")
    control = (raiz / "DEBIAN" / "control").read_text(encoding="utf-8")
    assert f"Version: {inst.version()}" in control and "Architecture: all" in control
    if os.name != "nt":
        assert (raiz / "usr" / "bin" / "amatista").stat().st_mode & 0o111
    assert (raiz / "usr" / "share" / "applications" / "amatista.desktop").is_file()
    assert (raiz / "usr" / "share" / "amatista" / f"amatista-{inst.version()}.zip").is_file()
