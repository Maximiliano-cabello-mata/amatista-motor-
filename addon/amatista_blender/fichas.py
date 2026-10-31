"""Fichas de herramientas dentro de Blender (motor 6.1): la ayuda que enseña.

La ficha es la misma que el alumno vio en la teoría de la plataforma
(practices/blender/fichas.json, bloques herramienta_blender y blender_mapa):
para qué sirve la herramienta, una comparación de la vida real, dónde está,
cómo se usa paso a paso y el error típico. Aquí aparece en tres momentos:

- **Presentar**: antes de una actividad que usa una herramienta que el alumno
  nunca vio, el taller la presenta (la tarjeta se vuelve ficha) y la ilumina
  en su lugar de la ventana. «Entendido» sigue con la actividad.
- **Curioso**: en los primeros pasos, cuando el alumno toca algo (elige una
  herramienta de la barra T o usa un operador), Amatista le dice qué es. Cada
  herramienta se explica a lo más dos veces y «No me lo expliques» la apaga.
- **Consulta**: «¿Qué es esto?» en el panel abre la ficha que pida.

El andamio (cuánta ayuda toca) lo decide el motor (taller/fichas.py) con lo
que el alumno ya vio; se guarda con su avance del taller (taller/datos.py).
"""
import json
import time
from pathlib import Path

import bpy

from . import _motor, ajustes, temas

F = _motor.taller.fichas

PRESENTAR, CURIOSO, CONSULTA = "presentar", "curioso", "consulta"
DURA_CURIOSO = 16.0  # la ficha del modo curioso se va sola si nadie la toca
DURA_ABIERTA = 45.0
REVISAR_CADA = 0.4

_CACHE = {"fichas": None}
ESTADO = {"ficha": "", "cola": [], "modo": "", "abierta": False, "desde": 0.0, "hasta": 0.0, "numero": 0, "de": 0}
ULTIMO = {"op": None, "herramienta": None, "listo": False}


# --- Las fichas ------------------------------------------------------------------------------------


def ruta_fichas(carpeta=None):
    carpeta = Path(carpeta) if carpeta is not None else temas.carpeta_paquete()
    for candidata in (carpeta / "fichas.json", carpeta / "blender" / "fichas.json"):
        if candidata.is_file():
            return candidata
    return None


def fichas(recargar=False):
    """Las fichas del paquete (Fichas del motor). Nunca falla: sin archivo, vacías."""
    if _CACHE["fichas"] is None or recargar:
        ruta = ruta_fichas()
        datos = {}
        if ruta is not None:
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                datos = {}
        _CACHE["fichas"] = F.leer_fichas(datos)
    return _CACHE["fichas"]


def ficha(ficha_id):
    return fichas().ficha(ficha_id)


# --- Lo que el alumno ya vio (con su avance del taller) ----------------------------------------------


def _avance():
    from .taller import datos

    return datos.avance()


def vistas():
    valor = _avance().get("fichas")
    return valor if isinstance(valor, dict) else {}


def conocidas():
    valor = _avance().get("conocidas")
    return set(valor) if isinstance(valor, list) else set()


def _guardar():
    from .taller import datos

    datos.guardar()


def marcar_vista(ficha_id):
    if not ficha_id:
        return
    avance = _avance()
    if not isinstance(avance.get("fichas"), dict):
        avance["fichas"] = {}
    avance["fichas"][ficha_id] = int(avance["fichas"].get(ficha_id, 0) or 0) + 1
    _guardar()


def marcar_conocida(ficha_id):
    if not ficha_id:
        return
    avance = _avance()
    lista = avance.get("conocidas") if isinstance(avance.get("conocidas"), list) else []
    if ficha_id not in lista:
        avance["conocidas"] = lista + [ficha_id]
    _guardar()


def _fase(habilidad_id):
    from .taller import datos

    try:
        d = datos.estado_alumno().get(habilidad_id)
    except Exception:  # noqa: BLE001 - sin catálogo, todo es nuevo
        d = None
    return _motor.taller.fase(d.p) if d is not None else _motor.taller.NUEVA


def herramientas_de(actividad):
    """Las herramientas de la habilidad de una actividad del taller (ids del catálogo)."""
    from .taller import datos

    if actividad is None or not getattr(actividad, "habilidad", ""):
        return ()
    c = datos.catalogo()
    h = c.habilidad(actividad.habilidad) if c is not None else None
    return tuple(h.herramientas) if h is not None else ()


def por_presentar(actividad):
    """Las fichas que se presentan antes de esta actividad (herramientas nuevas para el alumno)."""
    p = ajustes.prefs()
    if p is not None and not getattr(p, "presentar_herramientas", True):
        return []
    if actividad is None or actividad.tipo not in (_motor.taller.MIRA, _motor.taller.CONMIGO, _motor.taller.TU):
        return []  # en retos, repasos y el proyecto no se presenta nada: se trata de recordar sin ayuda
    return F.por_presentar(fichas(), herramientas_de(actividad), vistas(), conocidas(), _fase(actividad.habilidad))


