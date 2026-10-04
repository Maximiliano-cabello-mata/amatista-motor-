"""Formato declarativo de las prácticas: amatista.practice/1.

Documentación completa: docs/motor/02_formato_de_practica.md. Todos los
campos nuevos son opcionales: las prácticas del prototipo v0.1 siguen
siendo válidas.
"""
import re

SUPPORTED_SCHEMA = "amatista.practice/1"

# Ids de práctica: minúsculas, números, punto, guion y guion bajo («blender.n1.mesa»).
PATRON_PRACTICA = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
# Ids de objetivos, roles, etiquetas y habilidades.
PATRON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$")
PATRON_VERSION = re.compile(r"^\d+\.\d+(\.\d+)?$")

CAMPOS_OBJETIVO = {
    "id", "title", "validator", "params", "weight", "requires", "tip", "hints", "messages", "optional", "watch",
}
CAMPOS_PRACTICA = {
    "schema", "id", "version", "title", "level", "description", "intro", "completion", "estimatedMinutes",
    "blender", "skills", "roles", "tags", "tools", "targets",
}

MAX_OBJETIVOS = 40
MAX_PISTAS = 6
MAX_TEXTO = 600
NIVEL_MAXIMO = 5
