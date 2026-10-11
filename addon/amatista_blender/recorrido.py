"""«Conoce Amatista Motor» (add-on 5.2): las tres prácticas del add-on dentro de Blender.

Las paradas están en recorrido_pasos.py (sin bpy). Aquí:

- empezar(context, rid) prepara una escena propia, «Amatista · Conoce el add-on», con
  un cubo para practicar (la escena del alumno no se toca) y abre la pestaña
  Amatista;
- un temporizador comprueba la parada de ahora en la escena (la barra lateral
  abierta, la cuenta vinculada, la vista orbitada o acercada, el cubo elegido,
  movido, girado o escalado) y, cuando se cumple, la celebra y pasa sola a la
  siguiente; las paradas «uso:…» se marcan cuando el alumno pulsa el botón del
  que hablan (anotar(), llamado desde esos operadores);
- la tarjeta de la vista 3D (interfaz/hud.py) y el panel (dibujar_panel)
  muestran la parada con los botones reales del add-on; el latido (enlace.py) la
  manda a la plataforma, que la muestra en #/blender › «Conoce Amatista Motor» y
  puede mandar las órdenes empezar · siguiente · anterior · salir.

Al terminar una práctica queda marcada en las preferencias (recorridos_hechos) y
el panel ofrece la siguiente; se puede repetir desde la plataforma o con «Repetir».
"""
import time

import bpy

from . import ajustes, guia, recorrido_pasos

RECORRIDOS = recorrido_pasos.RECORRIDOS
ESCENA = "Amatista · Conoce el add-on"
MARCA = "amatista_recorrido"
CUBO = "Cubo de práctica"
RUTA_PLATAFORMA = "#/blender"  # «Conoce Amatista Motor» vive en la página Blender de la plataforma
ESPERA_AVANCE = 1.4  # segundos entre «¡Eso es!» y la parada siguiente
ORBITA_MINIMA = 0.35  # radianes (unos 20°)
ACERCAMIENTO_MINIMO = 0.15  # la distancia de la vista cambia al menos un 15 %
MOVIMIENTO_MINIMO = 0.3  # metros
GIRO_MINIMO = 0.2  # radianes (unos 11°)
ESCALA_MINIMA = 0.15  # 15 % de cambio de tamaño
# Herramientas que muestra la parada «Tus herramientas» (engine/amatista_engine/tools/catalogo.json).
HERRAMIENTAS = ("transform.move", "transform.rotate", "transform.scale")

ESTADO = {
    "activo": False,
    "rid": recorrido_pasos.PRIMERO,  # la práctica de ahora (o la última abierta)
    "indice": 0,
    "hechas": set(),
    "usos": set(),  # botones del add-on pulsados durante la práctica (paradas «uso:…»)
    "base_vista": {},  # rotación (orbitar) o distancia (acercar) de cada vista 3D al llegar a la parada
    "base_cubo": None,  # posición, giro o tamaño del cubo al llegar a «mover», «girar» o «escalar»
    "avanzar_en": 0.0,
    "escena_previa": "",
    "empezado_en": 0.0,
}


# --- Estado ---------------------------------------------------------------------------------------


def activo():
    return ESTADO["activo"]


def hechos():
    """Las prácticas terminadas, en su orden. El 5.1 tenía un solo recorrido: si se hizo, cuenta como la primera."""
    p = ajustes.prefs()
    if p is None:
        return []
    lista = recorrido_pasos.leer_hechos(p.recorridos_hechos)
    if p.recorrido_hecho and recorrido_pasos.PRIMERO not in lista:
        lista = recorrido_pasos.leer_hechos(",".join([recorrido_pasos.PRIMERO, *lista]))
    return lista


def hecho(rid=None):
    """¿Se terminó esta práctica? Sin id: ¿se terminaron las tres?"""
    lista = hechos()
    if rid is None:
        return all(r in lista for r in recorrido_pasos.ORDEN)
    return rid in lista


def pendiente():
    """La primera práctica sin terminar (None si ya están todas)."""
    lista = hechos()
    return next((r for r in recorrido_pasos.ORDEN if r not in lista), None)


