"""Acompañar al alumno mientras trabaja (motor 6.2): su ánimo y cuánta luz se enciende sola.

El motor decide (amatista_engine.taller.acompanamiento); aquí se juntan las
señales que Blender ya registra y se reparte la luz:

- **Señales**: el historial de operadores (``wm.operators``: cada operación
  registrada, con su nombre), los Ctrl+Z (``undo_post``), los intentos
  fallidos y las piezas del molde que se llenan o se vacían. Nada del
  teclado ni de la pantalla.
- **Ánimo**: tranquilo, duda, atorado o frustrado, con sus razones. La
  plataforma lo recibe en el latido (el profesor ve dónde se atora cada
  quien, no cuántas veces se equivocó).
- **Luz**: la pieza que toca pulsa con más fuerza (vista/molde.py), la
  herramienta brilla sola en su lugar (vista/brillo.py), la tarjeta dice
  «Te toca: Extruir» y «Estás haciendo: Mover» (vista/tarjeta.py) y, si se
  atora, Amatista le ofrece la siguiente pista con una frase de ánimo.
  Nunca hace el paso por él ni dicta las teclas: esas se piden.

Todo vuelve a cero al empezar otra actividad (``reiniciar``).
"""
import time

import bpy

from .. import _motor

ac = _motor.taller.acompanamiento

CADA = 1.0  # s entre lecturas del ánimo
OTRA_VEZ = 14.0  # s: con luz plena la herramienta vuelve a brillar si el alumno no avanzó
ESTADO = {
    "senales": None,  # Senales del motor
    "animo": None,
    "luz": None,
    "leido": 0.0,
    "op": None,  # puntero del último operador visto
    "ofrecido": "",  # nivel de ánimo al que ya se le ofreció ayuda en esta actividad
    "frases": 0,
    "brillo_auto": False,
    "brillo_en": 0.0,
}


def reiniciar(ahora=None):
    ahora = time.time() if ahora is None else ahora
    ESTADO.update(senales=ac.senales_nuevas(ahora), animo=None, luz=None, leido=0.0, ofrecido="", brillo_auto=False)
    ESTADO["op"] = _ultimo_operador()[0]  # lo que ya estaba en el historial no cuenta


def _senales():
    if ESTADO["senales"] is None:
        reiniciar()
    return ESTADO["senales"]


def _poner(s):
    ESTADO["senales"] = s
    ESTADO["leido"] = 0.0  # la próxima lectura es inmediata


def avanzo():
    _poner(ac.avanzo(_senales(), time.time()))


def fallo():
    _poner(ac.fallo(_senales()))


def deshizo():
    _poner(ac.deshizo(_senales()))


def retrocedio():
    _poner(ac.retrocedio(_senales()))


def pidio_pista():
    _poner(ac.pidio_pista(_senales()))


def salto(veces):
    from dataclasses import replace

    _poner(replace(_senales(), saltos=int(veces or 0)))


def _ultimo_operador():
    """(puntero, idname, propiedad) del último operador registrado en Blender."""
    wm = getattr(bpy.context, "window_manager", None)
    try:
        ops = wm.operators if wm is not None else ()
        op = ops[-1] if len(ops) else None
    except (AttributeError, IndexError, RuntimeError):
        op = None
    if op is None:
        return None, "", ""
    propiedad = ""
    if op.bl_idname == "OBJECT_OT_modifier_add":
        propiedad = str(getattr(op.properties, "type", "") or "")
    return op.as_pointer(), op.bl_idname, propiedad


def _anotar_operaciones(ahora):
    puntero, idname, _propiedad = _ultimo_operador()
    if puntero is not None and puntero != ESTADO["op"]:
        ESTADO["op"] = puntero
        _poner(_senales().con_operacion(ahora, idname))


def haciendo():
    """(nombre, coincide) de lo que el alumno está haciendo ahora (una operación modal en curso,
    como mover con G) o acaba de hacer; coincide=True si es la herramienta que toca. None si nada."""
    from .. import fichas
    from . import sesion

    ventana = getattr(bpy.context, "window", None)
    nombre_op, propiedad = "", ""
    for v in ([ventana] if ventana is not None else []) + list(getattr(bpy.context.window_manager, "windows", ()) or ()):
        try:
            modales = list(v.modal_operators)
        except (AttributeError, RuntimeError):
            modales = []
        utiles = [m for m in modales if m.bl_idname.startswith(("TRANSFORM_OT", "MESH_OT", "OBJECT_OT", "VIEW3D_OT"))]
        if utiles:
            nombre_op = utiles[-1].bl_idname
            break
    if not nombre_op:
        _puntero, nombre_op, propiedad = _ultimo_operador()
    if not nombre_op:
        return None
    try:
        f = fichas.fichas().por_blender(nombre_op, propiedad)
    except Exception:  # noqa: BLE001 - sin fichas no se nombra
        f = None
    if f is None:
        return None
    h = sesion.habilidad_actual()
    coincide = bool(h is not None and f.id in tuple(h.herramientas))
    return f.nombre, coincide


def te_toca():
    """El nombre de la herramienta que pide la actividad («Extruir»), sin teclas. "" si no aplica."""
    from .. import fichas
    from . import sesion

    h = sesion.habilidad_actual()
    if h is None:
        return ""
    for hid in h.herramientas:
        try:
            f = fichas.ficha(hid)
        except Exception:  # noqa: BLE001
            f = None
        if f is not None:
            return f.nombre
    return ""


