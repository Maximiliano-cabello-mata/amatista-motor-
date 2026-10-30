"""Amatista dentro de Blender (add-on 5.4): que no se sienta como un panel escondido.

Al probar la plataforma, el creador encontró que el add-on «no es nada
intuitivo»: todo vivía en la barra lateral (tecla N), que un principiante no
sabe abrir, y «Abrir en Blender» no abría Blender. Ahora Amatista aparece en
los lugares de Blender que el alumno ya ve:

- **Menú Amatista** en la barra de arriba, junto a Archivo · Editar · Ayuda:
  seguir, pista, Mi isla, la plataforma, la cuenta y la ayuda.
- **Botón Amatista** en la cabecera de la vista 3D, con lo que toca ahora
  («Hazlo conmigo · 2 de 5»). Al pulsarlo se despliega el taller entero, sin
  buscar la tecla N.
- **Barra de estado** (abajo): la actividad de ahora y su tecla, como Blender
  muestra los atajos de la herramienta.
- **Espacio de trabajo «Amatista»**: una pestaña junto a Layout, Modeling…
  Al abrir una práctica o un taller, Blender pasa a ella con la barra lateral
  ya abierta en Amatista. Se apaga en Preferencias › Amatista.
- **Enlace amatista://** (protocolo.py): al arrancar, el add-on lo registra
  para este Blender y cumple la orden que trajo el enlace (Blender cerrado →
  la plataforma lo abre directo en la actividad).
"""
import hashlib

import bpy

from . import ajustes, protocolo
from .interfaz import estilo

ESPACIO = "Amatista"
ESPERA_ORDEN = 2.0  # segundos antes de cumplir la orden del enlace (la ventana tiene que existir)
INTENTOS_ORDEN = 15
ESTADO = {"orden_inicio": None, "intentos": 0, "protocolo": ""}


def _sesion():
    from .taller import sesion

    return sesion


def actividad_corta():
    """(título, detalle) de lo que toca ahora, para la cabecera y la barra de estado. None sin actividad."""
    try:
        sesion = _sesion()
        a = sesion.actividad()
    except Exception:  # noqa: BLE001 - antes de cargar el catálogo no hay actividad
        return None
    if a is None:
        return None
    numero = f" · {a.numero} de {a.de}" if a.de > 1 else ""
    estado = sesion.estado()
    if estado == sesion.PAUSA:
        return a.titulo, "En pausa"
    if sesion.SESION.get("volver"):
        return a.titulo, "Listo: sigue en la plataforma"
    if estado == sesion.LOGRADA:
        return a.titulo, "¡Lograda! Sigue con la próxima"
    return a.titulo, f"{a.nombre_tipo}{numero}"


# --- Espacio de trabajo «Amatista» --------------------------------------------------------------


def _ventana(context):
    ventana = getattr(context, "window", None)
    if ventana is not None:
        return ventana
    ventanas = getattr(context.window_manager, "windows", ())
    return ventanas[0] if ventanas else None


def abrir_barra_lateral(screen):
    """Abre la barra lateral de cada vista 3D de la pantalla en la pestaña Amatista."""
    for area in getattr(screen, "areas", ()):
        if area.type != "VIEW_3D":
            continue
        area.spaces.active.show_region_ui = True
        for region in area.regions:
            if region.type == "UI":
                try:
                    region.active_panel_category = "Amatista"
                except (AttributeError, TypeError, ValueError):
                    pass  # Blender 4.2 todavía no deja elegir la pestaña desde Python


def entrar_al_espacio(context=None):
    """Pasa la ventana al espacio «Amatista» (lo crea a partir de Layout la primera vez). Devuelve si pudo."""
    context = context or bpy.context
    p = ajustes.prefs()
    if bpy.app.background or (p is not None and not p.espacio_amatista):
        return False
    ventana = _ventana(context)
    if ventana is None:
        return False
    try:
        espacio = bpy.data.workspaces.get(ESPACIO)
        if espacio is None:
            base = bpy.data.workspaces.get("Layout") or ventana.workspace
            antes = set(bpy.data.workspaces)
            with context.temp_override(window=ventana, workspace=base):
                bpy.ops.workspace.duplicate()
            nuevos = [w for w in bpy.data.workspaces if w not in antes]
            if not nuevos:
                return False
            espacio = nuevos[0]
            espacio.name = ESPACIO
        if ventana.workspace != espacio:
            ventana.workspace = espacio  # Blender lo cambia en el próximo ciclo: ventana.screen sigue siendo el de antes
        for screen in getattr(espacio, "screens", ()) or (ventana.screen,):
            abrir_barra_lateral(screen)
        return True
    except Exception as error:  # noqa: BLE001 - el espacio es una comodidad: nunca rompe la práctica
        print(f"[Amatista] No se pudo abrir el espacio Amatista: {error}")
        return False


