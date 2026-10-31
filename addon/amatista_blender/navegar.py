"""Volver a Amatista desde cualquier lado (motor 6.2).

El creador lo encontró probando: «cuando sales del panel de Amatista, no
sabes cómo regresar [...] si yo fuera nuevo, se me dificultaría mucho
regresar a la tarjeta de Amatista». Pasaba al cambiar de escena (el
selector de arriba a la derecha), al abrir otro archivo o al pasar a otra
pestaña de Blender: la tarjeta solo se dibuja en la escena de la actividad,
así que desaparecía sin decir dónde quedó.

Ahora, si hay algo de Amatista en curso y la vista 3D no lo muestra, aparece
abajo al centro una **pastilla «Volver a mi práctica»** (vista/tarjeta.py)
y el botón Amatista de la cabecera cambia a «Volver a Amatista». Un clic:

1. lleva a la escena de lo que estabas haciendo (la actividad del taller, el
   proyecto o la última práctica abierta), en Modo Objeto;
2. pasa al espacio de trabajo «Amatista» con la barra lateral abierta;
3. despierta la tarjeta con «Aquí sigues».

Nunca borra nada ni empieza de nuevo: solo te devuelve.
"""
import bpy

from . import integracion

USADA = "amatista_practica"
USADA_EN = "amatista_practica_en"


def _sesion():
    from .taller import sesion

    return sesion


def destino():
    """(escena, nombre) de lo que Amatista tiene en curso, o (None, "")."""
    try:
        sesion = _sesion()
        a = sesion.actividad()
    except Exception:  # noqa: BLE001 - sin catálogo no hay taller
        sesion, a = None, None
    if a is not None:
        if sesion.SESION["proyecto"]:
            suyas = [s for s in bpy.data.scenes if s.amatista.practica_id == a.practica_id]
            sc = max(suyas, key=lambda s: float(s.get(USADA_EN, 0.0)), default=None)
            return sc, a.titulo
        from .taller import escena

        sc = next((s for s in bpy.data.scenes if escena.es_del_taller(s)), None)
        return sc, a.titulo
    abiertas = [s for s in bpy.data.scenes if s.amatista.practica_json and not s.get("amatista_ejemplo")]
    sc = max(abiertas, key=lambda s: float(s.get(USADA_EN, 0.0)), default=None)
    if sc is None:
        return None, ""
    try:
        from . import practicas

        nombre = practicas._titulo_de(sc.amatista.practica_id)
    except Exception:  # noqa: BLE001
        nombre = sc.name
    return sc, nombre


def hace_falta(context=None):
    """¿Hay algo de Amatista en curso que esta ventana no muestra? (entonces aparece «Volver»)."""
    context = context or bpy.context
    sc = getattr(context, "scene", None)
    if sc is None:
        return False
    if sc.amatista.practica_json:
        return False  # ya estás en una práctica: su tarjeta está aquí
    try:
        if _sesion().cubre(sc):
            return False
    except Exception:  # noqa: BLE001
        pass
    otra, _nombre = destino()
    return otra is not None and otra != sc


def texto_boton():
    _sc, nombre = destino()
    return f"Volver a {nombre}" if nombre and len(nombre) <= 28 else "Volver a mi práctica"


def volver(context=None):
    """Lleva a la escena de lo que estabas haciendo, abre Amatista y despierta la tarjeta."""
    context = context or bpy.context
    sc, nombre = destino()
    if sc is None:
        return "No hay ninguna práctica abierta: elige una lección en la plataforma."
    ventana = getattr(context, "window", None) or getattr(bpy.context, "window", None)
    if ventana is None:
        ventanas = list(getattr(bpy.context.window_manager, "windows", ()) or ())
        ventana = ventanas[0] if ventanas else None
    if ventana is not None and ventana.scene != sc:
        obj = getattr(context, "active_object", None)
        if obj is not None and getattr(obj, "mode", "OBJECT") != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except RuntimeError as error:
                print(f"[Amatista] No se pudo volver a Modo Objeto: {error}")
        ventana.scene = sc
    if not integracion.entrar_al_espacio(context) and ventana is not None:
        integracion.abrir_barra_lateral(ventana.screen)
    texto = f"Aquí sigues: {nombre}." if nombre else "Aquí sigues."
    try:
        sesion = _sesion()
        if sesion.actividad() is not None:
            sesion.SESION["sucio"], sesion.SESION["ultimo_cambio"] = True, 0.0
            sesion.avisar(texto)
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Volver: {error}")
    integracion.redibujar_barras()
    return texto


class AMATISTA_OT_volver(bpy.types.Operator):
    """Vuelve a tu práctica de Amatista: su escena, el espacio Amatista y la tarjeta"""

    bl_idname = "amatista.volver"
    bl_label = "Volver a Amatista"

    def execute(self, context):
        self.report({"INFO"}, volver(context))
        return {"FINISHED"}


CLASES = (AMATISTA_OT_volver,)


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)


def unregister():
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)