def _marcar_hecho(rid):
    p = ajustes.prefs()
    if p is None:
        return
    lista = set(hechos()) | {rid}
    p.recorridos_hechos = recorrido_pasos.escribir_hechos(lista)
    if rid == recorrido_pasos.PRIMERO:
        p.recorrido_hecho = True
    ajustes.guardar_preferencias()


def pasos():
    return recorrido_pasos.pasos_de(ESTADO["rid"])


def paso_actual():
    return pasos()[ESTADO["indice"]]


def paso_hecho():
    return paso_actual()["id"] in ESTADO["hechas"]


def puede_seguir():
    return recorrido_pasos.puede_seguir(ESTADO["rid"], ESTADO["indice"], ESTADO["hechas"])


def info_latido():
    """detalle.recorrido del latido: siempre va, así la plataforma sabe que este add-on lo tiene."""
    return recorrido_pasos.estado_publico(ESTADO["rid"], ESTADO["indice"], ESTADO["hechas"], ESTADO["activo"],
                                          hechos())


def anotar(clave):
    """Un botón del add-on se pulsó (abrir la plataforma, guardar, usar una herramienta…): las paradas
    «uso:<clave>» lo esperan. Fuera de una práctica no hace nada."""
    if ESTADO["activo"]:
        ESTADO["usos"].add(clave)


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
    """La escena de las prácticas con su cubo en el centro (se crea si no existe) y en la ventana."""
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
    cubo.rotation_euler = (0.0, 0.0, 0.0)
    cubo.scale = (1.0, 1.0, 1.0)
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


def _distancias():
    return {str(area.as_pointer()): float(area.spaces.active.region_3d.view_distance) for area in _vistas_3d()}


def _orbito(context):
    base = ESTADO["base_vista"]
    for clave, rotacion in _rotaciones().items():
        antes = base.get(clave)
        if antes is not None and antes.rotation_difference(rotacion).angle > ORBITA_MINIMA:
            return True
    return False


def _acerco(context):
    base = ESTADO["base_vista"]
    for clave, distancia in _distancias().items():
        antes = base.get(clave)
        if antes and abs(distancia - antes) / antes > ACERCAMIENTO_MINIMO:
            return True
    return False


def _sc(context):
    return getattr(context, "scene", None) or bpy.context.scene


def _cubo_de(context):
    sc = _sc(context)
    return _cubo(sc) if sc is not None else None


def _eligio(context):
    sc = _sc(context)
    cubo = _cubo(sc) if sc is not None else None
    if cubo is None:
        return False
    capa = getattr(context, "view_layer", None) or sc.view_layers[0]
    return capa.objects.active == cubo and cubo.select_get(view_layer=capa)


def _movio(context):
    cubo, base = _cubo_de(context), ESTADO["base_cubo"]
    return cubo is not None and base is not None and (cubo.location - base).length > MOVIMIENTO_MINIMO


def _giro(context):
    cubo, base = _cubo_de(context), ESTADO["base_cubo"]
    if cubo is None or base is None:
        return False
    return base.to_quaternion().rotation_difference(cubo.rotation_euler.to_quaternion()).angle > GIRO_MINIMO


def _escalo(context):
    cubo, base = _cubo_de(context), ESTADO["base_cubo"]
    if cubo is None or base is None:
        return False
    return any(abs(a - b) / max(abs(b), 1e-6) > ESCALA_MINIMA for a, b in zip(cubo.scale, base))


COMPROBACIONES = {"barra": _barra_abierta, "cuenta": _cuenta, "orbitar": _orbito, "acercar": _acerco,
                  "elegir": _eligio, "mover": _movio, "girar": _giro, "escalar": _escalo}


def _funcion(comprobar):
    """La función que comprueba una parada; las «uso:<clave>» miran los botones pulsados."""
    if comprobar.startswith("uso:"):
        clave = comprobar[4:]
        return lambda context: clave in ESTADO["usos"]
    return COMPROBACIONES.get(comprobar)


