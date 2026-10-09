"""El ejemplo resuelto de cada práctica y la revisión autónoma contra él (motor 3.5).

Documentación: docs/motor/referencia/14_ejemplo_y_revision.md.
"""
from .pasos import describir, describir_paso, escena_esperada, lo_que_pide, revisar_pasos
from .revision import ASPECTOS, RevisionEjemplo, aspectos_del_ejemplo, revisar_ejemplo

__all__ = [
    "ASPECTOS", "RevisionEjemplo", "aspectos_del_ejemplo", "describir", "describir_paso", "escena_esperada",
    "lo_que_pide", "revisar_ejemplo", "revisar_pasos",
]
