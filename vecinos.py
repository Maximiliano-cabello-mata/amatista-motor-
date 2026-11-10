"""Dónde están los otros repositorios de Amatista en esta computadora.

El motor no depende de la API ni de la web para funcionar. Solo algunas
pruebas de contrato comparan lo que produce el motor con lo que esperan los
otros: el modelo ligero (API) y las lecciones que enlazan prácticas (web).

Orden de búsqueda de cada vecino:
  1. Variable de entorno (AMATISTA_API_DIR, AMATISTA_WEB_DIR): la raíz del
     checkout que contiene `backend/` o `frontend/`.
  2. Carpeta hermana de este repositorio (`../amatista-api-`, `../amatista-web-`,
     `../amatista`).
  3. Este mismo árbol, si es el monorepo original.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

RAIZ = Path(__file__).resolve().parent

_VECINOS = {
    "backend": ("AMATISTA_API_DIR", ("amatista-api-", "amatista-api", "amatista")),
    "frontend": ("AMATISTA_WEB_DIR", ("amatista-web-", "amatista-web", "amatista")),
}


def carpeta(nombre: str) -> Optional[Path]:
    """La carpeta `backend` o `frontend` de un repositorio vecino, o None si no está."""
    variable, hermanos = _VECINOS[nombre]
    candidatos = []
    if os.getenv(variable):
        candidatos.append(Path(os.environ[variable]).expanduser() / nombre)
    candidatos += [RAIZ.parent / hermano / nombre for hermano in hermanos]
    candidatos.append(RAIZ / nombre)
    return next((c for c in candidatos if c.is_dir()), None)


def requerir(nombre: str) -> Path:
    """Para pruebas de contrato: la carpeta del vecino, o salta la prueba diciendo qué falta."""
    import pytest

    ruta = carpeta(nombre)
    if ruta is None:
        variable = _VECINOS[nombre][0]
        pytest.skip(
            f"Prueba de contrato: necesita el repositorio que contiene {nombre}/ "
            f"(clónalo junto a este o define {variable}).",
            allow_module_level=True,
        )
    return ruta
