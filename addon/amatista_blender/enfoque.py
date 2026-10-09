"""Modo enfocado (motor 3.4): Blender muestra solo lo que usa la práctica.

Blender completo abruma a quien empieza: decenas de menús, una barra de
herramientas con 20 íconos y paneles por todas partes. Como las «ruedas de
entrenamiento» de los programas de diseño y el enmascarado de los tutoriales
de Unity, el modo enfocado esconde lo que la práctica no usa y deja a mano
lo que sí:

- En la vista 3D se ocultan la barra de herramientas (T) y la de ajustes de
  la herramienta; la barra lateral queda abierta en la pestaña Amatista.
- El menú de la cabecera muestra solo «Vista» y «Agregar» (y «Seleccionar»
  en modo edición), y «Agregar» (Shift+A) solo las piezas del modelo.
- El panel «Tus herramientas» (interfaz/paneles.py) lista las de la
  práctica, con «Usar» y «¿Cómo se usa?».

Nada se borra: «Ver todo Blender» lo devuelve como estaba. Lo que había en
cada vista se guarda en el propio Screen (propiedad «amatista_enfoque»),
así que cerrar Blender, abrir otro .blend o desinstalar el add-on también
lo restaura. Por defecto se enfoca en los niveles 1 y 2 («auto»).
"""
import bpy

from . import ajustes

PROPIEDAD = "amatista_enfoque"
NIVEL_AUTO = 2  # «auto»: enfocado hasta el nivel 2 (los dos primeros niveles del curso)
PRIMITIVAS_BASE = ("cube", "cylinder", "sphere", "cone")
# Agregar › Malla en español: (operador, texto, ícono).
PRIMITIVAS = {
    "cube": ("mesh.primitive_cube_add", "Cubo", "MESH_CUBE"),
    "cylinder": ("mesh.primitive_cylinder_add", "Cilindro", "MESH_CYLINDER"),
    "sphere": ("mesh.primitive_uv_sphere_add", "Esfera UV", "MESH_UVSPHERE"),
    "icosphere": ("mesh.primitive_ico_sphere_add", "Icoesfera", "MESH_ICOSPHERE"),
    "cone": ("mesh.primitive_cone_add", "Cono", "MESH_CONE"),
    "torus": ("mesh.primitive_torus_add", "Toroide", "MESH_TORUS"),
    "plane": ("mesh.primitive_plane_add", "Plano", "MESH_PLANE"),
    "circle": ("mesh.primitive_circle_add", "Círculo", "MESH_CIRCLE"),
    "suzanne": ("mesh.primitive_monkey_add", "Mono", "MESH_MONKEY"),
}

ESTADO = {
    "activo": False,
    "primitivas": PRIMITIVAS_BASE,
    "herramientas": frozenset(),
    # El alumno pidió «Ver todo Blender» en esta práctica: no se vuelve a enfocar solo.
    "rechazado": "",
    "originales": {},
}


# --- ¿Enfocar? -------------------------------------------------------------------------


def preferencia():
    p = ajustes.prefs()
    return getattr(p, "enfoque", "auto") if p else "auto"


def debe_enfocar(practica):
    modo = preferencia()
    if practica is None or modo == "nunca":
        return False
    if modo == "siempre":
        return True
    return int(getattr(practica, "level", 1) or 1) <= NIVEL_AUTO


def activo():
    return ESTADO["activo"]


def primitivas_de(practica):
    """Las piezas que el modelo usa (o las básicas si la práctica no trae modelo)."""
    referencia = getattr(practica, "reference", None)
    vistas = []
    for parte in getattr(referencia, "compared", ()) or ():  # el suelo de la escena no es una pieza
        clave = "sphere" if parte.primitive == "uv_sphere" else parte.primitive
        if clave in PRIMITIVAS and clave not in vistas:
            vistas.append(clave)
    return tuple(vistas) or PRIMITIVAS_BASE


# --- Vistas 3D -----------------------------------------------------------------------------


def _areas_3d():
    wm = getattr(bpy.context, "window_manager", None)
    for ventana in getattr(wm, "windows", ()) or ():
        pantalla = ventana.screen
        if pantalla is None:
            continue
        for indice, area in enumerate(pantalla.areas):
            if area.type == "VIEW_3D":
                yield pantalla, indice, area


def _enfocar_area(pantalla, indice, area):
    espacio = area.spaces.active
    guardado = dict(pantalla.get(PROPIEDAD, {}) or {})
    clave = str(indice)
    if clave not in guardado:  # la primera vez: lo que el alumno tenía
        guardado[clave] = [int(espacio.show_region_toolbar), int(espacio.show_region_tool_header),
                           int(espacio.show_region_ui)]
        pantalla[PROPIEDAD] = guardado
    espacio.show_region_toolbar = False
    espacio.show_region_tool_header = False
    espacio.show_region_ui = True
    for region in area.regions:
        if region.type == "UI":
            try:  # Blender 4.2 todavía no deja elegir la pestaña desde Python
                region.active_panel_category = "Amatista"
            except (AttributeError, TypeError, ValueError):
                pass
    area.tag_redraw()


def restaurar_pantalla(pantalla):
    """Devuelve cada vista 3D de un Screen a como estaba antes de enfocar."""
    guardado = pantalla.get(PROPIEDAD) if pantalla is not None else None
    if not guardado:
        return False
    areas = list(pantalla.areas)
    for clave, valores in dict(guardado).items():
        try:
            area = areas[int(clave)]
        except (ValueError, IndexError):
            continue
        if area.type != "VIEW_3D":
            continue
        espacio = area.spaces.active
        barra, cabecera, lateral = (bool(v) for v in list(valores)[:3])
        espacio.show_region_toolbar = barra
        espacio.show_region_tool_header = cabecera
        espacio.show_region_ui = lateral
        area.tag_redraw()
    del pantalla[PROPIEDAD]
    return True


