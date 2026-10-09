"""Enlace en vivo con la plataforma (motor 3.4, API /api/addon/v1/enlace).

Antes Blender y la plataforma solo se hablaban al vincular y al enviar un
intento: eran dos programas separados. Ahora Blender «late» cada pocos
segundos con lo que está pasando (práctica, paso, progreso, si está
enfocado) y en la respuesta recibe:

- órdenes de la plataforma: abrir una práctica («Abrir en Blender»),
  enfocar, ver todo Blender o volver a leer los ajustes. Cada orden trae un
  id y se repite hasta que Blender avisa que la cumplió (orden_hecha), así
  que un latido perdido no pierde la orden;
- los ajustes que el alumno eligió en «Mi Blender» de la plataforma
  (enfoque, acompañamiento, avisos y tarjeta 3D), que mandan sobre los de
  Blender.

Sin cuenta vinculada, sin internet o con un servidor sin la tabla del
enlace (Oracle 010 sin ejecutar) no pasa nada: Blender sigue funcionando y
solo late más despacio.
"""
import time

import bpy

from . import ajustes, red

INTERVALO = 5.0
SEPARACION = 2.0  # entre latidos urgentes: el servidor acepta 40 por minuto
LENTO = 60.0  # sin enlace en el servidor o sin red: se reintenta despacio
ESTADO = {
    "en_vuelo": False,
    "enlace": None,  # None: todavía no sabemos; False: el servidor no tiene enlace
    "intervalo": INTERVALO,
    "hecha": "",  # id de la última orden cumplida (se avisa en el siguiente latido)
    "cumplidas": [],
    "ultimo": 0.0,
    "ajustes": {},
    "mensaje": "",
}
# Ajuste de la plataforma → preferencia de Blender.
AJUSTES = {
    "enfoque": ("enfoque", str),
    "acompanamiento": ("acompanamiento", str),
    "avisos_herramientas": ("avisar_herramientas", bool),
    "tarjeta_3d": ("mostrar_hud", bool),
}


def _datos():
    from . import enfoque, practicas

    datos = {
        "version_addon": ajustes.VERSION_ADDON,
        "version_blender": bpy.app.version_string[:20],
        "enfocado": enfoque.activo(),
    }
    sc = getattr(bpy.context, "scene", None)
    practica = practicas.practica_activa() if sc is not None else None
    if practica is not None and sc.amatista.origen != "borrador":
        reporte = practicas.ESTADO["reporte"]
        datos["practica_id"] = practica.id[:80]
        if reporte is not None:
            datos["progreso"] = max(0, min(100, int(round(reporte.progress))))
            if reporte.current_target_id:
                datos["paso"] = str(reporte.current_target_id)[:80]
    if ESTADO["hecha"]:
        datos["orden_hecha"] = ESTADO["hecha"]
    return datos


def latir(forzar=False):
    """Un latido (si hay cuenta y no hay otro en camino)."""
    p = ajustes.prefs()
    if not (p and p.token) or not red.en_linea_permitido() or ESTADO["en_vuelo"]:
        return
    if not forzar and time.time() - ESTADO["ultimo"] < ESTADO["intervalo"] - 0.5:
        return
    ESTADO["en_vuelo"] = True
    ESTADO["ultimo"] = time.time()
    enviado = ESTADO["hecha"]

    def listo(respuesta, error, estado):
        ESTADO["en_vuelo"] = False
        if error is not None or not isinstance(respuesta, dict):
            ESTADO["intervalo"] = LENTO if estado in (0, 404) else INTERVALO * 2
            ESTADO["mensaje"] = error or ""
            return
        ESTADO["enlace"] = bool(respuesta.get("enlace"))
        ESTADO["intervalo"] = float(respuesta.get("intervalo") or INTERVALO) if ESTADO["enlace"] else LENTO
        ESTADO["mensaje"] = ""
        if enviado and ESTADO["hecha"] == enviado:
            ESTADO["hecha"] = ""  # el servidor ya sabe que se cumplió
        aplicar_ajustes(respuesta.get("ajustes") or {})
        orden = respuesta.get("orden")
        if isinstance(orden, dict) and orden.get("id"):
            cumplir(orden)

    red.pedir("POST", "/api/addon/v1/enlace", listo, _datos(), segundos=8)


def latir_pronto():
    """Algo importante cambió (se abrió una práctica, avanzó…): latir pronto."""
    if not bpy.app.timers.is_registered(_latir_ya):
        espera = max(0.3, SEPARACION - (time.time() - ESTADO["ultimo"]))
        bpy.app.timers.register(_latir_ya, first_interval=espera)


def _latir_ya():
    if ESTADO["en_vuelo"]:
        return 0.5  # el que va en camino no lleva lo último: se espera y se manda
    latir(forzar=True)
    return None


def aplicar_ajustes(valores):
    """Lo que el alumno eligió en la plataforma manda sobre las preferencias de Blender."""
    p = ajustes.prefs()
    if p is None or not isinstance(valores, dict):
        return False
    cambio = False
    for clave, (propiedad, tipo) in AJUSTES.items():
        if clave not in valores:
            continue
        valor = tipo(valores[clave])
        try:
            if getattr(p, propiedad) != valor:
                setattr(p, propiedad, valor)
                cambio = True
        except (TypeError, ValueError, AttributeError):
            continue  # un valor que esta versión no conoce
    ESTADO["ajustes"] = dict(valores)
    if cambio:
        ajustes.guardar_preferencias()
    return cambio


def _terminada(orden_id):
    ESTADO["hecha"] = orden_id
    ESTADO["cumplidas"] = (ESTADO["cumplidas"] + [orden_id])[-20:]
    latir_pronto()


def cumplir(orden):
    """Ejecuta una orden de la plataforma una sola vez (aunque llegue repetida)."""
    from . import enfoque, practicas

    orden_id = str(orden["id"])
    if orden_id in ESTADO["cumplidas"]:
        ESTADO["hecha"] = orden_id
        return False
    tipo = orden.get("tipo")
    datos = orden.get("datos") or {}
    context = bpy.context
    if tipo == "abrir_practica" and datos.get("practica_id"):
        def abierta(error):
            if error:
                print(f"[Amatista] La plataforma pidió abrir {datos['practica_id']}: {error}")
            _terminada(orden_id)

        ESTADO["cumplidas"] = (ESTADO["cumplidas"] + [orden_id])[-20:]  # que un latido no la repita mientras baja
        practicas.abrir_por_id(context, datos["practica_id"], abierta)
        practicas.mostrar_en_amatista(context)
        return True
    if tipo == "enfocar":
        enfoque.activar(practicas.practica_activa(context))
    elif tipo == "ver_todo":
        enfoque.ver_todo(getattr(practicas.practica_activa(context), "id", ""))
    elif tipo == "actualizar":
        practicas.refrescar_catalogo()
        practica = practicas.practica_activa(context)
        if practica is not None:
            enfoque.al_abrir_practica(practica, nueva=False)
    _terminada(orden_id)
    practicas.redibujar()
    return True


def _latidor():
    try:
        latir()
    except Exception as error:  # noqa: BLE001 - el enlace nunca rompe Blender
        ESTADO["en_vuelo"] = False
        print(f"[Amatista] Enlace: {error}")
    return 1.0


def register():
    if not bpy.app.timers.is_registered(_latidor):
        bpy.app.timers.register(_latidor, first_interval=3.0, persistent=True)


def unregister():
    for temporizador in (_latidor, _latir_ya):
        if bpy.app.timers.is_registered(temporizador):
            bpy.app.timers.unregister(temporizador)
