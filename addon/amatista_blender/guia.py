"""Acompañante de Amatista dentro de Blender (etapa 2 del motor).

Después de cada evaluación:
    1. El motor arma la guía del paso actual (qué hacer, teclas, qué mirar).
    2. El acompañante decide si hay algo que decir (paso logrado, nuevo
       paso, «vas mejor», retroceso, «¿te ayudo?»).
    3. Aquí se convierte en avisos breves sobre la vista 3D (se desvanecen
       solos) o en un diálogo, según la preferencia «Acompañamiento».

«Hazlo conmigo» arranca la herramienta correcta de Blender sobre el objeto
correcto (por ejemplo Escalar restringido a Z sobre la cubierta) y el
alumno la termina con el ratón o escribiendo el número que muestra la guía.
Usarlo cuenta como guía paso a paso (nivel 3 de pistas) para la autonomía.
"""
import time

import bpy

from . import _motor, ajustes

# Estado de la sesión (no se guarda en el .blend).
ESTADO = {
    "guia": None,
    "practica": None,
    "companion": None,
    "avisos": [],  # [{titulo, texto, tono, hasta}]
    "ayudas": {"hazlo_conmigo": 0, "mostrarme": 0, "explicar": 0},
}

DURACION_AVISO = 5.0
MAX_AVISOS = 3

NIVEL_ACOMPANADO = "acompanado"
NIVEL_TARJETA = "tarjeta"
NIVEL_SILENCIOSO = "silencioso"


def nivel():
    p = ajustes.prefs()
    return p.acompanamiento if p else NIVEL_ACOMPANADO


def guia_actual():
    return ESTADO["guia"]


def reiniciar():
    ESTADO.update(guia=None, practica=None, companion=None, avisos=[])
    ESTADO["ayudas"] = {"hazlo_conmigo": 0, "mostrarme": 0, "explicar": 0}


def _companion(practica_id):
    if ESTADO["practica"] != practica_id or ESTADO["companion"] is None:
        p = ajustes.prefs()
        ESTADO["companion"] = _motor.guia.Companion(
            help_after_tries=p.ayuda_tras_intentos if p else 4,
            help_after_seconds=float(p.ayuda_tras_segundos if p else 120),
        )
        ESTADO["practica"] = practica_id
        # Los avisos no se borran aquí: los de «Práctica nueva, escena nueva» y «Escena lista»
        # llegan justo antes de esta primera evaluación (guia.reiniciar ya limpió los de antes).
    return ESTADO["companion"]


def avisar(titulo, texto="", tono="animo"):
    """Aviso breve sobre la vista 3D (la tarjeta del HUD lo dibuja y se desvanece)."""
    ESTADO["avisos"] = (ESTADO["avisos"] + [{"titulo": titulo, "texto": texto, "tono": tono,
                                             "hasta": time.time() + DURACION_AVISO}])[-MAX_AVISOS:]
    _animar()


def avisos_vigentes():
    ahora = time.time()
    ESTADO["avisos"] = [a for a in ESTADO["avisos"] if a["hasta"] > ahora]
    return ESTADO["avisos"]


def _animar():
    """Redibuja la vista 3D mientras haya avisos (para que se desvanezcan)."""
    if bpy.app.background or bpy.app.timers.is_registered(_paso_animacion):
        return
    bpy.app.timers.register(_paso_animacion, first_interval=0.1)


def unregister():
    if bpy.app.timers.is_registered(_paso_animacion):
        bpy.app.timers.unregister(_paso_animacion)


def _paso_animacion():
    from . import practicas

    practicas.redibujar()
    return 0.1 if avisos_vigentes() else None


TONO_INTERVENCION = {
    "paso_logrado": "logrado",
    "nuevo_paso": "animo",
    "mejorando": "cerca",
    "retroceso": "ojo",
    "ofrecer_ayuda": "animo",
    "practica_completa": "logrado",
    "pausa": "ojo",
    "reanuda": "logrado",
}


