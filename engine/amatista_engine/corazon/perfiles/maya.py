"""Perfil de Autodesk Maya (borrador).

Ubicadas las herramientas base del primer módulo. Falta el adaptador dentro
de Maya (``maya.cmds``: la foto con ``cmds.ls``/``cmds.xform`` y las señales
con ``cmds.setToolTo``) y probarlo con una persona.
"""
from __future__ import annotations

from ..adaptador import Perfil
from ..contrato import BARRA, DIALOGO, MENU, PESTANA, Lugar

CAJA = "en la caja de herramientas (Tool Box), a la izquierda"

PERFIL = Perfil(
    software="maya",
    nombre="Maya",
    estado="borrador",
    lugares={
        "object.add": Lugar("object.add", "Crear", "en la barra de menús de arriba", MENU,
                            ruta="Create › Polygon Primitives", objetivo="mainCreateMenu"),
        "transform.move": Lugar("transform.move", "Move Tool", CAJA, BARRA, atajo="W", objetivo="moveSuperContext"),
        "transform.rotate": Lugar("transform.rotate", "Rotate Tool", CAJA, BARRA, atajo="E",
                                  objetivo="RotateSuperContext"),
        "transform.scale": Lugar("transform.scale", "Scale Tool", CAJA, BARRA, atajo="R",
                                 objetivo="scaleSuperContext"),
        "file.save": Lugar("file.save", "Save Scene As", "en la barra de menús de arriba", DIALOGO,
                           ruta="File › Save Scene As", atajo="Ctrl + Shift + S"),
        "material.basic": Lugar("material.basic", "Material", "en el Attribute Editor, a la derecha", PESTANA,
                                atajo="Ctrl + A"),
    },
    por_validador={"object.count": "object.add", "dimension.approx": "transform.scale",
                   "spatial.grounded": "transform.move", "file.saved": "file.save"},
    mallas={"cube": "Cube", "cylinder": "Cylinder", "sphere": "Sphere", "plane": "Plane", "cone": "Cone"},
)

__all__ = ["PERFIL"]
