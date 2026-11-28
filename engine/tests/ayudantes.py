"""Ayudantes de prueba: objetos de escena de la práctica de la mesa (patas, cubierta) y rutas del repo."""
from pathlib import Path

from amatista_engine.models import SceneObject, SceneState

REPO = Path(__file__).resolve().parents[2]
MESA = REPO / "practices" / "archivo" / "v2" / "mesa.json"


def pata(nombre, x, y, alto=0.75):
    """Pata de mesa de prueba en (x, y) con su alto."""
    return SceneObject(nombre, "MESH", roles=("pata",), location=(x, y, alto / 2), dimensions=(0.1, 0.1, alto))


def cubierta(z=0.8, grosor=0.1, **extra):
    """Cubierta de mesa de prueba a la altura ``z`` y grosor dados."""
    return SceneObject(
        "Cubierta", "MESH", roles=("cubierta",), location=(0, 0, z), dimensions=(2.0, 1.0, grosor), **extra
    )


def mesa_completa(guardada=True, **extra):
    """Escena de la mesa completa (cubierta y 4 patas), guardada por defecto."""
    return SceneState(
        blender_version="5.1.1",
        file_path="/tmp/mi_mesa.blend",
        file_saved=guardada,
        objects=(
            cubierta(z=0.75 + 0.05, **extra),
            pata("P1", -0.9, -0.4),
            pata("P2", 0.9, -0.4),
            pata("P3", -0.9, 0.4),
            pata("P4", 0.9, 0.4),
        ),
    )
