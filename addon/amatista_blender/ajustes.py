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
VERSION_ADDON = "7.1.0"
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


def sin_progreso():
    """Motor 7: un administrador no lleva progreso. Practica cuantas veces quiera; nada se guarda en este equipo
    ni se envía, y cada vez que Blender arranca todo empieza de cero (pedido del creador, 31 de octubre de 2026)."""
    p = prefs()
    return bool(p and getattr(p, "token", "") and getattr(p, "rol", "") == "admin")


def _al_cambiar_hud(self, context):
    from .interfaz import hud

    hud.activar(self.mostrar_hud)


def _al_cambiar_enfoque(self, context):
    from . import enfoque, enlace, practicas

    practica = practicas.practica_activa(context)
    if practica is not None:
        enfoque.ESTADO["rechazado"] = ""
        enfoque.al_abrir_practica(practica, nueva=False)
    elif self.enfoque == "nunca":
        enfoque.desactivar()
    enlace.latir_pronto()


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
    # Add-on 5.4 (integracion.py): el espacio de trabajo «Amatista» y el enlace amatista:// registrado.
    espacio_amatista: bpy.props.BoolProperty(
        name="Espacio de trabajo Amatista",
        description="Al abrir una práctica, Blender pasa a la pestaña Amatista (junto a Layout) con tu taller a la vista",
        default=True,
    )
    # Motor 6: la tarjeta como referencia (compacta mientras trabajas), las herramientas que brillan y
    # Blender Amatista (plantilla de aplicación, blender_amatista.py).
    tarjeta_compacta: bpy.props.BoolProperty(
        name="Tarjeta compacta mientras trabajo",
        description="Mientras trabajas, la tarjeta se achica a una línea; se abre al pasar el ratón o cuando hay algo nuevo",
        default=True,
    )
    # Motor 7: el guion paso a paso (guion/): avanza por el resultado y señala de verdad.
    guion_paso_a_paso: bpy.props.BoolProperty(
        name="Guía paso a paso (motor 7)",
        description="Un paso a la vez, arriba de la vista 3D y en N › Amatista. Avanza en cuanto tu escena lo "
                    "cumple; las pistas dicen dónde está de verdad cada herramienta",
        default=True,
    )
    brillo_herramientas: bpy.props.BoolProperty(
        name="Hacer brillar la herramienta que necesito",
        description="Guía del motor 6 (con la guía paso a paso apagada): si te atascas, se marca dónde está la "
                    "herramienta de la actividad",
        default=True,
    )
    # Motor 6.1: la ayuda que enseña (fichas.py).
    presentar_herramientas: bpy.props.BoolProperty(
        name="Presentarme cada herramienta nueva",
        description="Antes de una actividad con una herramienta que nunca usaste, su ficha: para qué sirve, dónde está (brilla) y cómo se usa",
        default=True,
    )
    modo_curioso: bpy.props.EnumProperty(
        name="Modo curioso",
        description="Cuando tocas una herramienta que todavía no conoces, Amatista te dice qué es",
        items=(
            ("auto", "Mientras aprendo", "Solo en tus primeros pasos (se apaga cuando ya te salen solas 10 habilidades)"),
            ("siempre", "Siempre", "Explica cada herramienta nueva que toques, las primeras dos veces"),
            ("nunca", "Nunca", "Sin explicaciones al tocar herramientas"),
        ),
        default="auto",
    )
    blender_amatista: bpy.props.BoolProperty(
        name="Blender Amatista",
        description="Instala la plantilla «Blender Amatista» (colores, pantalla de inicio y barra de arriba de Amatista) y un acceso directo",
        default=True,
    )
    plantilla_version: bpy.props.StringProperty(default="", options={"HIDDEN"})
    protocolo_version: bpy.props.IntProperty(default=0, options={"HIDDEN"})
    protocolo_blender: bpy.props.StringProperty(default="", options={"HIDDEN"})
    # Add-on 5.1: los primeros pasos (recorrido.py) ya se hicieron o se omitieron. Desde el 5.2 cuenta como
    # la primera práctica de «Conoce Amatista Motor»; recorridos_hechos guarda las tres («pestana,vista,taller»).
    recorrido_hecho: bpy.props.BoolProperty(default=False)
    recorridos_hechos: bpy.props.StringProperty(default="")
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
        description="Muestra la tarjeta de la actividad (y el molde) sobre la vista 3D",
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
    # Motor 4: nombre nuevo para que el «sí» guardado de antes (un diálogo por paso) no siga activo.
    dialogo_por_mision: bpy.props.BoolProperty(
        name="Un diálogo por cada misión",
        description="Además de la tarjeta, abre un diálogo con el porqué y las teclas al empezar cada misión",
        default=False,
    )
    animaciones: bpy.props.BoolProperty(
        name="Animaciones",
        description="La tarjeta entra deslizándose, el molde late en la pieza que toca y se celebra lo logrado",
        default=True,
    )
    preparar_herramienta: bpy.props.BoolProperty(
        name="Dejarme lista la herramienta",
        description="En los niveles 1 y 2, al empezar una misión elige su herramienta en la barra T (Mover, Escalar…)",
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
    enfoque: bpy.props.EnumProperty(
        name="Modo enfocado",
        description="Esconde lo que la práctica no usa y deja a mano solo sus herramientas",
        items=[
            ("auto", "Según el nivel", "Enfocado en los niveles 1 y 2; Blender completo después", "AUTO", 0),
            ("siempre", "Siempre", "Siempre solo las herramientas de la práctica", "HIDE_ON", 1),
            ("nunca", "Nunca", "Blender completo, como siempre", "HIDE_OFF", 2),
        ],
        default="auto",
        update=_al_cambiar_enfoque,
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
        caja.label(text="Amatista dentro de Blender", icon="WORKSPACE")
        caja.prop(self, "espacio_amatista")
        caja.prop(self, "blender_amatista")
        fila = caja.row(align=True)
        fila.operator("amatista.reparar_enlace", icon="URL")
        fila.operator("amatista.blender_amatista", icon="BLENDER")
        nota = caja.row()
        nota.active = False
        nota.label(text="Hace que «Abrir en Blender» de la plataforma abra este Blender aunque esté cerrado.")

        caja = layout.box()
        caja.label(text="En la vista 3D", icon="HEART")
        caja.prop(self, "guion_paso_a_paso")
        caja.prop(self, "mostrar_hud")
        caja.prop(self, "tarjeta_compacta")
        caja.prop(self, "brillo_herramientas")
        caja.prop(self, "presentar_herramientas")
        caja.row().prop(self, "modo_curioso", expand=True)
        caja.prop(self, "animaciones")
        caja.prop(self, "sincronizar_solo")

        caja = layout.box()
        caja.label(text="Modo enfocado", icon="HIDE_ON")
        caja.row().prop(self, "enfoque", expand=True)
        nota = caja.row()
        nota.active = False
        nota.label(text="También lo puedes elegir en la plataforma, en «Mi Blender».")

        if self.modo_desarrollador:
            # Add-on 5: el taller decide la ayuda (escalera con freno); esto queda para las prácticas sueltas.
            caja = layout.box()
            caja.label(text="Prácticas sueltas (desarrollo)", icon="PREFERENCES")
            caja.row().prop(self, "acompanamiento", expand=True)
            sub = caja.column()
            sub.active = self.acompanamiento != "silencioso"
            sub.prop(self, "resaltar_3d")
            sub.prop(self, "dialogo_por_mision")
            sub.prop(self, "preparar_herramienta")
            fila = sub.row(align=True)
            fila.prop(self, "ayuda_tras_intentos")
            fila.prop(self, "ayuda_tras_segundos")
            caja.prop(self, "comprobar_solo")
            caja.prop(self, "avisar_herramientas")

        from . import saneamiento

        copias = saneamiento.resumen()
        if copias["apagadas"] or copias["encendidas"]:
            caja = layout.box()
            caja.label(text="Otras copias de Amatista", icon="ERROR" if copias["encendidas"] else "CHECKMARK")
            for nombre in copias["apagadas"]:
                caja.label(text=f"Apagada para que no se cruce: {nombre}")
            for nombre in copias["encendidas"]:
                caja.label(text=f"Sigue encendida (es más nueva): {nombre}")

        caja = layout.box()
        caja.label(text="Avanzado", icon="TOOL_SETTINGS")
        caja.prop(self, "modo_desarrollador")
        caja.prop(self, "servidor")
        caja.prop(self, "plataforma")
        caja.label(text=f"Servidor en uso: {servidor()}", icon="WORLD")
