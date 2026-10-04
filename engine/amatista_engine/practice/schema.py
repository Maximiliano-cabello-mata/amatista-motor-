"""Formato declarativo de las prácticas: amatista.practice/1 y /2.

Documentación completa: docs/motor/referencia/02_formato_de_practica.md. Todos los
campos nuevos son opcionales: las prácticas del prototipo v0.1 siguen
siendo válidas.

amatista.practice/2 (motor v3) agrega píldoras de teoría (pills),
vigilantes que pausan el progreso (guards), repaso espaciado (review), el
lugar de la práctica en el curso (course) y cómo empieza la escena
(starter). Un add-on anterior a la v3 rechaza el /2 con «Schema no
soportado» y pide actualizarse, en lugar de mostrar media práctica.
"""
import re

SCHEMA_V1 = "amatista.practice/1"
SCHEMA_V2 = "amatista.practice/2"
SUPPORTED_SCHEMA = SCHEMA_V2  # el que escriben las herramientas nuevas
SUPPORTED_SCHEMAS = (SCHEMA_V1, SCHEMA_V2)
CAMPOS_V2 = ("guards", "pills", "review", "course", "starter")

# Ids de práctica: minúsculas, números, punto, guion y guion bajo («blender.n1.mesa»).
PATRON_PRACTICA = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
# Ids de objetivos, roles, etiquetas y habilidades.
PATRON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$")
PATRON_VERSION = re.compile(r"^\d+\.\d+(\.\d+)?$")

CAMPOS_OBJETIVO = {
    "id", "title", "validator", "params", "weight", "requires", "tip", "hints", "messages", "optional", "watch", "guide",
}
CAMPOS_PRACTICA = {
    "schema", "id", "version", "title", "level", "description", "intro", "completion", "estimatedMinutes",
    "blender", "skills", "roles", "tags", "tools", "targets",
    "guards", "pills", "review", "course", "starter",
}
CAMPOS_PILDORA = {"id", "title", "text", "keys", "visual", "trigger", "once", "check"}

MAX_OBJETIVOS = 40
MAX_PISTAS = 6
MAX_PASOS_GUIA = 8
MAX_TECLAS = 6
MAX_TEXTO = 600
NIVEL_MAXIMO = 5
MAX_PILDORAS = 24
MAX_VIGILANTES = 6
MAX_TEXTO_PILDORA = 600
PILDORA_IDEAL = 280  # una píldora se lee de un vistazo: más largo da un aviso
DISPAROS = ("start", "target", "mode", "selection", "tool", "guard", "complete")
PESTANAS = ("MODIFIER", "MATERIAL", "RENDER", "OUTPUT", "DATA", "OBJECT", "WORLD", "SCENE")
VISUALES = ("", "axes", "keys", "mode")  # además tab:<PESTAÑA> e image:<archivo>
ESCENAS_INICIALES = ("keep", "empty")
# Acciones de «Hazlo conmigo» que un vigilante puede ofrecer como arreglo.
ARREGLOS = (
    "merge_by_distance", "apply_scale", "apply_all", "edit_mode", "object_mode", "open_tab", "focus", "save",
)
