"""Perfil del Motor Web de A-Frame (lecciones, Estudio y la página que se descarga).

En el Motor Web no hay barra de herramientas: el alumno arrastra, toca y
lleva cosas a zonas en el lienzo (``frontend/src/motor3d/componentes.js``).
La foto del Motor Web (``foto()``: objetos con x, y, z, tocado y zonas con
radio) se vuelve una escena del corazón con ``escena_desde_foto``; así el
servidor puede revisar un reto de A-Frame con el mismo motor que Blender.
"""
from __future__ import annotations

from typing import Any, Mapping

from ...models import SceneObject, SceneState
from ..adaptador import Perfil
from ..contrato import LIENZO, MENU, TECLA, Lugar

LIENZO_3D = "en la escena 3D de la lección"

PERFIL = Perfil(
    software="aframe",
    nombre="A-Frame (Motor Web)",
    lugares={
        "transform.move": Lugar("transform.move", "Arrastrar", LIENZO_3D + ": haz clic sobre el objeto y arrástralo",
                                LIENZO, atajo="dedo o ratón; en VR, el gatillo del control"),
        "object.touch": Lugar("object.touch", "Tocar", LIENZO_3D + ": un clic o un toque sobre el objeto", LIENZO,
                              atajo="clic o toque"),
        "view.navigate": Lugar("view.navigate", "Mover la vista", LIENZO_3D, LIENZO,
                               atajo="arrastra el fondo para girar · rueda o pellizco para acercar"),
        "view.walk": Lugar("view.walk", "Caminar", LIENZO_3D, TECLA, atajo="W A S D o las flechas"),
        "object.add": Lugar("object.add", "Agregar", "en el Estudio, el botón «Agregar» de arriba", MENU,
                            ruta="Agregar"),
        "transform.rotate": Lugar("transform.rotate", "Girar", "en el Estudio, el panel del objeto elegido", MENU,
                                  ruta="Objeto › Girar"),
        "transform.scale": Lugar("transform.scale", "Tamaño", "en el Estudio, el panel del objeto elegido", MENU,
                                 ruta="Objeto › Tamaño"),
        "file.save": Lugar("file.save", "Descargar", "en el Estudio, el botón «Descargar mi escena»", MENU,
                           ruta="Descargar"),
    },
    por_validador={"spatial.grounded": "transform.move", "spatial.touching": "transform.move",
                   "object.count": "object.add", "dimension.approx": "transform.scale"},
)


def escena_desde_foto(foto: Mapping[str, Any]) -> SceneState:
    """La foto del Motor Web (y arriba, en A-Frame) como escena del corazón (z arriba, como Blender).

    Cada zona viaja como un vacío con la etiqueta ``zona`` y su radio en las
    dimensiones; los objetos tocados llevan la etiqueta ``tocado``.
    """
    objetos = []
    for nombre, o in sorted((foto.get("objetos") or {}).items()):
        x, y, z = float(o.get("x", 0)), float(o.get("y", 0)), float(o.get("z", 0))
        objetos.append(SceneObject(name=str(nombre), object_type="MESH", location=(x, -z, y),
                                   tags=("tocado",) if o.get("tocado") else ()))
    for nombre, zona in sorted((foto.get("zonas") or {}).items()):
        r = float(zona.get("radio", 1))
        objetos.append(SceneObject(name=str(nombre), object_type="EMPTY",
                                   location=(float(zona.get("x", 0)), -float(zona.get("z", 0)), 0.0),
                                   dimensions=(2 * r, 2 * r, 0.0), tags=("zona",)))
    return SceneState(blender_version="", file_path="", file_saved=False, objects=tuple(objetos))


__all__ = ["PERFIL", "escena_desde_foto"]
