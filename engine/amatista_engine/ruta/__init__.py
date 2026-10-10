"""Motor 4: la experiencia del alumno.

    ruta = construir_ruta(practica, reporte, guia, tools)   # misiones en fila, una a la vez
    ajustar(objetivo, nivel)                               # medidas amables según el nivel
    frase_amable(practica, objetivo, resultado, nivel)     # el instructor sin decimales

Documentación: docs/motor/referencia/15_experiencia_del_alumno.md.
"""
from .frases import LOGROS, YA_LO_TENIAS, frase_amable, logro
from .medidas import HOLGURA, ajustar, ajustar_parametros, holgura
from .mision import ACTUAL, ADELANTADA, HECHA, SIGUIENTE, Mision, Parte, Ruta, construir_ruta, ruta_a_dict, titulo_parte

__all__ = [
    "ACTUAL", "ADELANTADA", "HECHA", "HOLGURA", "LOGROS", "Mision", "Parte", "Ruta", "SIGUIENTE", "YA_LO_TENIAS",
    "ajustar", "ajustar_parametros", "construir_ruta", "frase_amable", "holgura", "logro", "ruta_a_dict",
    "titulo_parte",
]
