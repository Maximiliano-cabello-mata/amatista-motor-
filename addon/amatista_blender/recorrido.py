"""Primeros pasos dentro de Blender (add-on 5.1): un recorrido corto por lo esencial.

Las paradas están en recorrido_pasos.py (sin bpy). Aquí:

- empezar() prepara una escena propia, «Amatista · Primeros pasos», con un
  cubo para practicar (la escena del alumno no se toca) y abre la pestaña
  Amatista;
- un temporizador comprueba la parada de ahora en la escena (la barra
  lateral abierta, la cuenta vinculada, la vista orbitada, el cubo elegido o
  movido) y, cuando se cumple, la celebra y pasa sola a la siguiente;
- la tarjeta de la vista 3D (interfaz/hud.py) y el panel (dibujar_panel)
  muestran la parada; el latido (enlace.py) la manda a la plataforma, que la
  muestra en la lección «Tus primeros pasos en Blender» y puede mandar las
  órdenes empezar · siguiente · anterior · salir.

Al terminar queda marcado en las preferencias (recorrido_hecho) y el panel
deja de ofrecerlo; se puede repetir desde la lección o con «Repetir».
"""
import time

import bpy

from . import ajustes, guia, recorrido_pasos

PASOS = recorrido_pasos.PASOS
ESCENA = "Amatista · Primeros pasos"
MARCA = "amatista_recorrido"
CUBO = "Cubo de práctica"
RUTA_LECCION = "#/curso/primeros_pasos/leccion/pp1_blender"
ESPERA_AVANCE = 1.4  # segundos entre «¡Eso es!» y la parada siguiente
ORBITA_MINIMA = 0.35  # radianes (unos 20°)
MOVIMIENTO_MINIMO = 0.3  # metros

ESTADO = {
    "activo": False,
    "indice": 0,
    "hechas": set(),
    "base_vista": {},  # rotación de cada vista 3D al llegar a «orbitar»
    "base_cubo": None,  # dónde estaba el cubo al llegar a «mover»
    "avanzar_en": 0.0,
    "escena_previa": "",
    "empezado_en": 0.0,
}


# --- Estado ---------------------------------------------------------------------------------------


def activo():
    return ESTADO["activo"]


def hecho():
    p = ajustes.prefs()
    return bool(p and p.recorrido_hecho)


def paso_actual():
    return PASOS[ESTADO["indice"]]


def paso_hecho():
    return paso_actual()["id"] in ESTADO["hechas"]


def puede_seguir():
    return recorrido_pasos.puede_seguir(ESTADO["indice"], ESTADO["hechas"])


def info_latido():
    """detalle.recorrido del latido: siempre va, así la plataforma sabe que este add-on lo tiene."""
    return recorrido_pasos.estado_publico(ESTADO["indice"], ESTADO["hechas"], ESTADO["activo"], hecho() and not ESTADO["activo"])


# --- La escena del recorrido --------------------------------------------------------------------


def _ventana(context):
    ventana = getattr(context, "window", None) or getattr(bpy.context, "window", None)
    if ventana is None and bpy.context.window_manager.windows:
        ventana = bpy.context.window_manager.windows[0]
    return ventana


def _a_modo_objeto():
    obj = getattr(bpy.context, "active_object", None)
    if obj is not None and getattr(obj, "mode", "OBJECT") != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(f"[Amatista] No se pudo volver a Modo Objeto: {error}")


def _cubo(sc):
    return next((o for o in sc.objects if o.get(MARCA)), None)


