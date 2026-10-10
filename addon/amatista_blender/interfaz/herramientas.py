"""«Tus herramientas» (motor 3.4): solo las de la práctica, con «Usar» y «¿Cómo se usa?».

Las herramientas vienen del catálogo del motor (tools/catalogo.json): nombre,
teclas, cómo se usa paso a paso, el error típico y la acción que arranca la
herramienta en Blender. Las del paso actual aparecen primero y marcadas.
"""
import bpy

from .. import _motor, enfoque, enlace, guia, mision, practicas
from . import estilo

ICONO_CATEGORIA = {
    "vista": "VIEW3D",
    "objeto": "MESH_CUBE",
    "transformación": "OBJECT_ORIGIN",
    "organización": "OUTLINER",
    "archivo": "FILE_TICK",
    "material": "MATERIAL",
    "malla": "EDITMODE_HLT",
    "modificador": "MODIFIER",
    "selección": "RESTRICT_SELECT_OFF",
    "escena": "LIGHT",
    "render": "RENDER_STILL",
    "animación": "KEYFRAME",
}


def icono(herramienta):
    if herramienta.id.startswith("camera"):
        return "CAMERA_DATA"
    return ICONO_CATEGORIA.get(herramienta.category, "TOOL_SETTINGS")


def actuales(practica, reporte=None):
    """(todas las de la práctica, las del paso actual)."""
    registro = _motor.MOTOR.tools
    if registro is None or practica is None:
        return (), ()
    todas = registro.for_practice(practica)
    g = guia.guia_actual()
    teclas, textos = [], []
    if g is not None and not g.completed:
        teclas = [i.keys for i in g.instructions]
        textos = [i.text for i in g.instructions]
    reporte = reporte or practicas.ESTADO["reporte"]
    objetivo = practica.target(reporte.current_target_id) if reporte and reporte.current_target_id else None
    if objetivo is not None and not reporte.completed:
        textos += [objetivo.tip] + [h.text for h in objetivo.hints]
    del_paso = registro.for_step(practica, teclas, " ".join(t for t in textos if t))
    return todas, del_paso


def dibujar(layout, context, practica, reporte):
    todas, del_paso = actuales(practica, reporte)
    cabecera = layout.row(align=True)
    if enfoque.activo():
        cabecera.label(text="Blender enfocado en esta práctica", icon="HIDE_ON")
        cabecera.operator("amatista.ver_todo", text="Ver todo", icon="FULLSCREEN_ENTER")
    else:
        cabecera.label(text="Blender completo", icon="HIDE_OFF")
        cabecera.operator("amatista.enfocar", text="Enfocar", icon="HIDE_ON")
    if not todas:
        estilo.parrafo(layout, context, "Esta práctica no limita las herramientas: usa las que quieras.", icon="INFO")
        return
    ahora = {t.id for t in del_paso}
    orden = list(del_paso) + [t for t in todas if t.id not in ahora]
    for herramienta in orden:
        en_paso = herramienta.id in ahora
        contenedor = layout.box() if en_paso else layout
        fila = contenedor.row(align=True)
        fila.label(text=herramienta.name, icon="TRIA_RIGHT" if en_paso else icono(herramienta))
        atajo = fila.row()
        atajo.alignment = "RIGHT"
        atajo.active = False
        atajo.label(text=(herramienta.keys[0] if herramienta.keys else ""))
        if herramienta.action:
            fila.operator("amatista.usar_herramienta", text="", icon="PLAY").herramienta = herramienta.id
        fila.operator("amatista.herramienta_ayuda", text="", icon="QUESTION").herramienta = herramienta.id
        if en_paso:
            sub = contenedor.row()
            sub.active = False
            sub.label(text="La usas en este paso", icon="BLANK1")


# --- Usar una herramienta ---------------------------------------------------------------------


def _vista_3d(context):
    """(ventana, área, región) de la vista 3D donde arrancar la herramienta."""
    if context.area is not None and context.area.type == "VIEW_3D":
        region = next((r for r in context.area.regions if r.type == "WINDOW"), None)
        return context.window, context.area, region
    for ventana in context.window_manager.windows:
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                return ventana, area, next((r for r in area.regions if r.type == "WINDOW"), None)
    return None, None, None


