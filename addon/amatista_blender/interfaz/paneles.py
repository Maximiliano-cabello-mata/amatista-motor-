"""Paneles de la barra lateral de la vista 3D (N › Amatista).

Modo Alumno (Student), motor v3: tres secciones como en una plataforma
educativa, elegidas con las pestañas de arriba:
    Aprender   la teoría de este momento (píldoras), las demás ideas de la
               práctica y el repaso espaciado
    Practicar  la práctica: curso y módulo, progreso, pausa si un vigilante
               la detuvo, la tarjeta guía «Ahora», asignar rol y los pasos
    Mi curso   el mapa de los cursos (Principiante, Principiante-Intermedio…)
               con lo terminado, lo disponible y lo bloqueado
Modo Desarrollador (Author): Borrador · Tagger · Inspector · Objetivos ·
                             Validación y depurador · Publicar
Vista previa: el borrador exactamente como lo verá el alumno (sin
diagnóstico).
"""
import time

import bpy

from .. import _motor, ajustes, aprendizaje, autor, cuenta, guia, integridad, practicas, red, temas
from . import aprender, dialogos, estilo

CATEGORIA = "Amatista"
ESTADOS_SYNC = {
    practicas.SYNC_GUARDADO: ("Guardado en tu cuenta", "sincronizado"),
    practicas.SYNC_ENVIANDO: ("Enviando tu progreso…", None),
    practicas.SYNC_PENDIENTE: ("Sin conexión: se enviará después", None),
    practicas.SYNC_SIN_CUENTA: ("Vincula tu cuenta para guardar tu progreso", None),
    practicas.SYNC_ERROR: ("No se pudo guardar", None),
}


def modo_alumno(context):
    wm = context.window_manager.amatista
    return wm.modo == "alumno" or wm.vista_previa or not ajustes.es_desarrollador()


def modo_autor(context):
    return ajustes.es_desarrollador() and context.window_manager.amatista.modo == "autor"


def seccion(context, nombre):
    return modo_alumno(context) and context.window_manager.amatista.pestana == nombre


ICONO_PLAN = {
    "completado": ("completado", None),
    "disponible": ("actual", None),
    "bloqueado": ("bloqueado", None),
    "proximamente": (None, "TIME"),
}
DIFICULTAD_TEXTO = {
    "principiante": "Desde cero",
    "principiante_intermedio": "Ya conoces lo básico",
    "intermedio": "Intermedio",
    "avanzado": "Avanzado",
}


# Temática por módulo (add-on 3.2): un ícono de Blender por escenario del tema.
ICONO_ESCENA = {
    "engranes": "PREFERENCES",
    "chispas": "LIGHT_SUN",
    "estrellas": "WORLD",
    "gotas": "MATERIAL",
    "reflectores": "CAMERA_DATA",
    "carpa": "ANIM",
    "aldea": "HOME",
    "mapa": "OUTLINER_COLLECTION",
    "galeria": "IMAGE_DATA",
    "portal": "URL",
    "cristales": "SHADERFX",
}
ICONO_MENSAJE = {"hola": "HEART", "consejo": "LIGHT", "dato": "INFO"}


def icono_tema(tema):
    return ICONO_ESCENA.get(tema.get("escena"), "SHADERFX")


