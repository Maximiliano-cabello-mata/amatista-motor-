"""Operadores del modo Alumno y de la cuenta (botones de los paneles)."""
import bpy

from . import _motor, ajustes, cuenta, guia, practicas, red


def _avisar(operador, error, ok=None):
    if error:
        operador.report({"WARNING"}, error)
    elif ok:
        operador.report({"INFO"}, ok)


class AMATISTA_OT_vincular(bpy.types.Operator):
    bl_idname = "amatista.vincular"
    bl_label = "Vincular con Amatista"
    bl_description = "Conecta Blender con tu cuenta de Amatista usando un código (sin escribir tu contraseña)"

    def execute(self, context):
        def listo(error):
            if error is None and cuenta.VINCULO["url"]:
                import webbrowser

                webbrowser.open(cuenta.VINCULO["url"])

        cuenta.iniciar_vinculo(listo)
        return {"FINISHED"}


class AMATISTA_OT_cancelar_vinculo(bpy.types.Operator):
    bl_idname = "amatista.cancelar_vinculo"
    bl_label = "Cancelar"

    def execute(self, context):
        cuenta.cancelar_vinculo()
        return {"FINISHED"}


class AMATISTA_OT_desvincular(bpy.types.Operator):
    bl_idname = "amatista.desvincular"
    bl_label = "Desvincular esta computadora"
    bl_description = "Cierra la sesión de Amatista en este Blender"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        cuenta.desvincular()
        return {"FINISHED"}


class AMATISTA_OT_permitir_internet(bpy.types.Operator):
    bl_idname = "amatista.permitir_internet"
    bl_label = "Permitir acceso en línea"
    bl_description = "Activa Preferencias › Sistema › Red › Permitir acceso en línea (lo pides tú con este botón)"

    def execute(self, context):
        sistema = context.preferences.system
        if hasattr(sistema, "use_online_access"):
            sistema.use_online_access = True
            ajustes.guardar_preferencias()
        if red.en_linea_permitido():
            cuenta.al_iniciar()
            self.report({"INFO"}, "Listo: Amatista ya puede conectarse.")
        else:
            self.report({"WARNING"}, "Blender pide reiniciar para aplicar el cambio.")
        return {"FINISHED"}


class AMATISTA_OT_abrir_plataforma(bpy.types.Operator):
    bl_idname = "amatista.abrir_plataforma"
    bl_label = "Abrir la plataforma"
    bl_description = "Abre Amatista en el navegador"

    ruta: bpy.props.StringProperty(default="#/panel")

    def execute(self, context):
        if not cuenta.abrir_plataforma(self.ruta):
            self.report({"WARNING"}, "Este paquete no sabe la dirección de la plataforma (Preferencias del add-on).")
        return {"FINISHED"}


class AMATISTA_OT_ver_referencia(bpy.types.Operator):
    bl_idname = "amatista.ver_referencia"
    bl_label = "Ver el modelo de referencia"
    bl_description = "Abre la imagen o el plano con medidas de cómo debe verse la figura"

    archivo: bpy.props.StringProperty(default="referencia.jpg")

    def execute(self, context):
        practica = practicas.practica_activa(context)
        ruta = practicas.archivo_de_referencia(practica.id, self.archivo) if practica else None
        if ruta is None:
            self.report({"WARNING"}, "Esta práctica no trae imagen de referencia.")
            return {"CANCELLED"}
        bpy.ops.wm.path_open(filepath=str(ruta))
        return {"FINISHED"}


class AMATISTA_OT_abrir_practica(bpy.types.Operator):
    bl_idname = "amatista.abrir_practica"
    bl_label = "Empezar práctica"
    bl_description = "Abre la práctica en esta escena"

    practica_id: bpy.props.StringProperty()

    def execute(self, context):
        practicas.abrir_por_id(context, self.practica_id, lambda error: error and print(f"[Amatista] {error}"))
        _registrar_apertura(self.practica_id)
        return {"FINISHED"}


def _registrar_apertura(practica_id):
    if practicas.vinculado():
        red.pedir("POST", f"/api/addon/v1/practicas/{practica_id}/abrir", None, {"origen": "blender"})


