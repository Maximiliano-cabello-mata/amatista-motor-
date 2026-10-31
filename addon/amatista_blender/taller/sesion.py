"""La sesión del taller: qué actividad hay, en qué va el alumno y qué viene después.

Una actividad a la vez (Mira, Hazlo conmigo, Hazlo tú, Úsalo, Recuérdalo,
Demuéstralo o el reto del módulo). El plan lo decide el motor con el
modelo del alumno (amatista_engine.taller.planear); aquí se abre, se revisa
mientras el alumno trabaja y se registra el intento al terminar:

    abrir() → empezar(actividad) → [Mira: demo.empezar → «Ahora tú»]
                                  → [trabajando: evaluar() en cada cambio
                                     → lograr() → «Siguiente» → abrir()]

- Las actividades cortas pasan en la escena del taller (escena.py) y se
  revisan con la práctica generada (practica_de_actividad) más el molde
  pieza por pieza (revisar_molde), que dice qué falta sobre el modelo.
- El proyecto (Úsalo) es la práctica de siempre, en su escena y con su
  sincronización (practicas.py); el taller la envuelve: dibuja su molde en
  los niveles 1 y 2, muestra la pieza que toca y la cuenta como intento de
  todas las habilidades del taller al terminarla.
- Las pistas suben un escalón a la vez (Qué falta → Con qué → Cómo →
  Mírame) y las teclas tienen freno: se intentan antes de verse.

Motor 6:

- **La plataforma marca la ruta** (RUTA, amatista_engine.taller.etapas): la
  lección manda su etapa (exploración o práctica) y Blender no sale de ella.
  Al cumplirla no sigue solo: la tarjeta dice «Vuelve a la plataforma» y la
  lección se da por hecha. Con la cuenta conectada, en modo alumno, Blender
  no deja elegir módulos ni empezar talleres por su cuenta.
- **«Mira» y «Mírame» muestran ESTA actividad** (pasos_de_actividad): las
  piezas de su molde, o la pieza que toca en el proyecto, con el gesto de la
  habilidad. Nunca objetos de la demostración genérica.
- **La herramienta brilla** (vista/brillo.py) al pedir «¿Con qué?» o al
  quedarse atascado: dónde está, nunca cómo se usa.
"""
import dataclasses
import time

import bpy
from bpy.app.handlers import persistent

from .. import _motor, ajustes, enfoque, enlace
from . import acompanar, datos, demo, escena

taller = _motor.taller
ayudas = _motor.taller.ayudas
etapas = _motor.taller.etapas

MIRANDO, TRABAJANDO, LOGRADA, PAUSA = "mirando", "trabajando", "lograda", "pausa"
PRESENTANDO = "presentando"  # motor 6.1: la ficha de una herramienta nueva antes de la actividad
CALMA = 0.35  # s sin cambios antes de revisar
MENSAJE_DURA = 6.0

SESION = {}
SALTOS = {}  # habilidad → veces seguidas que se saltó (se borra al lograrla)
SALTOS_PARA_CAMBIAR = 2


def _vacia():
    return {
        "taller": "",
        "actividad": None,
        "practica": None,  # PracticeDefinition generada (None en Mira y en el proyecto)
        "estado": "",
        "inicio": 0.0,
        "entrada": 0.0,  # cuándo entró la tarjeta (animación)
        "logro_en": 0.0,
        "pausa_desde": 0.0,
        "pausado": 0.0,
        "escalera": None,
        "pista": None,
        "ayuda": 0,  # la ayuda más alta que se usó en esta actividad
        "revision": None,  # RevisionMolde
        "reporte": None,
        "llenas": 0,
        "cumplidos": 0,
        "equivocadas": set(),
        "cambios": {},  # {habilidad: (fase antes, fase después)} del último logro
        "sucio": False,
        "ultimo_cambio": 0.0,
        "mensaje": "",
        "mensaje_hasta": 0.0,
        "ofrecida": -1,  # escalón que ya se ofreció por estar atascado
        "mirame": False,  # la demo de «Mírame» está corriendo dentro de una actividad
        "proyecto": False,
        "molde_proyecto": (),
        "repaso_ofrecido": False,
        "plan": None,
        "volver": False,  # motor 6: la etapa de la plataforma se cumplió; lo que sigue es allá
    }


SESION.update(_vacia())

# Motor 6: la etapa que mandó la plataforma (sobrevive a cada actividad; la cambia la próxima orden).
RUTA = {"etapa": None, "leccion": "", "cumplida": False}


# --- Consultas ------------------------------------------------------------------------------


def activa():
    return SESION["actividad"] is not None


def actividad():
    return SESION["actividad"]


def estado():
    return SESION["estado"]


def modo_alumno():
    wm = getattr(bpy.context, "window_manager", None)
    sesion = getattr(wm, "amatista", None) if wm is not None else None
    if sesion is None:
        return True
    return sesion.modo == "alumno" or not ajustes.es_desarrollador()


def manda_la_plataforma():
    """En modo alumno con la cuenta conectada, la ruta la marca la plataforma (Blender no elige módulos)."""
    p = ajustes.prefs()
    return modo_alumno() and bool(p and p.token)


def etapa():
    return RUTA["etapa"]


def fijar_etapa(taller_id, nombre="", habilidades=(), leccion=""):
    """La orden de la plataforma dice qué etapa del taller toca (vacío: la práctica completa)."""
    c = datos.catalogo()
    t = c.taller(taller_id or "") if c is not None else None
    RUTA.update(etapa=etapas.etapa_de(t, nombre, habilidades) if t is not None else None,
                leccion=str(leccion or "")[:120], cumplida=False)
    return RUTA["etapa"]


