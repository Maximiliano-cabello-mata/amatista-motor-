"""Propiedades del add-on.

- Scene.amatista: la práctica abierta en este .blend (se guarda con el
  archivo: al reabrirlo sigue la misma práctica, con sus pistas).
- Scene.amatista_autor: el trabajo del modo desarrollador (Author).
- WindowManager.amatista: estado de la sesión (no se guarda).
"""
import bpy

# Blender exige conservar las listas de los EnumProperty dinámicos mientras
# se muestran: si Python las libera, la interfaz muestra basura.
_CACHE = {"roles": [], "catalogo": [], "objetivos": [], "plantillas": []}


def _items_roles(self, context):
    from . import practicas

    items = []
    wm = getattr(context, "window_manager", None) if context else None
    if wm is not None and wm.amatista.modo == "autor":
        # En Author mandan los roles del borrador, aunque aún no compile.
        from . import autor

        roles = (autor.leer_borrador() or {}).get("roles") or {}
        for rid, datos in roles.items():
            datos = datos if isinstance(datos, dict) else {}
            etiqueta = datos.get("label") or rid
            items.append((rid, etiqueta, datos.get("description") or etiqueta))
    if not items:
        practica = practicas.practica_activa(context) or practicas.practica_borrador()
        items = [(r.id, r.label, r.description or r.label) for r in (practica.roles if practica else ())]
    if not items:
        items = [("", "Sin roles", "La práctica no declara roles")]
    _CACHE["roles"] = items
    return items


def _items_catalogo(self, context):
    from . import practicas

    items = [
        (pid, meta.get("title", pid), meta.get("description", "")[:200])
        for pid, meta in practicas.catalogo().items()
    ]
    _CACHE["catalogo"] = items or [("", "Sin prácticas", "")]
    return _CACHE["catalogo"]


def _items_objetivos(self, context):
    from . import autor

    borrador = autor.leer_borrador() or {}
    items = [(t.get("id", ""), t.get("title") or t.get("id", ""), t.get("validator", "")) for t in borrador.get("targets", [])]
    _CACHE["objetivos"] = items or [("", "Sin objetivos", "")]
    return _CACHE["objetivos"]


def _items_requisito(self, context):
    items = [("__ninguno__", "Ninguno", "No depende de otro objetivo")] + [
        i for i in _items_objetivos(self, context) if i[0]
    ]
    _CACHE["requisitos"] = items
    return items


def _items_plantillas(self, context):
    from . import _motor

    items = [
        (spec.id, spec.label, spec.description) for spec in _motor.MOTOR.registry.specs()
    ]
    _CACHE["plantillas"] = items
    return items


SIN_PLANTILLA = "__ninguna__"


def _items_plantillas_practica(self, context):
    from . import _motor

    # Un identificador vacío en Blender es un título, no una opción: «Sin
    # plantilla» no se podía elegir y Blender avisaba «matches no enum».
    items = [(SIN_PLANTILLA, "Sin plantilla", "Solo lo mínimo")] + [
        (nombre, nombre.capitalize(), f"Práctica de tipo {nombre} con píldoras y objetivos de ejemplo")
        for nombre in sorted(_motor.practica.PLANTILLAS)
    ]
    _CACHE["plantillas_practica"] = items
    return items


CURSOS = [
    ("blender_principiante", "Principiante", "Curso para quien empieza desde cero"),
    ("blender_principiante_intermedio", "Principiante-Intermedio", "Materiales, luces, render y animación"),
    ("blender_intermedio", "Intermedio", "Próximamente"),
    ("blender_avanzado", "Avanzado", "Próximamente"),
]
DISPAROS = [
    ("start", "Al empezar", "En cuanto se abre la práctica"),
    ("target", "En un paso", "Cuando un objetivo es el paso actual"),
    ("guard", "Al pausar", "Cuando un vigilante pausa el progreso"),
    ("complete", "Al terminar", "Cuando la práctica se completa"),
]
EJES = [("x", "X", "Eje X"), ("y", "Y", "Eje Y"), ("z", "Z", "Eje Z (altura)")]
MODOS = [
    ("alumno", "Alumno", "La práctica como la ve un alumno", "USER", 0),
    ("autor", "Desarrollador", "Amatista Author: diseñar, depurar y publicar prácticas", "TOOL_SETTINGS", 1),
]


class EstadoEscena(bpy.types.PropertyGroup):
    practica_id: bpy.props.StringProperty()
    practica_json: bpy.props.StringProperty(description="Definición de la práctica usada en este archivo")
    origen: bpy.props.StringProperty(description="paquete, servidor o borrador")
    pistas_json: bpy.props.StringProperty(default="{}")
    correcciones: bpy.props.IntProperty(default=0, min=0)
    mejor_progreso: bpy.props.FloatProperty(default=0.0)
    progreso_enviado: bpy.props.FloatProperty(default=-1.0)
    completada_enviada: bpy.props.BoolProperty(default=False)
    avisos_vistos: bpy.props.StringProperty(description="Herramientas ya avisadas (ids separados por comas)")
    celebrada: bpy.props.BoolProperty(default=False)
    rol_elegido: bpy.props.EnumProperty(name="Rol", items=_items_roles)


