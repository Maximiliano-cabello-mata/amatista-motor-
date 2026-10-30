"""Lo que el taller sabe sin red: el catálogo de habilidades y lo que el alumno ya domina.

- El catálogo es practices/blender/habilidades.json (amatista.skill/1), que
  viaja en el paquete (practicas/habilidades.json).
- avance_taller.json, en la carpeta del usuario, guarda el modelo del alumno
  (P(L), cajas de repaso…), los proyectos y retos terminados y la cola de
  intentos que todavía no llegan al servidor. Hay un archivo por cuenta: si
  dos personas usan la misma computadora, cada una ve lo suyo.
- Con cuenta vinculada, los intentos van a POST /api/addon/v1/habilidades/intentos;
  el servidor vuelve a calcular el modelo (y revisa la escena con el mismo
  motor) y responde el estado, que manda sobre el local.
"""
import hashlib
import json
import time
from pathlib import Path

from .. import _motor, ajustes, red

taller = _motor.taller

RUTA_INTENTOS = "/api/addon/v1/habilidades/intentos"
RUTA_ESTADO = "/api/addon/v1/habilidades"
POR_ENVIO = 50  # intentos por petición (el servidor acepta hasta 50)
MAX_COLA = 400
ESPERA_SIN_SERVIDOR = 600.0  # un servidor sin el taller (404): se vuelve a probar en 10 minutos

ESTADO = {
    "catalogo": None,
    "catalogo_error": "",
    "avance": None,
    "cuenta": None,
    "enviando": False,
    "otro_envio": False,
    "sin_servidor_hasta": 0.0,
    "mensaje": "",
    "ultima_sync": 0.0,
}


# --- El catálogo ------------------------------------------------------------------------------


def _ruta_catalogo():
    from .. import practicas

    carpeta = practicas.carpeta_paquete()
    for ruta in (carpeta / "habilidades.json", carpeta / "blender" / "habilidades.json"):
        if ruta.exists():
            return ruta
    return None


def catalogo():
    """El catálogo de habilidades y talleres (None si no viene en el paquete o está roto)."""
    if ESTADO["catalogo"] is None and not ESTADO["catalogo_error"]:
        ruta = _ruta_catalogo()
        if ruta is None:
            ESTADO["catalogo_error"] = "Este paquete no trae el catálogo de habilidades."
            return None
        try:
            ESTADO["catalogo"] = taller.leer_catalogo(ruta)
        except Exception as error:  # noqa: BLE001 - un catálogo roto no rompe Blender
            ESTADO["catalogo_error"] = str(error)
            print(f"[Amatista] No se pudo leer el catálogo de habilidades: {error}")
    return ESTADO["catalogo"]


def parametros():
    c = catalogo()
    return {hid: h.bkt for hid, h in c.habilidades.items()} if c is not None else {}


# --- El avance del alumno -------------------------------------------------------------------


def _cuenta():
    p = ajustes.prefs()
    return (getattr(p, "cuenta_id", "") or "") if p and getattr(p, "token", "") else ""