def ruta_de_vuelta():
    """La dirección de la lección en la plataforma (para «Volver a la plataforma»)."""
    c = datos.catalogo()
    e = RUTA["etapa"]
    t = c.taller(e.taller) if c is not None and e is not None else None
    leccion = RUTA["leccion"] or (t.leccion if t is not None else "")
    if t is None or not leccion:
        return "#/"
    return f"#/curso/{t.curso}/leccion/{leccion}"


def volver_a_la_plataforma(forzar=False):
    """Motor 6.1: si la plataforma está abierta, la lección ya siguió sola y no se abre otra pestaña."""
    from .. import cuenta, plataforma

    if plataforma.viva() and not forzar:
        return plataforma.frase_al_volver(RUTA["leccion"]) or "Sigue en tu navegador: tu lección ya está ahí."
    if not cuenta.abrir_plataforma(plataforma.ruta() if plataforma.viva() else ruta_de_vuelta()):
        return "Abre la plataforma en tu navegador para seguir."
    return "Sigue en la plataforma: tu avance ya está allá."


def cubre(sc):
    """¿La escena que se ve es la de la actividad del taller? (entonces la tarjeta es la del taller)."""
    a = SESION["actividad"]
    if a is None or sc is None:
        return False
    if SESION["proyecto"]:
        return sc.amatista.practica_id == a.practica_id
    return escena.es_del_taller(sc)


def habilidad_actual():
    """La habilidad de la actividad o, en el proyecto, la de la pieza que toca."""
    c = datos.catalogo()
    a = SESION["actividad"]
    if c is None or a is None:
        return None
    if a.habilidad:
        return c.habilidad(a.habilidad)
    r = SESION["revision"]
    pieza = r.pieza_actual if r is not None else None
    if pieza is not None and pieza.habilidad and c.habilidad(pieza.habilidad) is not None:
        return c.habilidad(pieza.habilidad)
    return next((c.habilidad(h) for h in a.habilidades if c.habilidad(h) is not None), None)


def pieza_actual():
    r = SESION["revision"]
    return r.pieza_actual if r is not None else None


def molde_visible():
    """(piezas, estados, índice actual, solo la marca) para dibujar, o None."""
    a = SESION["actividad"]
    if a is None or SESION["estado"] in ("", MIRANDO):
        return None
    if SESION["proyecto"]:
        piezas = SESION["molde_proyecto"]
        marca = False
    else:
        piezas = a.molde
        marca = a.dibujo == "marca"
    if not piezas:
        return None
    r = SESION["revision"]
    estados = [p.estado for p in r.piezas] if r is not None and len(r.piezas) == len(piezas) else ["vacia"] * len(piezas)
    actual = r.actual if r is not None else 0
    return piezas, estados, actual, marca


def avisar(texto, segundos=MENSAJE_DURA):
    SESION["mensaje"] = texto
    SESION["mensaje_hasta"] = time.time() + segundos
    _redibujar()


def mensaje():
    return SESION["mensaje"] if time.time() < SESION["mensaje_hasta"] else ""


def segundos_trabajados():
    if not SESION["inicio"]:
        return 0.0
    pausa = (time.time() - SESION["pausa_desde"]) if SESION["estado"] == PAUSA else 0.0
    return max(0.0, time.time() - SESION["inicio"] - SESION["pausado"] - pausa)


def espera_teclas():
    """Segundos que faltan para poder pedir «Cómo» (0 si ya se puede o no aplica)."""
    e = SESION["escalera"]
    if e is None:
        return 0.0
    _puede, espera = ayudas.puede_pedir(e, time.time())
    return espera


def siguiente_pista():
    """(nombre del siguiente escalón, ¿se puede pedir ya?) o (None, False) si no quedan."""
    e = SESION["escalera"]
    if e is None or SESION["actividad"] is None:
        return None, False
    nivel = e.nivel + 1
    if nivel > e.techo:
        return None, False
    puede, _espera = ayudas.puede_pedir(e, time.time())
    return ayudas.NOMBRES.get(nivel, ""), puede


# --- Abrir y empezar ------------------------------------------------------------------------


def abrir(context=None, taller_id="", actividad_id="", elegida="", repasar=True):
    """Abre el taller (el que sigue si no se dice) en la actividad que toca o en la pedida."""
    context = context or bpy.context
    c = datos.catalogo()
    if c is None:
        return datos.ESTADO["catalogo_error"] or "No se encontró el catálogo de habilidades."
    taller_id = taller_id if c.taller(taller_id or "") is not None else datos.taller_inicial()
    if not taller_id:
        return "No hay talleres en este paquete."
    ahora = time.time()
    estado_alumno = datos.estado_alumno()
    a = None
    e = RUTA["etapa"]
    if e is not None and e.taller != taller_id:
        RUTA.update(etapa=None, cumplida=False)  # otro taller: la etapa era de otra lección
        e = None
    if actividad_id:
        a = taller.actividad_por_id(c, taller_id, actividad_id, estado_alumno, ahora)
        if a is None:
            return "Esa actividad ya no existe en el taller."
        if not etapas.permitida(e, a):
            actividad_id, a = "", None  # una orden vieja no saca al alumno de la etapa de su lección
    if a is None and e is not None and not elegida:
        a, p, cumplida = etapas.siguiente(c, e, estado_alumno, ahora, datos.completadas())
        if a is None:
            RUTA["cumplida"] = cumplida
            return _etapa_cumplida(taller_id, p)
    elif not actividad_id:
        # «Recuérdalo»: un minuto con lo que toca repasar, una vez por sesión. Se puede saltar.
        pendientes = datos.repasos_pendientes() if repasar and not SESION["repaso_ofrecido"] else []
        if pendientes:
            SESION["repaso_ofrecido"] = True
            t_rep, h_rep = pendientes[0]
            a = taller.actividad_de_repaso(c, t_rep, h_rep)
        else:
            p = datos.plan(taller_id, elegida)
            a = p.actual if p is not None else None
            if a is None:
                datos.recordar_taller(taller_id)
                SESION.update(_vacia(), repaso_ofrecido=True, taller=taller_id, plan=p)
                _redibujar()
                return "Terminaste este taller: tu pieza ya está en la isla."
    datos.recordar_taller(a.taller)
    return empezar(context, a)


