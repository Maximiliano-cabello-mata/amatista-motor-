"""Amatista para Blender (add-on 5.4: Amatista dentro de Blender).

Add-on 5.4 (integracion.py, protocolo.py): menú Amatista en la barra de arriba,
botón Amatista en la cabecera de la vista 3D (despliega el taller sin la tecla
N), la actividad en la barra de estado, el espacio de trabajo «Amatista» y el
enlace amatista:// que abre Blender desde la plataforma aunque esté cerrado.

Add-on 5.3: menús en el idioma de tu Blender y «Palabras de Blender».

Add-on 5.2: tres prácticas cortas (recorrido.py y recorrido_pasos.py) explican
todas las herramientas del add-on: la pestaña Amatista (cuenta, plataforma,
lección actual, ajustes, guardar), la vista 3D con «Tus herramientas», «¿Cómo
se usa?» y el modo enfocado, y cómo enseña el taller (tarjeta, «Mira», molde,
pistas, pausa, Mi isla, repasos). La página Blender de la plataforma las
empieza y las ve en vivo por el enlace. Reemplazan los primeros pasos del 5.1.

Add-on 5.0, motor 5 (taller/): la habilidad es la unidad. El alumno aprende
cada habilidad con el ciclo Mira → Hazlo conmigo → Hazlo tú → Úsalo →
Recuérdalo; el modelo del alumno decide qué toca, el molde translúcido dice
qué falta sobre el modelo, las teclas se piden (no se dictan) y cada
proyecto terminado deja su pieza en «Mi isla». La barra lateral del alumno
es un panel mínimo: la instrucción vive en la tarjeta de la vista 3D y los
cursos, en la plataforma. Lo de las versiones anteriores sigue para el modo
desarrollador y su vista previa.

Historia:

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

Motor 4: la práctica es una ruta de misiones en fila (mision.py): una sola
tarjeta en la vista 3D con la misión de ahora, sus teclas que se encienden al
usarlas, sus herramientas iluminadas (y elegidas en la barra T en los niveles
1 y 2), animaciones al empezar y al cumplir cada misión, y medidas amables.

Nada pesado al importar: la red y la evaluación arrancan con temporizadores.
Documentación: docs/motor/ en el repositorio.
"""
bl_info = {  # solo para instalarlo como add-on clásico; en 4.2+ manda blender_manifest.toml
    "name": "Amatista Motor",
    "author": "Maximiliano Cabello Mata",
    "version": (5, 4, 0),
    "blender": (4, 2, 0),
    "location": "Vista 3D › Barra lateral (N) › Amatista",
    "description": "Aprende Blender habilidad por habilidad con Amatista Taller",
    "category": "3D View",
}

import bpy  # noqa: E402

from . import ajustes, cuenta, desarrollo, enfoque, enlace, escenarios, estado, guia, integracion, mision, operadores, practicas, recorrido, red
from . import taller
from .interfaz import aprender, dialogos, estilo, herramientas, hud, paneles

CLASES = (
    (ajustes.PreferenciasAmatista,)
    + operadores.CLASES
    + desarrollo.CLASES
    + dialogos.CLASES
    + aprender.CLASES
    + herramientas.CLASES
    + paneles.CLASES
    + recorrido.CLASES
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
    taller.register()  # después de los paneles: su panel cuelga de AMATISTA_PT_principal
    practicas.register()
    enlace.register()
    hud.register()
    integracion.register()  # menú, cabecera, barra de estado y la orden que trajo amatista://
    bpy.app.timers.register(_primer_arranque, first_interval=1.5)


def unregister():
    if bpy.app.timers.is_registered(_primer_arranque):
        bpy.app.timers.unregister(_primer_arranque)
    try:
        escenarios.restaurar_todo()  # el cielo del tema vuelve a como estaba
    except Exception as error:  # noqa: BLE001 - desregistrar nunca debe fallar
        print(f"[Amatista] No se pudo restaurar el mundo: {error}")
    integracion.unregister()
    enfoque.unregister()  # Blender completo otra vez, como estaba
    enlace.unregister()
    recorrido.unregister()
    hud.unregister()
    practicas.unregister()
    cuenta.unregister()  # deja de preguntar por el código de vinculación
    guia.unregister()
    mision.unregister()
    taller.unregister()
    red.unregister()
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
    estilo.liberar_iconos()
    estado.unregister()
