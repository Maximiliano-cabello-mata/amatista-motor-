"""Diálogos de Amatista: pista, felicitación, aviso de herramienta y bienvenida.

Son ventanas emergentes pequeñas con el mismo estilo que los paneles
(tarjeta con ícono propio, texto partido y botones grandes). Nunca bloquean
Blender: se cierran al mover el ratón fuera o con Esc.
"""
import bpy

from .. import _motor, ajustes, practicas
from . import estilo

ANCHO = 380


def _popup(operador, context, ancho=ANCHO):
    if bpy.app.background:
        return operador.execute(context)
    return context.window_manager.invoke_popup(operador, width=ancho)


class AMATISTA_OT_pista(bpy.types.Operator):
    bl_idname = "amatista.pista"
    bl_label = "Necesito una pista"
    bl_description = "Muestra la siguiente pista del objetivo (Amatista cuenta cuántas usaste)"

    objetivo: bpy.props.StringProperty()

    def _revelar(self, context):
        self.revelada = practicas.pedir_pista(context, self.objetivo or None)
        return self.revelada

    def execute(self, context):
        if getattr(self, "revelada", None) is None and self._revelar(context) is None:
            self.report({"INFO"}, "No hay pistas para este paso.")
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        if self._revelar(context) is None or self.revelada.hint is None:
            self.report({"INFO"}, "Este paso no tiene pistas. ¡Inténtalo a tu manera!")
            return {"CANCELLED"}
        return _popup(self, context)

    def draw(self, context):
        layout = self.layout
        revelada = self.revelada
        practica = practicas.practica_activa(context)
        objetivo = practica.target(revelada.target_id) if practica else None
        cuerpo = estilo.tarjeta(
            layout, objetivo.title if objetivo else "Pista", icono_propio="pista",
            derecha=f"Pista {revelada.level} de {revelada.total}",
        )
        texto = revelada.hint.text if revelada.hint else "Ya viste todas las pistas de este paso."
        estilo.parrafo(cuerpo, context, texto, margen=0)
        if objetivo and objetivo.tip and revelada.level == 1:
            estilo.parrafo(cuerpo, context, objetivo.tip, icon="INFO", margen=0)
        fila = layout.row(align=True)
        fila.scale_y = 1.3
        if not revelada.exhausted:
            fila.operator("amatista.pista", text="Otra pista", icon_value=estilo.icono("pista")).objetivo = revelada.target_id
        fila.operator("amatista.comprobar", text="Intentaré hacerlo", icon="CHECKMARK")


class AMATISTA_OT_felicitar(bpy.types.Operator):
    bl_idname = "amatista.felicitar"
    bl_label = "¡Práctica completada!"

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return _popup(self, context, 420)

    def draw(self, context):
        layout = self.layout
        practica = practicas.practica_activa(context)
        reporte = practicas.ESTADO["reporte"]
        if practica is None or reporte is None:
            return
        cabecera = layout.row()
        cabecera.scale_y = 1.6
        cabecera.label(text="¡Práctica completada!", icon_value=estilo.icono("celebrar"))
        cuerpo = estilo.tarjeta(layout, practica.title, icono_propio="completado", derecha="100 %")
        estilo.parrafo(cuerpo, context, practica.completion or "Terminaste todos los objetivos.", margen=0)
        pistas = practicas.pistas(context)
        autonomia = _motor.pedagogia.classify(True, pistas, context.scene.amatista.correcciones)
        texto = {
            "autonoma": "Lo resolviste sin pistas: ¡autonomía!",
            "con_pistas": f"Usaste {sum(pistas.values())} pista(s). La próxima, intenta con menos.",
            "con_guia": "Usaste la guía paso a paso. Repite la práctica para afianzarla.",
        }.get(autonomia, "")
        if texto:
            cuerpo.label(text=texto, icon="FUND")
        if practicas.vinculado():
            cuerpo.label(text="Tu progreso se guarda en tu cuenta de Amatista.", icon_value=estilo.icono("sincronizado"))
        else:
            cuerpo.label(text="Vincula tu cuenta para que cuente en la plataforma.", icon="INFO")
        fila = layout.row(align=True)
        fila.scale_y = 1.3
        fila.operator("amatista.abrir_plataforma", text="Ver en la plataforma", icon="URL").ruta = "#/panel"
        if not practicas.vinculado():
            fila.operator("amatista.vincular", text="Vincular", icon="LINKED")


class AMATISTA_OT_aviso_herramienta(bpy.types.Operator):
    bl_idname = "amatista.aviso_herramienta"
    bl_label = "Amatista"

    herramienta: bpy.props.StringProperty()
    explicar: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return _popup(self, context, 420)

    def draw(self, context):
        layout = self.layout
        herramienta = _motor.MOTOR.tools.get(self.herramienta) if _motor.MOTOR.tools else None
        practica = practicas.practica_activa(context)
        if herramienta is None or practica is None:
            return
        cuerpo = estilo.tarjeta(layout, f"Detectamos que usaste {herramienta.name}", icon="ERROR")
        estilo.parrafo(
            cuerpo, context,
            f"{herramienta.name} pertenece al Nivel {herramienta.minimum_level}. Esta práctica busca que la "
            f"resuelvas con las herramientas fundamentales del Nivel {practica.level}.",
            margen=0,
        )
        caja = cuerpo.box()
        caja.label(text=f"¿Qué es {herramienta.name}?", icon="QUESTION")
        estilo.parrafo(caja, context, herramienta.description, margen=2)
        if herramienta.shortcut:
            caja.label(text=herramienta.shortcut, icon="EVENT_TAB" if "Tab" in herramienta.shortcut else "KEYINGSET")
        nota = layout.row()
        nota.active = False
        nota.label(text="Es solo un aviso: puedes seguir experimentando.", icon="INFO")


class AMATISTA_OT_bienvenida(bpy.types.Operator):
    bl_idname = "amatista.bienvenida"
    bl_label = "Bienvenida a Amatista"

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return _popup(self, context, 420)

    def draw(self, context):
        layout = self.layout
        cabecera = layout.row()
        cabecera.scale_y = 1.6
        cabecera.label(text="Amatista ya está en tu Blender", icon_value=estilo.icono("logo"))
        cuerpo = estilo.tarjeta(layout, "Así funciona", icon="INFO")
        for paso in (
            "1. Abre la barra lateral con N y elige la pestaña Amatista.",
            "2. Empieza la práctica de tu lección.",
            "3. Trabaja: Amatista revisa tu escena y te dice qué falta.",
            "4. Tu avance aparece en la plataforma.",
        ):
            estilo.parrafo(cuerpo, context, paso, margen=0)
        p = ajustes.prefs()
        if not (p and p.token):
            layout.operator("amatista.vincular", text="Vincular con mi cuenta", icon="LINKED")


CLASES = (AMATISTA_OT_pista, AMATISTA_OT_felicitar, AMATISTA_OT_aviso_herramienta, AMATISTA_OT_bienvenida)
