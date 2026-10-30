"""Blender Amatista (motor 6): Blender y Amatista se sienten como una sola cosa.

El creador pidió «meterse con el código de Blender» para que fuera «prácticamente
un Blender Amatista». Se eligió hacerlo **sin recompilar** (decisión del
30 de octubre de 2026): recompilar Blender obliga a firmar y publicar binarios
de 300 MB por sistema y a rehacerlos con cada versión de Blender; una
plantilla de aplicación cambia lo que el alumno ve con el mismo Blender
oficial, y llega con el mismo add-on que ya descarga.

Qué hace este módulo al encender el add-on (y en Preferencias › Amatista ›
«Blender Amatista»):

1. Copia la plantilla ``plantilla_amatista/`` (pantalla de inicio, colores,
   barra de arriba, espacio Amatista al empezar) a
   ``scripts/startup/bl_app_templates_user/amatista``. Se vuelve a copiar
   cuando cambia la versión del add-on.
2. Crea el acceso directo **Blender Amatista** en el menú del sistema
   (protocolo.crear_lanzador): abre Blender con ``--app-template amatista``.
   El enlace amatista:// de la plataforma también abre Blender Amatista.
3. Si Blender se abrió sin la plantilla y los colores de Amatista quedaron
   puestos (Blender se cerró sin devolverlos), los devuelve: Blender normal
   se ve como Blender normal.
"""
import json
import os
import shutil
from pathlib import Path

import bpy

from . import ajustes, protocolo

CARPETA = Path(__file__).resolve().parent / "plantilla_amatista"
ARCHIVOS = ("__init__.py", "splash.png", "splash_2x.png")
ESTADO = {"plantilla": "", "lanzador": ""}


def destino():
    base = bpy.utils.user_resource("SCRIPTS", path=os.path.join("startup", "bl_app_templates_user"), create=True)
    return Path(base) / protocolo.PLANTILLA


def instalada():
    d = destino()
    return all((d / nombre).is_file() for nombre in ARCHIVOS)


def instalar_plantilla(forzar=False):
    """Copia la plantilla «Blender Amatista». Devuelve (ok, texto)."""
    p = ajustes.prefs()
    if not forzar and p is not None and p.plantilla_version == ajustes.VERSION_ADDON and instalada():
        return True, "Blender Amatista ya está instalado."
    try:
        d = destino()
        d.mkdir(parents=True, exist_ok=True)
        for nombre in ARCHIVOS:
            shutil.copyfile(CARPETA / nombre, d / nombre)
        if p is not None:
            p.plantilla_version = ajustes.VERSION_ADDON
        texto = f"Blender Amatista instalado en {d}"
    except Exception as error:  # noqa: BLE001 - la plantilla es un extra: nunca rompe el add-on
        texto = f"No se pudo instalar Blender Amatista ({error})."
        ESTADO["plantilla"] = texto
        return False, texto
    ESTADO["plantilla"] = texto
    return True, texto


def crear_lanzador():
    icono = Path(__file__).resolve().parent / "iconos" / "logo.png"
    ok, texto = protocolo.crear_lanzador(bpy.app.binary_path, str(icono) if icono.is_file() else "")
    ESTADO["lanzador"] = texto
    return ok, texto


def en_plantilla():
    return getattr(bpy.context.preferences, "app_template", "") == protocolo.PLANTILLA


def devolver_tema():
    """Fuera de la plantilla, si los colores de Amatista quedaron puestos, vuelven los de antes."""
    if en_plantilla():
        return False
    try:
        ruta = Path(bpy.utils.user_resource("CONFIG", path="amatista")) / "tema_original.json"
        if not ruta.is_file():
            return False
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not datos.get("aplicado"):
        return False
    tema = bpy.context.preferences.themes[0]
    for camino, valor in (datos.get("tema") or {}).items():
        try:
            objeto = tema
            *partes, atributo = camino.split(".")
            for parte in partes:
                objeto = getattr(objeto, parte)
            setattr(objeto, atributo, tuple(valor))
        except (AttributeError, TypeError, ValueError, IndexError):
            continue
    datos["aplicado"] = False
    try:
        ruta.write_text(json.dumps(datos), encoding="utf-8")
    except OSError:
        pass
    print("[Amatista] Devolví los colores de Blender (quedaron puestos los de Blender Amatista).")
    return True


class AMATISTA_OT_blender_amatista(bpy.types.Operator):
    """Instala Blender Amatista (pantalla de inicio, colores y barra de Amatista) y su acceso directo"""

    bl_idname = "amatista.blender_amatista"
    bl_label = "Instalar Blender Amatista"

    def execute(self, context):
        ok, texto = instalar_plantilla(forzar=True)
        if not ok:
            self.report({"WARNING"}, texto)
            return {"CANCELLED"}
        ok_l, texto_l = crear_lanzador()
        ajustes.guardar_preferencias()
        self.report({"INFO"}, "Listo: abre «Blender Amatista» desde el menú de tu sistema (o Archivo › Nuevo › Amatista)."
                    if ok_l else texto_l)
        return {"FINISHED"}


CLASES = (AMATISTA_OT_blender_amatista,)


def _al_arrancar():
    try:
        devolver_tema()
        p = ajustes.prefs()
        if p is not None and p.blender_amatista:
            antes = p.plantilla_version
            ok, _texto = instalar_plantilla()
            if ok and antes != ajustes.VERSION_ADDON and not bpy.app.background:
                crear_lanzador()
                ajustes.guardar_preferencias()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Blender Amatista: {error}")
    return None


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)
    if bpy.app.background:
        _al_arrancar()  # el instalador corre sin ventana: la plantilla queda lista para el primer arranque
    else:
        bpy.app.timers.register(_al_arrancar, first_interval=3.0)


def unregister():
    if bpy.app.timers.is_registered(_al_arrancar):
        bpy.app.timers.unregister(_al_arrancar)
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)


__all__ = ["crear_lanzador", "devolver_tema", "en_plantilla", "instalar_plantilla", "instalada"]
