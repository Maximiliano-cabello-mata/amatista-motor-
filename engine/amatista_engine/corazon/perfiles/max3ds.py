"""Perfil de Autodesk 3ds Max (borrador).

Ubicadas las herramientas base del primer módulo. Falta el adaptador dentro
de 3ds Max (``pymxs``: la foto con ``rt.objects`` y las señales con
``rt.toolMode``) y probarlo con una persona.
"""
from __future__ import annotations

from ..adaptador import Perfil
from ..contrato import BARRA, DIALOGO, PESTANA, Lugar

BARRA_PRINCIPAL = "en la barra de herramientas principal, arriba"

PERFIL = Perfil(
    software="3dsmax",
    nombre="3ds Max",
    estado="borrador",
    lugares={
        "object.add": Lugar("object.add", "Create", "en el panel de comandos de la derecha, pestaña Create", PESTANA,
                            ruta="Create › Geometry › Standard Primitives", objetivo="create"),
        "transform.move": Lugar("transform.move", "Select and Move", BARRA_PRINCIPAL, BARRA, atajo="W",
                                objetivo="move"),
        "transform.rotate": Lugar("transform.rotate", "Select and Rotate", BARRA_PRINCIPAL, BARRA, atajo="E",
                                  objetivo="rotate"),
        "transform.scale": Lugar("transform.scale", "Select and Uniform Scale", BARRA_PRINCIPAL, BARRA, atajo="R",
                                 objetivo="uscale"),
        "file.save": Lugar("file.save", "Save As", "en el menú File, arriba a la izquierda", DIALOGO,
                           ruta="File › Save As"),
        "material.basic": Lugar("material.basic", "Material Editor", BARRA_PRINCIPAL, DIALOGO, atajo="M"),
    },
    por_validador={"object.count": "object.add", "dimension.approx": "transform.scale",
                   "spatial.grounded": "transform.move", "file.saved": "file.save"},
    mallas={"cube": "Box", "cylinder": "Cylinder", "sphere": "Sphere", "plane": "Plane", "cone": "Cone"},
)

__all__ = ["PERFIL"]
