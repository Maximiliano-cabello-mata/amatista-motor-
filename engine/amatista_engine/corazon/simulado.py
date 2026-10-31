"""Un programa 3D de mentira para probar el corazón (y para escribir adaptadores nuevos).

Tiene una escena (``SceneState``), una herramienta activa y una selección; sabe
elegir herramientas y seleccionar piezas, y el alumno simulado puede cambiar
de herramienta para que una señal se pierda. Lo usan las pruebas del corazón y
``conformidad.py``.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ..models import SceneState
from .adaptador import AdaptadorBase, Perfil
from .contrato import ELEGIR_HERRAMIENTA, SELECCIONAR, ResultadoSenal, Senal


class AdaptadorSimulado(AdaptadorBase):
    def __init__(self, perfil: Perfil, escena: Optional[SceneState] = None, *, sabe_elegir: bool = True,
                 sabe_seleccionar: bool = True) -> None:
        super().__init__(perfil, id=f"simulado-{perfil.software}", version="simulado")
        self.escena = escena or SceneState(blender_version="", file_path="", file_saved=False)
        self.activa = ""
        self.hechas = []  # las señales que se hicieron, en orden
        if sabe_elegir:
            self.hacer[ELEGIR_HERRAMIENTA] = self._elegir
            self.ver[ELEGIR_HERRAMIENTA] = lambda s: self.activa == (s.objetivo or s.herramienta)
        if sabe_seleccionar:
            self.hacer[SELECCIONAR] = self._seleccionar
            self.ver[SELECCIONAR] = lambda s: set(s.objetos) <= set(self.escena.selected)

    def _elegir(self, s: Senal) -> ResultadoSenal:
        self.activa = s.objetivo or s.herramienta
        self.hechas.append(s)
        return ResultadoSenal(True)

    def _seleccionar(self, s: Senal) -> ResultadoSenal:
        nombres = {o.name for o in self.escena.objects}
        if not set(s.objetos) & nombres:
            return ResultadoSenal(False, "no están en la escena")
        self.escena = replace(self.escena, selected=tuple(o for o in s.objetos if o in nombres))
        self.hechas.append(s)
        return ResultadoSenal(True)

    def capturar(self) -> SceneState:
        return self.escena

    def herramienta_activa(self) -> str:
        return self.activa

    # Lo que haría el alumno.
    def elegir_otra(self, herramienta: str) -> None:
        self.activa = herramienta


__all__ = ["AdaptadorSimulado"]