class EstadoAutor(bpy.types.PropertyGroup):
    texto: bpy.props.StringProperty(name="Borrador", default="amatista_practica.json")
    # Datos de la práctica
    nuevo_id: bpy.props.StringProperty(name="Id", default="blender.n1.nueva")
    nuevo_titulo: bpy.props.StringProperty(name="Título", default="Nueva práctica")
    nuevo_nivel: bpy.props.IntProperty(name="Nivel", default=1, min=1, max=5)
    nueva_plantilla: bpy.props.EnumProperty(name="Plantilla", items=_items_plantillas_practica)
    nuevo_curso: bpy.props.EnumProperty(name="Curso", items=CURSOS)
    nuevo_modulo: bpy.props.IntProperty(name="Módulo", default=1, min=1, max=12)
    # Píldoras (motor v3)
    pil_titulo: bpy.props.StringProperty(name="Título")
    pil_texto: bpy.props.StringProperty(name="Idea", description="Una idea, dos frases como máximo (≤ 280 caracteres)")
    pil_teclas: bpy.props.StringProperty(name="Teclas", description="Separadas por + (Ctrl + R)")
    pil_disparo: bpy.props.EnumProperty(name="Aparece", items=DISPAROS, default="start")
    pil_objetivo: bpy.props.EnumProperty(name="Objetivo", items=_items_objetivos)
    # Casos de prueba
    caso_nombre: bpy.props.StringProperty(name="Caso", default="Solución completa")
    # Tagger
    nuevo_rol: bpy.props.StringProperty(name="Rol nuevo", description="Id del rol (minúsculas, sin espacios)")
    nuevo_rol_etiqueta: bpy.props.StringProperty(name="Nombre visible")
    etiqueta: bpy.props.StringProperty(name="Etiqueta")
    # Constructor de objetivos
    plantilla: bpy.props.EnumProperty(name="Tipo", items=_items_plantillas)
    obj_id: bpy.props.StringProperty(name="Id del objetivo")
    obj_titulo: bpy.props.StringProperty(name="Título")
    obj_rol: bpy.props.EnumProperty(name="Rol", items=_items_roles)
    obj_rol_ref: bpy.props.EnumProperty(name="Rol de referencia", items=_items_roles)
    obj_nombre: bpy.props.StringProperty(name="Nombre")
    obj_cantidad: bpy.props.IntProperty(name="Cantidad", default=1, min=0)
    obj_minimo: bpy.props.FloatProperty(name="Mínimo", default=0.0)
    obj_maximo: bpy.props.FloatProperty(name="Máximo", default=1.0)
    obj_eje: bpy.props.EnumProperty(name="Eje", items=EJES, default="z")
    obj_modificador: bpy.props.StringProperty(name="Modificador", default="BEVEL")
    obj_texto: bpy.props.StringProperty(name="Texto")
    obj_peso: bpy.props.FloatProperty(name="Peso", default=10.0, min=0.0, max=100.0)
    obj_requiere: bpy.props.EnumProperty(name="Requiere", items=_items_requisito)
    obj_opcional: bpy.props.BoolProperty(name="Opcional")
    obj_consejo: bpy.props.StringProperty(name="Consejo")
    # Pistas y edición de un objetivo existente
    objetivo: bpy.props.EnumProperty(name="Objetivo", items=_items_objetivos)
    pista: bpy.props.StringProperty(name="Pista")
    # Publicación
    curso_id: bpy.props.StringProperty(name="Curso", default="blender")
    leccion_id: bpy.props.StringProperty(name="Lección", description="Lección de la plataforma donde vive (opcional)")
    nota: bpy.props.StringProperty(name="Nota de versión")
    depurar: bpy.props.BoolProperty(name="Mostrar diagnóstico", default=True)


PESTANAS = [
    ("aprender", "Aprender", "La teoría de este momento y tu repaso", "HELP", 0),
    ("practicar", "Practicar", "La práctica en Blender, paso a paso", "PLAY", 1),
    ("curso", "Mi curso", "El mapa de tus cursos y tu avance", "OUTLINER_COLLECTION", 2),
]


class EstadoSesion(bpy.types.PropertyGroup):
    modo: bpy.props.EnumProperty(name="Modo", items=MODOS, default="alumno")
    pestana: bpy.props.EnumProperty(name="Sección", items=PESTANAS, default="practicar")
    practica_elegida: bpy.props.EnumProperty(name="Práctica", items=_items_catalogo)
    vista_previa: bpy.props.BoolProperty(
        name="Vista previa como alumno", description="Prueba el borrador exactamente como lo verá un alumno"
    )


CLASES = (EstadoEscena, EstadoAutor, EstadoSesion)


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)
    bpy.types.Scene.amatista = bpy.props.PointerProperty(type=EstadoEscena)
    bpy.types.Scene.amatista_autor = bpy.props.PointerProperty(type=EstadoAutor)
    bpy.types.WindowManager.amatista = bpy.props.PointerProperty(type=EstadoSesion)


def unregister():
    del bpy.types.WindowManager.amatista
    del bpy.types.Scene.amatista_autor
    del bpy.types.Scene.amatista
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
