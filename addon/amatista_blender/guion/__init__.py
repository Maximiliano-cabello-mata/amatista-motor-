"""Motor 7 · Guion en Blender: un paso a la vez, avanzando por lo que hay en la escena.

Pedido del creador (31 de octubre de 2026): «el motor habla de una
herramienta que brilla a la izquierda y no hay ninguna»; «si el usuario ya
acabó la práctica, no avanza hasta que la herramienta de la izquierda que
está señalando no esté bien»; «se sobreponen los paneles, los cuadros de
diálogo». Las simulaciones (addon/tests/simular_alumnos.py) lo midieron con
el motor 6.2: 24 de 100 alumnos simulados terminaban el tren.

Lo que cambia para el alumno (modo alumno, preferencia «Guía paso a paso»):

- **Avanza el resultado, en el momento.** Cada cambio de la escena (y cada
  guardado, y cada Ctrl + Z) se revisa a los 0,15 s con el motor de
  siempre; el paso que se cumple se marca, venga como venga. Nada espera a
  que se use una herramienta, se lea una ficha o pase un temporizador.
- **Una sola voz.** El guion (amatista_engine.guion) dice el paso que toca
  con verbo y pieza, y lo que falta sale del objetivo de ESE paso. La
  tarjeta del taller, el molde del proyecto, el brillo, las fichas y la
  tarjeta de la misión no se dibujan mientras el guion manda (interfaz/turno.py).
- **Señales reales.** «¿Dónde está?» dice el lugar real de la herramienta y,
  si puede, la señala de verdad: la deja elegida en la barra de herramientas
  (que se muestra), abre su menú o su pestaña, o selecciona la pieza de la
  que habla. Solo entonces el texto dice que algo quedó resaltado.
- **Un lugar para cada cosa.** Arriba de la vista 3D, la banda con el paso
  (banda.py); en N › Amatista, el panel con los botones y la lista de pasos
  (panel.py). Ningún diálogo se abre solo.
- **Administradores sin progreso** (``sin_progreso``): con una cuenta admin
  nada se guarda ni se envía y cada vez que Blender arranca las prácticas
  empiezan de cero.
"""
import re
import time
from importlib import import_module

import bpy
from bpy.app.handlers import persistent

from .. import _motor, ajustes

g7 = import_module(_motor.engine.__name__ + ".guion")

CALMA = 0.15  # s sin cambios antes de revisar (mientras se arrastra con G no se revisa a cada cuadro)
ESTADO = {
    "practica_id": "",
    "guion": None,
    "avance": None,
    "pista": None,  # la última Pista pedida (del paso que toca)
    "nivel": 0,  # el último nivel de pista pedido en este paso
    "paso_de_la_pista": "",
    "senal": "",  # lo que se señaló de verdad («Te dejé elegida «Escalar»…»)
    "aviso": "",  # una frase corta de lo último que pasó («Paso 3 listo: las ruedas»)
    "aviso_hasta": 0.0,
    "escena": "",
    "sucio": False,
    "ultimo_cambio": 0.0,
}
NOMBRE_EN_TEXTO = re.compile(r"«([^»]{1,63})»")


# --- ¿Manda el guion? --------------------------------------------------------------------------


def preferido():
    p = ajustes.prefs()
    return p is None or getattr(p, "guion_paso_a_paso", True)


def modo_alumno():
    try:
        from ..taller import sesion

        return sesion.modo_alumno()
    except Exception:  # noqa: BLE001 - sin taller, el modo lo dice la ventana
        wm = getattr(bpy.context, "window_manager", None)
        return getattr(getattr(wm, "amatista", None), "modo", "alumno") == "alumno"


def _escena(context=None):
    context = context or bpy.context
    return getattr(context, "scene", None)


def activo(escena=None):
    """El guion manda en esta escena: modo alumno, preferencia encendida y una práctica o actividad aquí."""
    if not preferido() or not modo_alumno():
        return False
    escena = escena if escena is not None else _escena()
    if escena is None:
        return False
    try:
        from ..taller import sesion

        if sesion.activa() and sesion.cubre(escena):
            return True
    except Exception:  # noqa: BLE001
        pass
    return bool(getattr(getattr(escena, "amatista", None), "practica_json", ""))


