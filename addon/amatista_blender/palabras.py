"""Palabras de Blender en lenguaje simple (motor 5.3, 2026-10-23).

La fuente es practices/blender/palabras.json, la misma que muestra la plataforma en la página
Blender. construir.py la empaqueta como practicas/palabras.json. Si el Blender del alumno está en
inglés, cada palabra se muestra también como la ve en sus menús («Malla · Mesh»).
"""
import json
from pathlib import Path

from . import _motor, temas

_CACHE = {"datos": None}


def ruta_palabras(carpeta=None):
    carpeta = Path(carpeta) if carpeta is not None else temas.carpeta_paquete()
    for candidata in (carpeta / "palabras.json", carpeta / "blender" / "palabras.json"):
        if candidata.is_file():
            return candidata
    return None


def cargar(ruta=None, recargar=False):
    """[{id, termino, ingles, que_es, donde, tecla}]. Nunca falla: sin archivo, lista vacía."""
    if _CACHE["datos"] is not None and not recargar and ruta is None:
        return _CACHE["datos"]
    archivo = Path(ruta) if ruta is not None else ruta_palabras()
    lista = []
    if archivo is not None:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            lista = [p for p in datos.get("palabras", []) if isinstance(p, dict) and p.get("termino")]
        except (OSError, ValueError, AttributeError):
            lista = []
    if ruta is None:
        _CACHE["datos"] = lista
    return lista


def titulo(palabra, idioma=None):
    """«Malla» o, con Blender en inglés, «Malla · Mesh»."""
    idioma = idioma or _motor.terminos.idioma()
    ingles = palabra.get("ingles") or ""
    if idioma == "es" or not ingles or ingles == palabra["termino"]:
        return palabra["termino"]
    return f"{palabra['termino']} · {ingles}"


def detalle(palabra, idioma=None):
    """Qué es, dónde está y su tecla, en un párrafo (las rutas de menú, en el idioma del alumno)."""
    partes = [palabra.get("que_es", "")]
    if palabra.get("donde"):
        partes.append(f"Dónde: {_motor.terminos.menus(palabra['donde'], idioma)}")
    if palabra.get("tecla"):
        partes.append(f"Tecla: {palabra['tecla']}")
    return " ".join(p for p in partes if p)