def usar(context, herramienta):
    """Arranca la herramienta como si el alumno pulsara su tecla. Devuelve un aviso o None."""
    accion = herramienta.action or {}
    ventana, area, region = _vista_3d(context)
    if accion.get("mode") == "EDIT" and context.mode != "EDIT_MESH":
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return "Primero selecciona un objeto con clic."
        bpy.ops.object.mode_set(mode="EDIT")

    def en_vista(funcion, *args, **kwargs):
        if area is not None:
            with context.temp_override(window=ventana, area=area, region=region):
                return funcion(*args, **kwargs)
        return funcion(*args, **kwargs)

    if "tool" in accion:
        en_vista(bpy.ops.wm.tool_set_by_id, name=accion["tool"])
        return None
    if "operator" in accion:
        categoria, nombre = accion["operator"].split(".", 1)
        operador = getattr(getattr(bpy.ops, categoria), nombre)
        if not en_vista(operador.poll):
            return "Primero selecciona un objeto con clic."
        modo = "INVOKE_DEFAULT" if accion.get("invoke") and not bpy.app.background else "EXEC_DEFAULT"
        en_vista(operador, modo, **dict(accion.get("props") or {}))
        return None
    if "menu" in accion:
        if bpy.app.background:
            return None
        en_vista(bpy.ops.wm.call_menu, name=accion["menu"])
        return None
    if "panel" in accion:
        if bpy.app.background:
            return None
        en_vista(bpy.ops.wm.call_panel, name=accion["panel"])
        return None
    if "tab" in accion:
        if guia.abrir_pestana(context, accion["tab"]):
            return None
        return "Abre el panel Propiedades: está a la derecha, debajo del Outliner."
    return None


class AMATISTA_OT_usar_herramienta(bpy.types.Operator):
    bl_idname = "amatista.usar_herramienta"
    bl_label = "Usar"
    bl_description = "Arranca la herramienta como si pulsaras su tecla"
    bl_options = {"REGISTER", "UNDO"}

    herramienta: bpy.props.StringProperty()

    def execute(self, context):
        herramienta = _motor.MOTOR.tools.get(self.herramienta)
        if herramienta is None:
            return {"CANCELLED"}
        try:
            aviso = usar(context, herramienta)
        except (RuntimeError, TypeError, AttributeError) as error:
            aviso = str(error).strip().splitlines()[-1] if str(error).strip() else "No se pudo usar la herramienta."
        if aviso:
            self.report({"WARNING"}, aviso)
            return {"CANCELLED"}
        mision.marcar_usada(herramienta.id)  # motor 4: se enciende en la tarjeta de la misión
        if herramienta.keys:
            self.report({"INFO"}, f"{herramienta.name}: la próxima vez pulsa {herramienta.keys[0]}.")
        return {"FINISHED"}


class AMATISTA_OT_herramienta_ayuda(bpy.types.Operator):
    bl_idname = "amatista.herramienta_ayuda"
    bl_label = "¿Cómo se usa?"
    bl_description = "Explica paso a paso cómo se usa esta herramienta y el error típico"

    herramienta: bpy.props.StringProperty()

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        if _motor.MOTOR.tools.get(self.herramienta) is None:
            return {"CANCELLED"}
        guia.ESTADO["ayudas"]["explicar"] += 1
        if bpy.app.background:
            return self.execute(context)
        return context.window_manager.invoke_popup(self, width=420)

    def draw(self, context):
        layout = self.layout
        herramienta = _motor.MOTOR.tools.get(self.herramienta)
        if herramienta is None:
            return
        cuerpo = estilo.tarjeta(layout, herramienta.name, icon=icono(herramienta), derecha=herramienta.shortcut[:24])
        if herramienta.description:
            estilo.parrafo(cuerpo, context, herramienta.description, margen=0)
        for combinacion in herramienta.keys[:3]:
            estilo.teclas(cuerpo, combinacion.split("+"), escala=1.2)
        if herramienta.howto:
            caja = estilo.tarjeta(layout, "Cómo se usa", icon="KEYINGSET")
            for indice, paso in enumerate(herramienta.howto, start=1):
                estilo.parrafo(caja, context, f"{indice}. {paso}", margen=6)
        if herramienta.mistake:
            caja = layout.box()
            caja.label(text="Error típico", icon="ERROR")
            estilo.parrafo(caja, context, herramienta.mistake, margen=2)
        if herramienta.action:
            fila = layout.row()
            fila.scale_y = 1.3
            fila.operator("amatista.usar_herramienta", text="Probar ahora", icon="PLAY").herramienta = herramienta.id


class AMATISTA_OT_ver_todo(bpy.types.Operator):
    bl_idname = "amatista.ver_todo"
    bl_label = "Ver todo Blender"
    bl_description = "Muestra Blender completo: todos los menús y la barra de herramientas"

    def execute(self, context):
        practica = practicas.practica_activa(context)
        enfoque.ver_todo(practica.id if practica else "")
        enlace.latir_pronto()
        practicas.redibujar()
        self.report({"INFO"}, "Blender completo. Vuelve con «Enfocar» en N › Amatista.")
        return {"FINISHED"}


class AMATISTA_OT_enfocar(bpy.types.Operator):
    bl_idname = "amatista.enfocar"
    bl_label = "Enfocar Blender"
    bl_description = "Esconde lo que la práctica no usa y deja a mano solo sus herramientas"

    def execute(self, context):
        enfoque.ESTADO["rechazado"] = ""
        enfoque.activar(practicas.practica_activa(context))
        enlace.latir_pronto()
        practicas.redibujar()
        return {"FINISHED"}


CLASES = (AMATISTA_OT_usar_herramienta, AMATISTA_OT_herramienta_ayuda, AMATISTA_OT_ver_todo, AMATISTA_OT_enfocar)
