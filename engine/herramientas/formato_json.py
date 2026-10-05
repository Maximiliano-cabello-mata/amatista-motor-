"""Escribe JSON de prácticas legible: sangría de 2 y en una línea lo que cabe.

    python engine/herramientas/formato_json.py practices/blender/**/practica.json

Lo usan las herramientas que reescriben prácticas para que el diff quede
pequeño (una pieza del modelo de referencia = una línea).
"""
import json
import sys
from pathlib import Path

ANCHO = 118


def formatear(valor, sangria: int = 0) -> str:
    plano = json.dumps(valor, ensure_ascii=False)
    if not isinstance(valor, (dict, list)) or len(plano) + sangria <= ANCHO or not valor:
        return plano
    dentro = " " * (sangria + 2)
    if isinstance(valor, dict):
        filas = [f"{dentro}{json.dumps(k, ensure_ascii=False)}: {formatear(v, sangria + 2)}" for k, v in valor.items()]
        return "{\n" + ",\n".join(filas) + "\n" + " " * sangria + "}"
    filas = [dentro + formatear(v, sangria + 2) for v in valor]
    return "[\n" + ",\n".join(filas) + "\n" + " " * sangria + "]"


def escribir(ruta: Path, datos) -> None:
    ruta.write_text(formatear(datos) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for nombre in sys.argv[1:]:
        ruta = Path(nombre)
        escribir(ruta, json.loads(ruta.read_text(encoding="utf-8")))
