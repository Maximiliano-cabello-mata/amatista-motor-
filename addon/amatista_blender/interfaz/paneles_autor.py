"""Paneles del modo Desarrollador / Author en la barra lateral de Blender."""
import bpy

from .. import _motor, ajustes, autor, practicas
from . import estilo


class _Autor:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Amatista"
    bl_parent_id = "AMATISTA_PT_principal"

    @classmethod
    def poll(cls, context):
        return (ajustes.es_desarrollador()
                and context.window_manager.amatista.modo == "autor"
                and not context.window_manager.amatista.vista_previa)


class AMATISTA_PT_autor_borrador(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_borrador"
    bl_label = "Borrador de práctica"

    def draw_header(self, context):
        self.layout.label(text="", icon_value=estilo.icono("autor"))

    def draw(self, context):
        layout = self.layout
        a = context.scene.amatista_autor
        datos = autor.leer_borrador()
        if datos is None:
            cuerpo = estilo.tarjeta(layout, "Nueva práctica", icon="ADD")
            cuerpo.prop(a, "nueva_plantilla")
            cuerpo.prop(a, "nuevo_id")
            cuerpo.prop(a, "nuevo_titulo")
            fila = cuerpo.row(align=True)
            fila.prop(a, "nuevo_curso", text="")
            fila.prop(a, "nuevo_modulo")
            cuerpo.prop(a, "nuevo_nivel")
            estilo.boton_principal(cuerpo, "amatista.autor_nuevo", "Crear borrador", icon="ADD", escala=1.3)
            fila = layout.row(align=True)
            fila.operator("amatista.autor_desde_activa", text="Partir de la práctica abierta", icon="DUPLICATE")
            fila.operator("amatista.autor_importar", text="Abrir JSON", icon="FILEBROWSER")
            return
        cuerpo = estilo.tarjeta(layout, datos.get("title", "Sin título"), icono_propio="autor",
                                derecha=f"v{datos.get('version', 1)}")
        info = cuerpo.row()
        info.active = False
        info.label(text=f"{datos.get('id', '?')} · Nivel {datos.get('level', '?')} · "
                        f"{len(datos.get('targets', []))} objetivos · {len(datos.get('roles') or {})} roles")
        estilo.parrafo(cuerpo, context, f"El JSON vive en el Editor de texto: «{a.texto}».", icon="TEXT")
        fila = cuerpo.row(align=True)
        fila.scale_y = 1.3
        fila.operator("amatista.autor_probar", text="Probar en esta escena", icon="PLAY")
        fila.operator("amatista.autor_vista_previa", text="Vista previa", icon="HIDE_OFF")


class AMATISTA_PT_autor_tagger(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_tagger"
    bl_label = "Tagger: roles y etiquetas"

    def draw_header(self, context):
        self.layout.label(text="", icon="BOOKMARKS")

    def draw(self, context):
        layout = self.layout
        a = context.scene.amatista_autor
        obj = context.active_object
        if obj is None:
            layout.label(text="Selecciona un objeto.", icon="RESTRICT_SELECT_OFF")
        else:
            rol = _motor.tagger.get_role(obj)
            cuerpo = estilo.tarjeta(layout, obj.name, icon="OBJECT_DATA", derecha=rol or "Sin rol")
            if practicas.practica_borrador() or practicas.practica_activa(context):
                cuerpo.prop(context.scene.amatista, "rol_elegido", text="Rol")
                fila = cuerpo.row(align=True)
                fila.operator("amatista.asignar_rol", text="Asignar", icon="CHECKMARK")
                fila.operator("amatista.quitar_rol", text="Quitar", icon="X")
            etiquetas = _motor.tagger.get_tags(obj)
            if etiquetas:
                flujo = cuerpo.grid_flow(columns=3, align=True)
                for etiqueta in etiquetas:
                    flujo.operator("amatista.quitar_etiqueta", text=f"#{etiqueta}", icon="X").etiqueta = etiqueta
            fila = cuerpo.row(align=True)
            fila.prop(a, "etiqueta", text="", icon="BOOKMARKS")
            fila.operator("amatista.agregar_etiqueta", text="Etiquetar", icon="ADD")
        caja = estilo.tarjeta(layout, "Declarar un rol nuevo", icon="ADD")
        caja.prop(a, "nuevo_rol", text="Id")
        caja.prop(a, "nuevo_rol_etiqueta", text="Nombre")
        caja.operator("amatista.declarar_rol", icon="CHECKMARK")
        conteo = autor.roles_en_escena(context)
        if conteo:
            col = layout.column(align=True)
            col.label(text="En la escena:", icon="SCENE_DATA")
            for rol, objetos in sorted(conteo.items()):
                col.label(text=f"{rol}: {len(objetos)}  ({', '.join(objetos[:3])}{'…' if len(objetos) > 3 else ''})")


class AMATISTA_PT_autor_inspector(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_inspector"
    bl_label = "Inspector"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.label(text="", icon="VIEWZOOM")

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if obj is None:
            layout.label(text="Selecciona un objeto.", icon="RESTRICT_SELECT_OFF")
            return
        datos = _motor.tagger.inspect_object(obj)
        col = layout.column(align=True)
        col.label(text=f"{datos['name']} · {datos['type']}", icon="OBJECT_DATA")
        col.label(text=f"Rol: {datos['role'] or '—'}   Etiquetas: {', '.join(datos['tags']) or '—'}")
        col.label(text="Dimensiones: X {:.2f}  Y {:.2f}  Z {:.2f}".format(*datos["dimensions"]))
        col.label(text="Posición: X {:.2f}  Y {:.2f}  Z {:.2f}".format(*datos["location"]))
        col.label(text="Escala: X {:.2f}  Y {:.2f}  Z {:.2f}".format(*datos["scale"]))
        if datos["vertices"] is not None:
            col.label(text=f"Malla: {datos['vertices']} vértices · {datos['faces']} caras")
        col.label(text=f"Modificadores: {', '.join(datos['modifiers']) or '—'}")
        col.label(text=f"Materiales: {', '.join(datos['materials']) or '—'}")
        col.label(text=f"Colecciones: {', '.join(datos['collections'])}")
        layout.label(text="Validadores aplicables:", icon="CHECKMARK")
        flujo = layout.column(align=True)
        flujo.active = False
        for spec in _motor.MOTOR.registry.specs():
            if spec.selects or (datos["role"] and spec.param("role")):
                flujo.label(text=f"✓ {spec.id} — {spec.label}")
        layout.operator("amatista.autor_rango_desde_objeto", text="Usar sus medidas en el constructor", icon="DRIVER_DISTANCE")


class AMATISTA_PT_autor_objetivos(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_objetivos"
    bl_label = "Constructor de objetivos"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and autor.leer_borrador() is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="OUTLINER_DATA_GP_LAYER")

    def draw(self, context):
        layout = self.layout
        a = context.scene.amatista_autor
        datos = autor.leer_borrador() or {}
        for objetivo in datos.get("targets", []):
            fila = layout.row(align=True)
            texto = objetivo.get("title") or objetivo.get("id")
            if objetivo.get("optional"):
                texto += " (extra)"
            fila.label(text=texto, icon="DOT")
            fila.label(text=f"{objetivo.get('validator')} · {objetivo.get('weight', 1)}")
            for paso, icono in ((-1, "TRIA_UP"), (1, "TRIA_DOWN")):
                op = fila.operator("amatista.autor_mover_objetivo", text="", icon=icono)
                op.objetivo, op.paso = objetivo.get("id", ""), paso
            fila.operator("amatista.autor_quitar_objetivo", text="", icon="X").objetivo = objetivo.get("id", "")

        cuerpo = estilo.tarjeta(layout, "Nuevo objetivo", icon="ADD")
        cuerpo.prop(a, "plantilla")
        spec = _motor.MOTOR.registry.spec(a.plantilla)
        if spec and spec.description:
            estilo.parrafo(cuerpo, context, spec.description)
        cuerpo.prop(a, "obj_titulo")
        nombres = {p.name for p in spec.params} if spec else set()
        if "role" in nombres:
            cuerpo.prop(a, "obj_rol")
        if "name" in nombres:
            cuerpo.prop(a, "obj_nombre", text="o nombre exacto")
        if "reference_role" in nombres:
            cuerpo.prop(a, "obj_rol_ref")
        if "equals" in nombres:
            cuerpo.prop(a, "obj_cantidad")
        if "axis" in nombres:
            fila = cuerpo.row(align=True)
            fila.prop(a, "obj_eje", expand=True)
            fila = cuerpo.row(align=True)
            fila.prop(a, "obj_minimo")
            fila.prop(a, "obj_maximo")
        if "modifier" in nombres:
            cuerpo.prop(a, "obj_modificador")
        if nombres & {"collection", "contains", "material"}:
            cuerpo.prop(a, "obj_texto", text={"collection": "Colección", "contains": "Contiene"}.get(
                next(iter(nombres & {"collection", "contains", "material"})), "Material"))
        fila = cuerpo.row(align=True)
        fila.prop(a, "obj_peso")
        fila.prop(a, "obj_opcional", toggle=True)
        cuerpo.prop(a, "obj_requiere")
        cuerpo.prop(a, "obj_consejo")
        estilo.boton_principal(cuerpo, "amatista.autor_agregar_objetivo", "Agregar objetivo", icon="ADD", escala=1.3)

        cuerpo = estilo.tarjeta(layout, "Pistas progresivas", icon="LIGHT")
        cuerpo.prop(a, "objetivo")
        objetivo = next((t for t in datos.get("targets", []) if t.get("id") == a.objetivo), None)
        for indice, pista in enumerate((objetivo or {}).get("hints", [])):
            fila = cuerpo.row(align=True)
            fila.label(text=f"{indice + 1}. {pista if isinstance(pista, str) else pista.get('text')}")
            op = fila.operator("amatista.autor_quitar_pista", text="", icon="X")
            op.objetivo, op.indice = a.objetivo, indice
        fila = cuerpo.row(align=True)
        fila.prop(a, "pista", text="")
        fila.operator("amatista.autor_agregar_pista", text="", icon="ADD")


class AMATISTA_PT_autor_depurador(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_depurador"
    bl_label = "Validación y depurador"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and autor.leer_borrador() is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="CONSOLE")

    def draw(self, context):
        layout = self.layout
        resultado = autor.compilar()
        if resultado is None:
            return
        cuerpo = estilo.tarjeta(layout, "Compilador", icon="CHECKMARK" if resultado.ok else "ERROR")
        p = resultado.practice
        if p is not None:
            col = cuerpo.column(align=True)
            col.label(text=f"Práctica: {p.id}   Nivel {p.level}")
            col.label(text=f"Objetivos: {len(p.targets)} · Habilidades: {len(p.skills)} · "
                           f"Validadores: {len({t.validator for t in p.targets})}")
        if resultado.ok:
            for linea in ("Schema válido", "Dependencias válidas y sin ciclos", "Todos los validadores existen",
                          "Pesos de progreso correctos"):
                cuerpo.label(text=linea, icon="CHECKMARK")
        for error in resultado.errors:
            estilo.parrafo(cuerpo, context, error, icon="CANCEL", alerta=True)
        for aviso in resultado.warnings[:8]:
            estilo.parrafo(cuerpo, context, aviso, icon="INFO")
        estilo.boton_principal(layout, "amatista.autor_probar", "Validar con esta escena", icon="PLAY", escala=1.3)
        if context.scene.amatista.origen == "borrador" and practicas.ESTADO["reporte"]:
            from .paneles import _dibujar_detalle

            reporte = practicas.ESTADO["reporte"]
            estilo.barra(layout, reporte.progress / 100.0, f"Progreso simulado: {reporte.progress:.0f} %")
            for r in reporte.results:
                caja = layout.box()
                icono = "CHECKMARK" if r.passed else ("QUESTION" if r.passed is None else "CANCEL")
                caja.label(text=f"{r.target_id}: {'OK' if r.passed else 'FALLA'}", icon=icono)
                estilo.parrafo(caja, context, r.message)
                _dibujar_detalle(caja, context, r)


class AMATISTA_PT_autor_teoria(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_teoria"
    bl_label = "Teoría y casos de prueba"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and autor.leer_borrador() is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="HELP")

    def draw(self, context):
        layout = self.layout
        a = context.scene.amatista_autor
        datos = autor.leer_borrador() or {}
        for pildora in datos.get("pills") or []:
            fila = layout.row()
            disparo = (pildora.get("trigger") or {}).get("on", "start")
            fila.label(text=f"{pildora.get('title', pildora.get('id'))}", icon="LIGHT")
            sub = fila.row()
            sub.alignment = "RIGHT"
            sub.active = False
            sub.label(text=disparo)
        cuerpo = estilo.tarjeta(layout, "Nueva píldora", icon="ADD")
        cuerpo.prop(a, "pil_titulo")
        cuerpo.prop(a, "pil_texto")
        largo = len(a.pil_texto)
        if largo > 280:
            cuerpo.label(text=f"{largo} caracteres: mejor 280 o menos (una sola idea).", icon="ERROR")
        cuerpo.prop(a, "pil_teclas")
        fila = cuerpo.row(align=True)
        fila.prop(a, "pil_disparo", text="")
        if a.pil_disparo in ("target", "guard"):
            fila.prop(a, "pil_objetivo", text="")
        estilo.boton_principal(cuerpo, "amatista.autor_agregar_pildora", "Agregar píldora", icon="ADD", escala=1.2)
        cuerpo = estilo.tarjeta(layout, "Casos de prueba sin código", icon="CHECKBOX_HLT")
        estilo.parrafo(cuerpo, context, "Arma la escena (bien o con un error a propósito) y guárdala como caso: "
                       "practicas.py probar comprueba que el motor responda igual.")
        cuerpo.prop(a, "caso_nombre")
        estilo.boton_principal(cuerpo, "amatista.autor_caso_prueba", "Guardar caso de esta escena", icon="ADD",
                               escala=1.2)


class AMATISTA_PT_autor_publicar(_Autor, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_autor_publicar"
    bl_label = "Exportar y publicar"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return super().poll(context) and autor.leer_borrador() is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="EXPORT")

    def draw(self, context):
        layout = self.layout
        a = context.scene.amatista_autor
        layout.operator("amatista.autor_exportar", text="Exportar practice.json", icon="EXPORT")
        cuerpo = estilo.tarjeta(layout, "Registrar en Amatista", icon="WORLD")
        estilo.parrafo(cuerpo, context, "Se guarda en Oracle como borrador con su historial de versiones. "
                       "Un administrador la publica desde la plataforma.")
        cuerpo.prop(a, "curso_id")
        cuerpo.prop(a, "leccion_id")
        cuerpo.prop(a, "nota")
        p = ajustes.prefs()
        fila = cuerpo.row()
        fila.scale_y = 1.4
        fila.enabled = bool(p and p.token)
        fila.operator("amatista.autor_publicar", text="Subir a Amatista", icon="EXPORT")
        if not (p and p.token):
            cuerpo.label(text="Vincula una cuenta de profesor o administrador.", icon="INFO")
        caja = estilo.tarjeta(layout, "Matriz de compatibilidad", icon="BLENDER")
        estilo.parrafo(caja, context, f"Anota que la lección funciona en Blender {bpy.app.version_string}.")
        fila = caja.row(align=True)
        fila.enabled = bool(p and p.token and a.leccion_id)
        for resultado, texto in (("verificada", "Funciona"), ("con_diferencias", "Con diferencias"), ("falla", "Falla")):
            fila.operator("amatista.autor_verificacion", text=texto).resultado = resultado


CLASES_AUTOR = (
    AMATISTA_PT_autor_borrador,
    AMATISTA_PT_autor_tagger,
    AMATISTA_PT_autor_inspector,
    AMATISTA_PT_autor_objetivos,
    AMATISTA_PT_autor_depurador,
    AMATISTA_PT_autor_teoria,
    AMATISTA_PT_autor_publicar,
)