def actualizar(context, practica, foto, reporte, motivo="cambio"):
    """Recalcula la guía y procesa lo que el acompañante quiera decir."""
    guia = _motor.guia.build_guidance(practica, foto, reporte)
    ESTADO["guia"] = guia
    intervenciones = _companion(practica.id).observe(practica, reporte, time.time())
    modo = nivel()
    if modo == NIVEL_SILENCIOSO:
        return intervenciones
    from . import practicas

    p = ajustes.prefs()
    for i in intervenciones:
        if i.kind == "practica_completa":
            continue  # la felicitación ya es un diálogo propio (practicas.evaluar)
        if i.kind == "pausa" and modo == NIVEL_ACOMPANADO:
            practicas._invocar("amatista.pausa")
            continue
        if i.kind == "ofrecer_ayuda":
            if modo == NIVEL_ACOMPANADO:
                practicas._invocar("amatista.ofrecer_ayuda")
            else:
                avisar(i.title, "Pulsa «¿Cómo lo hago?» en la pestaña Amatista.", "animo")
            continue
        if i.kind == "nuevo_paso" and modo == NIVEL_ACOMPANADO and (p is None or p.explicar_pasos) and motivo != "abrir":
            practicas._invocar("amatista.explicar_paso")
            continue
        avisar(i.title, i.text, TONO_INTERVENCION.get(i.kind, "animo"))
    return intervenciones


# --- «Hazlo conmigo» ------------------------------------------------------------------