def sin_progreso():
    """Administradores: practican cuantas veces quieran, sin progreso guardado ni enviado."""
    return ajustes.sin_progreso()


# --- El guion de lo que está abierto -----------------------------------------------------------


def _actividad():
    try:
        from ..taller import sesion

        return sesion.actividad(), sesion
    except Exception:  # noqa: BLE001
        return None, None


def _guion_para(practica):
    a, sesion = _actividad()
    if a is not None and sesion is not None and sesion.SESION.get("practica") is practica:
        h = sesion.habilidad_actual()
        return g7.guion_de_practica(
            practica, herramientas_actividad=tuple(getattr(h, "herramientas", ()) or ()), haz_actividad=a.pide,
            como_actividad=tuple(x for x in (getattr(h, "como", ""),) if x),
            teclas_actividad=tuple(getattr(h, "teclas", ()) or ()),
        )
    return g7.guion_de_practica(practica)


def al_evaluar(context, practica, reporte):
    """practicas.evaluar o sesion.evaluar revisaron la escena: el guion avanza con ese reporte."""
    if practica is None or reporte is None:
        return None
    sc = _escena(context)
    if ESTADO["practica_id"] != practica.id or ESTADO["guion"] is None:
        ESTADO.update(practica_id=practica.id, guion=_guion_para(practica), avance=None, pista=None, nivel=0,
                      paso_de_la_pista="", senal="", aviso="")
    anterior = ESTADO["avance"]
    nuevo = g7.avanzar(ESTADO["guion"], reporte, anterior)
    ESTADO["avance"] = nuevo
    ESTADO["escena"] = getattr(sc, "name", "")
    if nuevo.actual != ESTADO["paso_de_la_pista"]:
        # Otro paso: la pista y la señal eran del anterior.
        ESTADO.update(pista=None, nivel=0, paso_de_la_pista=nuevo.actual or "", senal="")
    if nuevo.recien:
        ultimo = ESTADO["guion"].paso(nuevo.recien[-1])
        if nuevo.completo:
            avisar("¡Terminado! Todo lo que pedía la práctica está en tu escena.")
        elif ultimo is not None:
            avisar(f"Listo: {ultimo.titulo.lower()}." if len(nuevo.recien) == 1 else
                   f"Listos {len(nuevo.recien)} pasos de una vez.")
    elif nuevo.deshechos:
        p = ESTADO["guion"].paso(nuevo.deshechos[0])
        if p is not None:
            avisar(f"Se deshizo: {p.titulo.lower()}. Vuelve a hacerlo cuando quieras.")
    _redibujar()
    return nuevo


def avisar(texto, segundos=5.0):
    ESTADO.update(aviso=texto, aviso_hasta=time.time() + segundos)


def aviso():
    return ESTADO["aviso"] if ESTADO["aviso_hasta"] > time.time() else ""


def guion():
    return ESTADO["guion"]


def avance():
    return ESTADO["avance"]


def paso_actual():
    g, a = ESTADO["guion"], ESTADO["avance"]
    if g is None or a is None or not a.actual:
        return None
    return g.paso(a.actual)


def completo():
    a, sesion = _actividad()
    if sesion is not None and a is not None and sesion.estado() == sesion.LOGRADA:
        return True
    av = ESTADO["avance"]
    return bool(av is not None and av.completo)


def _idioma():
    try:
        return _motor.terminos.idioma()
    except Exception:  # noqa: BLE001
        return "es"


# --- Revisar en el momento ---------------------------------------------------------------------


def revisar_ya(context=None):
    """Revisa la escena ahora (la actividad corta del taller o la práctica) y devuelve el reporte."""
    from .. import practicas

    context = context or bpy.context
    ESTADO["sucio"] = False
    a, sesion = _actividad()
    if a is not None and sesion is not None and not sesion.SESION.get("proyecto") and sesion.SESION.get("practica"):
        return sesion.evaluar(context)
    return practicas.evaluar(context, "cambio")