def _etapa_cumplida(taller_id, plan=None):
    """La etapa de la plataforma ya está: Blender no sigue solo, la tarjeta manda a la plataforma."""
    a = SESION["actividad"]
    SESION.update(estado=LOGRADA, volver=True, taller=taller_id, plan=plan or datos.plan(taller_id),
                  logro_en=SESION["logro_en"] or time.time())
    _al_cambiar_estado()
    if a is None:
        return "Listo por ahora en Blender: sigue en la plataforma."
    return None


def _revisar_etapa(a):
    """Después de un logro: ¿se cumplió la etapa que mandó la plataforma?"""
    e = RUTA["etapa"]
    if e is None or a is None or a.taller != e.taller:
        return False
    if etapas.cumplida(e, SESION["plan"] or datos.plan(a.taller)):
        RUTA["cumplida"] = True
        SESION["volver"] = True
        return True
    return False


def _pasos_demo(h, a=None):
    """Los pasos de «Mira» o «Mírame» para ESTA actividad (motor 6), no la demostración genérica."""
    try:
        if a is not None and SESION["proyecto"]:
            pieza = pieza_actual()
            if pieza is not None:
                return taller.pasos_de_actividad(h.demo, [taller.pieza_de_revision(pieza)])
        if a is not None and a.tipo != taller.MIRA and (a.molde or a.piezas):
            piezas = a.molde or a.piezas
            pieza = pieza_actual()
            if pieza is not None and pieza.estado != "llena" and 0 <= pieza.indice < len(piezas):
                piezas = [piezas[pieza.indice]]  # la que le cuesta, no el ejercicio entero
            return taller.pasos_de_actividad(h.demo, piezas, a.inicio)
        v = h.variaciones[0] if h.variaciones else None
        if v is not None and v.molde:
            return taller.pasos_de_actividad(h.demo, v.molde, tuple((v.inicio or {}).get("objetos") or ()))
    except Exception as error:  # noqa: BLE001 - sin pasos propios queda la demostración de la habilidad
        print(f"[Amatista] Demostración de la actividad: {error}")
    return h.demo


def _practica_generada(a):
    datos_practica = taller.practica_de_actividad(datos.catalogo(), a)
    if datos_practica is None:
        return None
    resultado = _motor.practica.compile_practice(datos_practica)
    if resultado.practice is None:
        raise ValueError(resultado.errors[0] if resultado.errors else "La actividad no se pudo armar")
    return resultado.practice


def empezar(context, a):
    """Empieza una actividad (Actividad del motor)."""
    from .. import fichas

    context = context or bpy.context
    demo.detener(llamar=False)
    if fichas.modo() == fichas.PRESENTAR:
        fichas.cerrar(marcar=False)  # la presentación era de la actividad anterior
    _apagar_brillo()
    repaso = SESION["repaso_ofrecido"]
    SESION.update(_vacia(), repaso_ofrecido=repaso)
    ahora = time.time()
    escalera = ayudas.escalera_para(a.fase, ahora, reto=a.tipo in (taller.RETO, taller.REPASO, taller.PRUEBA))
    SESION.update(taller=a.taller, actividad=a, inicio=ahora, entrada=ahora,
                  escalera=dataclasses.replace(escalera, techo=a.techo, freno=a.freno),
                  plan=datos.plan(a.taller))
    acompanar.reiniciar(ahora)  # motor 6.2: el ánimo y la luz son de esta actividad
    if a.habilidad and SALTOS.get(a.habilidad):
        acompanar.salto(SALTOS[a.habilidad])
    if a.tipo == taller.PROYECTO:
        return _empezar_proyecto(context, a)
    practica = _practica_generada(a) if a.revisa else None
    sc = escena.preparar(context, a)
    SESION.update(practica=practica)
    try:
        if practica is not None:
            enfoque.al_abrir_practica(practica, True)
    except Exception as error:  # noqa: BLE001 - enfocar es comodidad
        print(f"[Amatista] No se pudo enfocar Blender: {error}")
    try:
        escena.encuadrar(context, a.molde or a.piezas or a.inicio)
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] No se pudo encuadrar la vista: {error}")
    # Motor 6.1: una herramienta que el alumno nunca vio se presenta antes (su ficha, iluminada en su lugar).
    from .. import fichas

    from .. import guion

    # Motor 7: con el guion no se abre una ficha encima antes de la actividad (la herramienta la dice el paso).
    cola = () if guion.preferido() and modo_alumno() else fichas.por_presentar(a)
    if cola and fichas.mostrar(cola, fichas.PRESENTAR):
        SESION["estado"] = PRESENTANDO
        _al_cambiar_estado()
        return None
    return _arrancar(context, a, sc)