def _al_llegar(context):
    """Lo que necesita la parada antes de comprobarla (la vista o el cubo de partida)."""
    comprobar = paso_actual()["comprobar"]
    cubo = _cubo_de(context)
    if comprobar == "orbitar":
        ESTADO["base_vista"] = _rotaciones()
    elif comprobar == "acercar":
        ESTADO["base_vista"] = _distancias()
    elif comprobar == "mover":
        ESTADO["base_cubo"] = cubo.location.copy() if cubo is not None else None
    elif comprobar == "girar":
        ESTADO["base_cubo"] = cubo.rotation_euler.copy() if cubo is not None else None
    elif comprobar == "escalar":
        ESTADO["base_cubo"] = cubo.scale.copy() if cubo is not None else None
    if comprobar.startswith("uso:"):
        ESTADO["usos"].discard(comprobar[4:])  # cuenta lo que se pulse desde esta parada
    ESTADO["avanzar_en"] = 0.0


def comprobar(context=None):
    """Comprueba la parada de ahora; True si se acaba de cumplir."""
    context = context or bpy.context
    paso = paso_actual()
    funcion = _funcion(paso["comprobar"])
    if not ESTADO["activo"] or funcion is None or paso["id"] in ESTADO["hechas"]:
        return False
    try:
        cumplida = bool(funcion(context))
    except (AttributeError, ReferenceError, RuntimeError) as error:
        print(f"[Amatista] Conoce el add-on ({paso['id']}): {error}")
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


def empezar(context=None, rid=None):
    """Empieza una práctica (sin id: la primera sin terminar, o la primera si ya están todas)."""
    context = context or bpy.context
    from . import practicas

    rid = recorrido_pasos.valido(rid or pendiente() or recorrido_pasos.PRIMERO)
    preparar_escena(context)
    ESTADO.update(activo=True, rid=rid, indice=0, hechas=set(), usos=set(), base_vista={}, base_cubo=None,
                  empezado_en=time.time())
    _al_llegar(context)
    comprobar(context)  # la barra ya abierta o la cuenta ya vinculada se marcan solas
    practicas.mostrar_en_amatista(context)
    numero = recorrido_pasos.ORDEN.index(rid) + 1
    guia.avisar(f"Práctica {numero} de {len(recorrido_pasos.ORDEN)}", RECORRIDOS[rid]["nombre"], "animo")
    if not bpy.app.timers.is_registered(_vigilar):
        bpy.app.timers.register(_vigilar, first_interval=0.4)
    _cambio()
    return f"Empezó «{RECORRIDOS[rid]['nombre']}» en tu Blender."


def ir(context, paso):
    """Avanza o retrocede; avanzar solo si la parada lo permite (o ya está hecha)."""
    context = context or bpy.context
    if not ESTADO["activo"]:
        return None
    if paso > 0 and not puede_seguir():
        return "Primero haz lo que pide esta parada."
    nuevo = recorrido_pasos.mover(ESTADO["rid"], ESTADO["indice"], paso)
    if nuevo == ESTADO["indice"]:
        return None
    ESTADO["indice"] = nuevo
    _al_llegar(context)
    comprobar(context)  # si ya estaba hecho (la cuenta vinculada, la barra abierta), se marca solo
    _cambio()
    return None


def terminar(context=None):
    context = context or bpy.context
    rid = ESTADO["rid"]
    _marcar_hecho(rid)
    ESTADO.update(activo=False, avanzar_en=0.0)
    _volver_a_la_escena_previa(context)
    siguiente = pendiente()
    if siguiente:
        guia.avisar("¡Práctica completa!", f"Sigue con «{RECORRIDOS[siguiente]['nombre']}».", "logrado")
    else:
        guia.avisar("¡Ya conoces Amatista Motor!", "Tu primer taller te espera en la plataforma.", "logrado")
    _cambio()
    return f"Terminaste «{RECORRIDOS[rid]['nombre']}»."


def salir(context=None):
    context = context or bpy.context
    ESTADO.update(activo=False, avanzar_en=0.0)
    _volver_a_la_escena_previa(context)
    _cambio()
    return "Saliste de la práctica. Puedes retomarla desde la pestaña Amatista o desde la plataforma."


def omitir():
    """«Ya lo conozco»: marca las tres como hechas (se pueden repetir desde la plataforma o el panel)."""
    p = ajustes.prefs()
    if p is not None:
        p.recorrido_hecho = True
        p.recorridos_hechos = recorrido_pasos.escribir_hechos(recorrido_pasos.ORDEN)
        ajustes.guardar_preferencias()
    _cambio()