def _revisar_si_calmo():
    if not ESTADO["sucio"]:
        return None
    espera = CALMA - (time.time() - ESTADO["ultimo_cambio"])
    if espera > 0:
        return espera
    try:
        if activo():
            revisar_ya(bpy.context)
    except Exception as error:  # noqa: BLE001 - revisar nunca rompe Blender
        print(f"[Amatista] Guion: {error}")
    ESTADO["sucio"] = False
    return None


def _marcar_cambio():
    ESTADO["sucio"], ESTADO["ultimo_cambio"] = True, time.time()
    if not bpy.app.timers.is_registered(_revisar_si_calmo):
        bpy.app.timers.register(_revisar_si_calmo, first_interval=CALMA)


@persistent
def _al_cambiar(scene, depsgraph=None):
    if not activo(scene):
        return
    try:
        from ..taller import demo

        if demo.activa():
            return  # la demostración mueve objetos suyos: no es trabajo del alumno
    except Exception:  # noqa: BLE001
        pass
    _marcar_cambio()


@persistent
def _al_guardar(*_args):
    if activo():
        _marcar_cambio()  # guardar no pasa por el depsgraph: el paso «guarda tu tren» se ve en el momento


@persistent
def _al_deshacer(*_args):
    if activo():
        _marcar_cambio()


@persistent
def _al_abrir(*_args):
    ESTADO.update(practica_id="", guion=None, avance=None, pista=None, nivel=0, paso_de_la_pista="", senal="",
                  aviso="")


# --- Pistas y señales --------------------------------------------------------------------------


def _seleccionar_nombrados(context, texto):
    """Selecciona las piezas que nombra el mensaje («Cylinder.003»): Blender las marca con su borde naranja."""
    sc = _escena(context)
    if sc is None or not texto:
        return []
    nombres = [n for n in NOMBRE_EN_TEXTO.findall(texto) if n in sc.objects]
    if not nombres:
        return []
    try:
        for obj in sc.objects:
            obj.select_set(obj.name in nombres)
        context.view_layer.objects.active = sc.objects[nombres[0]]
    except (RuntimeError, ReferenceError, AttributeError):
        return []
    return nombres


def pedir_pista(context=None, nivel=0):
    """La siguiente pista del paso que toca (o la de ese nivel). Devuelve un dict o None."""
    from . import senalar

    context = context or bpy.context
    g, av = ESTADO["guion"], ESTADO["avance"]
    if g is None or av is None or av.completo or not av.actual:
        return None
    if av.actual != ESTADO["paso_de_la_pista"]:
        ESTADO.update(nivel=0, paso_de_la_pista=av.actual, senal="")
    nivel = nivel or (ESTADO["nivel"] % 3) + 1
    p = g7.pista(g, av, nivel, _idioma())
    if p is None:
        return None
    texto, senalado = p.texto, False
    if nivel == g7.QUE_FALTA:
        nombres = _seleccionar_nombrados(context, texto)
        if nombres:
            texto += f" Lo dejé seleccionado: {', '.join(f'«{n}»' for n in nombres[:3])} (borde naranja en la vista 3D)."
            senalado = True
    elif nivel == g7.DONDE:
        extra = senalar.senalar(context, p.herramienta, paso_actual())
        if extra:
            texto += " " + extra
            senalado = True
    ESTADO.update(pista=p, nivel=nivel, senal=texto if senalado else "")
    _redibujar()
    return {"nivel": nivel, "titulo": p.titulo, "texto": texto, "herramienta": p.herramienta,
            "herramientas": [p.herramienta] if p.herramienta else [], "teclas": list(p.teclas), "senalado": senalado}


def texto_pista():
    p = ESTADO["pista"]
    if p is None:
        return "", ""
    return p.titulo, ESTADO["senal"] or p.texto


# --- Lo que muestran la banda, el panel y la plataforma ----------------------------------------


