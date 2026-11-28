"""Operadores del modo Alumno y de la cuenta (botones de los paneles)."""
import bpy

from . import _motor, ajustes, cuenta, guia, practicas, recorrido, red


def _avisar(operador, error, ok=None):
    """Muestra al alumno en la barra de estado de Blender el error (aviso) o, si no hay, el mensaje de éxito."""
    if error:
        operador.report({"WARNING"}, error)
    elif ok:
        operador.report({"INFO"}, ok)


class AMATISTA_OT_vincular(bpy.types.Operator):
    """Botón «Vincular con Amatista»: pide un código de vínculo a la plataforma y abre el navegador para confirmarlo."""
    bl_idname = "amatista.vincular"
    bl_label = "Vincular con Amatista"
    bl_description = "Conecta Blender con tu cuenta de Amatista usando un código (sin escribir tu contraseña)"

    def execute(self, context):
        """Inicia el vínculo en segundo plano; cuando la API devuelve la URL, abre el navegador del alumno (red)."""
        def listo(error):
            """Al obtener el código sin error, abre la página de confirmación en el navegador."""
            if error is None and cuenta.VINCULO["url"]:
                import webbrowser

                webbrowser.open(cuenta.VINCULO["url"])

        cuenta.iniciar_vinculo(listo)
        return {"FINISHED"}


class AMATISTA_OT_cancelar_vinculo(bpy.types.Operator):
    bl_idname = "amatista.cancelar_vinculo"
    bl_label = "Cancelar"

    def execute(self, context):
        """Botón «Cancelar»: abandona el vínculo en curso (el panel deja de mostrar el código)."""
        cuenta.cancelar_vinculo()
        return {"FINISHED"}


class AMATISTA_OT_desvincular(bpy.types.Operator):
    """Botón «Desvincular esta computadora»: tras confirmar, cierra la sesión de Amatista en este Blender."""
    bl_idname = "amatista.desvincular"
    bl_label = "Desvincular esta computadora"
    bl_description = "Cierra la sesión de Amatista en este Blender"

    def invoke(self, context, event):
        """Muestra el diálogo de confirmación de Blender antes de desvincular."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Borra el vínculo guardado; el panel vuelve a ofrecer «Vincular»."""
        cuenta.desvincular()
        return {"FINISHED"}


class AMATISTA_OT_permitir_internet(bpy.types.Operator):
    """Botón «Permitir acceso en línea»: activa la preferencia de red de Blender 4.2+ que Amatista necesita."""
    bl_idname = "amatista.permitir_internet"
    bl_label = "Permitir acceso en línea"
    bl_description = "Activa Preferencias › Sistema › Red › Permitir acceso en línea (lo pides tú con este botón)"

    def execute(self, context):
        """Activa ``use_online_access`` y guarda las preferencias; si ya hay red, reanuda la cuenta. Avisa si Blender pide reiniciar."""
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
    """Botón «Abrir la plataforma»: abre la web de Amatista en la ruta indicada (por defecto el panel del alumno)."""
    bl_idname = "amatista.abrir_plataforma"
    bl_label = "Abrir la plataforma"
    bl_description = "Abre Amatista en el navegador"

    ruta: bpy.props.StringProperty(default="#/panel")

    def execute(self, context):
        """Anota el uso en el recorrido y abre el navegador; avisa si el paquete no conoce la dirección de la plataforma."""
        recorrido.anotar("plataforma")
        if not cuenta.abrir_plataforma(self.ruta):
            self.report({"WARNING"}, "Este paquete no sabe la dirección de la plataforma (Preferencias del add-on).")
        return {"FINISHED"}


class AMATISTA_OT_ver_referencia(bpy.types.Operator):
    """Botón «Ver el modelo de referencia»: abre la imagen o el plano con medidas de la práctica en el visor del sistema."""
    bl_idname = "amatista.ver_referencia"
    bl_label = "Ver el modelo de referencia"
    bl_description = "Abre la imagen o el plano con medidas de cómo debe verse la figura"

    archivo: bpy.props.StringProperty(default="referencia.jpg")

    def execute(self, context):
        """Busca el archivo de referencia de la práctica activa y lo abre; avisa si la práctica no trae imagen."""
        practica = practicas.practica_activa(context)
        ruta = practicas.archivo_de_referencia(practica.id, self.archivo) if practica else None
        if ruta is None:
            self.report({"WARNING"}, "Esta práctica no trae imagen de referencia.")
            return {"CANCELLED"}
        bpy.ops.wm.path_open(filepath=str(ruta))
        return {"FINISHED"}


