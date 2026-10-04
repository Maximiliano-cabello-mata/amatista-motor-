"""Plantillas de práctica para `practicas.py nueva` (motor v3).

Cada plantilla es el esqueleto de un tipo de práctica del plan de estudios
con píldoras, objetivos, pistas y vigilantes ya conectados. El autor cambia
textos y números; la estructura pedagógica (teoría breve al empezar, un
objetivo por idea, guardar al final) ya viene puesta. Todas compilan: lo
comprueba engine/tests/test_v3_herramientas.py.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List

from .schema import SCHEMA_V2

CAMBIA = "Cambia este texto"

_GUARDAR = {
    "id": "guardar",
    "title": "Guarda tu trabajo",
    "validator": "file.saved",
    "weight": 5,
    "tip": "Ctrl+S (o Ctrl+Shift+S la primera vez).",
    "hints": ["Archivo › Guardar como y escribe un nombre que reconozcas."],
}
_MALLA_LIMPIA = {
    "id": "malla-limpia",
    "title": "Malla sin vértices encimados",
    "validator": "mesh.no_duplicates",
    "params": {},
    "fix": {"action": "merge_by_distance", "label": "Fusionar por distancia conmigo"},
    "messages": {"fail": "Quedaron caras encimadas (pasa al cancelar una extrusión). Límpialas antes de seguir."},
}


def _pildora(pid: str, titulo: str, texto: str, **extra) -> Dict[str, Any]:
    return {"id": pid, "title": titulo, "text": texto, "trigger": {"on": "start"}, **extra}


PLANTILLAS: Dict[str, Dict[str, Any]] = {
    "vacia": {
        "level": 1,
        "pills": [_pildora("idea", "La idea de hoy", f"{CAMBIA}: una idea, dos frases como máximo.")],
        "targets": [
            {"id": "paso-1", "title": "Primer paso", "validator": "object.count", "params": {"type": "MESH", "min": 1},
             "weight": 10, "tip": CAMBIA, "hints": [CAMBIA]},
            _GUARDAR,
        ],
    },
    "ensamblar": {
        "level": 1,
        "roles": {"pieza": {"label": "Pieza"}, "base": {"label": "Base"}},
        "pills": [
            _pildora("agregar", "Shift + A", "Shift + A agrega formas: Malla › Cubo, Cilindro…", keys=["Shift", "A"],
                     visual="keys"),
            {"id": "grs", "title": "G, R y S", "text": "G mueve, R rota y S escala. Luego X, Y o Z para un solo eje.",
             "keys": ["G", "R", "S"], "visual": "keys", "trigger": {"on": "selection"}},
        ],
        "targets": [
            {"id": "base", "title": "La base", "validator": "role.count", "params": {"role": "base", "equals": 1},
             "weight": 10, "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "piezas", "title": "Las piezas", "validator": "object.count",
             "params": {"role": "pieza", "primitive": "cylinder", "min": 2}, "weight": 20, "requires": ["base"],
             "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "apoyadas", "title": "En el suelo", "validator": "spatial.grounded",
             "params": {"role": "pieza", "height": 0, "tolerance": 0.1}, "weight": 20, "requires": ["piezas"],
             "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "unidas", "title": "Unidas a la base", "validator": "spatial.touching",
             "params": {"role": "pieza", "reference_role": "base", "tolerance": 0.1}, "weight": 20,
             "requires": ["apoyadas"], "tip": CAMBIA, "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["unidas"]},
        ],
    },
    "modelado": {
        "level": 2,
        "roles": {"modelo": {"label": "Modelo"}},
        "pills": [
            _pildora("modos", "Objeto y Edición", "Tab cambia entre Modo Objeto (la pieza entera) y Modo Edición "
                     "(sus vértices, aristas y caras).", keys=["Tab"], visual="mode"),
            {"id": "extruir", "title": "E extruye", "text": "E saca caras nuevas desde las seleccionadas.",
             "keys": ["E"], "visual": "keys", "trigger": {"on": "mode", "mode": "EDIT"}},
            {"id": "fusionar", "title": "M › Por distancia", "text": "Si cancelaste una extrusión, M › Por distancia "
             "une los vértices encimados.", "keys": ["M"], "trigger": {"on": "guard", "target": "malla-limpia"}},
        ],
        "targets": [
            {"id": "modelo", "title": "Tu modelo", "validator": "role.count", "params": {"role": "modelo", "equals": 1},
             "weight": 10, "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "caras", "title": "Forma con extrusiones", "validator": "mesh.face_count",
             "params": {"role": "modelo", "min": 14}, "weight": 30, "requires": ["modelo"], "tip": CAMBIA,
             "hints": [CAMBIA]},
            {"id": "low-poly", "title": "Low-poly", "validator": "mesh.vertex_count",
             "params": {"role": "modelo", "max": 300}, "weight": 10, "requires": ["caras"], "tip": CAMBIA,
             "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["low-poly"]},
        ],
        "guards": [_MALLA_LIMPIA],
    },
    "modificadores": {
        "level": 2,
        "roles": {"modelo": {"label": "Modelo"}},
        "pills": [
            _pildora("llave", "La llave inglesa", "Los modificadores son filtros que cambian la forma sin tocar tu "
                     "malla. Viven en la llave inglesa de Propiedades.", visual="tab:MODIFIER"),
        ],
        "targets": [
            {"id": "modelo", "title": "Tu modelo", "validator": "role.count", "params": {"role": "modelo", "equals": 1},
             "weight": 10, "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "escala", "title": "Escala aplicada", "validator": "transform.scale_applied",
             "params": {"role": "modelo"}, "weight": 15, "requires": ["modelo"], "tip": "Ctrl+A › Escala.",
             "hints": [CAMBIA]},
            {"id": "espejo", "title": "Espejo en X", "validator": "modifier.configured",
             "params": {"role": "modelo", "modifier": "MIRROR", "axis": "x"}, "weight": 25, "requires": ["escala"],
             "tip": CAMBIA, "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["espejo"]},
        ],
        "guards": [_MALLA_LIMPIA],
    },
    "materiales": {
        "level": 2,
        "pills": [
            _pildora("principled", "Tres controles", "Del Principled BSDF basta con Color base, Metálico y Rugosidad.",
                     visual="tab:MATERIAL"),
        ],
        "targets": [
            {"id": "materiales", "title": "Materiales distintos", "validator": "material.distinct", "params": {"min": 2},
             "weight": 30, "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "metal", "title": "Un metal", "validator": "material.matches",
             "params": {"metallic_min": 0.7, "label": "un metal"}, "weight": 30, "tip": CAMBIA, "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["materiales", "metal"]},
        ],
    },
    "iluminacion": {
        "level": 2,
        "pills": [_pildora("luces", "Área y Sol", "Área da sombras suaves; Sol, luz pareja desde una dirección.")],
        "targets": [
            {"id": "camara", "title": "Cámara activa", "validator": "camera.active", "weight": 15, "tip": CAMBIA,
             "hints": [CAMBIA]},
            {"id": "tres-puntos", "title": "Tres puntos", "validator": "light.three_point", "params": {},
             "weight": 40, "requires": ["camara"], "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "render", "title": "Render", "validator": "render.done", "weight": 20, "requires": ["tres-puntos"],
             "tip": "F12.", "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["render"]},
        ],
    },
    "animacion": {
        "level": 2,
        "pills": [_pildora("clave", "Fotograma clave", "I guarda la posición del objeto en el fotograma actual.",
                           keys=["I"], visual="keys")],
        "targets": [
            {"id": "claves", "title": "Fotogramas clave", "validator": "animation.keyframes",
             "params": {"primitive": "sphere", "property": "location", "axis": "z", "min": 3}, "weight": 30,
             "tip": CAMBIA, "hints": [CAMBIA]},
            {"id": "movimiento", "title": "Se mueve", "validator": "animation.varies",
             "params": {"primitive": "sphere", "property": "location", "axis": "z", "min_delta": 1},
             "weight": 30, "requires": ["claves"], "tip": CAMBIA, "hints": [CAMBIA]},
            {**_GUARDAR, "requires": ["movimiento"]},
        ],
    },
}


def nueva_practica(practica_id: str, plantilla: str, titulo: str, curso: str, modulo: int) -> Dict[str, Any]:
    base = copy.deepcopy(PLANTILLAS[plantilla])
    datos: Dict[str, Any] = {
        "schema": SCHEMA_V2,
        "id": practica_id,
        "version": 1,
        "title": titulo,
        "level": base.pop("level", 1),
        "description": f"{CAMBIA}: qué construye el alumno en una frase.",
        "intro": f"{CAMBIA}: la frase que ve al abrir la práctica.",
        "completion": f"{CAMBIA}: la felicitación y qué se desbloquea.",
        "estimatedMinutes": 20,
        "blender": {"min": "4.2"},
        "course": {"id": curso, "module": modulo},
    }
    datos.update(base)
    return datos


def nuevas_pruebas(practica_id: str, plantilla: str) -> Dict[str, Any]:
    primer = PLANTILLAS[plantilla]["targets"][0]["id"]
    casos: List[Dict[str, Any]] = [
        {"nombre": "Escena vacía", "construir": [], "espera": {"completada": False, "actual": primer}},
        {"nombre": "Escena de inicio de Blender", "construir": [{"inicial": True}], "espera": {"completada": False}},
    ]
    return {"schema": "amatista.practice-tests/1", "practica": practica_id, "casos": casos}