def vista():
    """Todo lo que el alumno ve ahora, en un dict (la banda, el panel, el latido y las simulaciones)."""
    a, sesion = _actividad()
    salida = {"activo": activo(), "modo": "", "titulo": "", "numero": 0, "total": 0, "parte": "", "haz": "",
              "por_que": "", "pista": "", "pista_titulo": "", "teclas": [], "pasos": [], "objetivo": None,
              "completo": completo(), "aviso": aviso(), "herramienta": ""}
    if sesion is not None and a is not None and sesion.cubre(_escena()):
        if sesion.estado() == sesion.MIRANDO or sesion.SESION.get("mirame"):
            from ..taller import demo

            paso = demo.paso_actual() if demo.activa() else None
            salida.update(modo="mirando", titulo=a.titulo, haz=(paso.texto if paso is not None and paso.texto
                                                                 else f"Mira cómo se hace: {a.pide}"),
                          teclas=list(paso.teclas) if paso is not None else [])
            return salida
        if sesion.estado() == sesion.PAUSA:
            salida.update(modo="pausa", titulo=a.titulo, haz="En pausa. Tu trabajo está a salvo: sigue cuando quieras.")
            return salida
        if sesion.estado() == sesion.LOGRADA:
            salida.update(modo="logrado", titulo=a.titulo, haz=sesion.frase_logro(), completo=True)
            return salida
    g, av = ESTADO["guion"], ESTADO["avance"]
    if g is None or av is None:
        return salida
    paso = g.paso(av.actual) if av.actual else None
    titulo_pista, texto = texto_pista()
    salida.update(
        modo="terminado" if av.completo else "trabajando", titulo=g.titulo, numero=paso.numero if paso else g.total,
        total=g.total, parte=paso.parte if paso else "", objetivo=av.actual,
        haz=(_motor.terminos.menus(paso.haz, _idioma()) if paso else "¡Terminado! Todo lo que pedía está en tu escena."),
        por_que=(av.pausa or (av.por_que if paso and av.por_que != paso.listo else "")),
        pista=texto, pista_titulo=titulo_pista, herramienta=paso.herramienta if paso else "",
        teclas=list(ESTADO["pista"].teclas) if ESTADO["pista"] is not None and ESTADO["nivel"] == g7.COMO else [],
        pasos=[(p.titulo, av.estado(p.id)) for p in g.pasos],
    )
    return salida


def para_latido():
    """Lo que la plataforma muestra en «Ahora en tu Blender» (corto)."""
    v = vista()
    if not v["activo"]:
        return None
    return {"modo": v["modo"], "paso": v["numero"], "de": v["total"], "haz": v["haz"][:200],
            "por_que": v["por_que"][:200], "completo": v["completo"], "sin_progreso": sin_progreso()}


def _redibujar():
    if bpy.app.background:
        return
    wm = getattr(bpy.context, "window_manager", None)
    for ventana in getattr(wm, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type in ("VIEW_3D", "PROPERTIES"):
                area.tag_redraw()


# --- Registro ----------------------------------------------------------------------------------

_MANEJADORES = (
    ("depsgraph_update_post", _al_cambiar),
    ("save_post", _al_guardar),
    ("undo_post", _al_deshacer),
    ("redo_post", _al_deshacer),
    ("load_post", _al_abrir),
)


def register():
    from . import banda, panel

    panel.register()
    for nombre, funcion in _MANEJADORES:
        lista = getattr(bpy.app.handlers, nombre)
        if funcion not in lista:
            lista.append(funcion)
    banda.activar(True)


def unregister():
    from . import banda, panel

    banda.activar(False)
    for nombre, funcion in _MANEJADORES:
        lista = getattr(bpy.app.handlers, nombre)
        if funcion in lista:
            lista.remove(funcion)
    if bpy.app.timers.is_registered(_revisar_si_calmo):
        bpy.app.timers.unregister(_revisar_si_calmo)
    panel.unregister()
    _al_abrir()


__all__ = ["activo", "al_evaluar", "avance", "completo", "guion", "para_latido", "paso_actual", "pedir_pista",
           "revisar_ya", "sin_progreso", "vista"]
