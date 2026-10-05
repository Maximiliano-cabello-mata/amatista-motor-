"""integridad.py: el add-on reconoce si su copia es la oficial (sin red, sin bpy)."""
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "herramientas"))

import construir  # noqa: E402


def cargar_integridad(carpeta: Path):
    spec = importlib.util.spec_from_file_location(f"integridad_{id(carpeta)}", carpeta / "integridad.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def instalar(tmp_path: Path, **opciones) -> Path:
    carpeta = tmp_path / "amatista"
    zipfile.ZipFile(io.BytesIO(construir.construir_extension(**opciones))).extractall(carpeta)
    return carpeta


def test_copia_oficial(tmp_path):
    carpeta = instalar(tmp_path, vinculo={"id": "v", "secreto": "s"})
    (carpeta / "__pycache__").mkdir()  # Blender crea cachés: no cuentan
    (carpeta / "__pycache__" / "x.pyc").write_bytes(b"x")
    revision = cargar_integridad(carpeta).revisar()
    assert revision["estado"] == "oficial"
    assert revision["huella"] == construir.huella_oficial()


def test_copia_modificada_o_con_archivos_extra(tmp_path):
    carpeta = instalar(tmp_path)
    red = carpeta / "red.py"
    red.write_text(red.read_text(encoding="utf-8") + "\n# cambio\n", encoding="utf-8")
    (carpeta / "trampa.py").write_text("print('hola')\n", encoding="utf-8")
    revision = cargar_integridad(carpeta).revisar()
    assert revision["estado"] == "modificada"
    assert set(revision["cambios"]) == {"red.py", "trampa.py"}


def test_desde_el_repositorio_es_desarrollo():
    carpeta = Path(__file__).resolve().parents[1] / "amatista_blender"
    assert cargar_integridad(carpeta).revisar()["estado"] == "desarrollo"