# --- Menús de la cabecera y Shift+A ----------------------------------------------------------


def _menus_enfocados(self, context):
    layout = self.layout
    layout.menu("VIEW3D_MT_view")
    modo = context.mode
    if modo == "OBJECT":
        layout.menu("VIEW3D_MT_add")
    elif modo == "EDIT_MESH":
        layout.menu("VIEW3D_MT_select_edit_mesh")
    layout.separator()
    fila = layout.row()
    fila.alert = False
    fila.operator("amatista.ver_todo", text="Ver todo Blender", icon="FULLSCREEN_ENTER", emboss=False)


def _agregar_enfocado(self, context):
    layout = self.layout
    layout.operator_context = "EXEC_REGION_WIN"
    for clave in ESTADO["primitivas"]:
        operador, texto, icono = PRIMITIVAS[clave]
        layout.operator(operador, text=texto, icon=icono)
    herramientas = ESTADO["herramientas"]
    if "light.add" in herramientas or "camera.add" in herramientas:
        layout.separator()
    if "light.add" in herramientas:
        layout.menu("VIEW3D_MT_light_add", text="Luz", icon="OUTLINER_OB_LIGHT")
    if "camera.add" in herramientas:
        layout.operator("object.camera_add", text="Cámara", icon="OUTLINER_OB_CAMERA")
    layout.separator()
    layout.operator_context = "INVOKE_DEFAULT"
    layout.operator("amatista.ver_todo", text="Más piezas: ver todo Blender", icon="FULLSCREEN_ENTER")


def _seguro(enfocado, original):
    """Si el dibujo enfocado falla, Blender dibuja su menú de siempre."""

    def dibujar(self, context):
        if not ESTADO["activo"]:
            return original(self, context)
        try:
            return enfocado(self, context)
        except Exception as error:  # noqa: BLE001 - un menú roto no puede romper Blender
            print(f"[Amatista] Menú enfocado: {error}")
            return original(self, context)

    dibujar._amatista = True
    return dibujar


MENUS = (("VIEW3D_MT_editor_menus", _menus_enfocados), ("VIEW3D_MT_add", _agregar_enfocado))


def _parchar_menus():
    for nombre, enfocado in MENUS:
        clase = getattr(bpy.types, nombre, None)
        if clase is None or getattr(clase.draw, "_amatista", False):
            continue
        ESTADO["originales"][nombre] = clase.draw
        clase.draw = _seguro(enfocado, clase.draw)


def _devolver_menus():
    for nombre, original in list(ESTADO["originales"].items()):
        clase = getattr(bpy.types, nombre, None)
        if clase is not None and getattr(clase.draw, "_amatista", False):
            clase.draw = original
    ESTADO["originales"].clear()


# --- Encender y apagar ------------------------------------------------------------------------


def activar(practica=None, herramientas=()):
    """Enfoca todas las vistas 3D abiertas (se puede llamar de nuevo sin daño)."""
    if practica is not None:
        ESTADO["primitivas"] = primitivas_de(practica)
        ESTADO["herramientas"] = frozenset(herramientas or getattr(practica, "allowed_tools", ()))
    ESTADO["activo"] = True
    _parchar_menus()
    for pantalla, indice, area in _areas_3d():
        try:
            _enfocar_area(pantalla, indice, area)
        except (AttributeError, TypeError, RuntimeError) as error:
            print(f"[Amatista] No se pudo enfocar una vista: {error}")
    return True


def desactivar():
    """Blender completo otra vez, exactamente como estaba."""
    ESTADO["activo"] = False
    _devolver_menus()
    vistas = set()
    for pantalla, _indice, _area in _areas_3d():
        if pantalla.as_pointer() in vistas:
            continue
        vistas.add(pantalla.as_pointer())
        try:
            restaurar_pantalla(pantalla)
        except (AttributeError, TypeError, RuntimeError) as error:
            print(f"[Amatista] No se pudo restaurar una vista: {error}")
    # Las demás pantallas del archivo (otros espacios de trabajo) también.
    for pantalla in getattr(bpy.data, "screens", ()):
        if pantalla.as_pointer() not in vistas and pantalla.get(PROPIEDAD):
            try:
                restaurar_pantalla(pantalla)
            except (AttributeError, TypeError, RuntimeError):
                pass
    return True


def al_abrir_practica(practica, nueva):
    """Al abrir una práctica: enfocar según el nivel y la preferencia del alumno."""
    if nueva:
        ESTADO["rechazado"] = ""
    if debe_enfocar(practica) and ESTADO["rechazado"] != practica.id:
        activar(practica)
    elif ESTADO["activo"]:
        desactivar()


def ver_todo(practica_id=""):
    """El alumno (o la plataforma) pide Blender completo."""
    ESTADO["rechazado"] = practica_id or ESTADO["rechazado"]
    desactivar()


def al_abrir_archivo():
    """Otro .blend: sus vistas pueden venir guardadas en modo enfocado sin que nada lo recuerde."""
    for pantalla in getattr(bpy.data, "screens", ()):
        if pantalla.get(PROPIEDAD) and not ESTADO["activo"]:
            try:
                restaurar_pantalla(pantalla)
            except (AttributeError, TypeError, RuntimeError):
                pass


def unregister():
    try:
        desactivar()
    except Exception as error:  # noqa: BLE001 - desregistrar nunca debe fallar
        print(f"[Amatista] No se pudo salir del modo enfocado: {error}")
        _devolver_menus()
