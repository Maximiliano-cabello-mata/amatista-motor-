"""Las partes de la ruta (motor 4): cada objetivo cae en una parte según lo que revisa.

Las partes ordenan la práctica: primero se arman las piezas, luego se les da
forma, se acomodan, se revisa la figura y al final se guarda. graph.ordered
recorre los objetivos por parte (respetando «requires») para que el alumno
no salte de «agrega un cubo» a «toca el suelo» y de vuelta a «agrega un
cilindro». El autor puede nombrar la parte de un objetivo con "stage".

No importa nada del motor: graph.py lo usa sin ciclos de importación.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

from ..models import TargetDefinition

# Parte de la ruta según lo que revisa el objetivo (el primer prefijo que coincide).
PARTES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Revisa tu figura", ("figure.", "example.")),
    ("Guarda y muestra", ("file.", "render.done")),
    ("Dale forma", ("shape.", "transform.", "mesh.", "dimension.", "scene.mode")),
    ("Modificadores", ("modifier.",)),
    ("Acomoda las piezas", ("spatial.",)),
    ("Pinta", ("material.",)),
    ("Luz y cámara", ("light.", "scene.light", "camera.", "render.")),
    ("Anima", ("animation.",)),
    ("Organiza tu escena", ("collection.",)),
    ("Arma las piezas", ("object.", "role.", "scene.")),
)


def _validador_base(target: TargetDefinition) -> str:
    if target.validator == "logic.any":
        opciones = (target.params or {}).get("options") or []
        if opciones and isinstance(opciones[0], dict):
            return str(opciones[0].get("validator", ""))
    return target.validator


def titulo_parte(target: TargetDefinition) -> str:
    if getattr(target, "stage", ""):
        return target.stage
    validador = _validador_base(target)
    for titulo, prefijos in PARTES:
        if any(validador == p or validador.startswith(p) for p in prefijos):
            return titulo
    return "Tu práctica"



FINAL = "Revisa y guarda"
CIERRE = {"Revisa tu figura", "Guarda y muestra"}


def titulos_partes(targets: Sequence[TargetDefinition]) -> Tuple[str, ...]:
    """El título de la parte de cada objetivo, ya ordenados (los de graph.ordered).

    El autor manda con "stage". Sin él, la parte sale de lo que revisa el
    objetivo, con dos arreglos para que la ruta no se vea partida:
    - una parte de una sola misión se une a la anterior (armar el vagón y
      estirarlo es una misma idea: «Arma las piezas»), salvo la de cierre;
    - revisar la figura y guardar, al final, son una sola parte: «Revisa y guarda».
    """
    titulos = [titulo_parte(t) for t in targets]
    propios = [bool(getattr(t, "stage", "")) for t in targets]
    # Revisar y guardar al final: una sola parte.
    i = len(titulos)
    while i > 0 and not propios[i - 1] and titulos[i - 1] in CIERRE:
        i -= 1
    if i < len(titulos) and len({titulos[j] for j in range(i, len(titulos))}) > 1:
        for j in range(i, len(titulos)):
            titulos[j] = FINAL
    # Corridas de una sola misión (sin «stage») se unen a la parte anterior.
    corridas = []
    for j, titulo in enumerate(titulos):
        if corridas and corridas[-1][0] == titulo:
            corridas[-1][2] = j
        else:
            corridas.append([titulo, j, j])
    for k in range(1, len(corridas)):
        titulo, desde, hasta = corridas[k]
        if (k == len(corridas) - 1 and not any(propios[desde:hasta + 1]) and titulo in CIERRE
                and corridas[k - 1][0] in CIERRE | {FINAL}):
            # El ejemplo que el cargador agrega al final entra en la parte de cierre del autor.
            for j in range(desde, hasta + 1):
                titulos[j] = corridas[k - 1][0]
            continue
        cierre = k == len(corridas) - 1 and titulo in CIERRE | {FINAL}
        if desde == hasta and not propios[desde] and not cierre:
            corridas[k][0] = corridas[k - 1][0]
            for j in range(desde, hasta + 1):
                titulos[j] = corridas[k - 1][0]
    return tuple(titulos)