def despues_de_presentar(context=None):
    """Las fichas de la actividad ya se vieron: ahora sí empieza (Mira o el trabajo)."""
    a = SESION["actividad"]
    if a is None or SESION["estado"] != PRESENTANDO:
        return None
    SESION["entrada"] = time.time()
    context = context or bpy.context
    return _arrancar(context, a, escena.escena_del_taller(context, cambiar=False))


def _arrancar(context, a, sc):
    sc = sc or getattr(context, "scene", None) or bpy.context.scene
    if a.tipo == taller.MIRA:
        SESION["estado"] = MIRANDO
        h = datos.catalogo().habilidad(a.habilidad)
        if h is None or not demo.empezar(h, _demo_termino, sc, pasos=_pasos_demo(h, a)):
            _demo_termino(False)
    else:
        SESION["estado"] = TRABAJANDO
        evaluar(context)
    _al_cambiar_estado()
    return None


def _empezar_proyecto(context, a):
    from .. import practicas

    SESION.update(proyecto=True, estado=TRABAJANDO)
    abierta = practicas.practica_activa(context)
    if abierta is not None and abierta.id == a.practica_id and practicas.escena(context).amatista.origen != "borrador":
        al_abrir_practica(abierta)
        practicas.evaluar_pronto()
    else:
        def lista(error):
            if error:
                avisar(f"No se pudo abrir el proyecto: {error}")

        practicas.abrir_por_id(context, a.practica_id, lista)
    _al_cambiar_estado()
    return None


def al_abrir_practica(practica, origen="paquete"):
    """practicas.activar() abrió una práctica: si es el proyecto de un taller, el taller la acompaña."""
    if origen == "borrador" or not modo_alumno():
        return False
    c = datos.catalogo()
    t = c.taller_de_proyecto(practica.id) if c is not None else None
    a = SESION["actividad"]
    if t is None:
        # Motor 6.2: también si lo de antes era el proyecto de OTRA práctica (antes su molde seguía
        # dibujándose encima de la práctica nueva).
        if a is not None and (not SESION["proyecto"] or a.practica_id != practica.id):
            demo.detener(llamar=False)
            SESION.update(_vacia(), repaso_ofrecido=SESION["repaso_ofrecido"])
            _redibujar()
        return False
    if a is not None and SESION["proyecto"] and a.practica_id == practica.id:
        SESION["molde_proyecto"] = taller.molde_del_proyecto(practica)
        return True
    nueva = taller.actividad_de_proyecto(t)
    if a is None or a.id != nueva.id:
        demo.detener(llamar=False)
        repaso = SESION["repaso_ofrecido"]
        ahora = time.time()
        SESION.update(_vacia(), repaso_ofrecido=repaso, taller=t.id, actividad=nueva, inicio=ahora, entrada=ahora,
                      estado=TRABAJANDO, proyecto=True, plan=datos.plan(t.id),
                      escalera=dataclasses.replace(ayudas.escalera_para(taller.SOLA, ahora), techo=nueva.techo))
        datos.recordar_taller(t.id)
        acompanar.reiniciar(ahora)
    SESION["molde_proyecto"] = taller.molde_del_proyecto(practica)
    _al_cambiar_estado()
    return True


# --- Revisar mientras trabaja -----------------------------------------------------------------


def _apagar_brillo():
    try:
        from .vista import brillo

        brillo.apagar()
    except Exception:  # noqa: BLE001 - sin vista (CI) no hay brillo
        pass



def _avanzo(llenas, cumplidos):
    if llenas > SESION["llenas"] or cumplidos > SESION["cumplidos"]:
        SESION["escalera"] = ayudas.avance(SESION["escalera"], time.time())
        SESION["ofrecida"] = -1
        _apagar_brillo()
        acompanar.avanzo()
        acompanar.apagar_brillo_auto()
    elif llenas < SESION["llenas"]:
        acompanar.retrocedio()  # motor 6.2: una pieza que estaba y se deshizo
    SESION["llenas"], SESION["cumplidos"] = llenas, cumplidos


def _equivocadas(revision):
    """Una pieza que aparece con la forma equivocada cuenta como intento fallido (abre «Cómo»)."""
    for p in revision.piezas:
        if p.estado == "equivocada" and p.indice not in SESION["equivocadas"]:
            SESION["equivocadas"].add(p.indice)
            SESION["escalera"] = ayudas.fallo(SESION["escalera"])
            acompanar.fallo()


def evaluar(context=None):
    """Revisa la actividad corta (no el proyecto: ese lo revisa practicas.evaluar)."""
    from .. import practicas

    a = SESION["actividad"]
    SESION["sucio"] = False
    if a is None or SESION["proyecto"] or SESION["estado"] != TRABAJANDO or SESION["practica"] is None:
        return None
    context = context or bpy.context
    sc = getattr(context, "scene", None) or bpy.context.scene
    if not escena.es_del_taller(sc):
        return None
    foto = practicas.capturar(sc)
    reporte = _motor.MOTOR.evaluate(SESION["practica"], foto)
    revision = taller.revisar_molde(a.piezas, foto, a.modo, a.nivel) if a.piezas else None
    SESION.update(reporte=reporte, revision=revision)
    try:
        from .. import guion

        guion.al_evaluar(context, SESION["practica"], reporte)  # motor 7
    except Exception as error:  # noqa: BLE001 - el guion nunca impide revisar
        print(f"[Amatista] Guion: {error}")
    if revision is not None:
        _equivocadas(revision)
    _avanzo(revision.llenas if revision is not None else 0, sum(1 for r in reporte.results if r.passed))
    if reporte.completed:
        lograr(foto)
    _redibujar()
    enlace.latir_pronto()
    return reporte


