"""Teoría dentro de Blender (motor v3): píldoras, repaso y pausa.

- Píldora: una idea corta (≤ 280 caracteres) con sus teclas en grande y,
  si trae pregunta, un «¿Lo entendiste?» de una sola respuesta. Aparece al
  empezar, al llegar a un paso, al entrar a un modo o cuando un vigilante
  pausa el progreso (practice/2 › pills › trigger).
- Repaso: al abrir una práctica, hasta 3 preguntas de píldoras de prácticas
  anteriores que ya tocan (cajas de Leitner: 1, 3, 7, 14 y 30 días).
- Pausa: un vigilante (por ejemplo «malla sin vértices encimados») detuvo
  el progreso; la ventana explica por qué y ofrece arreglarlo conmigo.
"""
import bpy

from .. import aprendizaje, guia, practicas
from . import estilo

VISUALES = {
    "axes": "ORIENTATION_GLOBAL",
    "mode": "EDITMODE_HLT",
    "keys": "KEYINGSET",
    "tab:MODIFIER": "MODIFIER",
    "tab:MATERIAL": "MATERIAL",
    "tab:RENDER": "SCENE",
    "tab:OUTPUT": "OUTPUT",
    "tab:DATA": "OUTLINER_DATA_LIGHT",
    "tab:OBJECT": "OBJECT_DATA",
    "tab:WORLD": "WORLD",
    "tab:SCENE": "SCENE_DATA",
}
DISPARO_TEXTO = {
    "start": "Para empezar",
    "target": "Para este paso",
    "mode": "En este modo",
    "selection": "Con lo que seleccionaste",
    "tool": "Sobre la herramienta",
    "guard": "Para arreglarlo",
    "complete": "Para terminar",
}


def icono_visual(pildora):
    visual = pildora.visual or ""
    if visual.startswith("image:"):
        return "IMAGE_DATA"
    return VISUALES.get(visual, "LIGHT")


def tarjeta_pildora(layout, context, pildora, con_botones=True, grande=False):
    """La tarjeta de teoría: título, texto, teclas grandes y botones."""
    caja = layout.box()
    cabecera = caja.row(align=True)
    cabecera.scale_y = 1.3 if grande else 1.1
    cabecera.label(text=pildora.title, icon=icono_visual(pildora))
    derecha = cabecera.row()
    derecha.alignment = "RIGHT"
    derecha.active = False
    derecha.label(text=DISPARO_TEXTO.get(pildora.trigger.on, "Teoría"))
    estilo.parrafo(caja, context, pildora.text, margen=2 if grande else 4)
    if pildora.keys:
        estilo.separador(caja, 0.3)
        estilo.teclas(caja, pildora.keys, escala=1.6 if grande else 1.25)
    visual = pildora.visual or ""
    if visual.startswith("tab:"):
        op = caja.operator("amatista.abrir_pestana", text="Muéstrame dónde está", icon="HIDE_OFF")
        op.pestana = visual[4:]
    if not con_botones:
        return caja
    practica = practicas.practica_activa(context)
    fila = caja.row(align=True)
    fila.scale_y = 1.25
    if pildora.check is not None:
        fila.operator("amatista.pildora", text="¿Lo entendí?", icon="QUESTION").pildora = pildora.id
    if practica is not None:
        fila.operator("amatista.pildora_vista", text="Entendido", icon="CHECKMARK").pildora = pildora.id
    return caja


def _pregunta(layout, context, check, operador, **propiedades):
    caja = estilo.tarjeta(layout, check.question, icon="QUESTION")
    col = caja.column(align=True)
    col.scale_y = 1.35
    for indice, opcion in enumerate(check.options):
        op = col.operator(operador, text=opcion)
        op.opcion = indice
        for clave, valor in propiedades.items():
            setattr(op, clave, valor)


