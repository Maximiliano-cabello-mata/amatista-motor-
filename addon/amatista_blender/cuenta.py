"""Vincular Blender con la cuenta de Amatista sin escribir la contraseña en Blender.

Dos caminos:
1. Paquete personal: si el alumno descargó el add-on con su sesión iniciada,
   config.json trae un vínculo de un solo uso ya confirmado. Al abrir
   Blender se canjea solo: el alumno no hace nada.
2. Código de dispositivo (como en las televisiones): Blender muestra un
   código, el alumno lo escribe en la plataforma (#/vincular) y Blender
   recibe su token.

El token es una sesión de la tabla SESIONES (dispositivo «blender-addon …»):
la plataforma la puede cerrar desde «Mis dispositivos».
"""
import time
import webbrowser

import bpy

from . import ajustes, red

VINCULO = {"id": "", "codigo": "", "secreto": "", "expira": 0.0, "url": "", "mensaje": "", "activo": False}
INTERVALO = 3.0


def _dispositivo():
    """Descripción del dispositivo que verá el alumno en «Mis dispositivos» (máx. 200 caracteres)."""
    return f"blender-addon {ajustes.VERSION_ADDON} · Blender {bpy.app.version_string} · {red.sistema()}"[:200]


def _guardar_cuenta(respuesta):
    """Guarda token y datos de la cuenta tras vincular, y dispara catálogo, cola pendiente y sincronización del taller."""
    p = ajustes.prefs()
    if p is None:
        return
    p.token = respuesta["token"]
    cuenta = respuesta.get("cuenta") or {}
    p.cuenta = cuenta.get("nombre") or cuenta.get("email") or "Mi cuenta"
    p.cuenta_id = cuenta.get("id") or ""
    p.rol = cuenta.get("rol") or "alumno"
    ajustes.guardar_preferencias()
    from . import practicas

    practicas.refrescar_catalogo()
    practicas.cargar_practica_actual()
    red.vaciar_cola()
    _sincronizar_taller()


def _sincronizar_taller():
    """Add-on 5: el avance del taller (lo hecho sin cuenta pasa a la cuenta) y el del servidor."""
    from .taller import datos

    try:
        datos.sincronizar()
    except Exception as error:  # noqa: BLE001 - sincronizar nunca rompe el vínculo
        print(f"[Amatista] Taller: {error}")


def iniciar_vinculo(al_terminar=None):
    """Pide un código nuevo y empieza a esperar la confirmación."""

    def listo(respuesta, error, estado):
        """Al recibir el código de vínculo: lo guarda (código, secreto, vencimiento), empieza a consultar y avisa a ``al_terminar``."""
        if error is None:
            VINCULO.update(
                id=respuesta["vinculo_id"],
                codigo=respuesta["codigo"],
                secreto=respuesta["secreto"],
                expira=time.time() + float(respuesta.get("expira_en_segundos", 600)),
                url=respuesta.get("url_vincular") or "",
                mensaje="Escribe este código en la plataforma.",
                activo=True,
            )
            if not bpy.app.timers.is_registered(_consultar):
                bpy.app.timers.register(_consultar, first_interval=INTERVALO)
        else:
            VINCULO.update(activo=False, mensaje=error)
        _redibujar()
        if al_terminar:
            al_terminar(error)

    red.pedir("POST", "/api/addon/v1/vinculos", listo, {"dispositivo": _dispositivo()}, con_token=False)


def _consultar():
    """Temporizador: mientras el código no venza, pregunta a la API si el alumno ya lo confirmó."""
    if not VINCULO["activo"]:
        return None
    if time.time() > VINCULO["expira"]:
        VINCULO.update(activo=False, codigo="", mensaje="El código venció. Pide uno nuevo.")
        _redibujar()
        return None
    consultar_vinculo(VINCULO["id"], VINCULO["secreto"])
    return INTERVALO