def al_evaluar_practica(context, practica, foto, reporte):
    """practicas.evaluar() revisó una práctica: si es el proyecto del taller, el molde y la pieza que toca."""
    a = SESION["actividad"]
    if a is None or not SESION["proyecto"] or a.practica_id != practica.id:
        return False
    SESION["reporte"] = reporte
    try:
        revision = taller.revisar_proyecto(practica, foto, con_molde=bool(SESION["molde_proyecto"]))
    except Exception as error:  # noqa: BLE001 - el molde nunca impide evaluar
        revision = None
        print(f"[Amatista] Molde del proyecto: {error}")
    SESION["revision"] = revision
    if revision is not None:
        _equivocadas(revision)
    _avanzo(revision.llenas if revision is not None else 0, sum(1 for r in reporte.results if r.passed))
    if reporte.completed and SESION["estado"] == TRABAJANDO:
        lograr(None, practica=practica)
    _redibujar()
    return True


def lograr(foto=None, practica=None):
    """La actividad salió: el intento al modelo del alumno y la tarjeta de logro."""
    a = SESION["actividad"]
    if a is None or SESION["estado"] == LOGRADA:
        return
    escena_dict = None
    if foto is not None and a.revisa and not SESION["proyecto"]:
        try:
            escena_dict = _motor.foto.scene_to_dict(foto)
        except Exception:  # noqa: BLE001 - sin foto el servidor confía en el resultado
            escena_dict = None
    molde = a.dibujo == "molde" or (SESION["proyecto"] and bool(SESION["molde_proyecto"]))
    cambios = datos.registrar(a, True, SESION["ayuda"], molde, segundos_trabajados(), escena_dict)
    SALTOS.pop(a.habilidad, None)
    SESION.update(estado=LOGRADA, logro_en=time.time(), cambios=cambios, pista=None)
    if a.tipo == taller.PROYECTO:
        try:
            from . import isla

            sc = bpy.context.scene
            if sc is not None and sc.amatista.practica_id == a.practica_id:
                isla.guardar_pieza(sc, a.taller)
        except Exception as error:  # noqa: BLE001 - la isla es un extra: el logro queda igual
            print(f"[Amatista] No se pudo guardar la pieza de la isla: {error}")
    SESION["plan"] = datos.plan(a.taller)
    _revisar_etapa(a)
    _al_cambiar_estado()


def frase_logro():
    """Qué sabe hacer ahora (no «¡Genial!»): la tarjeta y la plataforma lo muestran."""
    a = SESION["actividad"]
    if a is None:
        return ""
    c = datos.catalogo()
    if SESION["volver"]:
        from .. import plataforma

        # Motor 6.1: con la plataforma abierta, la lección ya avanzó sola: se dice a dónde.
        dicho = plataforma.frase_al_volver(RUTA["leccion"])
        if dicho:
            return dicho
        e = RUTA["etapa"]
        if e is not None and e.nombre == etapas.EXPLORACION:
            return "Exploración lista. Vuelve a la plataforma: ahora viene el porqué."
        return "Listo por ahora en Blender. Vuelve a la plataforma para seguir tu lección."
    if a.tipo == taller.MIRA:
        return "Ahora hazlo tú: el molde te dice dónde va cada pieza."
    if a.tipo == taller.PROYECTO:
        isla = c.taller(a.taller).isla if c is not None and c.taller(a.taller) is not None else {}
        return isla.get("texto") or "Tu proyecto ya está en tu isla."
    if a.tipo == taller.RETO:
        return "Lo hiciste sin molde ni teclas: este módulo es tuyo."
    titulo = a.titulo
    for hid, (antes, despues) in (SESION["cambios"] or {}).items():
        if antes == despues:
            continue
        if despues == taller.SOLA:
            return f"«{titulo}» ya te sale sola."
        if despues == taller.DOMINADA:
            return f"Dominas «{titulo}». Volverá en unos días para que no se olvide."
        if despues == taller.ACOMPANADA:
            return f"«{titulo}» va tomando forma."
    if a.tipo == taller.REPASO:
        return f"Todavía recuerdas «{titulo}»."
    return f"Una vez más «{titulo}»: cada repetición la fija."


# --- Lo que pide el alumno --------------------------------------------------------------------


def siguiente(context=None):
    if SESION["volver"]:
        return volver_a_la_plataforma()
    a = SESION["actividad"]
    tid = a.taller if a is not None else SESION["taller"]
    return abrir(context, tid)


def otra_vez(context=None):
    a = SESION["actividad"]
    if a is None:
        return abrir(context)
    if SESION["proyecto"]:
        return None
    return empezar(context, a)


def volver(context=None):
    """De vuelta a la escena de la actividad (el alumno se fue a otra escena), sin empezar de nuevo."""
    from .. import practicas

    context = context or bpy.context
    a = SESION["actividad"]
    if a is None or cubre(getattr(context, "scene", None)):
        return None
    if SESION["proyecto"]:
        practicas.abrir_por_id(context, a.practica_id)
        return None
    escena.escena_del_taller(context, cambiar=True)
    SESION["sucio"], SESION["ultimo_cambio"] = True, 0.0
    _al_cambiar_estado()
    return None


