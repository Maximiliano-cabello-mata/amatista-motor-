"""Configuración del add-on: servidor, cuenta vinculada y preferencias.

config.json viaja dentro del paquete: lo escribe el servidor al construir la
descarga (dirección de la API y de la plataforma y, si el alumno descargó
con la sesión iniciada, un vínculo de un solo uso para conectarse solo).
Las preferencias del usuario (token, modo desarrollador...) se guardan en
las preferencias de Blender.
"""
import json
from pathlib import Path

import bpy

PAQUETE = __package__
VERSION_ADDON = "3.2.0"
CARPETA = Path(__file__).resolve().parent


def leer_config():
    try:
        return json.loads((CARPETA / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CONFIG = leer_config()


def prefs():
    """Preferencias del add-on (None si todavía no está registrado)."""
    addon = bpy.context.preferences.addons.get(PAQUETE)
    return addon.preferences if addon else None


def servidor():
    p = prefs()
    url = (p.servidor if p and p.servidor else CONFIG.get("servidor")) or "http://localhost:8000"
    return url.rstrip("/")


def plataforma():
    p = prefs()
    url = (p.plataforma if p and p.plataforma else CONFIG.get("plataforma")) or ""
    return url.rstrip("/")


def carpeta_usuario():
    """Carpeta escribible del add-on (prácticas descargadas, cola sin conexión)."""
    try:
        ruta = bpy.utils.extension_path_user(PAQUETE, path="", create=True)
    except (ValueError, AttributeError, TypeError):
        ruta = bpy.utils.user_resource("CONFIG", path="amatista", create=True)
    carpeta = Path(ruta)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def guardar_preferencias():
    """Blender guarda las preferencias solo si el usuario lo pide o al salir con
    autoguardado: el token recién recibido se guarda de inmediato."""
    try:
        if not bpy.app.background:
            bpy.ops.wm.save_userpref()
    except RuntimeError:
        pass


def es_desarrollador():
    p = prefs()
    return bool(p and (p.modo_desarrollador or p.rol in ("profesor", "admin")))


def _al_cambiar_hud(self, context):
    from .interfaz import hud

    hud.activar(self.mostrar_hud)


class PreferenciasAmatista(bpy.types.AddonPreferences):
    bl_idname = PAQUETE

    servidor: bpy.props.StringProperty(
        name="Servidor", description="Dirección de la API de Amatista (vacío = la del paquete descargado)"
    )
    plataforma: bpy.props.StringProperty(
        name="Plataforma", description="Dirección de la plataforma web (vacío = la del paquete descargado)"
    )
    token: bpy.props.StringProperty(name="Token", subtype="PASSWORD", options={"HIDDEN"})
    cuenta: bpy.props.StringProperty(name="Cuenta vinculada")
    cuenta_id: bpy.props.StringProperty()
    rol: bpy.props.StringProperty(default="")
    vinculo_usado: bpy.props.StringProperty(description="Vínculo del paquete ya canjeado")
    bienvenida_vista: bpy.props.BoolProperty(default=False)
    modo_desarrollador: bpy.props.BoolProperty(
        name="Modo desarrollador",
        description="Muestra Amatista Author: Tagger, Inspector, constructor de objetivos y publicación",
        default=False,
    )
    comprobar_solo: bpy.props.BoolProperty(
        name="Comprobar mientras trabajo",
        description="Reevalúa la práctica cada vez que cambias algo relevante en la escena",
        default=True,
    )
    sincronizar_solo: bpy.props.BoolProperty(
        name="Enviar mi progreso automáticamente",
        description="Cuando avanzas, Amatista guarda el resultado en tu cuenta",
        default=True,
    )
    mostrar_hud: bpy.props.BoolProperty(
        name="Tarjeta en la vista 3D",
        description="Muestra el progreso y el paso actual sobre la vista 3D",
        default=True,
        update=_al_cambiar_hud,
    )
    acompanamiento: bpy.props.EnumProperty(
        name="Acompañamiento",
        description="Cuánto te acompaña Amatista mientras practicas",
        items=[
            ("acompanado", "Acompañado", "Tarjeta guía, avisos, resaltados en 3D y diálogos que explican cada paso", "HEART", 0),
            ("tarjeta", "Solo tarjeta", "Tarjeta guía, avisos y resaltados, sin diálogos", "WINDOW", 1),
            ("silencioso", "Silencioso", "Solo los objetivos y las pistas que pidas (como la etapa 1)", "HIDE_ON", 2),
        ],
        default="acompanado",
    )
    resaltar_3d: bpy.props.BoolProperty(
        name="Mostrar en la vista 3D",
        description="Resalta los objetos del paso actual y dibuja reglas, planos y fantasmas de ayuda",
        default=True,
    )
    explicar_pasos: bpy.props.BoolProperty(
        name="Explicarme cada paso nuevo",
        description="Abre un diálogo con el porqué y las teclas al empezar cada paso",
        default=True,
    )
    ayuda_tras_intentos: bpy.props.IntProperty(
        name="Ofrecer ayuda tras", description="Cambios sin avanzar antes de preguntar «¿Te ayudo?»",
        default=4, min=2, max=20,
    )
    ayuda_tras_segundos: bpy.props.IntProperty(
        name="o tras (segundos)", description="Tiempo en el mismo paso antes de preguntar «¿Te ayudo?»",
        default=120, min=30, max=900,
    )
    avisar_herramientas: bpy.props.BoolProperty(
        name="Avisar herramientas de otro nivel",
        description="Muestra un aviso (no bloquea) si usas una herramienta de un nivel posterior",
        default=True,
    )

    def draw(self, context):
        from .interfaz import estilo

        layout = self.layout
        cabecera = layout.row()
        cabecera.label(text=f"Amatista Motor {VERSION_ADDON.rsplit('.', 1)[0]}", icon_value=estilo.icono("logo"))
        cabecera.label(text=f"Add-on {VERSION_ADDON}")

        caja = layout.box()
        caja.label(text="Cuenta", icon="USER")
        if self.token:
            fila = caja.row()
            fila.label(text=self.cuenta or "Cuenta vinculada", icon="CHECKMARK")
            if self.rol:
                fila.label(text=self.rol.capitalize())
            caja.operator("amatista.desvincular", icon="UNLINKED")
        else:
            caja.label(text="Sin vincular: tu progreso se queda solo en esta computadora.")
            caja.operator("amatista.vincular", icon="LINKED")

        caja = layout.box()
        caja.label(text="Acompañamiento", icon="HEART")
        caja.row().prop(self, "acompanamiento", expand=True)
        sub = caja.column()
        sub.active = self.acompanamiento != "silencioso"
        sub.prop(self, "resaltar_3d")
        sub.prop(self, "explicar_pasos")
        fila = sub.row(align=True)
        fila.prop(self, "ayuda_tras_intentos")
        fila.prop(self, "ayuda_tras_segundos")

        caja = layout.box()
        caja.label(text="Práctica", icon="PREFERENCES")
        caja.prop(self, "comprobar_solo")
        caja.prop(self, "sincronizar_solo")
        caja.prop(self, "mostrar_hud")
        caja.prop(self, "avisar_herramientas")

        caja = layout.box()
        caja.label(text="Avanzado", icon="TOOL_SETTINGS")
        caja.prop(self, "modo_desarrollador")
        caja.prop(self, "servidor")
        caja.prop(self, "plataforma")
        caja.label(text=f"Servidor en uso: {servidor()}", icon="WORLD")