def tarjeta_tema(layout, context, practica, reporte=None):
    """Cabecera con la temática del módulo: tema, mascota con su mensaje y jefe final."""
    tema = temas.tema_de_practica(practica.id)
    mascota = tema["mascota"]
    caja = layout.box()
    fila = caja.row(align=True)
    fila.scale_y = 1.15
    fila.label(text=tema["nombre"], icon=icono_tema(tema))
    if tema.get("lema"):
        sub = caja.row()
        sub.active = False
        sub.label(text=tema["lema"])
    try:
        jefe = tema["jefe"] if aprendizaje.es_cierre(practica) else None
    except Exception:  # noqa: BLE001 - sin plan de estudios no hay jefe
        jefe = None
    if jefe:
        vencido = reporte is not None and reporte.completed
        fila = caja.row()
        fila.alert = not vencido
        fila.label(text=(f"¡Venciste a {jefe['nombre']}!" if vencido else f"Jefe final: {jefe['nombre']}"),
                   icon="FUND" if vencido else "SOLO_ON")
        if not vencido and jefe.get("frase"):
            sub = caja.row()
            sub.active = False
            sub.label(text=f"«{jefe['frase']}»")
    if guia.nivel() == guia.NIVEL_SILENCIOSO:
        return caja
    tipo, texto = temas.mensaje_mascota(tema, temas.indice_actual())
    mensaje = caja.column(align=True)
    cabecera = mensaje.row(align=True)
    etiqueta = {"consejo": "consejo", "dato": "dato curioso"}.get(tipo)
    cabecera.label(text=f"{mascota['nombre']}, {mascota.get('especie', '')}" + (f" · {etiqueta}" if etiqueta else ""),
                   icon=ICONO_MENSAJE.get(tipo, "HEART"))
    cabecera.operator("amatista.mascota_siguiente", text="", icon="FILE_REFRESH", emboss=False)
    estilo.parrafo(mensaje, context, texto, margen=6)
    return caja


class _Base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORIA


# --- Encabezado: cuenta, conexión y modo -----------------------------------------------


