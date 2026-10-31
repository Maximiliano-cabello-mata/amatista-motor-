"""Dónde está cada herramienta, dicho como lo ve el alumno (motor 7).

Hasta el motor 6 la pista «Con qué» decía siempre «mira la herramienta que
brilla en la barra de la izquierda», aunque la herramienta fuera Agregar
(un menú de la cabecera), Guardar (el menú Archivo de arriba) o un
modificador (Propiedades, a la derecha), y aunque el modo enfocado hubiera
escondido esa barra. Aquí cada herramienta dice **su** lugar real y qué
puede hacer Amatista para señalarla de verdad:

- ``barra``: es un botón de la barra de herramientas (T). El add-on la
  deja elegida con ``wm.tool_set_by_id``: Blender mismo pinta su botón
  resaltado y muestra su manipulador.
- ``menu``: es un menú. El add-on lo abre (``wm.call_menu``) donde está el
  ratón; no se puede «iluminar» una entrada de menú.
- ``pestana``: una pestaña del editor Propiedades. El add-on la abre.
- ``dialogo``: un operador con su ventana (Guardar como, F12). El add-on
  abre la ventana; el alumno escribe y confirma.
- ``tecla``: solo un atajo (las vistas 1, 3 y 7, deshacer).

El texto nunca dice «brilla»: eso lo agrega el add-on solo si de verdad
señaló algo (guion/senalar.py del add-on).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .. import terminos

BARRA, MENU, PESTANA, DIALOGO, TECLA = "barra", "menu", "pestana", "dialogo", "tecla"


@dataclass(frozen=True)
class Donde:
    herramienta: str
    nombre: str
    lugar: str  # dónde está en la pantalla, en una frase («en la cabecera de la vista 3D, arriba»)
    ruta: str = ""  # la ruta de menú («Agregar › Malla › Cilindro»); se traduce al idioma de Blender
    atajo: str = ""  # «Shift + A» (con el ratón sobre la vista 3D)
    tipo: str = TECLA
    objetivo: str = ""  # lo que el add-on usa para señalar: id de herramienta, menú, pestaña u operador
    modo: str = "OBJECT"  # el modo en que existe (EDIT para Extruir)


# Nombre de la malla de cada primitiva, como sale en Agregar › Malla.
MALLAS = {"cube": "Cubo", "cylinder": "Cilindro", "sphere": "Esfera UV", "uv_sphere": "Esfera UV",
          "icosphere": "Icoesfera", "cone": "Cono", "torus": "Toroide", "plane": "Plano", "circle": "Círculo",
          "suzanne": "Mono", "monkey": "Mono"}
SOBRE_LA_VISTA = "con el ratón sobre la vista 3D"
CABECERA = "en la cabecera de la vista 3D (la fila de menús de arriba de la vista)"
ARRIBA = "en la barra de menús de arriba de todo"
PROPIEDADES = "en el editor Propiedades (abajo a la derecha), en la columna de pestañas de su borde izquierdo"

TABLA = {
    "object.add": Donde("object.add", "Agregar", CABECERA, "Agregar › Malla", f"Shift + A {SOBRE_LA_VISTA}", MENU,
                        "VIEW3D_MT_add"),
    "transform.move": Donde("transform.move", "Mover", "en la barra de herramientas, a la izquierda de la vista 3D",
                            "", f"G {SOBRE_LA_VISTA}; X, Y o Z lo deja en un eje", BARRA, "builtin.move"),
    "transform.rotate": Donde("transform.rotate", "Rotar", "en la barra de herramientas, a la izquierda de la vista 3D",
                              "", f"R {SOBRE_LA_VISTA}; X, Y o Z gira sobre un eje", BARRA, "builtin.rotate"),
    "transform.scale": Donde("transform.scale", "Escalar", "en la barra de herramientas, a la izquierda de la vista 3D",
                             "", f"S {SOBRE_LA_VISTA}; X, Y o Z estira en un eje", BARRA, "builtin.scale"),
    "select.box": Donde("select.box", "Selección de caja", "en la barra de herramientas, arriba de todo", "",
                        "B", BARRA, "builtin.select_box"),
    "select.circle": Donde("select.circle", "Selección circular", "en la barra de herramientas, arriba", "",
                           "C", BARRA, "builtin.select_circle"),
    "object.duplicate": Donde("object.duplicate", "Duplicar", CABECERA, "Objeto › Duplicar objetos",
                              f"Shift + D {SOBRE_LA_VISTA}", MENU, "VIEW3D_MT_object"),
    "object.delete": Donde("object.delete", "Eliminar", CABECERA, "Objeto › Eliminar", f"X {SOBRE_LA_VISTA}", MENU,
                           "VIEW3D_MT_object"),
    "object.rename": Donde("object.rename", "Renombrar", "en la lista de la escena (arriba a la derecha): doble clic "
                           "sobre el nombre", "", "F2", TECLA),
    "transform.apply": Donde("transform.apply", "Aplicar la escala", CABECERA, "Objeto › Aplicar › Escala",
                             f"Ctrl + A {SOBRE_LA_VISTA}", MENU, "VIEW3D_MT_object_apply"),
    "collection.move": Donde("collection.move", "Mover a colección", CABECERA, "Objeto › Colección › Mover a colección",
                             f"M {SOBRE_LA_VISTA}", MENU, "VIEW3D_MT_object_collection"),
    "file.save": Donde("file.save", "Guardar", ARRIBA, "Archivo › Guardar como", "Ctrl + Shift + S", DIALOGO,
                       "wm.save_as_mainfile"),
    "mesh.edit": Donde("mesh.edit", "Modo edición", "en la cabecera de la vista 3D, el selector que dice «Modo objeto»",
                       "", f"Tab {SOBRE_LA_VISTA}", TECLA),
    "mesh.extrude": Donde("mesh.extrude", "Extruir", "en la barra de herramientas de la izquierda (en modo edición)", "",
                          "E", BARRA, "builtin.extrude_region", "EDIT"),
    "mesh.loopcut": Donde("mesh.loopcut", "Corte de bucle", "en la barra de herramientas de la izquierda (en modo edición)",
                          "", "Ctrl + R", BARRA, "builtin.loop_cut", "EDIT"),
    "mesh.merge": Donde("mesh.merge", "Fusionar por distancia", "en modo edición, el menú Malla de la cabecera",
                        "Malla › Fusionar › Por distancia", "M › Por distancia", MENU, "VIEW3D_MT_edit_mesh_merge", "EDIT"),
    "material.basic": Donde("material.basic", "Material", PROPIEDADES, "Material › Nuevo", "", PESTANA, "MATERIAL"),
    "material.principled": Donde("material.principled", "Material", PROPIEDADES, "Material › Nuevo", "", PESTANA,
                                 "MATERIAL"),
    "modifier": Donde("modifier", "Modificadores", PROPIEDADES + " (la llave azul)",
                      "Agregar modificador › Generar", "", PESTANA, "MODIFIER"),
    "light.add": Donde("light.add", "Luz", CABECERA, "Agregar › Luz", f"Shift + A {SOBRE_LA_VISTA}", MENU,
                       "VIEW3D_MT_light_add"),
    "camera.add": Donde("camera.add", "Cámara", CABECERA, "Agregar › Cámara", f"Shift + A {SOBRE_LA_VISTA}", MENU,
                        "VIEW3D_MT_add"),
    "camera.view": Donde("camera.view", "Vista de cámara", "el teclado numérico", "", "0 del teclado numérico", TECLA),
    "render.f12": Donde("render.f12", "Renderizar", ARRIBA, "Renderizar › Renderizar imagen", "F12", DIALOGO,
                        "render.render"),
    "render.engine": Donde("render.engine", "Motor de render", PROPIEDADES + " (la cámara de fotos de atrás)", "",
                           "", PESTANA, "RENDER"),
    "anim.keyframe": Donde("anim.keyframe", "Fotograma clave", "sobre la vista 3D o sobre un valor de la barra N",
                           "", f"I {SOBRE_LA_VISTA}", TECLA),
    "view.numpad": Donde("view.numpad", "Vistas", "el teclado numérico; sin él, los ejes de colores arriba a la "
                         "derecha de la vista 3D (clic en un eje)", "", "1 frente · 3 lado · 7 arriba", TECLA),
    "amatista.rol": Donde("amatista.rol", "Roles de Amatista", "en la barra lateral de la vista 3D (tecla N), pestaña "
                          "Amatista, sección «Roles»", "", "N", PESTANA, "ROLES"),
    "view.navigate": Donde("view.navigate", "Mover la vista", "la rueda del ratón sobre la vista 3D", "",
                           "rueda presionada gira · Shift + rueda desplaza · rueda acerca", TECLA),
}

# Validador → la herramienta con la que se arregla (la primera que sirve).
POR_VALIDADOR = {
    "object.count": "object.add", "role.count": "object.add", "object.exists": "object.add",
    "shape.proportion": "transform.scale", "dimension.approx": "transform.scale",
    "shape.thinnest_axis": "transform.rotate",
    "spatial.grounded": "transform.move", "spatial.touching": "transform.move", "spatial.on_top": "transform.move",
    "spatial.below": "transform.move",
    "figure.recognize": "view.numpad", "figure.silhouette": "view.numpad",
    "file.named": "file.save", "file.saved": "file.save",
    "modifier.exists": "modifier", "modifier.configured": "modifier",
    "material.matches": "material.principled", "material.exists": "material.principled",
    "material.distinct": "material.principled",
    "scene.light_exists": "light.add", "light.three_point": "light.add",
    "scene.camera_exists": "camera.add", "camera.frames": "camera.view", "camera.active": "camera.view",
    "render.done": "render.f12", "render.engine": "render.engine",
    "animation.keyframes": "anim.keyframe", "animation.varies": "anim.keyframe",
    "scene.mode": "mesh.edit", "mesh.face_count": "mesh.extrude", "mesh.vertex_count": "mesh.extrude",
    "mesh.no_duplicates": "mesh.merge", "mesh.one_side": "mesh.edit",
    "transform.scale_applied": "transform.apply", "collection.contains": "collection.move",
}


def de(herramienta: str) -> Optional[Donde]:
    if not herramienta:
        return None
    if herramienta.startswith("modifier."):
        return TABLA["modifier"]
    return TABLA.get(herramienta)


def para_validador(validador: str, params=None) -> str:
    """La herramienta que arregla un objetivo de ese validador ("" si no se sabe)."""
    params = params or {}
    if validador == "logic.any":
        for opcion in params.get("options") or ():
            h = para_validador(str(opcion.get("validator", "")), opcion.get("params"))
            if h:
                return h
        return ""
    if validador == "shape.thinnest_axis":
        return "transform.rotate" if params.get("axis") in ("horizontal", "x", "y") else "transform.scale"
    return POR_VALIDADOR.get(validador, "")


def frase(d: Donde, idioma: str = "", primitiva: str = "") -> str:
    """Una frase que dice dónde está y cómo se abre, con la ruta en el idioma de Blender."""
    ruta = d.ruta
    if d.herramienta == "object.add" and primitiva:
        ruta = f"Agregar › Malla › {MALLAS.get(primitiva, primitiva.capitalize())}"
    partes = []
    if ruta:
        partes.append(f"{ruta}, {d.lugar}")
    else:
        partes.append(f"«{d.nombre}» está {d.lugar}" if not d.lugar.startswith("el ") and not d.lugar.startswith("la ")
                      else f"«{d.nombre}»: {d.lugar}")
    if d.atajo:
        partes.append(f"atajo: {d.atajo}")
    return terminos.menus(". ".join(partes) + ".", idioma or None)


def todas() -> Tuple[Donde, ...]:
    return tuple(TABLA.values())


__all__ = ["BARRA", "DIALOGO", "MENU", "PESTANA", "TECLA", "Donde", "MALLAS", "POR_VALIDADOR", "TABLA", "de", "frase",
           "para_validador", "todas"]