class AMATISTA_OT_practica_actual(bpy.types.Operator):
    bl_idname = "amatista.practica_actual"
    bl_label = "Abrir mi lección actual"
    bl_description = "Abre la práctica de la lección que tienes abierta en la plataforma"

    def execute(self, context):
        def listo(error, respuesta):
            if error:
                print(f"[Amatista] {error}")
            elif not (respuesta and respuesta.get("definicion")):
                print("[Amatista] Abre en la plataforma una lección con práctica de Blender.")

        practicas.cargar_practica_actual(listo)
        return {"FINISHED"}


class AMATISTA_OT_elegir_practica(bpy.types.Operator):
    bl_idname = "amatista.elegir_practica"
    bl_label = "Elegir otra práctica"
    bl_description = "Vuelve a la lista de prácticas (tu avance queda guardado en este archivo)"

    def execute(self, context):
        practicas.cerrar(context)
        practicas.refrescar_catalogo()
        return {"FINISHED"}


class AMATISTA_OT_empezar_de_nuevo(bpy.types.Operator):
    bl_idname = "amatista.empezar_de_nuevo"
    bl_label = "Empezar de nuevo"
    bl_description = ("Abre la práctica en una escena limpia. Lo que hiciste no se borra: queda en una escena "
                      "«(anterior)» del mismo archivo")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        texto = practicas.reiniciar(context)
        if texto:
            self.report({"INFO"}, texto)
        return {"FINISHED"} if texto else {"CANCELLED"}


class AMATISTA_OT_ver_ejemplo(bpy.types.Operator):
    bl_idname = "amatista.ver_ejemplo"
    bl_label = "Ver el ejemplo resuelto"
    bl_description = ("Arma el ejemplo resuelto de la práctica en su propia escena para que lo mires y lo compares. "
                      "Tu escena no cambia")

    def execute(self, context):
        from . import ejemplo

        self.report({"INFO"}, ejemplo.ver_ejemplo(context))
        return {"FINISHED"}


class AMATISTA_OT_volver_practica(bpy.types.Operator):
    bl_idname = "amatista.volver_practica"
    bl_label = "Volver a mi práctica"
    bl_description = "Regresa de la escena del ejemplo a la escena de tu práctica"

    def execute(self, context):
        from . import ejemplo

        texto = ejemplo.volver(context)
        if texto:
            self.report({"INFO"}, texto)
        return {"FINISHED"} if texto else {"CANCELLED"}


class AMATISTA_OT_actualizar_catalogo(bpy.types.Operator):
    bl_idname = "amatista.actualizar_catalogo"
    bl_label = "Actualizar lista"

    def execute(self, context):
        practicas.refrescar_catalogo()
        return {"FINISHED"}


class AMATISTA_OT_comprobar(bpy.types.Operator):
    bl_idname = "amatista.comprobar"
    bl_label = "Comprobar"
    bl_description = "Revisa tu escena con Amatista"

    def execute(self, context):
        reporte = practicas.evaluar(context, "manual")
        if reporte is None:
            self.report({"WARNING"}, "Primero abre una práctica.")
            return {"CANCELLED"}
        practicas.sincronizar(context)
        self.report({"INFO"}, f"Progreso: {reporte.progress:.0f} %")
        return {"FINISHED"}


class AMATISTA_OT_sincronizar(bpy.types.Operator):
    bl_idname = "amatista.sincronizar"
    bl_label = "Enviar mi progreso"
    bl_description = "Guarda ahora tu progreso en la plataforma"

    def execute(self, context):
        if practicas.ESTADO["reporte"] is None:
            practicas.evaluar(context)
        practicas.sincronizar(context, forzar=True)
        red.vaciar_cola()
        return {"FINISHED"}


