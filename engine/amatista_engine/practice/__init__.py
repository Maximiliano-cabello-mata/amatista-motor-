from .compiler import CompileResult, compile_practice
from .loader import dump_practice, dumps_practice, load_practice, parse_practice
from .schema import SUPPORTED_SCHEMA, SUPPORTED_SCHEMAS
from .templates import PLANTILLAS, nueva_practica, nuevas_pruebas

__all__ = [
    "CompileResult",
    "PLANTILLAS",
    "SUPPORTED_SCHEMA",
    "SUPPORTED_SCHEMAS",
    "compile_practice",
    "dump_practice",
    "dumps_practice",
    "load_practice",
    "nueva_practica",
    "nuevas_pruebas",
    "parse_practice",
]