def _otra_habilidad(a):
    """La siguiente habilidad del taller que todavía no está lista (para no quedarse atorado en una)."""
    p = datos.plan(a.taller)
    if p is None:
        return ""
    dentro = etapas.habilidades_de_etapa(RUTA["etapa"], [h.id for h in p.habilidades])
    return next((h.id for h in p.habilidades if not h.lista and h.id != a.habilidad and h.id in dentro), "")


def saltar(context=None):
    """No le salió (o no quiere): cuenta como intento sin acierto, salvo en Mira y en el repaso.

    Saltar dos veces seguidas la misma habilidad pasa a otra del taller: la
    saltada vuelve después (nunca se queda uno atorado en la misma).
    """
    a = SESION["actividad"]
    if a is None:
        return None
    if SESION["estado"] == TRABAJANDO and a.revisa and a.tipo != taller.REPASO and not SESION["proyecto"]:
        datos.registrar(a, False, SESION["ayuda"], a.dibujo == "molde", segundos_trabajados())
    if a.habilidad and a.tipo in (taller.CONMIGO, taller.TU):
        SALTOS[a.habilidad] = SALTOS.get(a.habilidad, 0) + 1
        if SALTOS[a.habilidad] >= SALTOS_PARA_CAMBIAR:
            SALTOS[a.habilidad] = 0
            otra = _otra_habilidad(a)
            if otra:
                texto = abrir(context, a.taller, elegida=otra)
                return texto or f"Probemos otra cosa. «{a.titulo}» vuelve más tarde."
    return siguiente(context)


def pausar():
    if SESION["estado"] in (TRABAJANDO, MIRANDO) and SESION["actividad"] is not None:
        if SESION["estado"] == MIRANDO:
            demo.detener(llamar=False)
        SESION["antes_de_pausa"] = SESION["estado"]
        SESION.update(estado=PAUSA, pausa_desde=time.time())
        _al_cambiar_estado()
    return None


def seguir(context=None):
    if SESION["estado"] != PAUSA:
        return None
    SESION["pausado"] += time.time() - SESION["pausa_desde"]
    antes = SESION.pop("antes_de_pausa", TRABAJANDO)
    if antes == MIRANDO:
        return empezar(context, SESION["actividad"])
    SESION.update(estado=TRABAJANDO, entrada=time.time())
    SESION["escalera"] = ayudas.avance(SESION["escalera"], time.time())  # la pausa no cuenta como atascado
    evaluar(context)
    _al_cambiar_estado()
    return None


def _poner_herramienta(context, h):
    """«Con qué»: la herramienta queda elegida en la barra T, que Blender ilumina."""
    if h is None or bpy.app.background:
        return
    from ..interfaz.herramientas import _vista_3d

    try:
        from .vista import brillo

        brillo.encender(h.herramientas)  # motor 6: dónde está, nunca cómo se usa
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Brillo: {error}")
    registro = _motor.MOTOR.tools
    for hid in h.herramientas:
        herramienta = registro.get(hid) if registro is not None else None
        accion = (herramienta.action or {}) if herramienta is not None else {}
        if "tool" not in accion:
            continue
        ventana, area, region = _vista_3d(context)
        if area is None:
            return
        try:
            with context.temp_override(window=ventana, area=area, region=region):
                bpy.ops.wm.tool_set_by_id(name=accion["tool"])
        except (RuntimeError, TypeError) as error:
            print(f"[Amatista] No se pudo elegir la herramienta {hid}: {error}")
        return


def pedir_pista(context=None):
    """El siguiente escalón de la escalera (Qué falta → Con qué → Cómo → Mírame)."""
    context = context or bpy.context
    e = SESION["escalera"]
    if e is None or SESION["estado"] != TRABAJANDO:
        return None
    nueva, nivel, espera = ayudas.pedir_pista(e, time.time())
    if nivel is None:
        if espera > 0:
            avisar(f"Inténtalo un poco más: en {int(espera) + 1} s te muestro las teclas.")
        else:
            avisar("Aquí no hay más pistas: tú puedes.")
        return None
    h = habilidad_actual()
    pista = ayudas.pista_para(nivel, h, pieza_actual())
    SESION.update(escalera=nueva, pista=pista, ayuda=max(SESION["ayuda"], nivel), ofrecida=-1)
    acompanar.pidio_pista()
    if nivel == ayudas.CON_QUE:
        _poner_herramienta(context, h)
    if nivel == ayudas.MIRAME:
        mirame(context)
    _al_cambiar_estado()
    return pista


def mirame(context=None):
    """La demostración de la habilidad que toca, sin tocar lo que el alumno ya hizo."""
    h = habilidad_actual()
    if h is None or SESION["estado"] not in (TRABAJANDO, LOGRADA):
        return None
    if SESION["actividad"] is not None and SESION["actividad"].tipo == taller.MIRA:
        return otra_vez(context)
    SESION["ayuda"] = max(SESION["ayuda"], ayudas.MIRAME)
    SESION["mirame"] = True
    if not demo.empezar(h, _mirame_termino, bpy.context.scene, pasos=_pasos_demo(h, SESION["actividad"])):
        SESION["mirame"] = False
    _al_cambiar_estado()
    return None


def _mirame_termino(_completa):
    SESION["mirame"] = False
    SESION["escalera"] = ayudas.avance(SESION["escalera"], time.time()) if SESION["escalera"] else None
    _redibujar()


def _demo_termino(completa):
    a = SESION["actividad"]
    if a is None or a.tipo != taller.MIRA:
        return
    cambios = datos.registrar(a, True, 0, False, segundos_trabajados())
    SESION.update(estado=LOGRADA, logro_en=time.time(), cambios=cambios, plan=datos.plan(a.taller))
    _revisar_etapa(a)
    _al_cambiar_estado()