class AMATISTA_OT_pildora(bpy.types.Operator):
    """Ventana de una píldora de teoría (la principal o la que se indique)."""

    bl_idname = "amatista.pildora"
    bl_label = "Teoría rápida"
    bl_description = "Lee la idea clave de este momento de la práctica"

    pildora: bpy.props.StringProperty()

    def _buscar(self, context):
        practica = practicas.practica_activa(context)
        if practica is None:
            return None, None
        if self.pildora:
            return practica, practica.pill(self.pildora)
        return practica, aprendizaje.pildora_principal()

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        _, pildora = self._buscar(context)
        if pildora is None:
            return {"CANCELLED"}
        self.pildora = pildora.id
        if bpy.app.background:
            return {"FINISHED"}
        return context.window_manager.invoke_popup(self, width=440)

    def draw(self, context):
        practica, pildora = self._buscar(context)
        if pildora is None:
            return
        layout = self.layout
        cabecera = layout.row()
        cabecera.scale_y = 1.4
        cabecera.label(text="Teoría rápida", icon_value=estilo.icono("logo"))
        tarjeta_pildora(layout, context, pildora, con_botones=False, grande=True)
        if pildora.check is not None:
            _pregunta(layout, context, pildora.check, "amatista.responder_pildora", pildora=pildora.id)
        else:
            estilo.boton_principal(layout, "amatista.pildora_vista", "Entendido, a practicar", icon="CHECKMARK",
                                   escala=1.35, pildora=pildora.id)


class AMATISTA_OT_pildora_vista(bpy.types.Operator):
    bl_idname = "amatista.pildora_vista"
    bl_label = "Entendido"
    bl_description = "Marca la idea como leída (entra a tu repaso si tiene pregunta)"

    pildora: bpy.props.StringProperty()

    def execute(self, context):
        practica = practicas.practica_activa(context)
        if practica is None or not self.pildora:
            return {"CANCELLED"}
        aprendizaje.marcar_vista(practica, self.pildora)
        practicas.redibujar()
        return {"FINISHED"}


class AMATISTA_OT_responder_pildora(bpy.types.Operator):
    bl_idname = "amatista.responder_pildora"
    bl_label = "Responder"

    pildora: bpy.props.StringProperty()
    opcion: bpy.props.IntProperty()

    def execute(self, context):
        practica = practicas.practica_activa(context)
        pildora = practica.pill(self.pildora) if practica else None
        if pildora is None or pildora.check is None:
            return {"CANCELLED"}
        aprendizaje.marcar_vista(practica, pildora.id)
        if self.opcion == pildora.check.answer:
            guia.avisar("¡Correcto!", pildora.title, "logrado")
        else:
            correcta = pildora.check.options[pildora.check.answer]
            guia.avisar("Casi", f"La respuesta era «{correcta}». La repasarás mañana.", "cerca")
            aprendizaje.responder(aprendizaje.spaced.item_id(practica.id, pildora.id), False)
        practicas.redibujar()
        return {"FINISHED"}


class AMATISTA_OT_repaso(bpy.types.Operator):
    """Repaso espaciado al abrir la práctica: preguntas de lo que viste antes."""

    bl_idname = "amatista.repaso"
    bl_label = "Repaso rápido"
    bl_description = "Responde lo que aprendiste en prácticas anteriores (fortalece la memoria)"

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        if not aprendizaje.repasos_pendientes(practicas.practica_activa(context)):
            return {"CANCELLED"}
        if bpy.app.background:
            return {"FINISHED"}
        return context.window_manager.invoke_popup(self, width=440)

    def draw(self, context):
        pendientes = aprendizaje.repasos_pendientes(practicas.practica_activa(context))
        layout = self.layout
        cabecera = layout.row()
        cabecera.scale_y = 1.4
        cabecera.label(text="Antes de empezar: repaso rápido", icon_value=estilo.icono("logo"))
        if not pendientes:
            layout.label(text="¡Listo! Ya repasaste todo lo que tocaba.", icon="CHECKMARK")
            return
        item, pildora = pendientes[0]
        fila = layout.row()
        fila.active = False
        fila.label(text=f"{pildora.title} · quedan {len(pendientes)}")
        _pregunta(layout, context, pildora.check, "amatista.responder_repaso", item=item)
        nota = layout.row()
        nota.active = False
        nota.label(text="Repasar justo antes de olvidar es lo que más ayuda a recordar.", icon="INFO")