def recordatorio(actividad):
    """Una línea para las primeras veces («Escalar (S): cambia el tamaño…») o ""."""
    if actividad is None or actividad.tipo in (_motor.taller.RETO, _motor.taller.REPASO, _motor.taller.PRUEBA):
        return ""
    return F.recordatorio(fichas(), herramientas_de(actividad), vistas(), conocidas(), _fase(actividad.habilidad))


# --- La ficha que se ve -------------------------------------------------------------------------------


def visible():
    """La Ficha que se muestra ahora, o None (la del modo curioso se va sola)."""
    fid = ESTADO["ficha"]
    if not fid:
        return None
    if ESTADO["modo"] == CURIOSO and time.time() > ESTADO["hasta"]:
        cerrar(marcar=True)
        return None
    return ficha(fid)


def modo():
    return ESTADO["modo"] if ESTADO["ficha"] else ""


def mostrar(ids, modo_ficha=CONSULTA):
    """Muestra una ficha (o una cola de fichas, una a la vez) y la ilumina en su lugar."""
    ids = [i for i in (ids or ()) if ficha(i) is not None]
    if not ids:
        return False
    ahora = time.time()
    dura = DURA_CURIOSO if modo_ficha == CURIOSO else 0.0
    ESTADO.update(ficha=ids[0], cola=ids[1:], modo=modo_ficha, abierta=False, desde=ahora, hasta=ahora + dura,
                  numero=1, de=len(ids))
    _iluminar(ids[0])
    _redibujar()
    return True


def _iluminar(ficha_id):
    from .taller.vista import brillo

    f = ficha(ficha_id)
    if f is None:
        return
    dura = 30.0 if ESTADO["modo"] != CURIOSO else DURA_CURIOSO
    if not brillo.encender_zona(f.zona, f.nombre, f.tecla, f.id, dura):
        brillo.apagar()


def como():
    """Abre o cierra los pasos «Cómo se usa» de la ficha."""
    if not ESTADO["ficha"]:
        return None
    ESTADO["abierta"] = not ESTADO["abierta"]
    if ESTADO["modo"] == CURIOSO:
        ESTADO["hasta"] = time.time() + (DURA_ABIERTA if ESTADO["abierta"] else DURA_CURIOSO)
    _redibujar()
    return None


def cerrar(marcar=True):
    from .taller.vista import brillo

    fid = ESTADO["ficha"]
    if marcar and fid:
        marcar_vista(fid)
    ESTADO.update(ficha="", cola=[], modo="", abierta=False, desde=0.0, hasta=0.0, numero=0, de=0)
    if brillo.ESTADO.get("herramienta") == fid:
        brillo.apagar()
    _redibujar()


def entendido(context=None):
    """«Entendido»: la ficha cuenta como vista; sigue la siguiente o, al presentar, la actividad."""
    fid, modo_ficha = ESTADO["ficha"], ESTADO["modo"]
    if not fid:
        return None
    marcar_vista(fid)
    if ESTADO["cola"]:
        siguiente = ESTADO["cola"][0]
        ESTADO.update(ficha=siguiente, cola=ESTADO["cola"][1:], abierta=False, desde=time.time(),
                      numero=ESTADO["numero"] + 1)
        _iluminar(siguiente)
        _redibujar()
        return None
    cerrar(marcar=False)
    if modo_ficha == PRESENTAR:
        from .taller import sesion

        return sesion.despues_de_presentar(context)
    return None


def ya_la_conozco(context=None):
    """«Ya la conozco» / «No me lo expliques»: esa herramienta no se vuelve a presentar sola."""
    fid = ESTADO["ficha"]
    if fid:
        marcar_conocida(fid)
    return entendido(context)


def botones():
    """[(texto, acción, activo)] de la ficha (máximo tres, como la tarjeta)."""
    if not ESTADO["ficha"]:
        return []
    pasos = ("Ocultar pasos", "ficha_como", True) if ESTADO["abierta"] else ("¿Cómo se usa?", "ficha_como", True)
    if ESTADO["modo"] == PRESENTAR:
        siguiente = "Siguiente" if ESTADO["cola"] else "Entendido"
        return [(siguiente, "ficha_entendido", True), pasos, ("Ya la conozco", "ficha_conozco", True)]
    if ESTADO["modo"] == CURIOSO:
        return [("Entendido", "ficha_entendido", True), pasos, ("No me lo expliques", "ficha_conozco", True)]
    return [("Cerrar", "ficha_entendido", True), pasos]


def chip():
    if ESTADO["modo"] == PRESENTAR:
        numero = f" · {ESTADO['numero']} de {ESTADO['de']}" if ESTADO["de"] > 1 else ""
        return f"HERRAMIENTA NUEVA{numero}"
    if ESTADO["modo"] == CURIOSO:
        return "¿QUÉ ES ESTO?"
    return "FICHA"


# --- Modo curioso ---------------------------------------------------------------------------------------


