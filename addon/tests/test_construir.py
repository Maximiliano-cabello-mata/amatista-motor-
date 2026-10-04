"""El constructor del add-on (sin Blender): contenido, determinismo y config."""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "herramientas"))

import construir  # noqa: E402


def _zip(datos):
    return zipfile.ZipFile(io.BytesIO(datos))


def test_extension_trae_manifiesto_motor_y_practicas():
    nombres = _zip(construir.construir_extension()).namelist()
    assert "blender_manifest.toml" in nombres
    assert "__init__.py" in nombres
    assert "amatista_engine/engine.py" in nombres
    assert "amatista_engine/tools/catalogo.json" in nombres
    assert "practicas/level_1/mesa.json" in nombres
    assert "iconos/logo.png" in nombres
    assert not [n for n in nombres if "__pycache__" in n or n.startswith("tests/") or n.endswith(".pyc")]
    assert nombres.count("config.json") == 1


def test_mismo_codigo_mismo_zip():
    assert construir.construir_extension() == construir.construir_extension()


def test_config_con_direcciones_y_vinculo():
    datos = construir.construir_extension(
        servidor="https://api.amatista.cl/", plataforma="https://amatista.cl",
        vinculo={"id": "v1", "secreto": "s3", "otro": "no"},
    )
    config = json.loads(_zip(datos).read("config.json"))
    assert config == {
        "servidor": "https://api.amatista.cl", "plataforma": "https://amatista.cl",
        "canal": "estable", "vinculo": {"id": "v1", "secreto": "s3"},
    }


@pytest.mark.parametrize("sistema", construir.SISTEMAS)
def test_paquete_por_sistema(sistema):
    zf = _zip(construir.construir_paquete(sistema))
    lanzador, permisos = construir.LANZADORES[sistema]
    nombres = zf.namelist()
    assert f"Amatista/{lanzador}" in nombres
    assert "Amatista/instalar_en_blender.py" in nombres
    assert f"Amatista/{construir.nombre_extension()}" in nombres
    leeme = zf.read("Amatista/LEEME.txt").decode("utf-8")
    assert lanzador in leeme and "{{" not in leeme
    assert (zf.getinfo(f"Amatista/{lanzador}").external_attr >> 16) & 0o777 == permisos
    script = zf.read(f"Amatista/{lanzador}")
    if sistema == "windows":
        assert b"\r\n" in script and b"\n" not in script.replace(b"\r\n", b"")
    else:
        assert b"\r" not in script and script.startswith(b"#!")


def test_sistema_desconocido():
    with pytest.raises(ValueError):
        construir.construir_paquete("amiga")


def test_indice_de_repositorio():
    datos = construir.construir_extension()
    indice = construir.indice_repositorio(datos, "https://x/amatista.zip")
    entrada = indice["data"][0]
    assert indice["version"] == "v1"
    assert entrada["id"] == "amatista"
    assert entrada["version"] == construir.VERSION
    assert entrada["blender_version_min"] == "4.2.0"
    assert entrada["archive_hash"] == "sha256:" + hashlib.sha256(datos).hexdigest()
    assert entrada["archive_size"] == len(datos)
    assert set(entrada["permissions"]) == {"network", "files"}


def test_manifiesto_y_bl_info_coinciden():
    texto = (construir.ADDON / "__init__.py").read_text(encoding="utf-8")
    version = tuple(int(n) for n in construir.VERSION.split("."))
    assert f'"version": {version}' in texto