def preparar_escena(context):
    """La escena del recorrido con su cubo en el centro (se crea si no existe) y en la ventana."""
    sc = next((s for s in bpy.data.scenes if s.get(MARCA)), None)
    if sc is None:
        sc = bpy.data.scenes.new(ESCENA)
        sc[MARCA] = 1
    cubo = _cubo(sc)
    if cubo is None:
        malla = bpy.data.meshes.new("Cube")
        try:
            import bmesh

            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=2.0)
            bm.to_mesh(malla)
            bm.free()
        except ImportError:  # pragma: no cover - bmesh siempre viene con Blender
            pass
        cubo = bpy.data.objects.new(CUBO, malla)
        cubo[MARCA] = 1
        sc.collection.objects.link(cubo)
    cubo.location = (0.0, 0.0, 0.0)
    cubo.select_set(False, view_layer=sc.view_layers[0])
    sc.view_layers[0].objects.active = None
    ventana = _ventana(context)
    if ventana is not None and ventana.scene != sc:
        if not ESTADO["escena_previa"] and not ventana.scene.get(MARCA):
            ESTADO["escena_previa"] = ventana.scene.name
        _a_modo_objeto()
        ventana.scene = sc
    return sc


def _volver_a_la_escena_previa(context):
    previa = bpy.data.scenes.get(ESTADO["escena_previa"] or "")
    ESTADO["escena_previa"] = ""
    ventana = _ventana(context)
    if previa is not None and ventana is not None and ventana.scene.get(MARCA):
        _a_modo_objeto()
        ventana.scene = previa


# --- Comprobaciones -------------------------------------------------------------------------------


