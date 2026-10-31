"""Señalar de verdad dónde está una herramienta (motor 7).

El motor 6 dibujaba un borde alrededor de toda la barra de herramientas y
decía «brilla a la izquierda», incluso con la barra escondida por el modo
enfocado y para herramientas que no viven ahí (Agregar, Guardar). Aquí
solo se usa lo que Blender muestra por sí mismo, y el texto dice lo que
pasó **después** de comprobarlo:

- Barra de herramientas: se muestra la barra (T) y se deja elegida la
  herramienta; Blender pinta su botón resaltado y su manipulador.
- Menú: se abre el menú (Agregar, Objeto…) donde está el ratón.
- Pestaña de Propiedades: se abre esa pestaña (Material, Modificadores).
- Roles de Amatista: se abre la barra lateral en la pestaña Amatista.
- Ventanas (Guardar como, F12): no se abren solas; el panel tiene su botón.

Devuelve la frase que se agrega a la pista, o "" si no se pudo señalar nada.
"""
from importlib import import_module

import bpy

from .. import _motor

donde = import_module(_motor.engine.__name__ + ".guion.donde")


def _vistas(context):
    for ventana in getattr(context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                yield ventana, area


def _primera_vista(context):
    if context.area is not None and context.area.type == "VIEW_3D":
        return context.window, context.area
    return next(_vistas(context), (None, None))


def mostrar_barra(context):
    """La barra de herramientas visible en todas las vistas 3D. Devuelve si quedó visible en alguna."""
    visible = False
    for _ventana, area in _vistas(context):
        espacio = area.spaces.active
        try:
            espacio.show_region_toolbar = True
            visible = visible or bool(espacio.show_region_toolbar)
        except (AttributeError, RuntimeError):
            continue
    return visible


def herramienta_elegida(context, modo="OBJECT"):
    try:
        return getattr(context.workspace.tools.from_space_view3d_mode(modo), "idname", "")
    except (AttributeError, RuntimeError, TypeError):
        return ""


def _elegir(context, d):
    ventana, area = _primera_vista(context)
    if area is None:
        return ""
    if d.modo == "EDIT" and context.mode != "EDIT_MESH":
        return ""  # Extruir solo existe en modo edición: la pista lo dice, no se cambia de modo a escondidas
    if not mostrar_barra(context):
        return ""
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    try:
        with context.temp_override(window=ventana, area=area, region=region):
            bpy.ops.wm.tool_set_by_id(name=d.objetivo)
    except (RuntimeError, TypeError) as error:
        print(f"[Amatista] No se pudo elegir {d.objetivo}: {error}")
        return ""
    modo = "EDIT_MESH" if d.modo == "EDIT" else "OBJECT"
    if herramienta_elegida(context, modo) != d.objetivo:
        return ""
    return (f"Te dejé elegida «{d.nombre}»: es el botón resaltado en la barra de herramientas, a la izquierda "
            "de la vista 3D (T la muestra u oculta).")


def _abrir_menu(context, d):
    if bpy.app.background or context.window is None:
        return ""
    ventana, area = _primera_vista(context)
    if area is None:
        return ""
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    try:
        with context.temp_override(window=ventana, area=area, region=region):
            bpy.ops.wm.call_menu(name=d.objetivo)
    except (RuntimeError, TypeError) as error:
        print(f"[Amatista] No se pudo abrir {d.objetivo}: {error}")
        return ""
    return f"Te abrí el menú «{d.nombre}» junto a tu ratón."


def _abrir_pestana(context, d):
    if d.objetivo == "ROLES":
        hecho = False
        for _ventana, area in _vistas(context):
            try:
                area.spaces.active.show_region_ui = True
                for region in area.regions:
                    if region.type == "UI" and hasattr(region, "active_panel_category"):
                        region.active_panel_category = "Amatista"
                hecho = True
            except (AttributeError, RuntimeError, TypeError):
                continue
        return "Te abrí la barra lateral en la pestaña Amatista: baja hasta «Roles»." if hecho else ""
    hecho = False
    for ventana in getattr(context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type != "PROPERTIES":
                continue
            try:
                area.spaces.active.context = d.objetivo
                hecho = True
            except (TypeError, AttributeError, RuntimeError):
                continue
    nombres = {"MATERIAL": "Material", "MODIFIER": "Modificadores", "RENDER": "Render"}
    return f"Te abrí la pestaña «{nombres.get(d.objetivo, d.objetivo)}» en Propiedades (abajo a la derecha)." if hecho else ""


def senalar(context, herramienta, paso=None):
    """Señala la herramienta del paso, si se puede de verdad. Devuelve la frase o ""."""
    d = donde.de(herramienta)
    if d is None:
        return ""
    if d.tipo == donde.BARRA:
        return _elegir(context, d)
    if d.tipo == donde.MENU:
        return _abrir_menu(context, d)
    if d.tipo == donde.PESTANA:
        return _abrir_pestana(context, d)
    return ""


def se_puede_abrir(herramienta):
    """El panel ofrece «Ábrelo por mí» para las ventanas (Guardar como, F12)."""
    d = donde.de(herramienta)
    return d is not None and d.tipo == donde.DIALOGO


def abrir_ventana(context, herramienta, nombre_sugerido=""):
    d = donde.de(herramienta)
    if d is None or d.tipo != donde.DIALOGO:
        return False
    try:
        if d.objetivo == "wm.save_as_mainfile":
            if nombre_sugerido:
                bpy.ops.wm.save_as_mainfile("INVOKE_DEFAULT", filepath=nombre_sugerido)
            else:
                bpy.ops.wm.save_as_mainfile("INVOKE_DEFAULT")
        elif d.objetivo == "render.render":
            bpy.ops.render.render("INVOKE_DEFAULT")
        else:
            return False
    except (RuntimeError, TypeError) as error:
        print(f"[Amatista] No se pudo abrir {d.objetivo}: {error}")
        return False
    return True


__all__ = ["abrir_ventana", "herramienta_elegida", "mostrar_barra", "se_puede_abrir", "senalar"]
