"""La misión de ahora (Amatista Motor 4): una cosa a la vez, con animación y herramientas iluminadas.

Después de cada evaluación el motor arma la ruta (engine/amatista_engine/ruta):
la práctica en misiones, una sola explicada. Aquí se guarda lo que la
interfaz necesita para que eso se sienta vivo:

- Animaciones: la tarjeta entra deslizándose cuando empieza una misión, la
  misión cumplida se celebra con un sello y chispas, y la tecla que toca
  pulsar «respira» unos segundos. Todo con un temporizador que solo corre
  mientras hay algo animándose (no redibuja Blender sin motivo).
- Teclas que se encienden: Amatista mira los operadores que usa el alumno
  (G, S, Shift+A…) y marca como hecho el micro paso que los usa.
- Herramienta lista: en los niveles 1 y 2, al empezar una misión se elige
  su herramienta en la barra T de Blender (Mover, Escalar, Extruir…), así
  Blender mismo la ilumina y muestra su manipulador.

Nada de esto evalúa la escena: lee la ruta que dejó practicas.evaluar.
"""
import time

import bpy

from . import _motor, ajustes

ESTADO = {
    "ruta": None,
    "mision": None,  # id de la misión actual
    "practica": None,
    "inicio": 0.0,  # cuándo empezó la misión actual (animación de entrada)
    "logro": None,  # {"texto", "numero", "hasta", "inicio"}: la misión cumplida que se celebra
    "pulso_hasta": 0.0,  # la tecla que toca «respira» hasta este momento
    "operadores": set(),  # punteros de operadores ya vistos
    "usadas": set(),  # herramientas usadas en esta misión (ids del catálogo)
    "herramienta_puesta": None,  # misión para la que ya se eligió la herramienta de la barra T
}

ENTRADA = 0.45  # s: la tarjeta entra deslizándose
LOGRO = 1.6  # s: sello «¡Misión cumplida!» y chispas
PULSO = 8.0  # s: la tecla que toca respira

# Operador de Blender → herramienta del catálogo (tools/catalogo.json).
OPERADORES = {
    "TRANSFORM_OT_translate": "transform.move",
    "TRANSFORM_OT_rotate": "transform.rotate",
    "TRANSFORM_OT_resize": "transform.scale",
    "OBJECT_OT_duplicate_move": "object.duplicate",
    "OBJECT_OT_duplicate_move_linked": "object.duplicate",
    "OBJECT_OT_delete": "object.delete",
    "OBJECT_OT_editmode_toggle": "mesh.edit",
    "OBJECT_OT_mode_set": "mesh.edit",
    "MESH_OT_extrude_region_move": "mesh.extrude",
    "MESH_OT_extrude_context_move": "mesh.extrude",
    "MESH_OT_extrude_region_shrink_fatten": "mesh.extrude",
    "MESH_OT_loopcut_slide": "mesh.loopcut",
    "MESH_OT_merge": "mesh.merge",
    "MESH_OT_remove_doubles": "mesh.merge",
    "WM_OT_save_mainfile": "file.save",
    "WM_OT_save_as_mainfile": "file.save",
    "OBJECT_OT_move_to_collection": "collection.move",
    "OBJECT_OT_light_add": "light.add",
    "OBJECT_OT_camera_add": "camera.add",
    "RENDER_OT_render": "render.f12",
    "VIEW3D_OT_view_axis": "view.numpad",
    "MATERIAL_OT_new": "material.basic",
    "ANIM_OT_keyframe_insert": "anim.keyframe",
    "ANIM_OT_keyframe_insert_menu": "anim.keyframe",
    "ANIM_OT_keyframe_insert_by_name": "anim.keyframe",
}
MODIFICADORES = {"BEVEL": "modifier.bevel", "MIRROR": "modifier.mirror", "ARRAY": "modifier.array",
                 "SOLIDIFY": "modifier.solidify", "SUBSURF": "modifier.subdivision", "BOOLEAN": "modifier.boolean"}


def ruta():
    return ESTADO["ruta"]


def reiniciar():
    ESTADO.update(ruta=None, mision=None, practica=None, inicio=0.0, logro=None, pulso_hasta=0.0,
                  usadas=set(), herramienta_puesta=None)
    ESTADO["operadores"] = _punteros()


def animaciones():
    p = ajustes.prefs()
    return p is None or getattr(p, "animaciones", True)


# --- Después de cada evaluación ---------------------------------------------------------------