def _ventana_3d(context):
    """(área, región) de la vista 3D para arrancar herramientas interactivas."""
    area = context.area if context.area and context.area.type == "VIEW_3D" else None
    if area is None and context.window:
        area = next((a for a in context.window.screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        return None, None
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    return area, region


def seleccionar(context, nombres):
    # Solo lo que está en la capa de vista: un objeto en una colección excluida (o de otra
    # escena) no se puede seleccionar y Blender lanza RuntimeError.
    visibles = context.view_layer.objects
    objetos = [visibles[n] for n in nombres if n in visibles]
    if not objetos:
        return []
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in visibles:
        try:
            obj.select_set(False)
        except RuntimeError:
            pass
    elegidos = []
    for obj in objetos:
        try:
            obj.hide_set(False)
            obj.select_set(True)
            elegidos.append(obj)
        except RuntimeError:
            continue
    if elegidos:
        context.view_layer.objects.active = elegidos[0]
    return elegidos


def encuadrar(context):
    area, region = _ventana_3d(context)
    if area is None or bpy.app.background:
        return
    with context.temp_override(area=area, region=region):
        try:
            bpy.ops.view3d.view_selected(use_all_regions=False)
        except RuntimeError:
            pass


def registrar_ayuda(context, target_id, tipo, nivel_pista):
    """Cuenta la ayuda y la refleja en las pistas (la autonomía la toma en cuenta)."""
    import json

    from . import practicas

    ESTADO["ayudas"][tipo] = ESTADO["ayudas"].get(tipo, 0) + 1
    if not target_id:
        return
    estado = practicas.pistas(context)
    if estado.get(target_id, 0) < nivel_pista:
        estado[target_id] = nivel_pista
        practicas.escena(context).amatista.pistas_json = json.dumps(estado)


def _restriccion(eje):
    return tuple(e == eje for e in "xyz")


def ejecutar_accion(context, accion, interactivo=True):
    """Lleva a cabo la GuideAction. Devuelve el texto para el aviso o None si no aplica."""
    from . import practicas

    tipo = accion.kind
    if tipo == "save":
        if bpy.data.filepath:
            bpy.ops.wm.save_mainfile()
            return "Guardado."
        if interactivo and not bpy.app.background:
            bpy.ops.wm.save_as_mainfile("INVOKE_DEFAULT")
            return "Elige un nombre y pulsa Guardar."
        return None
    if tipo == "add_cube":
        area, region = _ventana_3d(context)
        if area is not None and not bpy.app.background:
            with context.temp_override(area=area, region=region):
                bpy.ops.mesh.primitive_cube_add()
        else:
            bpy.ops.mesh.primitive_cube_add()
        practica = practicas.practica_activa(context)
        if practica is not None and practica.infers_roles:
            return "Agregamos un cubo: Amatista lo reconoce por su forma. Dale la forma del modelo con S y G."
        if accion.role and context.active_object is not None:
            # El rol venía en la acción y no se ponía: el alumno tenía que asignarlo a mano.
            _motor.tagger.assign_role(context.active_object, accion.role)
            return f"Agregamos un cubo y ya es «{practica.role_label(accion.role) if practica else accion.role}»."
        return "Agregamos un cubo. Ahora dile a Amatista qué es."

    texto = _accion_v3(context, accion, interactivo)
    if texto is not None:
        return texto

    objetos = seleccionar(context, accion.objects)
    if not objetos:
        return None
    if tipo == "assign_role" and accion.role:
        for obj in objetos:
            _motor.tagger.assign_role(obj, accion.role)
        practicas.evaluar(context, "rol")
        return f"Listo: «{objetos[0].name}» ahora es {accion.role}."
    if tipo == "focus":
        encuadrar(context)
        return "Ese es el objeto: revisa la tarjeta para ver qué falta."
    if tipo == "apply_scale":
        if interactivo and not bpy.app.background:
            bpy.ops.wm.call_menu(name="VIEW3D_MT_object_apply")
            return "Elige «Escala» en el menú."
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return "Escala aplicada."

    eje = accion.axis
    valor = accion.value
    area, region = _ventana_3d(context)
    if interactivo and area is not None and not bpy.app.background:
        encuadrar(context)
        with context.temp_override(area=area, region=region):
            if tipo == "duplicate":
                bpy.ops.object.duplicate_move("INVOKE_DEFAULT")
                return "Mueve la copia con el ratón y haz clic para dejarla."
            if tipo == "scale":
                bpy.ops.transform.resize("INVOKE_DEFAULT", constraint_axis=_restriccion(eje), orient_type="GLOBAL")
                return f"Mueve el ratón o escribe {_num(valor)} y pulsa Enter."
            if tipo == "move":
                restriccion = _restriccion(eje) if eje else (True, True, False)
                bpy.ops.transform.translate("INVOKE_DEFAULT", constraint_axis=restriccion, orient_type="GLOBAL")
                return f"Mueve el ratón o escribe {_num(valor)} y pulsa Enter." if valor is not None else "Mueve y haz clic."
            if tipo == "rotate":
                bpy.ops.transform.rotate("INVOKE_DEFAULT", orient_axis=(eje or "z").upper(), orient_type="GLOBAL")
                return f"Gira con el ratón o escribe {_num(valor)} y pulsa Enter."
        return None
    # Sin ventana (pruebas, Blender en segundo plano): se aplica el valor sugerido.
    if tipo == "duplicate":
        bpy.ops.object.duplicate()
        return "Copia creada."
    if tipo == "scale" and valor:
        escala = [1.0, 1.0, 1.0]
        escala["xyz".index(eje or "z")] = valor
        bpy.ops.transform.resize(value=tuple(escala), orient_type="GLOBAL")
        return "Escalado."
    if tipo == "move" and valor is not None:
        delta = [0.0, 0.0, 0.0]
        delta["xyz".index(eje or "z")] = valor
        bpy.ops.transform.translate(value=tuple(delta), orient_type="GLOBAL")
        return "Movido."
    if tipo == "rotate" and valor is not None:
        import math

        bpy.ops.transform.rotate(value=math.radians(valor), orient_axis=(eje or "z").upper(), orient_type="GLOBAL")
        return "Girado."
    return None


# --- Acciones del motor v3 ------------------------------------------------------------------

PRIMITIVAS = {
    "cube": ("primitive_cube_add", "un cubo"), "cylinder": ("primitive_cylinder_add", "un cilindro"),
    "sphere": ("primitive_uv_sphere_add", "una esfera"), "plane": ("primitive_plane_add", "un plano"),
    "cone": ("primitive_cone_add", "un cono"), "torus": ("primitive_torus_add", "una dona"),
    "icosphere": ("primitive_ico_sphere_add", "una icoesfera"), "suzanne": ("primitive_monkey_add", "a Suzanne"),
}
PESTANAS = {
    "MODIFIER": "MODIFIER", "MATERIAL": "MATERIAL", "RENDER": "RENDER", "OUTPUT": "OUTPUT", "DATA": "DATA",
    "OBJECT": "OBJECT", "WORLD": "WORLD", "SCENE": "SCENE",
}
MOTORES = {"EEVEE": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"), "CYCLES": ("CYCLES",), "WORKBENCH": ("BLENDER_WORKBENCH",)}


def _en_vista(context, operador, *args, **kwargs):
    """Ejecuta un operador en la vista 3D si hay ventana (los de malla y vista lo necesitan)."""
    area, region = _ventana_3d(context)
    if area is not None and not bpy.app.background:
        with context.temp_override(area=area, region=region):
            return operador(*args, **kwargs)
    return operador(*args, **kwargs)


def abrir_pestana(context, pestana):
    """Cambia el editor Propiedades a una pestaña (Modificadores, Material, Render…)."""
    pestana = PESTANAS.get(str(pestana or "").upper())
    if pestana is None or context.window is None:
        return False
    for area in context.window.screen.areas:
        if area.type == "PROPERTIES":
            espacio = area.spaces.active
            try:
                espacio.context = pestana
            except TypeError:
                return False
            area.tag_redraw()
            return True
    return False


def _activo(context, nombres):
    objetos = seleccionar(context, nombres) if nombres else []
    return objetos[0] if objetos else context.active_object


def _accion_v3(context, accion, interactivo):
    """Acciones nuevas del motor v3. None si la acción no es de este grupo (o no aplica)."""
    tipo = accion.kind
    if tipo == "show_example":
        from . import ejemplo

        return ejemplo.ver_ejemplo(context)
    if tipo == "add_primitive":
        operador, nombre = PRIMITIVAS.get(accion.primitive or "cube", PRIMITIVAS["cube"])
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        _en_vista(context, getattr(bpy.ops.mesh, operador))
        if accion.role and context.active_object is not None:
            _motor.tagger.assign_role(context.active_object, accion.role)
        return f"Agregamos {nombre} en el cursor 3D."
    if tipo == "open_tab":
        if accion.objects:
            seleccionar(context, accion.objects)
        if abrir_pestana(context, accion.tab):
            return "Mira el panel Propiedades (a la derecha): ya está en la pestaña correcta."
        return "Abre el panel Propiedades: está a la derecha, debajo del Outliner."
    if tipo in ("edit_mode", "object_mode", "merge_by_distance"):
        obj = _activo(context, accion.objects)
        if obj is None or obj.type != "MESH":
            return None if tipo != "object_mode" else "Ya estás en Modo Objeto."
        if tipo == "object_mode":
            bpy.ops.object.mode_set(mode="OBJECT")
            return "Volviste a Modo Objeto."
        estaba_en_edicion = context.mode == "EDIT_MESH"
        bpy.ops.object.mode_set(mode="EDIT")
        if tipo == "edit_mode":
            return "Estás en Modo Edición: 1, 2 y 3 eligen vértices, aristas o caras."
        bpy.ops.mesh.select_all(action="SELECT")
        antes = len(obj.data.vertices)
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.object.mode_set(mode="OBJECT")
        quitados = antes - len(obj.data.vertices)
        if estaba_en_edicion:
            bpy.ops.object.mode_set(mode="EDIT")
        return f"Fusionamos {quitados} vértices encimados. Tu progreso sigue." if quitados else "La malla ya estaba limpia."
    if tipo == "apply_all":
        obj = _activo(context, accion.objects)
        if obj is None:
            return None
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        return "Rotación y escala aplicadas."
    if tipo == "add_modifier":
        obj = _activo(context, accion.objects)
        if obj is None or not accion.modifier:
            return None
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        mod = obj.modifiers.new(accion.modifier.title(), accion.modifier)
        if accion.modifier == "SUBSURF":
            mod.levels = 2
        if accion.modifier == "MIRROR":
            mod.use_clip = True
        abrir_pestana(context, "MODIFIER")
        return f"Agregamos el modificador a «{obj.name}». Míralo en la llave inglesa."
    if tipo == "add_light":
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        _en_vista(context, bpy.ops.object.light_add, type=accion.light_type or "AREA")
        luz = context.active_object
        if luz is not None and luz.type == "LIGHT":
            luz.data.energy = 300.0 if luz.data.type == "AREA" else luz.data.energy
        if interactivo and not bpy.app.background:
            _en_vista(context, bpy.ops.transform.translate, "INVOKE_DEFAULT")
            return "Mueve la luz con el ratón y haz clic para dejarla. Luego R para apuntarla."
        return "Agregamos una luz en el cursor 3D."
    if tipo == "add_camera":
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        _en_vista(context, bpy.ops.object.camera_add)
        context.scene.camera = context.active_object
        return "Agregamos una cámara y es la activa. Ahora encuádrala con Ctrl+Alt+0."
    if tipo == "align_camera":
        if context.scene.camera is None:
            return None
        area, region = _ventana_3d(context)
        if area is None or bpy.app.background:
            return "Mira tu modelo como quieras fotografiarlo y pulsa Ctrl+Alt+0."
        with context.temp_override(area=area, region=region):
            bpy.ops.view3d.camera_to_view()
        return "La cámara ahora ve lo mismo que tú. Pulsa 0 para comprobarlo."
    if tipo == "set_engine":
        motor = str(accion.option or "EEVEE").upper()
        disponibles = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
        for identificador in MOTORES.get(motor, (motor,)):
            if identificador in disponibles:
                context.scene.render.engine = identificador
                abrir_pestana(context, "RENDER")
                return f"El motor de render ahora es {motor.title()}."
        return None
    if tipo == "render":
        if bpy.app.background:
            bpy.ops.render.render()
            return "Render hecho."
        bpy.ops.render.render("INVOKE_DEFAULT")
        return "Haciendo el render… Imagen › Guardar para conservarlo."
    if tipo == "new_material":
        obj = _activo(context, accion.objects)
        if obj is None or obj.type != "MESH":
            return None
        material = bpy.data.materials.new(f"Material {len(obj.material_slots) + 1}")
        material.use_nodes = True
        obj.data.materials.append(material)
        abrir_pestana(context, "MATERIAL")
        return "Creamos un material nuevo en una ranura. En Edición, elige caras y pulsa Asignar."
    if tipo == "insert_keyframe":
        obj = _activo(context, accion.objects)
        if obj is None:
            return None
        propiedad = accion.option or "location"
        indice = "xyz".index(accion.axis) if accion.axis in ("x", "y", "z") else -1
        obj.keyframe_insert(data_path=propiedad, index=indice)
        return f"Guardamos la clave en el fotograma {context.scene.frame_current}. Avanza, cambia el objeto y repite."
    if tipo == "clear_scene":
        from . import escenarios

        escenarios.vaciar(context.scene)
        return "Quitamos el cubo, la luz y la cámara de inicio."
    return None


def _num(valor):
    if valor is None:
        return ""
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto or "0"
