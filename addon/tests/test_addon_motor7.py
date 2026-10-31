"""Motor 7 en el add-on, sin Blender: lo que no debe volver a pasar.

Lo que necesita Blender de verdad (el guion en el tren, las señales, el
administrador) está en en_blender.py › probar_motor7, y las 100 simulaciones
de alumnos en simular_alumnos.py.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ADDON = RAIZ / "addon" / "amatista_blender"
ENGINE = RAIZ / "engine" / "amatista_engine"


def _codigo(carpeta):
    for ruta in carpeta.rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        # Sin los docstrings y comentarios, que cuentan la historia del error.
        texto = re.sub(r'"""[\s\S]*?"""', "", texto)
        texto = "\n".join(linea.split("#", 1)[0] for linea in texto.splitlines())
        yield ruta, texto


def test_ningun_texto_dice_que_brilla_la_barra_de_la_izquierda():
    for carpeta in (ADDON, ENGINE):
        for ruta, texto in _codigo(carpeta):
            assert not re.search(r"brilla (en la barra )?(de )?(a )?la izquierda", texto), ruta


def test_el_modo_enfocado_no_esconde_la_barra_de_herramientas():
    texto = (ADDON / "enfoque.py").read_text(encoding="utf-8")
    assert "show_region_toolbar = False" not in texto


def test_el_guion_tiene_el_turno_antes_que_el_taller():
    texto = (ADDON / "interfaz" / "turno.py").read_text(encoding="utf-8")
    assert texto.index("return GUION") < texto.index("return TALLER")


def test_el_guion_revisa_al_guardar_y_al_deshacer():
    texto = (ADDON / "guion" / "__init__.py").read_text(encoding="utf-8")
    for manejador in ("depsgraph_update_post", "save_post", "undo_post", "redo_post"):
        assert f'"{manejador}"' in texto


def test_el_texto_solo_dice_resaltado_despues_de_comprobarlo():
    texto = (ADDON / "guion" / "senalar.py").read_text(encoding="utf-8")
    elegir = texto[texto.index("def _elegir"):texto.index("def _abrir_menu")]
    assert elegir.index("herramienta_elegida(context, modo) != d.objetivo") < elegir.index("resaltado")


def test_version_7():
    assert 'version = "7.1.0"' in (ADDON / "blender_manifest.toml").read_text(encoding="utf-8")
    assert "(7, 1, 0)" in (ADDON / "__init__.py").read_text(encoding="utf-8")
