"""El plano: las piezas que el ejemplo de una práctica espera, agrupadas por lo que son."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ...practice.loader import pieza_como_dict
from ...validators.base import primitiva
from ...validators.figure import caja_de_pieza

# Cómo se agrega cada primitiva en el programa (lo traduce el adaptador de cada programa).
NOMBRE_PRIMITIVA = {"cube": "cubo", "cylinder": "cilindro", "sphere": "esfera", "cone": "cono", "plane": "plano",
                    "torus": "toroide", "icosphere": "icoesfera"}


@dataclass(frozen=True)
class PiezaEsperada:
    grupo: str  # el rol («rueda») o, sin rol, la primitiva
    nombre: str  # «Locomotora», o la etiqueta del rol
    primitiva: str
    medidas: Tuple[float, float, float]  # caja en el mundo, ya girada como va en el ejemplo


@dataclass(frozen=True)
class Plano:
    practica_id: str
    piezas: Tuple[PiezaEsperada, ...]
    etiquetas: Dict[str, str]  # grupo → nombre para mostrar
    tolerancia: float  # holgura de medidas del ejemplo (0.35 = ±35 %)

    def del_grupo(self, grupo: str) -> Tuple[PiezaEsperada, ...]:
        return tuple(p for p in self.piezas if p.grupo == grupo)

    @property
    def grupos(self) -> Tuple[str, ...]:
        vistos: Dict[str, None] = {}
        for p in self.piezas:
            vistos.setdefault(p.grupo)
        return tuple(vistos)

    def etiqueta(self, grupo: str) -> str:
        return self.etiquetas.get(grupo) or grupo.capitalize()


def plano_de(practica) -> Optional[Plano]:
    """El plano de una práctica, o None si no tiene piezas sueltas que comparar.

    Las piezas unidas en una sola malla («join», como la espada) no se juzgan
    aquí: no se pueden separar en la escena del alumno. De eso se ocupa la silueta.
    """
    referencia = getattr(practica, "reference", None)
    comparadas = list(getattr(referencia, "compared", ()) or ()) if referencia else []
    if not comparadas or any(getattr(p, "join", "") for p in comparadas):
        return None
    etiquetas = {r.id: r.label for r in getattr(practica, "roles", ()) or ()}
    piezas = []
    for parte in comparadas:
        datos = pieza_como_dict(parte)
        minimo, maximo = caja_de_pieza(datos)
        base = primitiva(datos.get("primitive", ""))
        grupo = str(datos.get("role") or base)
        medidas = tuple(round(maximo[i] - minimo[i], 6) for i in range(3))
        piezas.append(PiezaEsperada(grupo, datos.get("name") or etiquetas.get(grupo) or grupo.capitalize(), base, medidas))
    return Plano(getattr(practica, "id", ""), tuple(piezas), etiquetas, float(getattr(referencia, "tolerance", 0.35) or 0.35))