def _fases_del_curso(sesion, datos):
    c = datos.catalogo()
    a = sesion.actividad()
    if c is None or a is None:
        return {}, {}
    t = c.taller(a.taller)
    curso = t.curso if t is not None else ""
    ids = []
    for otro in c.talleres:
        if not curso or otro.curso == curso:
            ids.extend(h for h in otro.habilidades if h not in ids)
    estado = datos.estado_alumno()
    param = datos.parametros()
    ahora = time.time()
    fases, intentos = {}, {}
    for hid in ids:
        d = estado.get(hid)
        p = _motor.taller.dominio(d, param[hid], ahora) if hid in param else (d.p if d is not None else 0.0)
        fases[hid] = _motor.taller.fase(p)
        intentos[hid] = d.intentos if d is not None else 0
    return fases, intentos


def calcular(ahora=None):
    """Lee el ánimo y decide la luz de la actividad en curso (None sin actividad)."""
    from . import datos, sesion

    ahora = time.time() if ahora is None else ahora
    a = sesion.actividad()
    if a is None or sesion.estado() != sesion.TRABAJANDO:
        ESTADO.update(animo=None, luz=None)
        return None
    animo = ac.leer_animo(_senales(), ahora)
    h = sesion.habilidad_actual()
    try:
        fases, intentos = _fases_del_curso(sesion, datos)
    except Exception as error:  # noqa: BLE001 - sin catálogo, todo es nuevo
        print(f"[Amatista] Acompañar: {error}")
        fases, intentos = {}, {}
    fase = fases.get(h.id, _motor.taller.NUEVA) if h is not None else _motor.taller.NUEVA
    debil = bool(h is not None and h.id in ac.debiles(fases, intentos))
    reto = a.tipo in (_motor.taller.RETO, _motor.taller.REPASO, _motor.taller.PRUEBA)
    luz = ac.luz_para(fase, ac.madurez(fases.values()), animo, debil=debil, reto=reto, indice_frase=ESTADO["frases"])
    ESTADO.update(animo=animo, luz=luz, leido=ahora)
    return luz


def luz():
    return ESTADO["luz"]


def animo():
    return ESTADO["animo"]


def pulso():
    """0 a 1: cuánto respira la pieza que toca (0 si no hay luz)."""
    l = ESTADO["luz"]
    return l.pulso if l is not None and l.pieza else 0.0


def _brillar_zona(herramientas):
    from .. import fichas
    from .vista import brillo

    for hid in herramientas or ():
        f = fichas.ficha(hid)
        if f is not None and brillo.encender_zona(f.zona, f.nombre, f.tecla, f.id):
            return True
    return False


def _toca_brillar(l, ahora):
    """Con luz plena la herramienta vuelve a brillar cada tanto mientras no avance; con luz media, una vez."""
    if not ESTADO["brillo_auto"]:
        return True
    if l.nivel < ac.PLENA:
        return False
    try:
        from .vista import brillo

        if brillo.activo():
            return False
    except Exception:  # noqa: BLE001
        return False
    return ahora - ESTADO["brillo_en"] >= OTRA_VEZ


def vigilar():
    """Lo llama el vigilante del taller cada 0.25 s: anota, lee y enciende lo que haga falta."""
    from . import sesion

    ahora = time.time()
    if sesion.actividad() is None or sesion.estado() != sesion.TRABAJANDO:
        return
    _anotar_operaciones(ahora)
    if ahora - ESTADO["leido"] < CADA:
        return
    antes = ESTADO["luz"]
    l = calcular(ahora)
    if l is None:
        return
    h = sesion.habilidad_actual()
    if l.herramienta and h is not None and _toca_brillar(l, ahora):
        try:
            from .vista import brillo

            if not brillo.encender(h.herramientas):  # dónde está, nunca cómo se usa
                _brillar_zona(h.herramientas)  # modificadores, materiales…: brilla su zona (la de su ficha)
            ESTADO.update(brillo_auto=True, brillo_en=ahora)
        except Exception as error:  # noqa: BLE001 - sin vista (CI) no hay brillo
            print(f"[Amatista] Brillo: {error}")
    animo_actual = ESTADO["animo"]
    if l.ofrecer_pista and animo_actual is not None and ESTADO["ofrecido"] != animo_actual.nivel:
        ESTADO["ofrecido"] = animo_actual.nivel
        ESTADO["frases"] += 1
        nombre, _puede = sesion.siguiente_pista()
        extra = f" Si quieres, toca «{nombre}»." if nombre else ""
        sesion.avisar((l.frase + extra).strip(), 10.0)
    if antes is None or antes.nivel != l.nivel or antes.pulso != l.pulso:
        sesion._redibujar()


def apagar_brillo_auto():
    """El alumno avanzó: el brillo automático se apaga y vuelve a decidirse con la luz nueva."""
    ESTADO["brillo_auto"] = False


def para_latido():
    """Lo que la plataforma (y el panel del profesor) recibe del ánimo: nivel y razones, nada más."""
    a = ESTADO["animo"]
    l = ESTADO["luz"]
    if a is None:
        return None
    return {"animo": a.nivel, "razones": [r[:60] for r in a.razones[:4]], "luz": l.nombre if l is not None else ""}