class AMATISTA_OT_asignar_rol(bpy.types.Operator):
    bl_idname = "amatista.asignar_rol"
    bl_label = "Asignar rol"
    bl_description = "Dice a Amatista qué es cada objeto seleccionado (se guarda en el objeto)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        rol = context.scene.amatista.rol_elegido
        if not rol:
            self.report({"WARNING"}, "La práctica no tiene roles.")
            return {"CANCELLED"}
        objetos = context.selected_objects or [context.active_object]
        for obj in objetos:
            _motor.tagger.assign_role(obj, rol)
        practicas.evaluar(context, "rol")
        self.report({"INFO"}, f"{len(objetos)} objeto(s) ahora son «{rol}».")
        return {"FINISHED"}


class AMATISTA_OT_quitar_rol(bpy.types.Operator):
    bl_idname = "amatista.quitar_rol"
    bl_label = "Quitar rol"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        for obj in context.selected_objects or [context.active_object]:
            _motor.tagger.remove_role(obj)
        practicas.evaluar(context, "rol")
        return {"FINISHED"}


class AMATISTA_OT_hazlo_conmigo(bpy.types.Operator):
    bl_idname = "amatista.hazlo_conmigo"
    bl_label = "Hazlo conmigo"
    bl_description = (
        "Selecciona el objeto del paso y arranca la herramienta correcta: tú la terminas con el ratón "
        "o escribiendo el número de la guía (cuenta como ayuda paso a paso)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        g = guia.guia_actual()
        if g is None or g.action is None:
            self.report({"INFO"}, "Este paso no necesita ayuda: ¡ya está!")
            return {"CANCELLED"}
        objetivo = g.target_id
        try:
            texto = guia.ejecutar_accion(context, g.action)
        except RuntimeError as error:
            self.report({"WARNING"}, f"No se pudo arrancar la herramienta: {error}")
            return {"CANCELLED"}
        guia.registrar_ayuda(context, objetivo, "hazlo_conmigo", _motor.pedagogia.hints.NIVEL_GUIA)
        if texto:
            guia.avisar(g.action.label, texto, "animo")
        return {"FINISHED"}


class AMATISTA_OT_mostrarme(bpy.types.Operator):
    bl_idname = "amatista.mostrarme"
    bl_label = "Muéstrame"
    bl_description = "Selecciona y encuadra el objeto que hay que cambiar en este paso"

    def execute(self, context):
        g = guia.guia_actual()
        if g is None:
            return {"CANCELLED"}
        nombres = [h.object_name for h in g.highlights if h.kind in ("corregir", "candidato")]
        if not nombres and g.action is not None:
            nombres = list(g.action.objects)
        if nombres and guia.seleccionar(context, nombres):
            guia.encuadrar(context)
            guia.avisar(g.title, g.feedback, "animo")
        else:
            guia.avisar(g.title, g.instructions[0].text if g.instructions else g.feedback, "animo")
        guia.registrar_ayuda(context, g.target_id, "mostrarme", 1)
        return {"FINISHED"}


class AMATISTA_OT_mascota_siguiente(bpy.types.Operator):
    bl_idname = "amatista.mascota_siguiente"
    bl_label = "Otro dato"
    bl_description = "La mascota del módulo te cuenta otro consejo o dato curioso"

    def execute(self, context):
        from . import temas

        temas.siguiente_mensaje()
        practicas.redibujar()
        return {"FINISHED"}


CLASES = (
    AMATISTA_OT_ver_referencia,
    AMATISTA_OT_hazlo_conmigo,
    AMATISTA_OT_mascota_siguiente,
    AMATISTA_OT_mostrarme,
    AMATISTA_OT_vincular,
    AMATISTA_OT_cancelar_vinculo,
    AMATISTA_OT_desvincular,
    AMATISTA_OT_permitir_internet,
    AMATISTA_OT_abrir_plataforma,
    AMATISTA_OT_abrir_practica,
    AMATISTA_OT_practica_actual,
    AMATISTA_OT_elegir_practica,
    AMATISTA_OT_empezar_de_nuevo,
    AMATISTA_OT_ver_ejemplo,
    AMATISTA_OT_volver_practica,
    AMATISTA_OT_actualizar_catalogo,
    AMATISTA_OT_comprobar,
    AMATISTA_OT_sincronizar,
    AMATISTA_OT_asignar_rol,
    AMATISTA_OT_quitar_rol,
)
