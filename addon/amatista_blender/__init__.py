"""Amatista para Blender (versión 3: plataforma educativa dentro de Blender).

Extensión de Blender 4.2+ (blender_manifest.toml). El alumno tiene tres
secciones: Aprender (teoría en píldoras y repaso), Practicar (la práctica
guiada) y Mi curso (el mapa de cursos). Tres modos sobre el mismo
Amatista Engine:

- Alumno (Student): la práctica de la lección, objetivos, pistas y progreso
  que se guarda en la plataforma.
- Vista previa (Preview): el borrador visto exactamente como un alumno.
- Desarrollador (Author): Tagger, Inspector, constructor de objetivos,
  depurador, compilador y publicación en Amatista.

Motor 3.4: la plataforma maneja Blender (enlace.py: Blender late cada pocos
segundos y recibe órdenes como «abrir esta práctica») y el modo enfocado
(enfoque.py) deja a la vista solo las herramientas de la práctica.

Motor 3.5: cada práctica en su propia escena (abrir otra ya no arrastra lo
de la anterior), la lista del instructor «Tu figura» (la silueta de la malla
comparada parte por parte con el modelo) y la plataforma maneja la práctica
(comprobar, pista, «Hazlo conmigo», guardar, empezar de nuevo).

Nada pesado al importar: la red y la evaluación arrancan con temporizadores.
Documentación: docs/motor/ en el repositorio.
"""
bl_info = {  # solo para instalarlo como add-on clásico; en 4.2+ manda blender_manifest.toml
    "name": "Amatista Motor",
    "author": "Maximiliano Cabello Mata",
    "version": (3, 5, 0),
    "blender": (4, 2, 0),
    "location": "Vista 3D › Barra lateral (N) › Amatista",
    "description": "Prácticas guiadas de Amatista dentro de Blender",
    "category": "3D View",
}

import bpy  # noqa: E402

from . import ajustes, cuenta, desarrollo, enfoque, enlace, escenarios, estado, operadores, practicas
from .interfaz import aprender, dialogos, estilo, herramientas, hud, paneles

CLASES = (
    (ajustes.PreferenciasAmatista,)
    + operadores.CLASES
    + desarrollo.CLASES
    + dialogos.CLASES
    + aprender.CLASES
    + herramientas.CLASES
    + paneles.CLASES
)


def _primer_arranque():
    cuenta.al_iniciar()
    p = ajustes.prefs()
    if p is not None and not p.bienvenida_vista and not bpy.app.background:
        p.bienvenida_vista = True
        ajustes.guardar_preferencias()
        practicas._invocar("amatista.bienvenida")
    return None


def register():
    estado.register()
    estilo.cargar_iconos()
    for clase in CLASES:
        bpy.utils.register_class(clase)
    practicas.register()
    enlace.register()
    hud.register()
    bpy.app.timers.register(_primer_arranque, first_interval=1.5)


def unregister():
    if bpy.app.timers.is_registered(_primer_arranque):
        bpy.app.timers.unregister(_primer_arranque)
    try:
        escenarios.restaurar_todo()  # el cielo del tema vuelve a como estaba
    except Exception as error:  # noqa: BLE001 - desregistrar nunca debe fallar
        print(f"[Amatista] No se pudo restaurar el mundo: {error}")
    enfoque.unregister()  # Blender completo otra vez, como estaba
    enlace.unregister()
    hud.unregister()
    practicas.unregister()
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
    estilo.liberar_iconos()
    estado.unregister()
