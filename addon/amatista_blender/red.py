"""Conexión con la API de Amatista sin congelar Blender.

bpy no es seguro entre hilos: el hilo solo hace la petición HTTP y el
resultado se entrega en el hilo principal con bpy.app.timers. Toda llamada
tiene tiempo límite; un error se informa en el panel, nunca rompe Blender.

Las extensiones deben respetar bpy.app.online_access: si el usuario
desactivó el acceso a internet en Blender, Amatista no se conecta y lo dice.

Los resultados que no se pudieron enviar quedan en una cola en disco
(pendientes.json) y se reenvían cuando vuelve la conexión.
"""
import json
import platform
import queue
import threading
import urllib.error
import urllib.request
import uuid

import bpy

from . import ajustes, integridad

_resultados = queue.Queue()
_activos = 0
_candado = threading.Lock()

SIN_INTERNET = "El acceso a internet está desactivado en Blender (Preferencias › Sistema › Red)."


def en_linea_permitido():
    return bool(getattr(bpy.app, "online_access", True))


def sistema():
    return f"{platform.system()} {platform.release()}"[:60]


def _cabeceras(con_token):
    cabeceras = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Amatista-Addon": ajustes.VERSION_ADDON,
        "X-Blender-Version": bpy.app.version_string,
        "User-Agent": f"Amatista-Blender/{ajustes.VERSION_ADDON} Blender/{bpy.app.version_string}",
    }
    # La copia del add-on (integridad.py) y la marca de agua de su descarga:
    # el servidor marca como «sin verificar» lo que mande una copia modificada.
    revision = integridad.revisar()
    cabeceras["X-Amatista-Integridad"] = revision["estado"]
    if revision["huella"]:
        cabeceras["X-Amatista-Huella"] = revision["huella"]
    licencia = integridad.licencia()
    if licencia.get("id"):
        cabeceras["X-Amatista-Licencia"] = str(licencia["id"])[:64]
    p = ajustes.prefs()
    if con_token and p and p.token:
        cabeceras["Authorization"] = f"Bearer {p.token}"
    return cabeceras


def _detalle(error):
    try:
        cuerpo = json.loads(error.read().decode("utf-8"))
        detalle = cuerpo.get("detail")
        if isinstance(detalle, list):
            return "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detalle)
        if isinstance(detalle, dict):
            return detalle.get("mensaje") or json.dumps(detalle, ensure_ascii=False)
        return str(detalle or error.reason)
    except Exception:  # noqa: BLE001
        return str(getattr(error, "reason", error))


def pedir(metodo, ruta, al_terminar=None, datos=None, con_token=True, segundos=12):
    """Petición en segundo plano. al_terminar(respuesta, error, estado) corre en el hilo principal."""
    global _activos
    if not en_linea_permitido():
        if al_terminar:
            al_terminar(None, SIN_INTERNET, 0)
        return
    url = ajustes.servidor() + ruta
    if not url.lower().startswith(("https://", "http://")):
        # Solo HTTP(S): una dirección file:// o rara en las preferencias no debe leerse.
        if al_terminar:
            al_terminar(None, "La dirección del servidor debe empezar con https://", 0)
        return
    cabeceras = _cabeceras(con_token)
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None

    def trabajo():
        global _activos
        try:
            peticion = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cabeceras)
            with urllib.request.urlopen(peticion, timeout=segundos) as respuesta:
                texto = respuesta.read().decode("utf-8")
                _resultados.put((al_terminar, json.loads(texto) if texto else {}, None, respuesta.status))
        except urllib.error.HTTPError as error:
            _resultados.put((al_terminar, None, _detalle(error), error.code))
        except Exception as error:  # noqa: BLE001 - sin red, DNS, tiempo agotado...
            razon = getattr(error, "reason", error)
            _resultados.put((al_terminar, None, f"No se pudo conectar con Amatista ({razon}).", 0))
        finally:
            with _candado:
                _activos -= 1

    with _candado:
        _activos += 1
    threading.Thread(target=trabajo, daemon=True).start()
    if not bpy.app.timers.is_registered(_entregar):
        bpy.app.timers.register(_entregar, first_interval=0.1, persistent=True)


def _entregar():
    while not _resultados.empty():
        al_terminar, respuesta, error, estado = _resultados.get()
        if al_terminar is None:
            continue
        try:
            al_terminar(respuesta, error, estado)
        except Exception as fallo:  # noqa: BLE001
            print(f"[Amatista] Error al procesar la respuesta: {fallo}")
    with _candado:
        ocupado = _activos > 0
    return 0.15 if ocupado or not _resultados.empty() else None


def esperar(segundos=10.0):
    """Solo para pruebas en modo background: procesa respuestas hasta vaciar la cola."""
    import time

    limite = time.time() + segundos
    while time.time() < limite:
        _entregar()
        with _candado:
            if _activos == 0 and _resultados.empty():
                return True
        time.sleep(0.05)
    return False


# --- Cola de resultados sin conexión -------------------------------------------


def _archivo_cola():
    return ajustes.carpeta_usuario() / "pendientes.json"


def leer_cola():
    try:
        return json.loads(_archivo_cola().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _guardar_cola(elementos):
    try:
        _archivo_cola().write_text(json.dumps(elementos[-50:], ensure_ascii=False), encoding="utf-8")
    except OSError as error:
        print(f"[Amatista] No se pudo guardar la cola: {error}")


def encolar(ruta, datos):
    elementos = leer_cola()
    elementos.append({"id": str(uuid.uuid4()), "ruta": ruta, "datos": datos})
    _guardar_cola(elementos)


def vaciar_cola(al_terminar=None):
    """Reenvía lo pendiente. Un error de red deja el elemento en la cola."""
    elementos = leer_cola()
    if not elementos:
        if al_terminar:
            al_terminar(0)
        return
    restantes = list(elementos)
    enviados = []

    def siguiente():
        if not restantes:
            _guardar_cola([e for e in leer_cola() if e["id"] not in enviados])
            if al_terminar:
                al_terminar(len(enviados))
            return
        elemento = restantes.pop(0)

        def listo(respuesta, error, estado):
            if error is None or 400 <= estado < 500:  # un 4xx no se arregla reintentando
                enviados.append(elemento["id"])
                siguiente()
            else:
                _guardar_cola([e for e in leer_cola() if e["id"] not in enviados])
                if al_terminar:
                    al_terminar(len(enviados))

        pedir("POST", elemento["ruta"], listo, elemento["datos"])

    siguiente()