def _vistas_3d():
    wm = getattr(bpy.context, "window_manager", None)
    for ventana in getattr(wm, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                yield area


def _barra_abierta(context):
    return any(area.spaces.active.show_region_ui for area in _vistas_3d())


def _cuenta(context):
    p = ajustes.prefs()
    return bool(p and p.token)


def _rotaciones():
    return {str(area.as_pointer()): area.spaces.active.region_3d.view_rotation.copy() for area in _vistas_3d()}


def _orbito(context):
    base = ESTADO["base_vista"]
    for clave, rotacion in _rotaciones().items():
        antes = base.get(clave)
        if antes is not None and antes.rotation_difference(rotacion).angle > ORBITA_MINIMA:
            return True
    return False


def _sc(context):
    return getattr(context, "scene", None) or bpy.context.scene


def _eligio(context):
    sc = _sc(context)
    cubo = _cubo(sc) if sc is not None else None
    if cubo is None:
        return False
    capa = getattr(context, "view_layer", None) or sc.view_layers[0]
    return capa.objects.active == cubo and cubo.select_get(view_layer=capa)


def _movio(context):
    sc = _sc(context)
    cubo = _cubo(sc) if sc is not None else None
    base = ESTADO["base_cubo"]
    if cubo is None or base is None:
        return False
    return (cubo.location - base).length > MOVIMIENTO_MINIMO


COMPROBACIONES = {"barra": _barra_abierta, "cuenta": _cuenta, "orbitar": _orbito, "elegir": _eligio, "mover": _movio}


def _al_llegar(context):
    """Lo que necesita la parada antes de comprobarla (la vista o el cubo de partida)."""
    paso = paso_actual()
    if paso["comprobar"] == "orbitar":
        ESTADO["base_vista"] = _rotaciones()
    elif paso["comprobar"] == "mover":
        sc = _sc(context)
        cubo = _cubo(sc) if sc is not None else None
        ESTADO["base_cubo"] = cubo.location.copy() if cubo is not None else None
    ESTADO["avanzar_en"] = 0.0


def comprobar(context=None):
    """Comprueba la parada de ahora; True si se acaba de cumplir."""
    context = context or bpy.context
    paso = paso_actual()
    funcion = COMPROBACIONES.get(paso["comprobar"])
    if not ESTADO["activo"] or funcion is None or paso["id"] in ESTADO["hechas"]:
        return False
    try:
        cumplida = bool(funcion(context))
    except (AttributeError, ReferenceError, RuntimeError) as error:
        print(f"[Amatista] Primeros pasos ({paso['id']}): {error}")
        return False
    if not cumplida:
        return False
    ESTADO["hechas"].add(paso["id"])
    ESTADO["avanzar_en"] = time.time() + ESPERA_AVANCE
    guia.avisar("¡Eso es!", paso["titulo"], "logrado")
    _cambio()
    return True


# --- Acciones ---------------------------------------------------------------------------------------


def _cambio():
    from . import enlace, practicas

    enlace.latir_pronto()
    practicas.redibujar()


def empezar(context=None):
    context = context or bpy.context
    from . import practicas

    preparar_escena(context)
    ESTADO.update(activo=True, indice=0, hechas=set(), base_vista={}, base_cubo=None, empezado_en=time.time())
    _al_llegar(context)
    practicas.mostrar_en_amatista(context)
    guia.avisar("Primeros pasos", "Diez paradas cortas. Sigue la tarjeta.", "animo")
    if not bpy.app.timers.is_registered(_vigilar):
        bpy.app.timers.register(_vigilar, first_interval=0.4)
    _cambio()
    return "Empezaron los primeros pasos en tu Blender."


def ir(context, paso):
    """Avanza o retrocede; avanzar solo si la parada lo permite (o ya está hecha)."""
    context = context or bpy.context
    if not ESTADO["activo"]:
        return None
    if paso > 0 and not puede_seguir():
        return "Primero haz lo que pide esta parada."
    nuevo = recorrido_pasos.mover(ESTADO["indice"], paso)
    if nuevo == ESTADO["indice"]:
        return None
    ESTADO["indice"] = nuevo
    _al_llegar(context)
    comprobar(context)  # si ya estaba hecho (la cuenta vinculada, la barra abierta), se marca solo
    _cambio()
    return None


def terminar(context=None):
    context = context or bpy.context
    p = ajustes.prefs()
    if p is not None and not p.recorrido_hecho:
        p.recorrido_hecho = True
        ajustes.guardar_preferencias()
    ESTADO.update(activo=False, avanzar_en=0.0)
    _volver_a_la_escena_previa(context)
    guia.avisar("¡Primeros pasos completos!", "Tu primer taller te espera en la plataforma.", "logrado")
    _cambio()
    return "Primeros pasos terminados."


def salir(context=None):
    context = context or bpy.context
    ESTADO.update(activo=False, avanzar_en=0.0)
    _volver_a_la_escena_previa(context)
    _cambio()
    return "Saliste de los primeros pasos. Puedes retomarlos desde la pestaña Amatista."


def omitir():
    """«Ya lo conozco»: no se vuelve a ofrecer (se puede repetir desde la lección)."""
    p = ajustes.prefs()
    if p is not None:
        p.recorrido_hecho = True
        ajustes.guardar_preferencias()
    _cambio()


def orden(context, accion):
    """Una orden de la plataforma (enlace.py): empezar · siguiente · anterior · salir."""
    if accion == "empezar":
        return empezar(context)
    if accion == "siguiente":
        if ESTADO["activo"] and ESTADO["indice"] == recorrido_pasos.ULTIMO:
            return terminar(context)
        return ir(context, 1)
    if accion == "anterior":
        return ir(context, -1)
    if accion in ("salir", "terminar"):
        return salir(context) if accion == "salir" else terminar(context)
    return None


def _vigilar():
    if not ESTADO["activo"]:
        return None
    try:
        comprobar(bpy.context)
        if ESTADO["avanzar_en"] and time.time() >= ESTADO["avanzar_en"]:
            ESTADO["avanzar_en"] = 0.0
            if ESTADO["indice"] < recorrido_pasos.ULTIMO:
                ir(bpy.context, 1)
    except Exception as error:  # noqa: BLE001 - el recorrido nunca rompe Blender
        print(f"[Amatista] Primeros pasos: {error}")
    return 0.4


# --- Operador y panel -----------------------------------------------------------------------------


class AMATISTA_OT_recorrido(bpy.types.Operator):
    bl_idname = "amatista.recorrido"
    bl_label = "Primeros pasos"
    bl_description = "Un recorrido corto por Blender y Amatista: la pestaña, tu cuenta, la vista 3D y la tarjeta"

    accion: bpy.props.EnumProperty(
        items=[(a, a.capitalize(), "") for a in ("empezar", "siguiente", "anterior", "salir", "terminar", "omitir")],
        default="empezar",
    )

    def execute(self, context):
        if self.accion == "omitir":
            omitir()
            return {"FINISHED"}
        texto = orden(context, self.accion)
        if texto and self.accion == "siguiente" and ESTADO["activo"]:
            self.report({"INFO"}, texto)  # «Primero haz lo que pide esta parada.»
        return {"FINISHED"}


def dibujar_panel(layout, context):
    """La tarjeta del recorrido en la pestaña Amatista (arriba de todo) o la invitación a hacerlo."""
    from .interfaz import estilo

    if not ESTADO["activo"]:
        if hecho():
            return
        cuerpo = estilo.tarjeta(layout, "¿Primera vez con Amatista?", icono_propio="logo")
        estilo.parrafo(cuerpo, context, "Primeros pasos: diez paradas cortas para conocer Blender, tu pestaña Amatista "
                       "y cómo se conecta con la plataforma. Unos 5 minutos.")
        estilo.boton_principal(cuerpo, "amatista.recorrido", "Empezar los primeros pasos", icon="PLAY", escala=1.4,
                               accion="empezar")
        fila = cuerpo.row()
        fila.active = False
        fila.operator("amatista.recorrido", text="Ya lo conozco", icon="CHECKMARK").accion = "omitir"
        return

    indice = ESTADO["indice"]
    paso = paso_actual()
    cuerpo = estilo.tarjeta(layout, f"Primeros pasos · {indice + 1} de {recorrido_pasos.TOTAL}", icono_propio="logo")
    estilo.barra(cuerpo, (indice + (1 if paso_hecho() else 0)) / recorrido_pasos.TOTAL, " ")
    titulo = cuerpo.row()
    titulo.scale_y = 1.3
    titulo.label(text=paso["titulo"], icon="CHECKMARK" if paso_hecho() else "RIGHTARROW")
    estilo.parrafo(cuerpo, context, paso["texto"])
    caja = cuerpo.box()
    caja.label(text="Qué hacer", icon="HAND")
    estilo.parrafo(caja, context, paso["hacer"], margen=6)
    if paso["teclas"]:
        estilo.teclas(caja, list(paso["teclas"]))
    if paso["comprobar"] != "ninguna":
        estado = caja.row()
        estado.active = paso_hecho()
        estado.label(text="¡Hecho! Seguimos…" if paso_hecho() else "Amatista lo nota sola cuando lo hagas.",
                     icon="CHECKMARK" if paso_hecho() else "TIME")
    if paso["id"] == "cuenta" and not paso_hecho():
        cuerpo.operator("amatista.vincular", text="Vincular con mi cuenta", icon="LINKED")
        fila = cuerpo.row()
        fila.active = False
        fila.label(text="¿Sin cuenta todavía? Puedes seguir y vincular después.", icon="INFO")
    if paso["id"] in ("enlace", "listo"):
        cuerpo.operator("amatista.abrir_plataforma", text="Abrir la lección en la plataforma", icon="URL").ruta = RUTA_LECCION

    fila = cuerpo.row(align=True)
    fila.scale_y = 1.4
    atras = fila.row(align=True)
    atras.enabled = indice > 0
    atras.operator("amatista.recorrido", text="", icon="TRIA_LEFT").accion = "anterior"
    siguiente = fila.row(align=True)
    siguiente.enabled = puede_seguir()  # la cuenta se puede dejar para después; las otras paradas esperan
    if indice == recorrido_pasos.ULTIMO:
        siguiente.operator("amatista.recorrido", text="Terminar", icon="CHECKMARK").accion = "terminar"
    else:
        etiqueta = "Más tarde" if paso["id"] == "cuenta" and not paso_hecho() else "Siguiente"
        siguiente.operator("amatista.recorrido", text=etiqueta, icon="TRIA_RIGHT").accion = "siguiente"
    fila.operator("amatista.recorrido", text="", icon="X").accion = "salir"


CLASES = (AMATISTA_OT_recorrido,)


def unregister():
    if bpy.app.timers.is_registered(_vigilar):
        bpy.app.timers.unregister(_vigilar)
    ESTADO.update(activo=False)