def abrir_primer_taller(context=None):
    """Última parada de «Así te enseña el taller»: termina y abre el taller que toca."""
    context = context or bpy.context
    terminar(context)
    from .taller import sesion

    return sesion.abrir(context)


def orden(context, accion, rid=None):
    """Una orden de la plataforma (enlace.py): empezar · siguiente · anterior · salir · terminar.

    Con `rid` la orden es para esa práctica: «empezar» la abre y las demás solo se cumplen si es la de ahora."""
    if accion == "empezar":
        return empezar(context, rid)
    if rid and recorrido_pasos.valido(rid) != ESTADO["rid"]:
        return None
    if accion == "siguiente":
        if ESTADO["activo"] and ESTADO["indice"] == recorrido_pasos.ultimo(ESTADO["rid"]):
            return terminar(context)
        return ir(context, 1)
    if accion == "anterior":
        return ir(context, -1)
    if accion == "terminar":
        return terminar(context) if ESTADO["activo"] else None
    if accion == "salir":
        return salir(context)
    return None


def _vigilar():
    if not ESTADO["activo"]:
        return None
    try:
        comprobar(bpy.context)
        if ESTADO["avanzar_en"] and time.time() >= ESTADO["avanzar_en"]:
            ESTADO["avanzar_en"] = 0.0
            if ESTADO["indice"] < recorrido_pasos.ultimo(ESTADO["rid"]):
                ir(bpy.context, 1)
    except Exception as error:  # noqa: BLE001 - la práctica nunca rompe Blender
        print(f"[Amatista] Conoce el add-on: {error}")
    return 0.4


# --- Operador y panel -----------------------------------------------------------------------------


class AMATISTA_OT_recorrido(bpy.types.Operator):
    bl_idname = "amatista.recorrido"
    bl_label = "Conoce Amatista Motor"
    bl_description = "Tres prácticas cortas que explican todas las herramientas del add-on"

    accion: bpy.props.EnumProperty(
        items=[(a, a.capitalize(), "") for a in ("empezar", "siguiente", "anterior", "salir", "terminar", "omitir",
                                                   "taller")],
        default="empezar",
    )
    recorrido: bpy.props.StringProperty(description="pestana · vista · taller (vacío: la que sigue)")

    def execute(self, context):
        if self.accion == "omitir":
            omitir()
            return {"FINISHED"}
        if self.accion == "taller":
            texto = abrir_primer_taller(context)
            if texto:
                self.report({"INFO"}, texto)
            return {"FINISHED"}
        texto = orden(context, self.accion, self.recorrido or None)
        if texto and self.accion == "siguiente" and ESTADO["activo"]:
            self.report({"INFO"}, texto)  # «Primero haz lo que pide esta parada.»
        return {"FINISHED"}


def _invitacion(layout, context, estilo):
    """Fuera de una práctica: las tres, con las terminadas marcadas (nada si ya se hicieron todas)."""
    lista = hechos()
    siguiente = pendiente()
    if siguiente is None:
        return
    titulo = "¿Primera vez con Amatista?" if not lista else "Conoce Amatista Motor"
    cuerpo = estilo.tarjeta(layout, titulo, icono_propio="logo")
    estilo.parrafo(cuerpo, context, "Tres prácticas cortas te enseñan todo lo que hace el add-on. Unos 3 minutos "
                   "cada una.")
    for numero, rid in enumerate(recorrido_pasos.ORDEN, start=1):
        fila = cuerpo.row(align=True)
        hecha = rid in lista
        fila.active = not hecha
        fila.label(text=f"{numero}. {RECORRIDOS[rid]['nombre']}", icon="CHECKMARK" if hecha else "RIGHTARROW")
        boton = fila.operator("amatista.recorrido", text="Repetir" if hecha else "", icon="LOOP_BACK" if hecha else "PLAY")
        boton.accion, boton.recorrido = "empezar", rid
    estilo.boton_principal(cuerpo, "amatista.recorrido", f"Empezar: {RECORRIDOS[siguiente]['nombre']}", icon="PLAY",
                           escala=1.4, accion="empezar", recorrido=siguiente)
    if not lista:
        fila = cuerpo.row()
        fila.active = False
        fila.operator("amatista.recorrido", text="Ya lo conozco", icon="CHECKMARK").accion = "omitir"