class AMATISTA_OT_abrir_practica(bpy.types.Operator):
    """Botón «Empezar práctica»: abre la práctica elegida en su propia escena de Blender."""
    bl_idname = "amatista.abrir_practica"
    bl_label = "Empezar práctica"
    bl_description = ("Abre la práctica en su propia escena (lo de otra práctica queda guardado en la suya)")

    practica_id: bpy.props.StringProperty()

    def execute(self, context):
        """Abre la práctica por id (crea/cambia de escena) y avisa a la plataforma de que el alumno la abrió."""
        practicas.abrir_por_id(context, self.practica_id, lambda error: error and print(f"[Amatista] {error}"))
        _registrar_apertura(self.practica_id)
        return {"FINISHED"}


def _registrar_apertura(practica_id):
    """Si el alumno está vinculado, informa a la API (POST, en cola) de que abrió la práctica desde Blender."""
    if practicas.vinculado():
        red.pedir("POST", f"/api/addon/v1/practicas/{practica_id}/abrir", None, {"origen": "blender"})


class AMATISTA_OT_practica_actual(bpy.types.Operator):
    """Botón «Abrir mi lección actual»: trae de la plataforma la práctica de la lección que el alumno tiene abierta."""
    bl_idname = "amatista.practica_actual"
    bl_label = "Abrir mi lección actual"
    bl_description = "Abre la práctica de la lección que tienes abierta en la plataforma"

    def execute(self, context):
        """Pide la práctica actual a la API en segundo plano; los problemas se escriben en la consola."""
        def listo(error, respuesta):
            """Informa en consola si hubo error o si la lección abierta no tiene práctica de Blender."""
            if error:
                print(f"[Amatista] {error}")
            elif not (respuesta and respuesta.get("definicion")):
                print("[Amatista] Abre en la plataforma una lección con práctica de Blender.")

        practicas.cargar_practica_actual(listo)
        return {"FINISHED"}


class AMATISTA_OT_elegir_practica(bpy.types.Operator):
    """Botón «Elegir otra práctica»: cierra la práctica activa y vuelve a la lista (el avance queda en el .blend)."""
    bl_idname = "amatista.elegir_practica"
    bl_label = "Elegir otra práctica"
    bl_description = "Vuelve a la lista de prácticas (tu avance queda guardado en este archivo)"

    def execute(self, context):
        """Cierra la práctica y refresca el catálogo de prácticas desde la plataforma."""
        practicas.cerrar(context)
        practicas.refrescar_catalogo()
        return {"FINISHED"}


class AMATISTA_OT_empezar_de_nuevo(bpy.types.Operator):
    """Botón «Empezar de nuevo»: reabre la práctica en una escena limpia; lo anterior queda en una escena «(anterior)»."""
    bl_idname = "amatista.empezar_de_nuevo"
    bl_label = "Empezar de nuevo"
    bl_description = ("Abre la práctica en una escena limpia. Lo que hiciste no se borra: queda en una escena "
                      "«(anterior)» del mismo archivo")

    def invoke(self, context, event):
        """Pide confirmación antes de reiniciar."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Reinicia la práctica y muestra el resultado en la barra de estado; cancela si no había práctica."""
        texto = practicas.reiniciar(context)
        if texto:
            self.report({"INFO"}, texto)
        return {"FINISHED"} if texto else {"CANCELLED"}


class AMATISTA_OT_ver_ejemplo(bpy.types.Operator):
    """Botón «Ver el ejemplo resuelto»: arma la solución de la práctica en una escena aparte para compararla."""
    bl_idname = "amatista.ver_ejemplo"
    bl_label = "Ver el ejemplo resuelto"
    bl_description = ("Arma el ejemplo resuelto de la práctica en su propia escena para que lo mires y lo compares. "
                      "Tu escena no cambia")

    def execute(self, context):
        """Construye/abre la escena del ejemplo y muestra el mensaje resultante."""
        from . import ejemplo

        self.report({"INFO"}, ejemplo.ver_ejemplo(context))
        return {"FINISHED"}


class AMATISTA_OT_volver_practica(bpy.types.Operator):
    """Botón «Volver a mi práctica»: regresa de la escena del ejemplo a la del alumno."""
    bl_idname = "amatista.volver_practica"
    bl_label = "Volver a mi práctica"
    bl_description = "Regresa de la escena del ejemplo a la escena de tu práctica"

    def execute(self, context):
        """Cambia a la escena de la práctica; cancela si no había a dónde volver."""
        from . import ejemplo

        texto = ejemplo.volver(context)
        if texto:
            self.report({"INFO"}, texto)
        return {"FINISHED"} if texto else {"CANCELLED"}