class AMATISTA_OT_responder_repaso(bpy.types.Operator):
    bl_idname = "amatista.responder_repaso"
    bl_label = "Responder"

    item: bpy.props.StringProperty()
    opcion: bpy.props.IntProperty()

    def execute(self, context):
        practica = practicas.practica_activa(context)
        pendiente = next((p for i, p in aprendizaje.repasos_pendientes(practica) if i == self.item), None)
        if pendiente is None:
            return {"CANCELLED"}
        correcto = self.opcion == pendiente.check.answer
        aprendizaje.responder(self.item, correcto)
        if correcto:
            guia.avisar("¡Lo recuerdas!", pendiente.title, "logrado")
        else:
            guia.avisar("Para la próxima", f"Era «{pendiente.check.options[pendiente.check.answer]}». "
                        + pendiente.text[:120], "cerca")
        if aprendizaje.repasos_pendientes(practica):
            practicas._invocar("amatista.repaso")
        elif aprendizaje.pildora_principal() is not None:
            practicas._invocar("amatista.pildora")
        return {"FINISHED"}


class AMATISTA_OT_pausa(bpy.types.Operator):
    """Un vigilante detuvo el progreso: qué pasó y cómo arreglarlo."""

    bl_idname = "amatista.pausa"
    bl_label = "Progreso en pausa"

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        g = guia.guia_actual()
        if g is None or not g.paused or bpy.app.background:
            return {"CANCELLED"}
        return context.window_manager.invoke_popup(self, width=440)

    def draw(self, context):
        g = guia.guia_actual()
        if g is None:
            return
        layout = self.layout
        cabecera = layout.row()
        cabecera.scale_y = 1.4
        cabecera.alert = True
        cabecera.label(text="Tu progreso está en pausa", icon="PAUSE")
        caja = estilo.tarjeta(layout, g.title, icon="ERROR")
        estilo.parrafo(caja, context, g.feedback, margen=0, alerta=True)
        if g.instructions:
            estilo.instrucciones(caja, context, g.instructions)
        if g.action is not None:
            estilo.boton_principal(layout, "amatista.hazlo_conmigo", g.action.label, icon="PLAY", escala=1.4)
        nota = layout.row()
        nota.active = False
        nota.label(text="Cuando lo arregles, todo lo que llevabas vuelve a contar.", icon="INFO")


class AMATISTA_OT_abrir_pestana(bpy.types.Operator):
    bl_idname = "amatista.abrir_pestana"
    bl_label = "Muéstrame dónde está"
    bl_description = "Cambia el panel Propiedades a la pestaña de la que habla la teoría"

    pestana: bpy.props.StringProperty()

    def execute(self, context):
        if guia.abrir_pestana(context, self.pestana):
            guia.avisar("Mira a la derecha", "El panel Propiedades ya muestra esa pestaña.", "animo")
            return {"FINISHED"}
        self.report({"INFO"}, "Abre el editor Propiedades (a la derecha) para verla.")
        return {"CANCELLED"}


class AMATISTA_OT_pestana(bpy.types.Operator):
    bl_idname = "amatista.pestana"
    bl_label = "Cambiar de sección"

    pestana: bpy.props.StringProperty()

    def execute(self, context):
        context.window_manager.amatista.pestana = self.pestana
        return {"FINISHED"}


CLASES = (
    AMATISTA_OT_pildora,
    AMATISTA_OT_pildora_vista,
    AMATISTA_OT_responder_pildora,
    AMATISTA_OT_repaso,
    AMATISTA_OT_responder_repaso,
    AMATISTA_OT_pausa,
    AMATISTA_OT_abrir_pestana,
    AMATISTA_OT_pestana,
)