def curioso_encendido():
    p = ajustes.prefs()
    modo_pref = getattr(p, "modo_curioso", "auto") if p is not None else "auto"
    if modo_pref == "nunca":
        return False
    try:
        from .taller import datos

        salen = sum(1 for d in datos.estado_alumno().values()
                    if _motor.taller.fase(d.p) in (_motor.taller.SOLA, _motor.taller.DOMINADA))
    except Exception:  # noqa: BLE001 - sin catálogo, es principiante
        salen = 0
    return F.curioso_activo(modo_pref, salen)


def _modo_objeto(ventana):
    try:
        objeto = ventana.view_layer.objects.active
    except AttributeError:
        objeto = None
    if objeto is None or objeto.mode == "OBJECT":
        return "OBJECT"
    if objeto.mode == "EDIT":
        return f"EDIT_{objeto.type}" if objeto.type != "MESH" else "EDIT_MESH"
    return objeto.mode


def tocado():
    """(nombre, propiedad) de lo último que el alumno tocó en Blender, o None si no cambió nada.

    Lo último puede ser el operador que acaba de usar (wm.operators) o la herramienta que eligió en la
    barra T. La primera vez solo anota lo que hay (no se explica lo que ya estaba al abrir).
    """
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return None
    nuevo = None
    try:
        ops = wm.operators
        op = ops[-1] if len(ops) else None
    except (AttributeError, IndexError, RuntimeError):
        op = None
    puntero = op.as_pointer() if op is not None else None
    if puntero != ULTIMO["op"]:
        ULTIMO["op"] = puntero
        if op is not None and ULTIMO["listo"]:
            propiedad = ""
            if op.bl_idname == "OBJECT_OT_modifier_add":
                propiedad = str(getattr(op.properties, "type", "") or "")
            elif op.bl_idname == "WM_OT_call_panel":
                propiedad = str(getattr(op.properties, "name", "") or "")
            nuevo = (op.bl_idname, propiedad)
    herramienta = None
    for ventana in getattr(wm, "windows", ()) or ():
        try:
            activa = ventana.workspace.tools.from_space_view3d_mode(_modo_objeto(ventana), create=False)
        except (AttributeError, TypeError, RuntimeError):
            activa = None
        if activa is not None:
            herramienta = activa.idname
            break
    if herramienta != ULTIMO["herramienta"]:
        cambio = ULTIMO["listo"] and herramienta is not None
        ULTIMO["herramienta"] = herramienta
        if cambio and nuevo is None:
            nuevo = (herramienta, "")
    ULTIMO["listo"] = True
    return nuevo


def revisar_curioso():
    """Si el alumno tocó algo que todavía no conoce, su ficha corta. Devuelve la Ficha mostrada o None."""
    algo = tocado()
    if algo is None or ESTADO["ficha"] or not curioso_encendido():
        return None
    from .taller import demo, sesion

    if demo.activa() or sesion.estado() == sesion.PRESENTANDO:
        return None  # la demostración y la presentación ya están explicando
    f = F.explicar_curioso(fichas(), algo[0], algo[1], vistas(), conocidas())
    if f is None:
        return None
    mostrar([f.id], CURIOSO)
    return f


def _vigilante():
    try:
        if bpy.app.background:
            return REVISAR_CADA
        revisar_curioso()
        if ESTADO["ficha"] and ESTADO["modo"] == CURIOSO and time.time() > ESTADO["hasta"]:
            cerrar(marcar=True)
    except Exception as error:  # noqa: BLE001 - nunca romper el temporizador
        print(f"[Amatista] Fichas: {error}")
    return REVISAR_CADA


def _redibujar():
    if bpy.app.background:
        return
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


class AMATISTA_OT_ficha(bpy.types.Operator):
    """Abre la ficha de una herramienta: para qué sirve, dónde está y cómo se usa"""

    bl_idname = "amatista.ficha"
    bl_label = "¿Qué es esto?"
    bl_options = {"INTERNAL"}

    herramienta: bpy.props.StringProperty(name="Herramienta", default="")

    def execute(self, context):
        if not mostrar([self.herramienta], CONSULTA):
            self.report({"WARNING"}, "Esa herramienta todavía no tiene ficha.")
            return {"CANCELLED"}
        return {"FINISHED"}


CLASES = (AMATISTA_OT_ficha,)


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)
    ULTIMO.update(op=None, herramienta=None, listo=False)
    if not bpy.app.timers.is_registered(_vigilante):
        bpy.app.timers.register(_vigilante, first_interval=2.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_vigilante):
        bpy.app.timers.unregister(_vigilante)
    ESTADO.update(ficha="", cola=[], modo="", abierta=False, desde=0.0, hasta=0.0, numero=0, de=0)
    for clase in reversed(CLASES):
        bpy.utils.unregister_class(clase)


__all__ = ["CONSULTA", "CURIOSO", "PRESENTAR", "botones", "cerrar", "como", "entendido", "ficha", "fichas",
           "marcar_conocida", "marcar_vista", "mostrar", "por_presentar", "recordatorio", "revisar_curioso",
           "tocado", "visible", "vistas", "ya_la_conozco"]