def _ruta_avance(cuenta):
    nombre = "local" if not cuenta else hashlib.sha1(cuenta.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return ajustes.carpeta_usuario() / f"avance_taller_{nombre}.json"


def _vacio():
    # Motor 6.1: «fichas» = veces que vio la ficha de cada herramienta; «conocidas» = las que marcó «Ya la conozco».
    return {"estado": {}, "completadas": [], "cola": [], "isla": {}, "ultimo_taller": "", "actualizado": 0.0,
            "fichas": {}, "conocidas": []}


def _leer(ruta):
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _vacio()
    if not isinstance(datos, dict):
        return _vacio()
    base = _vacio()
    for clave, defecto in base.items():
        valor = datos.get(clave, defecto)
        base[clave] = valor if isinstance(valor, type(defecto)) else defecto
    return base


def avance():
    """El avance de la cuenta vinculada (o el local sin cuenta). Al vincular, lo local pasa a la cuenta."""
    cuenta = _cuenta()
    if ESTADO["avance"] is None or ESTADO["cuenta"] != cuenta:
        datos = _leer(_ruta_avance(cuenta))
        if cuenta:
            local = _ruta_avance("")
            sin_cuenta = _leer(local) if local.exists() else None
            if sin_cuenta and (sin_cuenta["cola"] or sin_cuenta["estado"]):
                # Lo que hizo antes de vincular se envía a su cuenta una sola vez.
                datos["cola"] = (sin_cuenta["cola"] + datos["cola"])[-MAX_COLA:]
                for hid, valor in sin_cuenta["estado"].items():
                    datos["estado"].setdefault(hid, valor)
                datos["completadas"] = sorted(set(datos["completadas"]) | set(sin_cuenta["completadas"]))
                for tid, pieza in sin_cuenta["isla"].items():
                    datos["isla"].setdefault(tid, pieza)
                try:
                    local.unlink()
                except OSError:
                    pass
        ESTADO["avance"], ESTADO["cuenta"] = datos, cuenta
        if cuenta:
            guardar()
    return ESTADO["avance"]


def guardar():
    datos = ESTADO["avance"]
    if datos is None:
        return
    datos["actualizado"] = time.time()
    try:
        _ruta_avance(ESTADO["cuenta"] or "").write_text(json.dumps(datos, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    except OSError as error:
        print(f"[Amatista] No se pudo guardar tu avance del taller: {error}")


def estado_alumno():
    """{habilidad: Dominio} de este alumno."""
    return taller.estado_desde_dict(avance()["estado"], parametros())


def completadas():
    """Proyectos y retos terminados (aquí, según la plataforma o según las prácticas terminadas)."""
    from .. import aprendizaje

    hechas = set(avance()["completadas"])
    try:
        hechas |= set(aprendizaje.completadas())
    except Exception:  # noqa: BLE001 - sin plan de estudios igual se trabaja
        pass
    return hechas


def plan(taller_id, elegida=""):
    c = catalogo()
    if c is None or c.taller(taller_id) is None:
        return None
    return taller.planear(c, taller_id, estado_alumno(), time.time(), completadas(), elegida)


def taller_inicial():
    """El taller donde sigue el alumno: el último que abrió o el primero sin terminar."""
    c = catalogo()
    if c is None:
        return ""
    ultimo = avance().get("ultimo_taller") or ""
    if ultimo and c.taller(ultimo) is not None:
        p = plan(ultimo)
        if p is not None and not p.completo:
            return ultimo
    for t in c.talleres:
        p = plan(t.id)
        if p is not None and not p.completo:
            return t.id
    return c.talleres[0].id if c.talleres else ""


def recordar_taller(taller_id):
    datos = avance()
    if datos.get("ultimo_taller") != taller_id:
        datos["ultimo_taller"] = taller_id
        guardar()


def repasos_pendientes():
    """[(taller, habilidad)] con repaso vencido, el más atrasado primero (todos los talleres)."""
    c = catalogo()
    if c is None:
        return []
    estado = estado_alumno()
    vencidas = taller.vencidas(estado, time.time())
    salida = []
    for hid in vencidas:
        tid = next((t.id for t in c.talleres if hid in t.habilidades), "")
        if tid:
            salida.append((tid, hid))
    return salida


def registrar(actividad, correcto, ayuda=0, molde=False, segundos=0.0, escena=None):
    """Un intento terminado: actualiza el modelo aquí y lo deja en la cola para el servidor.

    Devuelve {habilidad: (fase antes, fase después)} para la tarjeta («¡Ya te sale sola!»).
    """
    c = catalogo()
    if c is None:
        return {}
    ahora = time.time()
    datos = avance()
    estado = estado_alumno()
    cambios = {}
    ids = list(actividad.habilidades) or ([actividad.habilidad] if actividad.habilidad else [])
    for hid in ids:
        h = c.habilidad(hid)
        if h is None:
            continue
        antes = estado.get(hid)
        fase_antes = taller.fase(taller.dominio(antes, h.bkt, ahora))
        if actividad.tipo == taller.MIRA:
            nuevo = taller.marcar_demo(antes, h.bkt)
        else:
            nuevo = taller.registrar_intento(antes, h.bkt, correcto, ayuda, ahora, molde=molde, tipo=actividad.tipo)
        datos["estado"][hid] = nuevo.a_dict()
        cambios[hid] = (fase_antes, taller.fase(taller.dominio(nuevo, h.bkt, ahora)))
    if correcto and actividad.tipo == taller.PROYECTO and actividad.practica_id:
        if actividad.practica_id not in datos["completadas"]:
            datos["completadas"].append(actividad.practica_id)
    if correcto and actividad.tipo == taller.RETO:
        marca = f"reto:{actividad.taller}"
        if marca not in datos["completadas"]:
            datos["completadas"].append(marca)
    intento = {
        "habilidad": actividad.habilidad or (ids[0] if ids else ""),
        "actividad": actividad.id,
        "taller": actividad.taller,
        "tipo": actividad.tipo,
        "correcto": bool(correcto),
        "ayuda": int(max(0, min(4, ayuda))),
        "molde": bool(molde),
        "segundos": round(max(0.0, float(segundos)), 1),
        "en": round(ahora, 3),
    }
    if escena is not None:
        intento["escena"] = escena
    datos["cola"] = (datos["cola"] + [intento])[-MAX_COLA:]
    guardar()
    sincronizar_pronto()
    return cambios


# --- Sincronización ---------------------------------------------------------------------------


def _vinculado():
    p = ajustes.prefs()
    return bool(p and p.token)


def _mezclar(respuesta):
    """El estado del servidor manda; los intentos que siguen en la cola ya se sumaron aquí."""
    if not isinstance(respuesta, dict):
        return
    datos = avance()
    servidor = respuesta.get("estado")
    pendientes = {i.get("habilidad") for i in datos["cola"]}
    if isinstance(servidor, dict):
        for hid, valor in servidor.items():
            if isinstance(valor, dict) and hid not in pendientes:
                datos["estado"][hid] = valor
    hechas = respuesta.get("completadas")
    if isinstance(hechas, list):
        datos["completadas"] = sorted(set(datos["completadas"]) | {str(h) for h in hechas if h})
    guardar()


def sincronizar(al_terminar=None):
    """Envía la cola de intentos (de a 50) y trae el estado del servidor."""
    if not _vinculado() or not red.en_linea_permitido():
        return False
    if ESTADO["enviando"]:
        ESTADO["otro_envio"] = True
        return False
    if time.time() < ESTADO["sin_servidor_hasta"]:
        return False
    datos = avance()
    lote = list(datos["cola"][:POR_ENVIO])
    ESTADO["enviando"] = True
    if not lote:
        def traido(respuesta, error, estado):
            ESTADO["enviando"] = False
            if error is None:
                _mezclar(respuesta)
                ESTADO["ultima_sync"] = time.time()
            elif estado == 404:
                ESTADO["sin_servidor_hasta"] = time.time() + ESPERA_SIN_SERVIDOR
            if al_terminar:
                al_terminar(error)

        red.pedir("GET", RUTA_ESTADO, traido)
        return True
    enviados = {i.get("en") for i in lote}

    def listo(respuesta, error, estado):
        ESTADO["enviando"] = False
        actual = avance()
        if error is None or (estado and not red.es_reintentable(estado) and estado != 404):
            # Aceptado, o rechazado para siempre (400, 403, 422): reintentar no lo arregla.
            actual["cola"] = [i for i in actual["cola"] if i.get("en") not in enviados]
            if error is None:
                _mezclar(respuesta)
                ESTADO["ultima_sync"] = time.time()
                ESTADO["mensaje"] = ""
            else:
                ESTADO["mensaje"] = error
            guardar()
        elif estado == 404:
            # Un servidor sin el taller: el avance sigue aquí y se envía cuando lo tenga.
            ESTADO["sin_servidor_hasta"] = time.time() + ESPERA_SIN_SERVIDOR
            ESTADO["mensaje"] = "La plataforma todavía no guarda el taller: tu avance queda en esta computadora."
        else:
            ESTADO["mensaje"] = error or ""
        if ESTADO["otro_envio"] or (error is None and actual["cola"]):
            ESTADO["otro_envio"] = False
            sincronizar_pronto(0.5)
        if al_terminar:
            al_terminar(error)

    try:
        red.pedir("POST", RUTA_INTENTOS, listo, {"intentos": lote, "version_addon": ajustes.VERSION_ADDON})
    except Exception:  # noqa: BLE001 - la marca nunca queda puesta
        ESTADO["enviando"] = False
        raise
    return True


def _sincronizar_ahora():
    try:
        sincronizar()
    except Exception as error:  # noqa: BLE001
        ESTADO["enviando"] = False
        print(f"[Amatista] Taller: {error}")
    return None


def sincronizar_pronto(segundos=2.0):
    import bpy

    p = ajustes.prefs()
    if p is not None and not p.sincronizar_solo:
        return
    if bpy.app.timers.is_registered(_sincronizar_ahora):
        bpy.app.timers.unregister(_sincronizar_ahora)
    bpy.app.timers.register(_sincronizar_ahora, first_interval=segundos)


def reiniciar_cache():
    """Para pruebas y al cambiar de cuenta: se vuelve a leer todo."""
    ESTADO.update(catalogo=None, catalogo_error="", avance=None, cuenta=None, enviando=False, otro_envio=False,
                  sin_servidor_hasta=0.0, mensaje="")


def unregister():
    import bpy

    if bpy.app.timers.is_registered(_sincronizar_ahora):
        bpy.app.timers.unregister(_sincronizar_ahora)
