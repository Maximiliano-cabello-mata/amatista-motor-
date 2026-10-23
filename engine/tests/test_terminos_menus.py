"""Menús de Blender en el idioma del alumno (motor 5.3)."""
from amatista_engine import terminos


def test_en_ingles_cada_paso_del_menu_dice_lo_que_ve_y_lo_que_significa():
    texto = "Agrega un cubo (Shift + A › Malla › Cubo)."
    assert terminos.menus(texto, "en") == "Agrega un cubo (Shift + A › Mesh (Malla) › Cube (Cubo))."
    assert terminos.menus("Archivo › Guardar como", "en") == "File (Archivo) › Save As (Guardar como)"
    assert terminos.menus("Malla › Fusionar › Por distancia", "en") == "Mesh (Malla) › Merge (Fusionar) › By Distance (Por distancia)"


def test_no_repite_ni_toca_lo_que_no_es_menu():
    una = terminos.menus("Shift+A › Luz › Área", "en")
    assert terminos.menus(una, "en") == una
    assert terminos.menus("Material › Nuevo", "en") == "Material › New (Nuevo)"
    assert terminos.menus("La Malla y el Cubo sin flechas", "en") == "La Malla y el Cubo sin flechas"
    assert terminos.menus(None, "en") is None


def test_en_espanol_queda_igual_y_el_idioma_se_fija_una_vez():
    assert terminos.menus("Archivo › Guardar", "es") == "Archivo › Guardar"
    try:
        assert terminos.fijar_idioma("en_US") == "en" and terminos.idioma() == "en"
        assert terminos.tecla("Malla") == "Mesh" and terminos.tecla("Shift+A") == "Shift+A"
        assert terminos.fijar_idioma("es_MX") == "es"
        assert terminos.tecla("Malla") == "Malla"
        assert terminos.fijar_idioma("") == "en"
    finally:
        terminos.fijar_idioma("es")