def repetir_demo(context=None):
    a = SESION["actividad"]
    if a is not None and a.tipo == taller.MIRA:
        return empezar(context, a)
    return mirame(context)


def probar(context=None, taller_id="", habilidad_id=""):
    """«¿Ya sabes esto? Demuéstralo»: el reto de la habilidad, sin ayuda."""
    c = datos.catalogo()
    if c is None:
        return None
    taller_id = taller_id or SESION["taller"] or datos.taller_inicial()
    a = taller.actividad_de_prueba(c, taller_id, habilidad_id)
    return empezar(context, a) if a is not None else "Esa habilidad no está en el taller."


def repasar(context=None, taller_id="", habilidad_id=""):
    c = datos.catalogo()
    if c is None:
        return None
    taller_id = taller_id or SESION["taller"] or datos.taller_inicial()
    a = taller.actividad_de_repaso(c, taller_id, habilidad_id)
    return empezar(context, a) if a is not None else "Esa habilidad no está en el taller."


def terminar():
    """Cierra la sesión del taller (la escena queda como está)."""
    from .. import fichas

    demo.detener(llamar=False)
    if fichas.modo() == fichas.PRESENTAR:
        fichas.cerrar(marcar=False)
    repaso = SESION["repaso_ofrecido"]
    SESION.update(_vacia(), repaso_ofrecido=repaso)
    _al_cambiar_estado()


# --- La plataforma maneja el taller -----------------------------------------------------------

ORDENES = ("taller_abrir", "taller_continuar", "taller_pausa", "taller_pista", "taller_mirame", "taller_probar",
           "taller_repaso", "isla")


def orden(context, tipo, datos_orden):
    """Una orden del enlace en vivo. Devuelve el texto que se avisa en Blender (o None)."""
    datos_orden = datos_orden or {}
    if tipo == "taller_abrir":
        taller_id = str(datos_orden.get("taller") or "")
        if "etapa" in datos_orden or datos_orden.get("leccion"):
            habilidades = datos_orden.get("habilidades") or ()
            fijar_etapa(taller_id, str(datos_orden.get("etapa") or ""),
                        [str(h) for h in habilidades] if isinstance(habilidades, (list, tuple)) else (),
                        str(datos_orden.get("leccion") or ""))
        return abrir(context, taller_id, str(datos_orden.get("actividad") or ""))
    if tipo == "taller_continuar":
        if SESION["estado"] == PAUSA:
            return seguir(context)
        if SESION["volver"]:
            return frase_logro()  # la plataforma ya sabe: no se abre nada fuera de la etapa
        if SESION["estado"] == LOGRADA or SESION["actividad"] is None:
            return siguiente(context) if SESION["actividad"] is not None else abrir(context, SESION["taller"])
        return None
    if tipo == "taller_pausa":
        return pausar()
    if tipo == "taller_pista":
        pista = pedir_pista(context)
        return pista.texto if pista is not None else None
    if tipo == "taller_mirame":
        return mirame(context)
    if tipo == "taller_probar":
        return probar(context, str(datos_orden.get("taller") or ""), str(datos_orden.get("habilidad") or ""))
    if tipo == "taller_repaso":
        return repasar(context, str(datos_orden.get("taller") or ""), str(datos_orden.get("habilidad") or ""))
    if tipo == "isla":
        from . import isla

        return isla.abrir(context)
    return None


def detalle():
    """Lo que la lección muestra en vivo (detalle.taller del latido)."""
    a = SESION["actividad"]
    if a is None:
        return None
    r = SESION["revision"]
    pieza = r.pieza_actual if r is not None else None
    pista = SESION["pista"]
    plan = SESION["plan"]
    estado_vivo = SESION["estado"] if SESION["estado"] in (MIRANDO, TRABAJANDO, LOGRADA, PAUSA, PRESENTANDO) \
        else TRABAJANDO
    if SESION["mirame"]:
        estado_vivo = MIRANDO
    mensaje_vivo = frase_logro() if SESION["estado"] == LOGRADA else (r.mensaje if r is not None else "")
    return {
        "taller": a.taller[:60],
        "actividad": {
            "id": a.id[:120], "tipo": a.tipo[:12], "nombre_tipo": a.nombre_tipo[:30], "titulo": a.titulo[:80],
            "pide": a.pide[:300], "habilidad": a.habilidad[:60], "numero": min(99, a.numero), "de": min(99, a.de),
            "dibujo": (a.dibujo or "")[:10], "molde": bool(a.molde or SESION["molde_proyecto"]),
        },
        "pieza": {"nombre": pieza.nombre[:60], "estado": pieza.estado[:12], "mensaje": pieza.mensaje[:200]}
        if pieza is not None else None,
        "llenas": min(99, r.llenas) if r is not None else 0,
        "total": min(99, r.total) if r is not None else 0,
        "mensaje": (mensaje_vivo or "")[:300],
        "pista": {"nivel": pista.nivel, "titulo": pista.titulo[:40], "texto": pista.texto[:300],
                  "teclas": [str(k)[:20] for k in pista.teclas[:6]]} if pista is not None else None,
        "estado": estado_vivo,
        "habilidades": [{"id": h.id[:60], "titulo": h.titulo[:60], "p": round(h.p, 3), "fase": h.fase[:12]}
                        for h in (plan.habilidades if plan is not None else ())][:12],
        "proyecto_abierto": bool(plan.proyecto_abierto) if plan is not None else False,
        "repasos": [h[:60] for h in (plan.repasos if plan is not None else ())][:12],
        # Motor 6: la etapa que mandó la plataforma y si ya se cumplió (la lección se da por hecha).
        "etapa": RUTA["etapa"].nombre if RUTA["etapa"] is not None else "",
        "etapa_cumplida": bool(RUTA["cumplida"]),
        # Motor 6.1: la herramienta nueva que Blender está presentando (la lección lo dice al lado).
        "ficha": _ficha_vivo(),
        # Motor 6.2: el ánimo y la luz (sin contar errores: dónde se atora, no cuántas veces falló).
        "acompanamiento": acompanar.para_latido(),
    }


