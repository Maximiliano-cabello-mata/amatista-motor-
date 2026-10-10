"""Amatista Taller en Blender (add-on 5.0): la habilidad es la unidad.

El alumno ya no recorre una práctica de once misiones: aprende habilidades
con el mismo ciclo (Mira → Hazlo conmigo → Hazlo tú → Úsalo → Recuérdalo)
y el modelo del alumno del motor (amatista_engine.taller) decide qué toca.

- datos.py: el catálogo de habilidades, el avance del alumno sin conexión
  (avance_taller_*.json) y su envío a la plataforma.
- sesion.py: la actividad de ahora, la revisión mientras trabaja, la
  escalera de pistas con freno y el registro de cada intento.
- escena.py: la escena del taller, limpia en cada actividad.
- demo.py: «Mira» y «Mírame», animadas en la vista 3D con objetos temporales.
- vista/: el molde translúcido (gpu) y la tarjeta clicable abajo al centro.
- panel.py: el panel lateral mínimo; operadores.py: sus botones.
- isla.py: cada proyecto terminado deja su pieza en «Mi isla».

Base: docs/investigacion/2026-10-10_addon_de_ensenanza/ (§6).
"""
import bpy

from . import datos, demo, operadores, panel, sesion, vista

CLASES = operadores.CLASES + panel.CLASES + vista.CLASES


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)
    sesion.register()
    vista.register()


def unregister():
    vista.unregister()
    sesion.unregister()
    demo.unregister()
    datos.unregister()
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