def consultar_vinculo(vinculo_id, secreto, al_terminar=None):
    """Pregunta a la API por el estado del vínculo (red); si está listo guarda la cuenta, si venció o se canjeó lo invalida."""
    def listo(respuesta, error, estado):
        """Procesa el estado del vínculo: listo → guarda token y cuenta; vencido/canjeado → pide un código nuevo."""
        if error is None and respuesta.get("estado") == "listo":
            VINCULO.update(activo=False, codigo="", mensaje="")
            _guardar_cuenta(respuesta)
        elif error is None and respuesta.get("estado") in ("vencido", "canjeado"):
            VINCULO.update(activo=False, codigo="", mensaje="El código ya no es válido. Pide uno nuevo.")
        elif estado in (404, 403):
            VINCULO.update(activo=False, codigo="", mensaje=error)
        _redibujar()
        if al_terminar:
            al_terminar(respuesta, error, estado)

    red.pedir(
        "POST", f"/api/addon/v1/vinculos/{vinculo_id}/estado", listo, {"secreto": secreto, "dispositivo": _dispositivo()},
        con_token=False,
    )


def cancelar_vinculo():
    """Detiene la espera del código de dispositivo."""
    VINCULO.update(activo=False, codigo="", mensaje="")
    _redibujar()


def canjear_vinculo_del_paquete():
    """Primer arranque tras instalar el paquete personal: conectar sin pasos."""
    vinculo = ajustes.CONFIG.get("vinculo") or {}
    p = ajustes.prefs()
    if not vinculo.get("id") or p is None or p.token or p.vinculo_usado == vinculo["id"]:
        return

    def listo(respuesta, error, estado):
        # Solo una respuesta definitiva gasta el vínculo: sin red o con el servidor caído
        # se vuelve a intentar en el próximo arranque.
        """Solo una respuesta definitiva gasta el vínculo incluido en el instalador; sin red se reintenta en el próximo arranque."""
        definitiva = (error is None and (respuesta or {}).get("estado") in ("listo", "canjeado", "vencido")) or \
            estado in (403, 404)
        p2 = ajustes.prefs()
        if p2 is not None and definitiva:
            p2.vinculo_usado = vinculo["id"]
            ajustes.guardar_preferencias()

    consultar_vinculo(vinculo["id"], vinculo.get("secreto", ""), listo)


def refrescar_cuenta():
    """Actualiza nombre y rol desde /yo; con 401 olvida el token."""
    p = ajustes.prefs()
    if p is None or not p.token:
        return

    def listo(respuesta, error, estado):
        """Actualiza nombre y rol de la cuenta; con 401 (token inválido) borra token y nombre guardados."""
        p2 = ajustes.prefs()
        if p2 is None:
            return
        # [REVISION-BUG] (menor) con 401 se borran token y nombre pero NO cuenta_id (desvincular() sí lo borra): lo que se encole después queda marcado con la cuenta vieja.
        if estado == 401:
            p2.token = ""
            p2.cuenta = ""
            ajustes.guardar_preferencias()
        elif error is None:
            p2.cuenta = respuesta.get("nombre") or respuesta.get("email") or p2.cuenta
            p2.rol = respuesta.get("rol") or p2.rol
        _redibujar()

    red.pedir("GET", "/api/addon/v1/yo", listo)


def desvincular():
    """Cierra la sesión en el servidor (si hay token) y borra los datos de la cuenta local."""
    p = ajustes.prefs()
    if p is None:
        return
    if p.token:
        red.pedir("POST", "/api/addon/v1/salir", None, {})
    p.token = ""
    p.cuenta = ""
    p.cuenta_id = ""
    p.rol = ""
    ajustes.guardar_preferencias()
    _redibujar()


def abrir_plataforma(ruta=""):
    """Abre la plataforma en el navegador en ``ruta``; False si el paquete no conoce su dirección."""
    base = ajustes.plataforma()
    if not base:
        return False
    webbrowser.open(base + ruta)
    return True


def _redibujar():
    """Redibuja los paneles."""
    from . import practicas

    practicas.redibujar()


def unregister():
    """Detiene el vínculo en curso y su temporizador."""
    VINCULO.update(activo=False)
    if bpy.app.timers.is_registered(_consultar):
        bpy.app.timers.unregister(_consultar)


def al_iniciar():
    """Tras registrar el add-on (o abrir Blender)."""
    canjear_vinculo_del_paquete()
    refrescar_cuenta()
    from . import practicas

    if red.en_linea_permitido():
        practicas.refrescar_catalogo()
        if ajustes.prefs() and ajustes.prefs().token:
            practicas.cargar_practica_actual()
            red.vaciar_cola()
            _sincronizar_taller()
    return None