class AMATISTA_PT_principal(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_principal"
    bl_label = "Amatista"

    def draw_header(self, context):
        self.layout.label(text="", icon_value=estilo.icono("logo"))

    def draw(self, context):
        layout = self.layout
        p = ajustes.prefs()

        if not red.en_linea_permitido():
            cuerpo = estilo.tarjeta(layout, "Sin acceso a internet", icon="ERROR")
            estilo.parrafo(cuerpo, context, "Blender tiene desactivado el acceso en línea. Amatista lo necesita para "
                           "descargar prácticas y guardar tu progreso.")
            cuerpo.operator("amatista.permitir_internet", icon="WORLD")

        if integridad.revisar()["estado"] == "modificada":
            cuerpo = estilo.tarjeta(layout, "Copia modificada", icon="ERROR")
            estilo.parrafo(cuerpo, context, "Algunos archivos de Amatista Motor no son los originales. Tus intentos "
                           "se guardan como «sin verificar». Vuelve a descargarlo desde la plataforma (Mi Blender).")

        if cuenta.VINCULO["activo"]:
            self._dibujar_codigo(layout, context)
        elif p and p.token:
            fila = layout.row(align=True)
            fila.label(text=p.cuenta or "Mi cuenta", icon="USER")
            if p.rol and p.rol != "alumno":
                derecha = fila.row()
                derecha.alignment = "RIGHT"
                derecha.label(text=p.rol.capitalize(), icon="SOLO_ON")
        else:
            cuerpo = estilo.tarjeta(layout, "Conecta tu cuenta", icon="LINKED")
            estilo.parrafo(cuerpo, context, "Así tu avance aparece en la plataforma y en tu panel.")
            estilo.boton_principal(cuerpo, "amatista.vincular", "Vincular con Amatista", icon="LINKED", escala=1.3)
            if cuenta.VINCULO["mensaje"]:
                estilo.parrafo(cuerpo, context, cuenta.VINCULO["mensaje"], icon="INFO")

        if ajustes.es_desarrollador():
            fila = layout.row()
            fila.scale_y = 1.2
            fila.prop(context.window_manager.amatista, "modo", expand=True)
            if context.window_manager.amatista.modo == "autor":
                layout.prop(context.window_manager.amatista, "vista_previa", icon="HIDE_OFF")

        if modo_alumno(context):
            # Las tres secciones del alumno, como pestañas de una plataforma.
            fila = layout.row(align=True)
            fila.scale_y = 1.45
            fila.prop(context.window_manager.amatista, "pestana", expand=True)

    def _dibujar_codigo(self, layout, context):
        cuerpo = estilo.tarjeta(layout, "Vincular con tu cuenta", icono_propio="logo")
        estilo.parrafo(cuerpo, context, "1. Abre la plataforma › Blender › Vincular.\n2. Escribe este código:")
        codigo = cuerpo.row()
        codigo.scale_y = 2.2
        codigo.alignment = "CENTER"
        codigo.label(text=cuenta.VINCULO["codigo"])
        restante = max(0, int(cuenta.VINCULO["expira"] - time.time()))
        cuerpo.label(text=f"Esperando confirmación… vence en {restante // 60}:{restante % 60:02d}", icon="TIME")
        fila = cuerpo.row(align=True)
        fila.operator("amatista.abrir_plataforma", text="Abrir la plataforma", icon="URL").ruta = (
            "#/vincular?codigo=" + cuenta.VINCULO["codigo"]
        )
        fila.operator("amatista.cancelar_vinculo", text="", icon="X")


# --- Modo Alumno --------------------------------------------------------------------------


class AMATISTA_PT_practica(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_practica"
    bl_label = "Práctica"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return seccion(context, "practicar")

    def draw(self, context):
        layout = self.layout
        practica = practicas.practica_activa(context)
        if practica is None:
            if not dibujar_mapa(layout, context, solo_siguiente=True):
                self._elegir(layout, context)
            return
        reporte = practicas.ESTADO["reporte"]
        if reporte is None:
            # Dibujar no puede modificar la escena: la evaluación se programa.
            practicas.evaluar_pronto()
            layout.label(text="Revisando tu escena…", icon="TIME")
            return

        curso, modulo = aprendizaje.lugar(practica)
        if curso is not None:
            miga = layout.row()
            miga.active = False
            miga.label(text=f"{curso.title} › Módulo {modulo.number}: {modulo.title}", icon="OUTLINER_COLLECTION")
        tarjeta_tema(layout, context, practica, reporte)
        cuerpo = estilo.tarjeta(
            layout, practica.title, icono_propio="celebrar" if reporte.completed else "logo",
            derecha=f"M{modulo.number}" if modulo is not None else f"N{practica.level}",
        )
        detalle = estilo.nivel_texto(practica.level) if curso is None else DIFICULTAD_TEXTO.get(curso.difficulty, "")
        if practica.estimated_minutes:
            detalle += f" · {practica.estimated_minutes} min"
        sub = cuerpo.row()
        sub.active = False
        sub.label(text=detalle)
        if reporte.progress == 0 and practica.intro:
            estilo.parrafo(cuerpo, context, practica.intro)

        estilo.separador(cuerpo, 0.4)
        obligatorios = [p for p in reporte.steps if not p.optional]
        hechos = sum(1 for p in obligatorios if p.status == "completado")
        estilo.barra(cuerpo, reporte.progress / 100.0, f"{reporte.progress:.0f} %  ·  {hechos} de {len(obligatorios)} objetivos")

        if reporte.needs_update:
            estilo.parrafo(cuerpo, context, "Esta práctica necesita una versión más reciente del add-on.",
                           icon="ERROR", alerta=True)

        if reporte.paused:
            self._tarjeta_pausa(layout, context, practica, reporte)

        self._modelo(layout, context, practica, reporte)

        g = guia.guia_actual()
        pildora = aprendizaje.pildora_principal()
        if pildora is not None and not reporte.completed:
            fila = layout.row(align=True)
            fila.scale_y = 1.2
            fila.operator("amatista.pildora", text=f"Teoría: {pildora.title}", icon=aprender.icono_visual(pildora))
            fila.operator("amatista.pestana", text="", icon="HELP").pestana = "aprender"
        if g is not None and guia.nivel() != guia.NIVEL_SILENCIOSO and not (reporte.paused and g.paused):
            self._tarjeta_guia(layout, context, g)
        elif reporte.completed:
            estilo.parrafo(cuerpo, context, practica.completion or "¡Práctica completada!", icon="FUND")
        elif reporte.current_target_id:
            paso = next(p for p in reporte.steps if p.target_id == reporte.current_target_id)
            cuerpo.label(text=f"Paso {reporte.step_number} de {len(reporte.steps)}: {paso.title}", icon="PLAY")

        fila = layout.row(align=True)
        fila.scale_y = 1.2
        fila.operator("amatista.comprobar", text="Comprobar", icon="CHECKMARK")
        if not reporte.completed:
            if guia.nivel() == guia.NIVEL_SILENCIOSO:
                fila.operator("amatista.pista", text="Necesito una pista", icon_value=estilo.icono("pista"))
            else:
                fila.operator("amatista.explicar_paso", text="¿Cómo lo hago?", icon="QUESTION")

        for aviso in reporte.tool_warnings:
            caja = layout.box()
            caja.alert = True
            estilo.parrafo(caja, context, aviso.message, icon="ERROR")

        self._estado_sync(layout, context)

        if reporte.completed and practica.place is not None and practica.place.next:
            estilo.boton_principal(layout, "amatista.abrir_practica", "Siguiente práctica", icon="FORWARD",
                                   escala=1.4, practica_id=practica.place.next)
        fila = layout.row(align=True)
        fila.operator("amatista.abrir_plataforma", text="Plataforma", icon="URL").ruta = "#/panel"
        fila.operator("amatista.elegir_practica", text="Otra práctica", icon="FILE_REFRESH")

    def _modelo(self, layout, context, practica, reporte):
        """«Así se debe ver»: la imagen del modelo de referencia (motor 3.3)."""
        referencia = getattr(practica, "reference", None)
        imagen = practicas.archivo_de_referencia(practica.id, "referencia.jpg")
        if referencia is None or imagen is None:
            return
        cuerpo = estilo.seccion(layout, context, "modelo", "Así se debe ver", icon="IMAGE_DATA",
                                cerrada=reporte.completed)
        if cuerpo is None:
            return
        cuerpo.template_icon(icon_value=estilo.imagen(imagen), scale=9.0)
        if referencia.description:
            estilo.parrafo(cuerpo, context, referencia.description)
        fila = cuerpo.row(align=True)
        fila.operator("amatista.ver_referencia", text="Ver grande", icon="ZOOM_IN").archivo = "referencia.jpg"
        if practicas.archivo_de_referencia(practica.id, "plano.svg"):
            fila.operator("amatista.ver_referencia", text="Plano con medidas", icon="DRIVER_DISTANCE").archivo = "plano.svg"

    def _tarjeta_pausa(self, layout, context, practica, reporte):
        """Un vigilante detuvo el progreso: aviso rojo con el arreglo a un clic."""
        vigilante = practica.guard(reporte.paused_by)
        resultado = next((r for r in reporte.guards if r.target_id == reporte.paused_by), None)
        caja = layout.box()
        caja.alert = True
        cabecera = caja.row()
        cabecera.scale_y = 1.2
        cabecera.label(text="Progreso en pausa", icon="PAUSE")
        if vigilante is not None:
            estilo.parrafo(caja, context, vigilante.title, icon="ERROR", alerta=True)
        if resultado is not None:
            estilo.parrafo(caja, context, resultado.message, alerta=True)
        if vigilante is not None and vigilante.tip:
            estilo.parrafo(caja, context, vigilante.tip, icon="INFO")
        g = guia.guia_actual()
        if g is not None and g.paused and g.action is not None:
            estilo.boton_principal(caja, "amatista.hazlo_conmigo", g.action.label, icon="PLAY", escala=1.35)

    def _tarjeta_guia(self, layout, context, g):
        """La tarjeta «Ahora»: el paso actual explicado, con teclas y botones."""
        caja = layout.box()
        cabecera = caja.row(align=True)
        cabecera.scale_y = 1.2
        if g.completed:
            cabecera.label(text=g.title, icon_value=estilo.icono("celebrar"))
        else:
            cabecera.label(text=f"Ahora: {g.title}", icon_value=estilo.icono("actual"))
            if g.step_total:
                derecha = cabecera.row()
                derecha.alignment = "RIGHT"
                derecha.active = False
                derecha.label(text=f"{g.step_number}/{g.step_total}")
        icono_tono, alerta = estilo.TONOS.get(g.tone, ("LIGHT", False))
        estilo.parrafo(caja, context, g.feedback, icon=icono_tono, alerta=alerta)
        if g.instructions:
            estilo.separador(caja, 0.3)
            estilo.instrucciones(caja, context, g.instructions)
        if g.why and not g.completed:
            fila = caja.column()
            fila.active = False
            estilo.parrafo(fila, context, g.why, icon="QUESTION")
        if not g.completed:
            estilo.separador(caja, 0.3)
            dialogos.botones_guia(caja, g)

    def _estado_sync(self, layout, context):
        sc = context.scene
        if sc.amatista.origen == "borrador":
            fila = layout.row()
            fila.active = False
            fila.label(text="Borrador: el progreso no se envía", icon="INFO")
            return
        estado = practicas.ESTADO["sync"] or (
            practicas.SYNC_SIN_CUENTA if not practicas.vinculado() else ""
        )
        if not estado:
            return
        texto, propio = ESTADOS_SYNC.get(estado, ("", None))
        fila = layout.row(align=True)
        fila.active = estado == practicas.SYNC_GUARDADO
        if propio:
            fila.label(text=texto, icon_value=estilo.icono(propio))
        else:
            fila.label(text=texto, icon="ERROR" if estado == practicas.SYNC_ERROR else "INFO")
        if estado in (practicas.SYNC_PENDIENTE, practicas.SYNC_ERROR):
            fila.operator("amatista.sincronizar", text="", icon="FILE_REFRESH")
        if practicas.ESTADO["sync_detalle"] and estado != practicas.SYNC_GUARDADO:
            estilo.parrafo(layout, context, practicas.ESTADO["sync_detalle"], alerta=estado == practicas.SYNC_ERROR)

    def _elegir(self, layout, context):
        cuerpo = estilo.tarjeta(layout, "Elige una práctica", icono_propio="logo")
        estilo.parrafo(cuerpo, context, "Abre la práctica de tu lección o elige una de la lista. "
                       "Amatista revisará tu escena mientras trabajas.")
        if practicas.vinculado():
            estilo.boton_principal(cuerpo, "amatista.practica_actual", "Abrir mi lección actual", icon="IMPORT")
        catalogo = practicas.catalogo()
        for pid, meta in catalogo.items():
            caja = layout.box()
            fila = caja.row()
            fila.label(text=meta["title"], icon_value=estilo.icono("logo"))
            derecha = fila.row()
            derecha.alignment = "RIGHT"
            derecha.label(text=f"N{meta['level']}")
            if meta.get("description"):
                estilo.parrafo(caja, context, meta["description"])
            info = caja.row()
            info.active = False
            progreso = meta.get("progreso")
            texto = estilo.nivel_texto(meta["level"])
            if meta.get("minutes"):
                texto += f" · {meta['minutes']} min"
            if progreso:
                texto += f" · {progreso.get('progreso', 0):.0f} %"
            info.label(text=texto)
            boton = caja.row()
            boton.scale_y = 1.2
            boton.operator("amatista.abrir_practica", text="Empezar", icon="PLAY").practica_id = pid
        if not catalogo:
            layout.label(text="No hay prácticas disponibles.", icon="INFO")
        layout.operator("amatista.actualizar_catalogo", text="Actualizar lista", icon="FILE_REFRESH")
        if practicas.ESTADO["red"]:
            estilo.parrafo(layout, context, practicas.ESTADO["red"], icon="ERROR")


def _dibujar_detalle(layout, context, resultado):
    """Diagnóstico de un objetivo (solo modo desarrollador)."""
    if resultado is None:
        return
    d = resultado.details
    col = layout.column(align=True)
    col.scale_y = 0.8
    col.label(text=f"Validador: {resultado.validator}", icon="SCRIPT")
    if "expected" in d:
        esperado = d["expected"]
        if isinstance(esperado, dict):
            esperado = " – ".join(str(v) for v in (esperado.get("min"), esperado.get("max")) if v is not None)
        col.label(text=f"Esperado: {esperado}   Encontrado: {d.get('found', '—')}")
    if d.get("min") is not None and d.get("axis"):
        col.label(text=f"Eje {d['axis'].upper()}: entre {d['min']:g} y {d['max']:g}")
    for fallo in d.get("failed", [])[:4]:
        col.label(text=f"✗ {fallo.get('object')}: {fallo.get('value', fallo.get('reason', ''))}")
    objetos = d.get("objects")
    if objetos:
        col.label(text="Objetos: " + ", ".join(objetos[:6]) + ("…" if len(objetos) > 6 else ""))
    if d.get("generated_message"):
        col.label(text=f"Mensaje generado: {d['generated_message']}")


class AMATISTA_PT_objetivos(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_objetivos"
    bl_label = "Todos los pasos"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        visible = seccion(context, "practicar") or modo_autor(context)
        return visible and practicas.practica_activa(context) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="CHECKBOX_HLT")

    def draw(self, context):
        layout = self.layout
        practica = practicas.practica_activa(context)
        reporte = practicas.ESTADO["reporte"]
        if practica is None or reporte is None:
            return
        depurar = modo_autor(context) and not context.window_manager.amatista.vista_previa
        pistas = practicas.pistas(context)
        titulos = {t.id: (t.title or t.id) for t in practica.targets}
        for paso in reporte.steps:
            objetivo = practica.target(paso.target_id)
            propio = estilo.ICONO_ESTADO.get(paso.status, "pendiente")
            actual = paso.status == "actual"
            contenedor = layout.box() if actual or depurar else layout
            fila = contenedor.row(align=True)
            titulo = paso.title + ("  (extra)" if paso.optional else "")
            fila.label(text=titulo, icon_value=estilo.icono(propio))
            if objetivo.weight and not paso.optional:
                peso = fila.row()
                peso.alignment = "RIGHT"
                peso.active = False
                peso.label(text=f"{objetivo.weight:.0f}")
            if paso.status == "bloqueado":
                faltan = [titulos.get(r, r) for r in objetivo.requires]
                sub = contenedor.row()
                sub.active = False
                sub.label(text="Primero: " + ", ".join(faltan), icon="BLANK1")
                if not depurar:
                    continue
            if actual or depurar or paso.status == "pendiente":
                estilo.parrafo(contenedor, context, paso.message, icon="BLANK1", alerta=False)
            if actual and objetivo.tip:
                estilo.parrafo(contenedor, context, objetivo.tip, icon="INFO")
            reveladas = [h for h in objetivo.hints if h.level <= pistas.get(objetivo.id, 0)]
            for pista in reveladas:
                estilo.parrafo(contenedor, context, f"Pista {pista.level}: {pista.text}", icon="LIGHT")
            if actual and objetivo.hints and len(reveladas) < len(objetivo.hints):
                op = contenedor.operator(
                    "amatista.pista", text=f"Pista {len(reveladas) + 1} de {len(objetivo.hints)}",
                    icon_value=estilo.icono("pista"),
                )
                op.objetivo = objetivo.id
            if depurar:
                _dibujar_detalle(contenedor, context, reporte.result(objetivo.id))


class AMATISTA_PT_roles(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_roles"
    bl_label = "Asignar rol"
    bl_parent_id = "AMATISTA_PT_principal"

    @classmethod
    def poll(cls, context):
        practica = practicas.practica_activa(context)
        return seccion(context, "practicar") and practica is not None and bool(practica.roles)

    def draw_header(self, context):
        self.layout.label(text="", icon="BOOKMARKS")

    def draw(self, context):
        layout = self.layout
        practica = practicas.practica_activa(context)
        obj = context.active_object
        if obj is None:
            estilo.parrafo(layout, context, "Selecciona un objeto para decirle a Amatista qué es.", icon="RESTRICT_SELECT_OFF")
        else:
            rol = _motor.tagger.get_role(obj)
            fila = layout.row()
            fila.label(text=obj.name, icon="OBJECT_DATA")
            derecha = fila.row()
            derecha.alignment = "RIGHT"
            derecha.label(text=practica.role_label(rol) if rol else "Sin rol")
            layout.prop(context.scene.amatista, "rol_elegido", text="Es")
            fila = layout.row(align=True)
            fila.scale_y = 1.3
            fila.operator("amatista.asignar_rol", text="Asignar rol", icon="CHECKMARK")
            fila.operator("amatista.quitar_rol", text="", icon="X")
        conteo = autor.roles_en_escena(context)
        if conteo:
            col = layout.column(align=True)
            col.active = False
            for rol in practica.roles:
                col.label(text=f"{rol.label}: {len(conteo.get(rol.id, []))}", icon="DOT")


# --- Aprender y Mi curso (motor v3) -----------------------------------------------------------


def dibujar_mapa(layout, context, solo_siguiente=False):
    """El mapa de los cursos. Devuelve False si no hay plan de estudios."""
    plan = aprendizaje.plan()
    if plan is None:
        return False
    estados = aprendizaje.estados()
    siguiente = aprendizaje.siguiente()
    catalogo = practicas.catalogo()
    if siguiente:
        meta = catalogo.get(siguiente, {})
        encontrado = plan.locate(siguiente)
        cuerpo = estilo.tarjeta(layout, "Tu siguiente práctica", icono_propio="actual")
        if encontrado:
            curso, modulo = encontrado
            fila = cuerpo.row()
            fila.active = False
            fila.label(text=f"{curso.title} › Módulo {modulo.number}")
        tema = temas.tema_de_practica(siguiente)
        cuerpo.label(text=f"{tema['nombre']} · con {tema['mascota']['nombre']}", icon=icono_tema(tema))
        cuerpo.label(text=meta.get("title") or siguiente, icon="PLAY")
        if meta.get("description"):
            estilo.parrafo(cuerpo, context, meta["description"])
        estilo.boton_principal(cuerpo, "amatista.abrir_practica", "Empezar", icon="PLAY", escala=1.5,
                               practica_id=siguiente)
    elif estados and all(e == "completado" for e in estados.values() if e != "proximamente"):
        cuerpo = estilo.tarjeta(layout, "¡Terminaste los cursos disponibles!", icono_propio="celebrar")
        estilo.parrafo(cuerpo, context, "Los cursos Intermedio y Avanzado llegan pronto. Mientras, repite una "
                       "práctica para afianzarla.")
    if solo_siguiente:
        fila = layout.row()
        fila.operator("amatista.pestana", text="Ver el mapa del curso", icon="OUTLINER_COLLECTION").pestana = "curso"
        return True
    for curso in plan.courses:
        # Un módulo cuenta como hecho cuando su práctica de cierre está completada.
        hechas = sum(1 for m in curso.modules if estados.get(m.practice) == "completado")
        cuerpo = estilo.tarjeta(
            layout, curso.title, icon="OUTLINER_COLLECTION",
            derecha=f"{hechas}/{len(curso.modules)}" if curso.modules else "Pronto",
        )
        fila = cuerpo.row()
        fila.active = False
        fila.label(text=DIFICULTAD_TEXTO.get(curso.difficulty, curso.difficulty))
        if curso.status == "proximamente" or not curso.modules:
            estilo.parrafo(cuerpo, context, curso.description or "Próximamente.", icon="TIME")
            continue
        if curso.modules:
            estilo.barra(cuerpo, hechas / len(curso.modules), f"{hechas} de {len(curso.modules)} módulos")
        for modulo in curso.modules:
            fila = cuerpo.row()
            fila.label(text=f"{modulo.number}. {modulo.title}")
            tema = temas.tema_de_practica(modulo.practice or modulo.explore)
            derecha = fila.row()
            derecha.alignment = "RIGHT"
            derecha.active = False
            derecha.label(text=tema["nombre"], icon=icono_tema(tema))
            # Teoría y Blender se intercalan: exploración a mitad del módulo y práctica de cierre.
            for practica_id in modulo.sequence:
                estado = estados.get(practica_id, "bloqueado")
                propio, icono = ICONO_PLAN.get(estado, ("pendiente", None))
                fila = cuerpo.row(align=True)
                texto = "Exploración" if practica_id == modulo.explore else (modulo.project or "Práctica de cierre")
                if propio:
                    fila.label(text=texto, icon_value=estilo.icono(propio))
                else:
                    fila.label(text=texto, icon=icono)
                if estado in ("disponible", "completado"):
                    op = fila.operator("amatista.abrir_practica", text="Repetir" if estado == "completado" else "Empezar",
                                       icon="FILE_REFRESH" if estado == "completado" else "PLAY")
                    op.practica_id = practica_id
    return True


class AMATISTA_PT_aprender(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_aprender"
    bl_label = "Aprender"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return seccion(context, "aprender")

    def draw(self, context):
        layout = self.layout
        practica = practicas.practica_activa(context)
        if practica is None:
            cuerpo = estilo.tarjeta(layout, "Teoría a tu ritmo", icono_propio="logo")
            estilo.parrafo(cuerpo, context, "Cada práctica trae ideas cortas que aparecen justo cuando las necesitas. "
                           "Abre una práctica para verlas aquí.")
            layout.operator("amatista.pestana", text="Ir a Mi curso", icon="OUTLINER_COLLECTION").pestana = "curso"
            return
        if not practica.pills:
            estilo.parrafo(layout, context, "Esta práctica no trae teoría: la guía de Practicar te acompaña.", icon="INFO")
            return
        principal = aprendizaje.pildora_principal()
        if principal is not None:
            fila = layout.row()
            fila.label(text="Ahora mismo", icon_value=estilo.icono("actual"))
            aprender.tarjeta_pildora(layout, context, principal, grande=True)
        pendientes = aprendizaje.repasos_pendientes(practica)
        if pendientes:
            caja = estilo.tarjeta(layout, f"Repaso: {len(pendientes)} pregunta(s)", icon="RECOVER_LAST")
            estilo.parrafo(caja, context, "Ideas de prácticas anteriores que conviene recordar hoy.")
            estilo.boton_principal(caja, "amatista.repaso", "Repasar ahora", icon="PLAY", escala=1.25)
        vistas = aprendizaje.vistas(practica.id)
        cuerpo = estilo.seccion(layout, context, "amatista_ideas", f"Ideas de esta práctica ({len(practica.pills)})",
                                icon="HELP")
        if cuerpo is not None:
            for pildora in practica.pills:
                if principal is not None and pildora.id == principal.id:
                    continue
                fila = cuerpo.row(align=True)
                fila.active = pildora.id not in vistas
                fila.operator("amatista.pildora", text=pildora.title, icon=aprender.icono_visual(pildora),
                              emboss=False).pildora = pildora.id
                if pildora.id in vistas:
                    fila.label(text="", icon="CHECKMARK")
        dominadas = len(aprendizaje.dominadas())
        if dominadas:
            fila = layout.row()
            fila.active = False
            fila.label(text=f"Ideas que ya dominas: {dominadas}", icon="FUND")


class AMATISTA_PT_curso(_Base, bpy.types.Panel):
    bl_idname = "AMATISTA_PT_curso"
    bl_label = "Mi curso"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return seccion(context, "curso")

    def draw(self, context):
        layout = self.layout
        if not dibujar_mapa(layout, context):
            estilo.parrafo(layout, context, "No encontramos el plan de estudios en este paquete.", icon="ERROR")
        fila = layout.row(align=True)
        fila.operator("amatista.abrir_plataforma", text="Ver en la plataforma", icon="URL").ruta = "#/cursos"
        fila.operator("amatista.actualizar_catalogo", text="", icon="FILE_REFRESH")


# --- Modo Desarrollador (Amatista Author) ---------------------------------------------------


class _Autor(_Base):
    bl_parent_id = "AMATISTA_PT_principal"

    @classmethod
    def poll(cls, context):
        return modo_autor(context) and not context.window_manager.amatista.vista_previa


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


CLASES = (
    AMATISTA_PT_principal,
    AMATISTA_PT_aprender,
    AMATISTA_PT_practica,
    AMATISTA_PT_curso,
    AMATISTA_PT_roles,
    AMATISTA_PT_objetivos,
    AMATISTA_PT_autor_borrador,
    AMATISTA_PT_autor_tagger,
    AMATISTA_PT_autor_inspector,
    AMATISTA_PT_autor_objetivos,
    AMATISTA_PT_autor_depurador,
    AMATISTA_PT_autor_teoria,
    AMATISTA_PT_autor_publicar,
)