def actualizar(context, practica, reporte, guia_actual, pistas=None, motivo="cambio"):
    """Arma la ruta con el motor y dispara las animaciones si cambió la misión."""
    anterior = ESTADO["mision"] if ESTADO["practica"] == practica.id else None
    nueva = _motor.MOTOR.route(practica, reporte, guia_actual, pistas or {}, anterior)
    ESTADO["ruta"] = nueva
    ahora = time.time()
    actual = nueva.mision.id if nueva.mision is not None else None
    if ESTADO["practica"] != practica.id:
        ESTADO.update(practica=practica.id, mision=actual, inicio=ahora, logro=None, pulso_hasta=ahora + PULSO,
                      usadas=set(), herramienta_puesta=None)
        ESTADO["operadores"] = _punteros()
        preparar_herramienta(context, practica)
        animar()
        return nueva
    if actual != ESTADO["mision"]:
        if nueva.celebracion or (nueva.completada and anterior):
            previa = next((m for m in nueva.misiones if m.id == anterior), None)
            ESTADO["logro"] = {
                "texto": "¡Práctica completada!" if nueva.completada else nueva.celebracion,
                "numero": previa.numero if previa is not None else 0,
                "inicio": ahora,
                "hasta": ahora + LOGRO,
            }
        ESTADO.update(mision=actual, inicio=ahora + (0.35 if ESTADO["logro"] else 0.0),
                      pulso_hasta=ahora + PULSO, usadas=set())
        ESTADO["operadores"] = _punteros()
        if motivo != "abrir":
            preparar_herramienta(context, practica)
        animar()
    return nueva


# --- Lo que el alumno usa -----------------------------------------------------------------------


def _punteros():
    try:
        return {op.as_pointer() for op in bpy.context.window_manager.operators}
    except (AttributeError, ReferenceError):
        return set()


def _herramienta_de(op):
    nombre = op.bl_idname
    if nombre.startswith("MESH_OT_primitive_") or nombre == "OBJECT_OT_add":
        return "object.add"
    if nombre == "OBJECT_OT_modifier_add":
        try:
            return MODIFICADORES.get(op.properties.type)
        except (AttributeError, ReferenceError):
            return None
    return OPERADORES.get(nombre)


def observar():
    """Marca las herramientas que el alumno usó desde que empezó la misión. True si hubo algo nuevo."""
    try:
        operadores = list(bpy.context.window_manager.operators)
    except (AttributeError, ReferenceError):
        return False
    nuevo = False
    vistos = ESTADO["operadores"]
    for op in operadores:
        puntero = op.as_pointer()
        if puntero in vistos:
            continue
        vistos.add(puntero)
        herramienta = _herramienta_de(op)
        if herramienta and herramienta not in ESTADO["usadas"]:
            ESTADO["usadas"].add(herramienta)
            nuevo = True
    if nuevo:
        animar()
    return nuevo


def marcar_usada(herramienta_id):
    """«Usar» y «Hazlo conmigo» cuentan como usar la herramienta."""
    if herramienta_id:
        ESTADO["usadas"].add(herramienta_id)


def _teclas_de(herramienta_id):
    registro = _motor.MOTOR.tools
    h = registro.get(herramienta_id) if registro is not None else None
    return {k.lower() for k in h.keys} if h is not None else set()


def paso_hecho(paso):
    """¿El alumno ya usó la herramienta de este micro paso (sus teclas)?"""
    if not paso.keys:
        return False
    combos = _motor.herramientas.registry._combos(paso.keys)
    return any(combos & _teclas_de(h) for h in ESTADO["usadas"])


def paso_siguiente(m):
    """Índice del primer micro paso sin hacer (la tecla que «respira»), o None."""
    if m is None:
        return None
    return next((i for i, p in enumerate(m.pasos) if p.keys and not paso_hecho(p)), None)


