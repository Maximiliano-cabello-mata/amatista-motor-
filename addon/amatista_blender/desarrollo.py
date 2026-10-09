"""Operadores de Amatista Author (modo desarrollador)."""
import json

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import _motor, autor, estado, practicas


def _error(operador, error):
    operador.report({"ERROR"}, str(error))
    return {"CANCELLED"}


class AMATISTA_OT_autor_nuevo(bpy.types.Operator):
    bl_idname = "amatista.autor_nuevo"
    bl_label = "Crear borrador"
    bl_description = "Crea el JSON de una práctica nueva en el Editor de texto"

    def execute(self, context):
        a = context.scene.amatista_autor
        plantilla = "" if a.nueva_plantilla == estado.SIN_PLANTILLA else a.nueva_plantilla
        autor.nuevo_borrador(a.nuevo_id, a.nuevo_titulo, a.nuevo_nivel, plantilla, a.nuevo_curso, a.nuevo_modulo)
        self.report({"INFO"}, "Borrador creado. Cambia los textos marcados «Cambia este texto»."
                    if plantilla else "Borrador creado. Declara roles y agrega objetivos.")
        return {"FINISHED"}


class AMATISTA_OT_autor_desde_activa(bpy.types.Operator):
    bl_idname = "amatista.autor_desde_activa"
    bl_label = "Partir de la práctica abierta"
    bl_description = "Copia la práctica abierta como borrador para editarla"

    @classmethod
    def poll(cls, context):
        return bool(context.scene.amatista.practica_json)

    def execute(self, context):
        autor.borrador_desde_practica(json.loads(context.scene.amatista.practica_json))
        return {"FINISHED"}


class AMATISTA_OT_autor_importar(bpy.types.Operator, ImportHelper):
    bl_idname = "amatista.autor_importar"
    bl_label = "Abrir practice.json"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            with open(self.filepath, encoding="utf-8") as archivo:
                autor.borrador_desde_practica(json.load(archivo))
        except (OSError, ValueError) as error:
            return _error(self, error)
        return {"FINISHED"}


class AMATISTA_OT_autor_exportar(bpy.types.Operator, ExportHelper):
    bl_idname = "amatista.autor_exportar"
    bl_label = "Exportar practice.json"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        datos = autor.leer_borrador() or {}
        self.filepath = (datos.get("id") or "practica").replace(".", "_") + ".json"
        return super().invoke(context, event)

    def execute(self, context):
        try:
            autor.exportar(self.filepath)
        except (OSError, ValueError) as error:
            return _error(self, error)
        self.report({"INFO"}, f"Exportada: {self.filepath}")
        return {"FINISHED"}


class AMATISTA_OT_autor_probar(bpy.types.Operator):
    bl_idname = "amatista.autor_probar"
    bl_label = "Validar práctica"
    bl_description = "Compila el borrador y lo evalúa con la escena actual (Live Validation)"

    def execute(self, context):
        try:
            resultado = autor.probar_borrador(context)
        except ValueError as error:
            return _error(self, error)
        reporte = practicas.ESTADO["reporte"]
        self.report({"INFO"}, f"Compilada con {len(resultado.warnings)} aviso(s). Progreso simulado: {reporte.progress:.0f} %")
        return {"FINISHED"}


class AMATISTA_OT_autor_vista_previa(bpy.types.Operator):
    bl_idname = "amatista.autor_vista_previa"
    bl_label = "Vista previa como alumno"
    bl_description = "Muestra el borrador exactamente como lo verá un alumno"

    def execute(self, context):
        try:
            autor.probar_borrador(context)
        except ValueError as error:
            return _error(self, error)
        context.window_manager.amatista.vista_previa = True
        return {"FINISHED"}


class AMATISTA_OT_declarar_rol(bpy.types.Operator):
    bl_idname = "amatista.declarar_rol"
    bl_label = "Declarar rol"
    bl_description = "Agrega el rol al catálogo de la práctica para que el Tagger lo ofrezca"

    def execute(self, context):
        a = context.scene.amatista_autor
        if not a.nuevo_rol.strip():
            return _error(self, "Escribe el id del rol (por ejemplo «pata»).")
        if autor.leer_borrador() is None:
            return _error(self, "Primero crea un borrador.")
        rol = autor.asegurar_rol(a.nuevo_rol, a.nuevo_rol_etiqueta)
        try:
            context.scene.amatista.rol_elegido = rol
        except TypeError:  # la lista de roles viene de la práctica abierta, no del borrador
            pass
        a.nuevo_rol = ""
        a.nuevo_rol_etiqueta = ""
        return {"FINISHED"}


