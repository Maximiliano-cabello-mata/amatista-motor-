"""Motor 6.1 en el add-on, sin Blender: Blender sabe en qué lección va la plataforma y las fichas se empaquetan.

plataforma.py no importa bpy. Lo que necesita Blender de verdad (la ficha en la tarjeta, el modo curioso,
el brillo en otras zonas) está en en_blender.py › probar_motor61.
"""
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ADDON = RAIZ / "addon" / "amatista_blender"


def _cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, ADDON / archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


plataforma = _cargar("amatista_plataforma_m61", "plataforma.py")


def setup_function():
    plataforma.reiniciar()


def test_blender_sabe_en_que_leccion_va_la_plataforma():
    assert plataforma.texto_corto() == "" and not plataforma.viva()
    cambio = plataforma.recibir({"curso": "blender_principiante", "leccion": "bp2_explora", "clase": "teoria",
                                 "titulo": "Extruir, cortar y limpiar", "numero": 3, "total": 5}, ahora=100.0)
    assert cambio
    assert plataforma.viva(ahora=120.0)
    assert plataforma.texto_corto(ahora=120.0) == "Lección 3 de 5 · Extruir, cortar y limpiar (teoría)"
    assert plataforma.ruta() == "#/curso/blender_principiante/leccion/bp2_explora"
    # La misma lección otra vez (la plataforma la repite mientras está a la vista) no es un cambio.
    assert not plataforma.recibir({"curso": "blender_principiante", "leccion": "bp2_explora"}, ahora=150.0)


def test_la_plataforma_cerrada_se_olvida():
    plataforma.recibir({"curso": "c", "leccion": "l", "titulo": "T"}, ahora=0.0)
    assert plataforma.viva(ahora=plataforma.VIVA - 1)
    assert not plataforma.viva(ahora=plataforma.VIVA + 1)
    assert plataforma.actual(ahora=plataforma.VIVA + 1) is None
    assert plataforma.frase_al_volver("l", ahora=plataforma.VIVA + 1) == ""


def test_al_cumplir_la_etapa_blender_dice_a_donde_paso_la_leccion():
    plataforma.recibir({"curso": "c", "leccion": "bp2_blender", "clase": "blender", "titulo": "Explora"}, ahora=0.0)
    assert "ya lo sabe" in plataforma.frase_al_volver("bp2_blender", ahora=1.0)  # todavía no avanzó
    plataforma.recibir({"curso": "c", "leccion": "bp2_explora", "clase": "teoria", "titulo": "Extruir"}, ahora=5.0)
    frase = plataforma.frase_al_volver("bp2_blender", ahora=6.0)
    assert "«Extruir»" in frase and "teoría" in frase


def test_datos_raros_no_rompen_nada():
    assert not plataforma.recibir(None)
    assert not plataforma.recibir({"leccion": ""})
    plataforma.recibir({"leccion": "x" * 500, "clase": "inventada", "numero": "muchos", "total": 10 ** 9}, ahora=0.0)
    assert len(plataforma.LECCION["leccion"]) == 120
    assert plataforma.LECCION["clase"] == "teoria"
    assert plataforma.LECCION["numero"] == 0 and plataforma.LECCION["total"] == 99
    assert plataforma.ruta() == ""  # sin curso no hay dirección


def test_las_fichas_viajan_con_el_add_on():
    """construir.py empaqueta todo practices/blender/*.json: fichas.json llega a practicas/fichas.json."""
    datos = json.loads((RAIZ / "practices" / "blender" / "fichas.json").read_text(encoding="utf-8"))
    assert datos["schema"] == "amatista.fichas/1"
    assert len(datos["fichas"]) >= 20 and len(datos["zonas"]) >= 8
    fuente = (ADDON / "fichas.py").read_text(encoding="utf-8")
    assert '"fichas.json"' in fuente