class AMATISTA_OT_actualizar_catalogo(bpy.types.Operator):
    bl_idname = "amatista.actualizar_catalogo"
    bl_label = "Actualizar lista"

    def execute(self, context):
        """Vuelve a descargar la lista de prácticas disponibles desde la plataforma."""
        practicas.refrescar_catalogo()
        return {"FINISHED"}


class AMATISTA_OT_comprobar(bpy.types.Operator):
    """Botón «Comprobar»: evalúa la escena del alumno con el motor ahora mismo."""
    bl_idname = "amatista.comprobar"
    bl_label = "Comprobar"
    bl_description = "Revisa tu escena con Amatista"

    def execute(self, context):
        """Evalúa (motivo «manual»), sincroniza el avance y muestra el progreso en %; avisa si no hay práctica abierta."""
        reporte = practicas.evaluar(context, "manual")
        if reporte is None:
            self.report({"WARNING"}, "Primero abre una práctica.")
            return {"CANCELLED"}
        practicas.sincronizar(context)
        self.report({"INFO"}, f"Progreso: {reporte.progress:.0f} %")
        return {"FINISHED"}


class AMATISTA_OT_sincronizar(bpy.types.Operator):
    """Botón «Enviar mi progreso»: guarda inmediatamente el avance en la plataforma."""
    bl_idname = "amatista.sincronizar"
    bl_label = "Enviar mi progreso"
    bl_description = "Guarda ahora tu progreso en la plataforma"

    def execute(self, context):
        """Evalúa si hace falta, fuerza la sincronización y vacía la cola de envíos pendientes (red)."""
        recorrido.anotar("guardar")
        if practicas.ESTADO["reporte"] is None:
            practicas.evaluar(context)
        practicas.sincronizar(context, forzar=True)
        red.vaciar_cola()
        return {"FINISHED"}


class AMATISTA_OT_asignar_rol(bpy.types.Operator):
    """Botón «Asignar rol»: le dice a Amatista qué es cada objeto seleccionado (el rol queda en el objeto; admite deshacer)."""
    bl_idname = "amatista.asignar_rol"
    bl_label = "Asignar rol"
    bl_description = "Dice a Amatista qué es cada objeto seleccionado (se guarda en el objeto)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        """Solo disponible si hay un objeto activo."""
        return context.active_object is not None

    def execute(self, context):
        """Asigna el rol elegido en el panel a los objetos seleccionados y reevalúa; avisa si la práctica no tiene roles."""
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
        """Solo disponible si hay un objeto activo."""
        return context.active_object is not None

    def execute(self, context):
        """Quita el rol de los objetos seleccionados (o del activo) y reevalúa la práctica."""
        for obj in context.selected_objects or [context.active_object]:
            _motor.tagger.remove_role(obj)
        practicas.evaluar(context, "rol")
        return {"FINISHED"}


class AMATISTA_OT_hazlo_conmigo(bpy.types.Operator):
    """Botón «Hazlo conmigo»: selecciona el objeto del paso y arranca la herramienta adecuada para que el alumno la termine."""
    bl_idname = "amatista.hazlo_conmigo"
    bl_label = "Hazlo conmigo"
    bl_description = (
        "Selecciona el objeto del paso y arranca la herramienta correcta: tú la terminas con el ratón "
        "o escribiendo el número de la guía (cuenta como ayuda paso a paso)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Ejecuta la acción de la guía actual y la registra como ayuda paso a paso (salvo «ver ejemplo»); avisa si no se pudo."""
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
        if g.action.kind != "show_example":
            # Mostrar el ejemplo no es ayuda paso a paso (y la escena ya es la del ejemplo: ahí no se anota nada).
            guia.registrar_ayuda(context, objetivo, "hazlo_conmigo", _motor.pedagogia.hints.NIVEL_GUIA)
        if texto:
            guia.avisar(g.action.label, texto, "animo")
        return {"FINISHED"}


class AMATISTA_OT_mostrarme(bpy.types.Operator):
    """Botón «Muéstrame»: selecciona y encuadra en la vista 3D el objeto que hay que cambiar en este paso."""
    bl_idname = "amatista.mostrarme"
    bl_label = "Muéstrame"
    bl_description = "Selecciona y encuadra el objeto que hay que cambiar en este paso"

    def execute(self, context):
        """Selecciona los objetos resaltados por la guía, encuadra la vista, muestra un aviso y registra la ayuda (nivel 1)."""
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
    """Botón «Otro dato»: la mascota del módulo muestra otro consejo o dato curioso."""
    bl_idname = "amatista.mascota_siguiente"
    bl_label = "Otro dato"
    bl_description = "La mascota del módulo te cuenta otro consejo o dato curioso"

    def execute(self, context):
        """Pasa al siguiente mensaje de la mascota y redibuja el panel."""
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