class AMATISTA_OT_agregar_etiqueta(bpy.types.Operator):
    bl_idname = "amatista.agregar_etiqueta"
    bl_label = "Etiquetar"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        etiqueta = context.scene.amatista_autor.etiqueta
        for obj in context.selected_objects or [context.active_object]:
            _motor.tagger.add_tag(obj, etiqueta)
        context.scene.amatista_autor.etiqueta = ""
        return {"FINISHED"}


class AMATISTA_OT_quitar_etiqueta(bpy.types.Operator):
    bl_idname = "amatista.quitar_etiqueta"
    bl_label = "Quitar etiqueta"
    bl_options = {"REGISTER", "UNDO"}

    etiqueta: bpy.props.StringProperty()

    def execute(self, context):
        if context.active_object:
            _motor.tagger.remove_tag(context.active_object, self.etiqueta)
        return {"FINISHED"}


class AMATISTA_OT_autor_rango_desde_objeto(bpy.types.Operator):
    bl_idname = "amatista.autor_rango_desde_objeto"
    bl_label = "Usar sus medidas"
    bl_description = "Llena mínimo y máximo del constructor con la medida del objeto activo (±25 %)"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        a = context.scene.amatista_autor
        indice = "xyz".index(a.obj_eje)
        valor = float(context.active_object.dimensions[indice])
        a.obj_minimo = round(valor * 0.75, 3)
        a.obj_maximo = round(valor * 1.25, 3)
        rol = _motor.tagger.get_role(context.active_object)
        if rol:
            try:
                a.obj_rol = rol
            except TypeError:
                pass
        return {"FINISHED"}


class AMATISTA_OT_autor_agregar_objetivo(bpy.types.Operator):
    bl_idname = "amatista.autor_agregar_objetivo"
    bl_label = "Agregar objetivo"

    def execute(self, context):
        try:
            objetivo = autor.agregar_objetivo(context.scene.amatista_autor)
        except ValueError as error:
            return _error(self, error)
        a = context.scene.amatista_autor
        a.obj_titulo = ""
        a.obj_id = ""
        a.obj_consejo = ""
        a.objetivo = objetivo["id"]
        self.report({"INFO"}, f"Objetivo «{objetivo['id']}» agregado.")
        return {"FINISHED"}


class AMATISTA_OT_autor_quitar_objetivo(bpy.types.Operator):
    bl_idname = "amatista.autor_quitar_objetivo"
    bl_label = "Quitar objetivo"

    objetivo: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        autor.quitar_objetivo(self.objetivo)
        return {"FINISHED"}


class AMATISTA_OT_autor_mover_objetivo(bpy.types.Operator):
    bl_idname = "amatista.autor_mover_objetivo"
    bl_label = "Mover objetivo"

    objetivo: bpy.props.StringProperty()
    paso: bpy.props.IntProperty()

    def execute(self, context):
        autor.mover_objetivo(self.objetivo, self.paso)
        return {"FINISHED"}


class AMATISTA_OT_autor_agregar_pista(bpy.types.Operator):
    bl_idname = "amatista.autor_agregar_pista"
    bl_label = "Agregar pista"

    def execute(self, context):
        a = context.scene.amatista_autor
        try:
            nivel = autor.agregar_pista(a.objetivo, a.pista)
        except ValueError as error:
            return _error(self, error)
        a.pista = ""
        self.report({"INFO"}, f"Pista {nivel} agregada.")
        return {"FINISHED"}


class AMATISTA_OT_autor_quitar_pista(bpy.types.Operator):
    bl_idname = "amatista.autor_quitar_pista"
    bl_label = "Quitar pista"

    objetivo: bpy.props.StringProperty()
    indice: bpy.props.IntProperty()

    def execute(self, context):
        autor.quitar_pista(self.objetivo, self.indice)
        return {"FINISHED"}


