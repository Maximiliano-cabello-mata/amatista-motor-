"""El panel lateral del alumno (N › Amatista): lo mínimo, porque la instrucción vive en la vista 3D.

    Amatista ─ tu cuenta
    ┌ La interfaz y navegación 3D ─ 3 de 6 habilidades listas ┐
    │ Hazlo conmigo · Estirar en un solo eje (2 de 3)          │
    │ [        Continuar        ]                              │
    │ [ Pausa ] [ Pista ]                                      │
    │ Recuérdalo: 1 repaso de un minuto                        │
    │ [ Mi isla ] [ Abrir la plataforma ]                      │
    └──────────────────────────────────────────────────────────┘
    ▸ ¿Ya sabes esto? Demuéstralo     (cerrado)
    ▸ Otros módulos                   (cerrado)

Los cursos, la teoría y el progreso detallado están en la plataforma, que
maneja este Blender por el enlace en vivo.
"""
import bpy

from .. import _motor, ajustes
from ..interfaz import estilo
from . import datos, sesion

taller = _motor.taller
FASE = {"nueva": "Nueva", "acompanada": "Con ayuda", "sola": "Ya te sale", "dominada": "Dominada"}
ICONO_FASE = {"nueva": "RADIOBUT_OFF", "acompanada": "RADIOBUT_ON", "sola": "CHECKMARK", "dominada": "SOLO_ON"}


def _alumno(context):
    wm = context.window_manager.amatista
    return (wm.modo == "alumno" or not ajustes.es_desarrollador()) and not wm.vista_previa


def _taller_actual():
    return sesion.SESION["taller"] or datos.taller_inicial()


class _Base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Amatista"