class AMATISTA_OT_espacio(bpy.types.Operator):
    """Pasa al espacio de trabajo Amatista: la vista 3D con tu taller a la derecha"""

    bl_idname = "amatista.espacio"
    bl_label = "Ir al espacio Amatista"

    def execute(self, context):
        p = ajustes.prefs()
        if p is not None and not p.espacio_amatista:
            p.espacio_amatista = True
        if not entrar_al_espacio(context):
            abrir_barra_lateral(context.screen)
        return {"FINISHED"}


class AMATISTA_OT_mostrar_panel(bpy.types.Operator):
    """Abre la barra lateral de la vista 3D en la pestaña Amatista (es la tecla N)"""

    bl_idname = "amatista.mostrar_panel"
    bl_label = "Mostrar el panel Amatista"

    def execute(self, context):
        abrir_barra_lateral(context.screen)
        return {"FINISHED"}


# --- El enlace amatista:// --------------------------------------------------------------------


def registrar_protocolo(forzar=False):
    """Registra amatista:// para este Blender una vez por versión del registro (o al pedirlo)."""
    p = ajustes.prefs()
    if bpy.app.background or p is None:
        return None
    if not forzar and p.protocolo_version >= protocolo.VERSION and p.protocolo_blender == bpy.app.binary_path:
        return None
    ok, texto = protocolo.registrar(bpy.app.binary_path)
    ESTADO["protocolo"] = texto
    print(f"[Amatista] {texto}")
    if ok:
        p.protocolo_version = protocolo.VERSION
        p.protocolo_blender = bpy.app.binary_path
        ajustes.guardar_preferencias()
    return ok


class AMATISTA_OT_reparar_enlace(bpy.types.Operator):
    """Vuelve a registrar el enlace amatista:// para que «Abrir en Blender» de la plataforma abra este Blender"""

    bl_idname = "amatista.reparar_enlace"
    bl_label = "Reparar «Abrir en Blender»"

    def execute(self, context):
        ok = registrar_protocolo(forzar=True)
        if ok:
            self.report({"INFO"}, "Listo: «Abrir en Blender» de la plataforma abrirá este Blender.")
        else:
            self.report({"WARNING"}, ESTADO["protocolo"] or "No se pudo registrar el enlace.")
        return {"FINISHED"}


def orden_de_inicio(argv=None):
    """La orden que trajo Blender al abrirse desde la plataforma (o None)."""
    orden = protocolo.orden_de_url(protocolo.url_de_argumentos(argv))
    if orden is None:
        return None
    huella = hashlib.sha1(repr(sorted(orden["datos"].items())).encode()).hexdigest()[:8]
    return {"id": f"inicio-{orden['tipo']}-{huella}", **orden}


def _cumplir_orden_de_inicio():
    orden = ESTADO["orden_inicio"]
    if orden is None:
        return None
    if not bpy.context.window_manager.windows:
        ESTADO["intentos"] += 1
        return ESPERA_ORDEN if ESTADO["intentos"] < INTENTOS_ORDEN else None
    ESTADO["orden_inicio"] = None
    from . import enlace, practicas

    try:
        if orden["tipo"] == "abrir":
            entrar_al_espacio(bpy.context) or practicas.mostrar_en_amatista(bpy.context)
        else:
            enlace.cumplir(orden)
            entrar_al_espacio(bpy.context)
    except Exception as error:  # noqa: BLE001 - una orden fallida nunca rompe Blender
        print(f"[Amatista] Blender se abrió desde la plataforma, pero la actividad no: {error}")
    return None


# --- Menú Amatista, botón de la vista 3D y barra de estado ---------------------------------------