class AMATISTA_OT_autor_publicar(bpy.types.Operator):
    bl_idname = "amatista.autor_publicar"
    bl_label = "Subir a Amatista"
    bl_description = "Registra el borrador en Oracle (queda en borrador con su número de versión)"

    def execute(self, context):
        a = context.scene.amatista_autor

        def listo(respuesta, error):
            if error:
                print(f"[Amatista] No se pudo subir la práctica: {error}")
                practicas.ESTADO["red"] = error
            else:
                practicas.ESTADO["red"] = ""
                print(f"[Amatista] Práctica {respuesta['id']} registrada (versión {respuesta['version']}, {respuesta['estado']}).")
            practicas.redibujar()

        try:
            autor.publicar(a.curso_id, a.leccion_id, a.nota, listo)
        except ValueError as error:
            return _error(self, error)
        self.report({"INFO"}, "Subiendo la práctica a Amatista…")
        return {"FINISHED"}


class AMATISTA_OT_autor_verificacion(bpy.types.Operator):
    bl_idname = "amatista.autor_verificacion"
    bl_label = "Registrar verificación"
    bl_description = "Anota en la matriz de compatibilidad el resultado de esta lección en este Blender"

    resultado: bpy.props.StringProperty(default="verificada")

    def execute(self, context):
        a = context.scene.amatista_autor

        def listo(respuesta, error):
            print(f"[Amatista] {'Verificación registrada' if not error else error}")

        autor.registrar_verificacion(a.curso_id, a.leccion_id, self.resultado, a.nota, listo)
        return {"FINISHED"}


class AMATISTA_OT_autor_agregar_pildora(bpy.types.Operator):
    bl_idname = "amatista.autor_agregar_pildora"
    bl_label = "Agregar píldora"
    bl_description = "Agrega una idea de teoría que aparece en el momento elegido"

    def execute(self, context):
        a = context.scene.amatista_autor
        try:
            autor.agregar_pildora("", a.pil_titulo, a.pil_texto, a.pil_disparo, a.pil_objetivo, a.pil_teclas)
        except ValueError as error:
            return _error(self, error)
        a.pil_titulo = a.pil_texto = a.pil_teclas = ""
        return {"FINISHED"}


class AMATISTA_OT_autor_caso_prueba(bpy.types.Operator):
    bl_idname = "amatista.autor_caso_prueba"
    bl_label = "Guardar caso de prueba"
    bl_description = (
        "Guarda la foto de esta escena y lo que el motor dice de ella en «amatista_pruebas.json»: "
        "pruebas sin escribir código (se corren con practicas.py probar)"
    )

    def execute(self, context):
        try:
            espera = autor.caso_de_prueba(context, context.scene.amatista_autor.caso_nombre)
        except ValueError as error:
            return _error(self, error)
        resumen = "completada" if espera.get("completada") else f"paso actual: {espera.get('actual', '—')}"
        self.report({"INFO"}, f"Caso guardado ({resumen}). Cópialo a pruebas.json de la práctica.")
        return {"FINISHED"}


CLASES = (
    AMATISTA_OT_autor_agregar_pildora,
    AMATISTA_OT_autor_caso_prueba,
    AMATISTA_OT_autor_nuevo,
    AMATISTA_OT_autor_desde_activa,
    AMATISTA_OT_autor_importar,
    AMATISTA_OT_autor_exportar,
    AMATISTA_OT_autor_probar,
    AMATISTA_OT_autor_vista_previa,
    AMATISTA_OT_declarar_rol,
    AMATISTA_OT_agregar_etiqueta,
    AMATISTA_OT_quitar_etiqueta,
    AMATISTA_OT_autor_rango_desde_objeto,
    AMATISTA_OT_autor_agregar_objetivo,
    AMATISTA_OT_autor_quitar_objetivo,
    AMATISTA_OT_autor_mover_objetivo,
    AMATISTA_OT_autor_agregar_pista,
    AMATISTA_OT_autor_quitar_pista,
    AMATISTA_OT_autor_publicar,
    AMATISTA_OT_autor_verificacion,
)