def _ficha_vivo():
    from .. import fichas

    f = fichas.visible() if fichas.modo() == fichas.PRESENTAR else None
    return {"id": f.id[:40], "nombre": f.nombre[:60]} if f is not None else None


def datos_latido():
    """(practica_id, progreso, paso) para el latido mientras el taller manda en la escena."""
    a = SESION["actividad"]
    if a is None:
        return None
    practica_id = a.practica_id or f"taller.{a.habilidad or a.taller}.{a.tipo}"
    r = SESION["revision"]
    if SESION["estado"] == LOGRADA:
        progreso = 100
    elif r is not None and r.total:
        progreso = int(round(100 * r.llenas / r.total))
    elif SESION["reporte"] is not None:
        progreso = int(round(SESION["reporte"].progress))
    else:
        progreso = 0
    return practica_id[:80], max(0, min(100, progreso)), a.id[:80]


# --- Vigilante y eventos de Blender -------------------------------------------------------------

OBSERVADOS = (bpy.types.Object, bpy.types.Mesh, bpy.types.Material, bpy.types.Collection, bpy.types.Light,
              bpy.types.Camera, bpy.types.Action)


def _redibujar():
    try:
        from . import vista

        vista.redibujar()
    except Exception:  # noqa: BLE001
        pass


def _al_cambiar_estado():
    _redibujar()
    try:
        enlace.latir_pronto()
    except Exception as error:  # noqa: BLE001 - el enlace nunca rompe el taller
        print(f"[Amatista] Enlace: {error}")


@persistent
def _al_cambiar(scene, depsgraph=None):
    if SESION["actividad"] is None or SESION["proyecto"] or not escena.es_del_taller(scene):
        return
    if demo.activa():
        return  # los objetos de la demostración no son del alumno
    if depsgraph is not None and not any(isinstance(u.id, OBSERVADOS) for u in depsgraph.updates):
        return
    SESION["sucio"] = True
    SESION["ultimo_cambio"] = time.time()


@persistent
def _al_deshacer(*_args):
    if SESION["escalera"] is not None and SESION["estado"] == TRABAJANDO:
        SESION["escalera"] = ayudas.deshizo(SESION["escalera"])
        acompanar.deshizo()
        SESION["sucio"] = True
        SESION["ultimo_cambio"] = time.time()


@persistent
def _al_abrir(*_args):
    demo.detener(llamar=False)
    SESION.update(_vacia())
    RUTA.update(etapa=None, leccion="", cumplida=False)


def _vigilante():
    try:
        if SESION["sucio"] and time.time() - SESION["ultimo_cambio"] > CALMA:
            evaluar(bpy.context)
        if SESION["actividad"] is not None:
            from .vista import tarjeta

            if tarjeta.cambio_compacta():
                _redibujar()  # motor 6: la tarjeta se achica sola al quedarse quieta
            acompanar.vigilar()  # motor 6.2: el ánimo del alumno decide cuánta luz se enciende
        e = SESION["escalera"]
        if e is not None and SESION["estado"] == TRABAJANDO and not demo.activa():
            ahora = time.time()
            if ayudas.atascado(e, ahora) and SESION["ofrecida"] != e.nivel:
                SESION["ofrecida"] = e.nivel
                nombre, _puede = siguiente_pista()
                if nombre:
                    avisar(f"¿Te ayudo? Toca «{nombre}» en la tarjeta.", 10.0)
                h = habilidad_actual()
                if h is not None and e.techo >= ayudas.CON_QUE:  # en retos y repasos no hay «Con qué»
                    from .vista import brillo

                    brillo.encender(h.herramientas)  # atascado: que brille dónde está, sin decir cómo
    except Exception as error:  # noqa: BLE001 - nunca romper el temporizador
        SESION["sucio"] = False
        print(f"[Amatista] Taller: {error}")
    return 0.25


def register():
    for lista, funcion in ((bpy.app.handlers.depsgraph_update_post, _al_cambiar),
                           (bpy.app.handlers.undo_post, _al_deshacer),
                           (bpy.app.handlers.load_post, _al_abrir)):
        if funcion not in lista:
            lista.append(funcion)
    if not bpy.app.timers.is_registered(_vigilante):
        bpy.app.timers.register(_vigilante, first_interval=1.0, persistent=True)


def unregister():
    demo.detener(llamar=False)
    for lista, funcion in ((bpy.app.handlers.depsgraph_update_post, _al_cambiar),
                           (bpy.app.handlers.undo_post, _al_deshacer),
                           (bpy.app.handlers.load_post, _al_abrir)):
        if funcion in lista:
            lista.remove(funcion)
    if bpy.app.timers.is_registered(_vigilante):
        bpy.app.timers.unregister(_vigilante)
    SESION.update(_vacia())
    RUTA.update(etapa=None, leccion="", cumplida=False)