class AMATISTA_MT_principal(bpy.types.Menu):
    bl_idname = "AMATISTA_MT_principal"
    bl_label = "Amatista"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        sesion = _sesion()
        a = sesion.actividad()
        if a is None and sesion.manda_la_plataforma():
            # Motor 6: la lección de la plataforma marca qué sigue; desde aquí se vuelve a ella.
            layout.operator("amatista.taller_accion", text="Seguir mi lección en la plataforma",
                            icon="URL").accion = "volver_plataforma"
        elif a is None:
            layout.operator("amatista.taller_abrir", text="Empezar o seguir mi taller", icon="PLAY")
        elif sesion.SESION["volver"]:
            layout.operator("amatista.taller_accion", text="Volver a la plataforma", icon="URL").accion = "volver_plataforma"
        elif sesion.estado() == sesion.PAUSA:
            layout.operator("amatista.taller_accion", text="Seguir la actividad", icon="PLAY").accion = "seguir"
        elif sesion.estado() == sesion.LOGRADA:
            layout.operator("amatista.taller_accion", text="Siguiente actividad", icon="FORWARD").accion = "siguiente"
        else:
            layout.operator("amatista.taller_accion", text="Dame una pista", icon="QUESTION").accion = "pista"
            layout.operator("amatista.taller_accion", text="Mírame hacerlo", icon="HIDE_OFF").accion = "mirame"
            layout.operator("amatista.taller_accion", text="Pausa", icon="PAUSE").accion = "pausa"
        layout.operator("amatista.taller_accion", text="Mi isla", icon="WORLD").accion = "isla"
        layout.separator()
        layout.operator("amatista.espacio", text="Ir al espacio Amatista", icon="WORKSPACE")
        layout.operator("amatista.mostrar_panel", text="Mostrar el panel (N)", icon="MENU_PANEL")
        layout.operator("amatista.abrir_plataforma", text="Abrir la plataforma", icon="URL")
        layout.separator()
        p = ajustes.prefs()
        if p and p.token:
            layout.label(text=p.cuenta or "Cuenta conectada", icon="USER")
        else:
            layout.operator("amatista.vincular", text="Conectar mi cuenta", icon="LINKED")
        layout.operator("amatista.bienvenida", text="¿Cómo funciona Amatista?", icon="HELP")
        layout.operator("amatista.reparar_enlace", icon="TOOL_SETTINGS")


def _menu_superior(self, context):
    self.layout.menu("AMATISTA_MT_principal", text="Amatista")


class AMATISTA_PT_rapido(bpy.types.Panel):
    """El taller desplegado desde el botón Amatista de la cabecera (sin buscar la tecla N)."""

    bl_idname = "AMATISTA_PT_rapido"
    bl_label = "Amatista"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_ui_units_x = 17

    def draw(self, context):
        from .taller import panel

        layout = self.layout
        p = ajustes.prefs()
        if not (p and p.token):
            cuerpo = estilo.tarjeta(layout, "Conecta tu cuenta", icon="LINKED")
            estilo.parrafo(cuerpo, context, "Así tu avance aparece en la plataforma y en tu panel.")
            estilo.boton_principal(cuerpo, "amatista.vincular", "Conectar mi cuenta", icon="LINKED", escala=1.4)
        if panel.AMATISTA_PT_taller.poll(context):
            panel.AMATISTA_PT_taller.draw(self, context)
        fila = layout.row(align=True)
        fila.scale_y = 1.2
        fila.operator("amatista.mostrar_panel", text="Ver todo el panel", icon="MENU_PANEL")
        fila.operator("amatista.bienvenida", text="Ayuda", icon="HELP")


def _boton_cabecera(self, context):
    if ajustes.prefs() is None:
        return
    corta = actividad_corta()
    texto = f"Amatista · {corta[1]}" if corta else "Amatista"
    fila = self.layout.row(align=True)
    fila.popover(panel="AMATISTA_PT_rapido", text=texto, icon_value=estilo.icono("logo"))


def _barra_estado(self, context):
    corta = actividad_corta()
    if corta is None:
        return
    fila = self.layout.row(align=True)
    fila.label(text=f"Amatista: {corta[0]} · {corta[1]}", icon_value=estilo.icono("logo"))


CLASES = (AMATISTA_MT_principal, AMATISTA_PT_rapido, AMATISTA_OT_espacio, AMATISTA_OT_mostrar_panel,
          AMATISTA_OT_reparar_enlace)
AGREGADOS = (("TOPBAR_MT_editor_menus", _menu_superior), ("VIEW3D_HT_header", _boton_cabecera),
             ("STATUSBAR_HT_header", _barra_estado))


def _al_arrancar():
    try:
        registrar_protocolo()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Enlace amatista://: {error}")
    return None


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)
    for nombre, funcion in AGREGADOS:
        tipo = getattr(bpy.types, nombre, None)
        if tipo is not None:
            tipo.append(funcion)
    ESTADO["orden_inicio"] = orden_de_inicio()
    ESTADO["intentos"] = 0
    if not bpy.app.background:
        bpy.app.timers.register(_al_arrancar, first_interval=4.0)
        if ESTADO["orden_inicio"] is not None:
            bpy.app.timers.register(_cumplir_orden_de_inicio, first_interval=ESPERA_ORDEN)


def unregister():
    for temporizador in (_al_arrancar, _cumplir_orden_de_inicio):
        if bpy.app.timers.is_registered(temporizador):
            bpy.app.timers.unregister(temporizador)
    for nombre, funcion in AGREGADOS:
        tipo = getattr(bpy.types, nombre, None)
        if tipo is not None:
            try:
                tipo.remove(funcion)
            except ValueError:
                pass
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