def estado_herramienta(herramienta_id):
    """ahora | mision | usada | despues | antes: cómo se dibuja en el cinturón de herramientas.

    ahora: la del micro paso que toca (brilla) · mision: otra de esta misión ·
    usada: ya la usaste en esta misión · antes: de una misión ya hecha ·
    despues: la usarás más adelante (solo el borde).
    """
    r = ESTADO["ruta"]
    if r is None:
        return "despues"
    m = r.mision
    if m is not None and herramienta_id in m.herramientas:
        if herramienta_id in ESTADO["usadas"]:
            return "usada"
        siguiente = paso_siguiente(m)
        if siguiente is None:
            return "ahora"
        combos = _motor.herramientas.registry._combos(m.pasos[siguiente].keys)
        # La del micro paso que toca brilla; las otras de la misión quedan encendidas a medias.
        return "ahora" if combos & _teclas_de(herramienta_id) else "mision"
    if herramienta_id in ESTADO["usadas"]:
        return "usada"
    actual = m.numero if m is not None else r.total + 1
    for otra in r.misiones:
        if herramienta_id in otra.herramientas:
            return "antes" if otra.numero < actual else "despues"
    return "despues"


# --- La herramienta lista en la barra T -----------------------------------------------------------


def _vista_3d(context):
    for ventana in context.window_manager.windows:
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                return ventana, area, region
    return None, None, None


def herramienta_de_barra(m, modo):
    """La primera herramienta de la misión que vive en la barra T y sirve en este modo."""
    registro = _motor.MOTOR.tools
    if registro is None or m is None:
        return None
    for hid in m.herramientas:
        h = registro.get(hid)
        accion = (h.action or {}) if h is not None else {}
        if "tool" not in accion:
            continue
        if accion.get("mode") == "EDIT" and modo != "EDIT_MESH":
            continue
        return h
    return None


def preparar_herramienta(context, practica):
    """Niveles 1 y 2: elige en la barra T la herramienta de la misión (Blender la ilumina)."""
    p = ajustes.prefs()
    r = ESTADO["ruta"]
    if r is None or r.mision is None or bpy.app.background:
        return None
    if p is not None and not getattr(p, "preparar_herramienta", True):
        return None
    if practica.level > 2 or ESTADO["herramienta_puesta"] == r.mision.id:
        return None
    h = herramienta_de_barra(r.mision, context.mode)
    if h is None:
        return None
    ventana, area, region = _vista_3d(context)
    if area is None:
        return None
    try:
        with context.temp_override(window=ventana, area=area, region=region):
            bpy.ops.wm.tool_set_by_id(name=h.action["tool"])
    except (RuntimeError, TypeError) as error:
        print(f"[Amatista] No se pudo elegir la herramienta {h.id}: {error}")
        return None
    ESTADO["herramienta_puesta"] = r.mision.id
    return h.id


# --- Animación --------------------------------------------------------------------------------------


def suave(t):
    """Curva «ease out»: arranca rápido y llega suave (0..1 → 0..1)."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def entrada():
    """0..1: cuánto entró la tarjeta de la misión actual."""
    if not animaciones():
        return 1.0
    return suave((time.time() - ESTADO["inicio"]) / ENTRADA)


def logro():
    """(datos, 0..1) de la celebración en curso, o (None, 1). Sin animaciones no hay sello."""
    datos = ESTADO["logro"]
    if datos is None or not animaciones():
        return None, 1.0
    ahora = time.time()
    if ahora >= datos["hasta"]:
        ESTADO["logro"] = None
        return None, 1.0
    return datos, max(0.0, (ahora - datos["inicio"]) / (datos["hasta"] - datos["inicio"]))


def pulso():
    """0..1 que sube y baja (≈1 Hz) mientras la tecla que toca respira; 1 fijo después."""
    if not animaciones() or time.time() > ESTADO["pulso_hasta"]:
        return 1.0
    import math

    return 0.5 + 0.5 * math.sin(time.time() * 2 * math.pi * 0.9)


def _en_curso():
    ahora = time.time()
    if ESTADO["logro"] is not None and ahora < ESTADO["logro"]["hasta"]:
        return 1 / 30
    if ahora < ESTADO["inicio"] + ENTRADA:
        return 1 / 30
    if ahora < ESTADO["pulso_hasta"]:
        return 1 / 8
    return None


def _paso():
    from . import practicas

    try:
        sc = bpy.context.scene
        if sc is None or not sc.amatista.practica_json:
            return None
    except (AttributeError, ReferenceError):
        return None
    practicas.redibujar()
    siguiente = _en_curso()
    if siguiente is None:
        practicas.redibujar()  # el último cuadro, ya quieto
    return siguiente


def animar():
    if bpy.app.background or not animaciones():
        return
    if not bpy.app.timers.is_registered(_paso):
        bpy.app.timers.register(_paso, first_interval=0.01)


def unregister():
    if bpy.app.timers.is_registered(_paso):
        bpy.app.timers.unregister(_paso)
    reiniciar()