def _botones_de_la_parada(cuerpo, paso):
    """Los botones reales del add-on de los que habla la parada: se usan aquí mismo."""
    ident = paso["id"]
    if ident == "cuenta" and not paso_hecho():
        cuerpo.operator("amatista.vincular", text="Vincular con mi cuenta", icon="LINKED")
        fila = cuerpo.row()
        fila.active = False
        fila.label(text="¿Sin cuenta todavía? Puedes seguir y vincular después.", icon="INFO")
    elif ident in ("plataforma", "enlace"):
        cuerpo.operator("amatista.abrir_plataforma", text="Abrir la plataforma", icon="URL").ruta = RUTA_PLATAFORMA
    elif ident == "guardar":
        cuerpo.operator("amatista.taller_sincronizar", text="Guardar mi avance", icon="FILE_REFRESH")
    elif ident in ("herramientas", "ayuda"):
        from . import _motor

        for clave in HERRAMIENTAS:
            herramienta = _motor.MOTOR.tools.get(clave)
            if herramienta is None:
                continue
            fila = cuerpo.row(align=True)
            tecla = f"  ({herramienta.keys[0]})" if herramienta.keys else ""
            fila.operator("amatista.usar_herramienta", text=f"Usar: {herramienta.name}{tecla}",
                          icon="PLAY").herramienta = clave
            fila.operator("amatista.herramienta_ayuda", text="¿Cómo se usa?", icon="QUESTION").herramienta = clave
    elif ident == "enfoque":
        fila = cuerpo.row(align=True)
        fila.operator("amatista.ver_todo", text="Ver todo Blender", icon="FULLSCREEN_ENTER")
        fila.operator("amatista.enfocar", text="Enfocar", icon="FULLSCREEN_EXIT")
    elif ident == "listo" and ESTADO["rid"] == "taller":
        cuerpo.operator("amatista.recorrido", text="Abrir mi primer taller", icon="PLAY").accion = "taller"


def dibujar_panel(layout, context):
    """La tarjeta de la práctica en la pestaña Amatista (arriba de todo) o la invitación a hacerlas."""
    from .interfaz import estilo

    if not ESTADO["activo"]:
        _invitacion(layout, context, estilo)
        return

    rid, indice = ESTADO["rid"], ESTADO["indice"]
    total = recorrido_pasos.total(rid)
    numero = recorrido_pasos.ORDEN.index(rid) + 1
    paso = paso_actual()
    cuerpo = estilo.tarjeta(layout, f"Práctica {numero} de 3 · {RECORRIDOS[rid]['nombre']}", icono_propio="logo",
                            derecha=f"{indice + 1}/{total}")
    estilo.barra(cuerpo, (indice + (1 if paso_hecho() else 0)) / total, " ")
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
        if paso_hecho():
            texto = "¡Hecho! Seguimos…"
        elif paso["comprobar"].startswith("uso:"):
            texto = "Se marca solo cuando pulses el botón."
        else:
            texto = "Amatista lo nota sola cuando lo hagas."
        estado.label(text=texto, icon="CHECKMARK" if paso_hecho() else "TIME")
    _botones_de_la_parada(cuerpo, paso)

    fila = cuerpo.row(align=True)
    fila.scale_y = 1.4
    atras = fila.row(align=True)
    atras.enabled = indice > 0
    atras.operator("amatista.recorrido", text="", icon="TRIA_LEFT").accion = "anterior"
    siguiente = fila.row(align=True)
    siguiente.enabled = puede_seguir()  # las opcionales se pueden dejar para después; las otras esperan
    if indice == total - 1:
        siguiente.operator("amatista.recorrido", text="Terminar", icon="CHECKMARK").accion = "terminar"
    else:
        etiqueta = "Más tarde" if paso.get("opcional") and not paso_hecho() else "Siguiente"
        siguiente.operator("amatista.recorrido", text=etiqueta, icon="TRIA_RIGHT").accion = "siguiente"
    fila.operator("amatista.recorrido", text="", icon="X").accion = "salir"


CLASES = (AMATISTA_OT_recorrido,)


def unregister():
    if bpy.app.timers.is_registered(_vigilar):
        bpy.app.timers.unregister(_vigilar)
    ESTADO.update(activo=False)
