"""Blender Amatista: la plantilla de aplicación que hace de Blender y Amatista una sola cosa (motor 6).

El add-on Amatista la copia a ``scripts/startup/bl_app_templates_user/amatista``
(blender_amatista.py) y el acceso directo «Blender Amatista» abre Blender
con ``--app-template amatista``. También se elige en Archivo › Nuevo ›
Amatista. Es Blender sin recompilar: el mismo programa, con

- su pantalla de inicio (splash.png y splash_2x.png, junto a este archivo);
- los colores de Amatista en la vista 3D, la barra de arriba, la barra de
  herramientas y los menús (se guardan los de antes y se devuelven al salir
  de la plantilla; si Blender se cerró sin devolverlos, el add-on lo hace la
  próxima vez que se abra Blender sin la plantilla);
- «◆ Blender Amatista» y el botón «Mi lección» al principio de la barra de
  arriba, para volver a la plataforma desde cualquier lugar;
- el espacio de trabajo Amatista al empezar, con el taller a la vista.

Esta carpeta no se importa como parte del add-on: Blender la carga como
plantilla. Por eso no usa nada del add-on salvo sus operadores (amatista.*),
que existen solo si el add-on está encendido.
"""
import json
import os

import sys

import bpy
from bpy.app.handlers import persistent

NOMBRE = "amatista"
ARCHIVO_TEMA = "tema_original.json"

# Ruta en preferences.themes[0] → valor. Lo que no exista en esta versión de Blender se salta.
TEMA = {
    "view_3d.space.gradients.high_gradient": (0.16, 0.10, 0.22),
    "view_3d.space.gradients.gradient": (0.07, 0.05, 0.10),
    "view_3d.object_active": (0.80, 0.60, 1.0),
    "view_3d.object_selected": (0.61, 0.35, 0.71),
    "topbar.space.header": (0.13, 0.08, 0.18, 1.0),
    "user_interface.wcol_tool.inner_sel": (0.55, 0.33, 0.78, 1.0),
    "user_interface.wcol_toolbar_item.inner_sel": (0.55, 0.33, 0.78, 1.0),
    "user_interface.wcol_menu_item.inner_sel": (0.55, 0.33, 0.78, 1.0),
    "user_interface.wcol_tab.inner_sel": (0.30, 0.18, 0.40, 1.0),
    "user_interface.wcol_regular.inner_sel": (0.55, 0.33, 0.78, 1.0),
}


def _carpeta_config():
    return bpy.utils.user_resource("CONFIG", path="amatista", create=True)


def _resolver(ruta):
    objeto = bpy.context.preferences.themes[0]
    *partes, atributo = ruta.split(".")
    for parte in partes:
        objeto = getattr(objeto, parte)
    return objeto, atributo


def aplicar_tema():
    originales = {}
    for ruta, valor in TEMA.items():
        try:
            objeto, atributo = _resolver(ruta)
            antes = tuple(getattr(objeto, atributo))
            setattr(objeto, atributo, valor[: len(antes)])
            originales[ruta] = list(antes)
        except (AttributeError, TypeError, ValueError, IndexError):
            continue
    try:
        ruta_json = os.path.join(_carpeta_config(), ARCHIVO_TEMA)
        anterior = {}
        if os.path.isfile(ruta_json):
            with open(ruta_json, encoding="utf-8") as archivo:
                anterior = json.load(archivo)
        if not anterior.get("aplicado"):  # no pisar los originales con los de Amatista
            with open(ruta_json, "w", encoding="utf-8") as archivo:
                json.dump({"aplicado": True, "tema": originales}, archivo)
    except (OSError, ValueError) as error:
        print(f"[Blender Amatista] No se pudo guardar el tema original: {error}")


def restaurar_tema():
    try:
        ruta_json = os.path.join(_carpeta_config(), ARCHIVO_TEMA)
        with open(ruta_json, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, ValueError):
        return
    for ruta, valor in (datos.get("tema") or {}).items():
        try:
            objeto, atributo = _resolver(ruta)
            setattr(objeto, atributo, tuple(valor))
        except (AttributeError, TypeError, ValueError, IndexError):
            continue
    try:
        with open(ruta_json, "w", encoding="utf-8") as archivo:
            json.dump({"aplicado": False, "tema": datos.get("tema") or {}}, archivo)
    except OSError:
        pass


def _barra_superior(self, context):
    fila = self.layout.row(align=True)
    fila.label(text="◆ Blender Amatista")
    if hasattr(bpy.types, "AMATISTA_OT_taller_accion"):
        texto = "Mi lección"
        # Motor 6.1: el título de la lección en la que va el alumno en la plataforma. La plantilla no es parte
        # del paquete de Amatista (que es «amatista_blender» o «bl_ext.….amatista»): se busca su módulo.
        plataforma = next((m for n, m in list(sys.modules.items())
                           if n.endswith(".plataforma") and "amatista" in n and hasattr(m, "actual")), None)
        leccion = plataforma.actual() if plataforma is not None else None
        if leccion and leccion.get("titulo"):
            texto = f"Mi lección: {leccion['titulo'][:40]}"
        boton = fila.operator("amatista.taller_accion", text=texto, icon="URL")
        boton.accion = "abrir_plataforma"
    fila.separator()


def _encender_amatista():
    import addon_utils

    for mod in addon_utils.modules(refresh=False):
        nombre = getattr(mod, "__name__", "")
        if nombre.endswith(".amatista") or nombre == "amatista_blender":
            encendido, _cargado = addon_utils.check(nombre)
            if not encendido:
                try:
                    addon_utils.enable(nombre, default_set=True)
                except Exception as error:  # noqa: BLE001
                    print(f"[Blender Amatista] No se pudo encender Amatista: {error}")
            return True
    print("[Blender Amatista] Amatista no está instalado: instálalo desde la plataforma.")
    return False


@persistent
def _al_abrir(*_args):
    if bpy.data.filepath:
        return  # un archivo del alumno: se respeta como está
    if hasattr(bpy.types, "AMATISTA_OT_espacio"):
        bpy.app.timers.register(lambda: (bpy.ops.amatista.espacio(), None)[1], first_interval=0.5)


def register():
    aplicar_tema()
    bpy.types.TOPBAR_HT_upper_bar.prepend(_barra_superior)
    if _al_abrir not in bpy.app.handlers.load_factory_startup_post:
        bpy.app.handlers.load_factory_startup_post.append(_al_abrir)
    if _al_abrir not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_al_abrir)
    bpy.app.timers.register(lambda: (_encender_amatista(), None)[1], first_interval=0.1)


def unregister():
    try:
        bpy.types.TOPBAR_HT_upper_bar.remove(_barra_superior)
    except ValueError:
        pass
    for lista in (bpy.app.handlers.load_factory_startup_post, bpy.app.handlers.load_post):
        if _al_abrir in lista:
            lista.remove(_al_abrir)
    restaurar_tema()
