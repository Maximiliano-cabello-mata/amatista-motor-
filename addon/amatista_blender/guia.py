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
        ESTADO["avisos"] = []
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
    objetos = [bpy.data.objects[n] for n in nombres if n in bpy.data.objects]
    if not objetos:
        return []
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in context.view_layer.objects:
        obj.select_set(False)
    for obj in objetos:
        obj.hide_set(False)
        obj.select_set(True)
    context.view_layer.objects.active = objetos[0]
    return objetos


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
        return "Agregamos un cubo. Ahora dile a Amatista qué es."

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


def _num(valor):
    if valor is None:
        return ""
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto or "0"