class AMATISTA_PT_taller(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_taller"
    bl_label = "Taller"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return _alumno(context)

    def draw(self, context):
        layout = self.layout
        c = datos.catalogo()
        if c is None:
            cuerpo = estilo.tarjeta(layout, "El taller no está disponible", icon="ERROR")
            estilo.parrafo(cuerpo, context, datos.ESTADO["catalogo_error"] or "Vuelve a descargar Amatista Motor.")
            return
        tid = _taller_actual()
        t = c.taller(tid)
        plan = datos.plan(tid) if t is not None else None
        a = sesion.actividad()
        titulo = t.titulo if t is not None else "Taller"
        cuerpo = estilo.tarjeta(layout, titulo, icono_propio="logo")
        if plan is not None:
            fila = cuerpo.row()
            fila.active = False
            fila.label(text=f"{plan.listas} de {len(plan.habilidades)} habilidades listas"
                       + (" · proyecto abierto" if plan.proyecto_abierto and not plan.proyecto_hecho else ""))
        if a is not None:
            numero = f" ({a.numero} de {a.de})" if a.de > 1 else ""
            cuerpo.label(text=f"{a.nombre_tipo} · {a.titulo}{numero}", icon="PLAY" if sesion.estado() != sesion.PAUSA else "PAUSE")
            pieza = sesion.pieza_actual()
            if pieza is not None and pieza.mensaje and sesion.estado() == sesion.TRABAJANDO:
                estilo.parrafo(cuerpo, context, pieza.mensaje, margen=4)
        principal = cuerpo.row()
        principal.scale_y = 1.6
        if a is None and sesion.manda_la_plataforma():
            # Motor 6: la ruta la marca la plataforma; Blender abre lo que mande la lección.
            principal.operator("amatista.taller_accion", text="Seguir en la plataforma", icon="URL").accion = "volver_plataforma"
        elif a is None:
            principal.operator("amatista.taller_abrir", text="Empezar el taller", icon="PLAY").taller = tid
        elif sesion.SESION["volver"]:
            principal.operator("amatista.taller_accion", text="Volver a la plataforma", icon="URL").accion = "volver_plataforma"
        elif not sesion.cubre(context.scene):
            principal.operator("amatista.taller_accion", text="Volver a la actividad", icon="LOOP_BACK").accion = "continuar"
        elif sesion.estado() == sesion.PAUSA:
            principal.operator("amatista.taller_accion", text="Seguir", icon="PLAY").accion = "seguir"
        elif sesion.estado() == sesion.LOGRADA:
            principal.operator("amatista.taller_accion", text="Siguiente", icon="FORWARD").accion = "siguiente"
        else:
            principal.operator("amatista.taller_accion", text="Pausa", icon="PAUSE").accion = "pausa"
        if a is not None and sesion.estado() == sesion.TRABAJANDO and sesion.cubre(context.scene):
            nombre, puede = sesion.siguiente_pista()
            fila = cuerpo.row(align=True)
            if nombre:
                sub = fila.row(align=True)
                sub.enabled = puede
                sub.operator("amatista.taller_accion", text=f"¿{nombre}?" if nombre != "Mírame" else nombre,
                             icon="QUESTION").accion = "pista"
            if not sesion.SESION["proyecto"]:
                fila.operator("amatista.taller_accion", text="Saltar", icon="FF").accion = "saltar"

        pendientes = datos.repasos_pendientes()
        if pendientes:
            t_rep, h_rep = pendientes[0]
            h = c.habilidad(h_rep)
            op = cuerpo.operator("amatista.taller_abrir", text=f"Recuérdalo: {h.titulo if h else h_rep} (1 min)",
                                 icon="RECOVER_LAST")
            op.taller, op.habilidad, op.repasar = t_rep, h_rep, True

        fila = cuerpo.row(align=True)
        fila.operator("amatista.taller_accion", text="Mi isla", icon="WORLD").accion = "isla"
        fila.operator("amatista.abrir_plataforma", text="Abrir la plataforma", icon="URL")

        estado_red = datos.ESTADO["mensaje"]
        pendientes_envio = len(datos.avance()["cola"])
        p = ajustes.prefs()
        nota = cuerpo.row()
        nota.active = False
        if not (p and p.token):
            nota.label(text="Tu avance se guarda aquí; vincula tu cuenta para verlo en la plataforma.", icon="INFO")
        elif estado_red:
            nota.label(text=estado_red[:90], icon="INFO")
        elif pendientes_envio:
            nota.label(text="Enviando tu avance…", icon="TIME")


class AMATISTA_PT_taller_habilidades(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_taller_habilidades"
    bl_label = "¿Ya sabes esto? Demuéstralo"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Motor 6: con la cuenta conectada, «Demuéstralo» vive en la lección de la plataforma.
        return _alumno(context) and datos.catalogo() is not None and not sesion.manda_la_plataforma()

    def draw(self, context):
        layout = self.layout
        tid = _taller_actual()
        plan = datos.plan(tid)
        if plan is None:
            return
        estilo.parrafo(layout, context, "Si ya sabes hacerlo, demuéstralo dos veces sin ayuda y te saltas su guía.",
                       margen=4)
        for h in plan.habilidades:
            fila = layout.row(align=True)
            fila.label(text=f"{h.titulo} · {FASE.get(h.fase, '')}", icon=ICONO_FASE.get(h.fase, "DOT"))
            if h.fase != taller.DOMINADA:
                op = fila.operator("amatista.taller_abrir", text="Demuéstralo")
                op.taller, op.habilidad, op.probar = tid, h.id, True


class AMATISTA_PT_taller_modulos(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_taller_modulos"
    bl_label = "Otros módulos"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Motor 6: los módulos se eligen en la plataforma, no en Blender (sin cuenta, Blender sigue solo).
        return _alumno(context) and datos.catalogo() is not None and not sesion.manda_la_plataforma()

    def draw(self, context):
        layout = self.layout
        c = datos.catalogo()
        actual = _taller_actual()
        for t in c.talleres:
            plan = datos.plan(t.id)
            completo = plan is not None and plan.completo
            fila = layout.row(align=True)
            icono = "CHECKMARK" if completo else ("PLAY" if t.id == actual else "DOT")
            fila.label(text=f"{t.titulo}", icon=icono)
            op = fila.operator("amatista.taller_abrir", text="Abrir")
            op.taller = t.id


CLASES = (AMATISTA_PT_taller, AMATISTA_PT_taller_habilidades, AMATISTA_PT_taller_modulos)
