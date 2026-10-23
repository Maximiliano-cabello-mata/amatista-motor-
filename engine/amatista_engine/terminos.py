"""Términos de Blender que muestra el motor, en un solo lugar (motor 3.5).

Los validadores, las instrucciones del ejemplo (ejemplo/pasos.py), la
revisión contra el ejemplo y la guía usan estos nombres para que el alumno
lea siempre lo mismo que dicen las prácticas.
"""
from __future__ import annotations

import re

# Nombre de cada modificador (los que usan las prácticas: «Array», «Bisel», «Subdivisión de superficie»…).
MODIFICADORES = {
    "MIRROR": "Espejo",
    "SUBSURF": "Subdivisión de superficie",
    "BEVEL": "Bisel",
    "SOLIDIFY": "Solidificar",
    "ARRAY": "Array",
    "BOOLEAN": "Booleano",
    "DECIMATE": "Diezmar",
    "WEIGHTED_NORMAL": "Normales ponderadas",
}


def nombre_modificador(tipo: str) -> str:
    tipo = str(tipo or "").upper()
    return MODIFICADORES.get(tipo, tipo.capitalize())


# --- Menús de Blender en el idioma de cada alumno (motor 5.3, 2026-10-23) -------------------
#
# Blender se instala en inglés: quien nunca lo abrió ve «Add › Mesh › Cube» aunque la práctica
# diga «Agregar › Malla › Cubo». El add-on avisa en qué idioma está la interfaz (fijar_idioma) y
# menus() reescribe las rutas de menú de cualquier texto: «Shift + A › Mesh (Malla) › Cube (Cubo)».
# Solo cambia las palabras pegadas a «›» y puede aplicarse dos veces sin repetir nada.

MENUS = {
    "Agregar": "Add", "Malla": "Mesh", "Cubo": "Cube", "Cilindro": "Cylinder", "Esfera UV": "UV Sphere",
    "Icoesfera": "Ico Sphere", "Cono": "Cone", "Toroide": "Torus", "Plano": "Plane", "Círculo": "Circle",
    "Mono": "Monkey", "Luz": "Light", "Punto": "Point", "Sol": "Sun", "Foco": "Spot", "Área": "Area",
    "Cámara": "Camera", "Archivo": "File", "Guardar": "Save", "Guardar como": "Save As", "Exportar": "Export",
    "Editar": "Edit", "Preferencias": "Preferences", "Objeto": "Object", "Aplicar": "Apply",
    "Escala": "Scale", "Rotación": "Rotation", "Ubicación": "Location", "Fusionar": "Merge",
    "Por distancia": "By Distance", "Generar": "Generate", "Modificadores": "Modifiers",
    "Agregar modificador": "Add Modifier", "Espejo": "Mirror", "Bisel": "Bevel", "Matriz": "Array",
    "Subdivisión de superficie": "Subdivision Surface", "Solidificar": "Solidify", "Booleano": "Boolean",
    "Diezmar": "Decimate", "Nuevo": "New", "Nueva colección": "New Collection", "Vértices": "Vertices",
    "Aristas": "Edges", "Caras": "Faces", "Extruir": "Extrude", "Partículas": "Particles", "Imagen": "Image",
    "Renderizar imagen": "Render Image", "Vista renderizada": "Rendered", "Enlazar materiales": "Link Materials",
    "Vincular materiales": "Link Materials", "Sistema": "System", "Entrada": "Input", "Interfaz": "Interface",
    "Emular teclado numérico": "Emulate Numpad", "Ver": "View", "Seleccionar": "Select",
}
IDIOMAS = ("es", "en")
_IDIOMA = {"actual": "es"}
_LETRA = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9"
_TERMINOS = "|".join(re.escape(t) for t in sorted(MENUS, key=len, reverse=True))
_AL_INICIO = re.compile(rf"^(\s*)({_TERMINOS})(?![{_LETRA}]| \()")
_AL_FINAL = re.compile(rf"(?<![{_LETRA}(])({_TERMINOS})(\s*)$")


def fijar_idioma(codigo: str | None) -> str:
    """'es' si la interfaz de Blender está en español; 'en' en cualquier otro caso. Devuelve el elegido."""
    _IDIOMA["actual"] = "es" if str(codigo or "").lower().startswith("es") else "en"
    return _IDIOMA["actual"]


def idioma() -> str:
    return _IDIOMA["actual"]


def _traducir(termino: str) -> str:
    ingles = MENUS[termino]
    return termino if ingles == termino else f"{ingles} ({termino})"


def menus(texto, idioma_ui: str | None = None):
    """El texto con sus rutas de menú («A › B › C») como las ve el alumno en su Blender."""
    if not isinstance(texto, str) or "›" not in texto or (idioma_ui or _IDIOMA["actual"]) == "es":
        return texto
    partes = texto.split("›")
    for i, parte in enumerate(partes):
        if i > 0:
            parte = _AL_INICIO.sub(lambda m: m.group(1) + _traducir(m.group(2)), parte, count=1)
        if i < len(partes) - 1:
            parte = _AL_FINAL.sub(lambda m: _traducir(m.group(1)) + m.group(2), parte, count=1)
        partes[i] = parte
    return "›".join(partes)


def tecla(texto, idioma_ui: str | None = None):
    """Una tecla o botón de la tarjeta («Malla» → «Mesh» si Blender está en inglés)."""
    if (idioma_ui or _IDIOMA["actual"]) == "es" or not isinstance(texto, str):
        return texto
    return MENUS.get(texto, texto)
