"""Amatista Taller (motor 5): la habilidad es la unidad, no la práctica.

Antes el motor sabía qué práctica terminaste; ahora sabe qué sabes hacer.
Cada habilidad (agregar una primitiva, estirar en un eje, extruir, poner un
material…) se aprende con el mismo ciclo y el modelo del alumno decide en
qué paso del ciclo está cada quien:

    Mira → Hazlo conmigo → Hazlo tú → Úsalo → Recuérdalo

- **Mira**: una demostración corta en la vista 3D (demo.py).
- **Hazlo conmigo**: lo haces tú con un molde translúcido (molde.py) y la
  herramienta iluminada; las teclas no se dictan, se piden (ayudas.py).
- **Hazlo tú**: variaciones cortas sin molde ni teclas, hasta dominarla.
- **Úsalo**: el proyecto del módulo, que queda en tu isla.
- **Recuérdalo**: un reto de un minuto días después (repaso.py).

Base: docs/investigacion/2026-10-10_addon_de_ensenanza/ (aprendiz cognitivo,
práctica de recuperación espaciada y un modelo del alumno BKT ajustado con
datos reales). Python puro: el add-on lo dibuja, el servidor lo vuelve a
calcular y las pruebas lo revisan sin Blender.
"""
from __future__ import annotations

from .actividades import (
    CONMIGO,
    MIRA,
    PROYECTO,
    PRUEBA,
    REPASO,
    RETO,
    TIPOS,
    TU,
    Actividad,
    EstadoHabilidad,
    Plan,
    actividad_de_proyecto,
    actividad_de_prueba,
    actividad_de_repaso,
    actividad_de_reto_final,
    actividad_por_id,
    molde_del_proyecto,
    planear,
    practica_de_actividad,
    revisar_proyecto,
)
from .ayudas import COMO, CON_QUE, MIRAME, NINGUNA, QUE, Escalera, Pista, atascado, pedir_pista, pista_para, puede_pedir
from .demo import PasoDemo, linea_de_tiempo, pasos_de_actividad, pieza_de_revision
from . import etapas
from .habilidades import (
    SCHEMA,
    Catalogo,
    Habilidad,
    ParametrosBKT,
    Reto,
    Taller,
    Variacion,
    cargar_catalogo,
    leer_catalogo,
)
from .modelo import (
    ACOMPANADA,
    DOMINADA,
    NUEVA,
    SOLA,
    Dominio,
    dominio,
    estado_a_dict,
    estado_desde_dict,
    fase,
    marcar_demo,
    registrar_intento,
)
from .molde import PiezaRevisada, RevisionMolde, revisar_molde
from .repaso import proximas, vencidas

__all__ = [
    "ACOMPANADA", "COMO", "CONMIGO", "CON_QUE", "DOMINADA", "MIRA", "MIRAME", "NINGUNA", "NUEVA", "PROYECTO", "PRUEBA",
    "QUE", "REPASO", "RETO", "SCHEMA", "SOLA", "TIPOS", "TU", "Actividad", "Catalogo", "Dominio", "Escalera",
    "EstadoHabilidad", "Habilidad", "ParametrosBKT", "PasoDemo", "PiezaRevisada", "Pista", "Plan", "Reto",
    "RevisionMolde", "Taller", "Variacion", "actividad_de_proyecto", "actividad_de_prueba", "actividad_de_repaso",
    "actividad_de_reto_final", "actividad_por_id",
    "atascado", "cargar_catalogo", "dominio", "estado_a_dict", "estado_desde_dict", "fase", "leer_catalogo", "linea_de_tiempo",
    "etapas", "marcar_demo", "molde_del_proyecto", "pasos_de_actividad", "pieza_de_revision", "pedir_pista", "pista_para", "planear", "practica_de_actividad",
    "proximas", "puede_pedir",
    "registrar_intento", "revisar_molde", "revisar_proyecto", "vencidas",
]
