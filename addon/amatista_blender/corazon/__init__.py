"""El Corazón Amatista dentro de Blender: el director de la práctica abierta.

Antes, quién decidía qué ver (qué señal, cuándo, por cuánto tiempo) eran
estados globales del add-on con relojes (brillo 9 s, ficha 16 s, avisos 5 s).
Ahora lo decide el corazón (``amatista_engine.corazon``) y aquí solo se
conecta Blender:

- un ``Director`` por práctica, armado con la rama ``blender-principiante``
  (``practices/ramas/``, viaja en el .zip en ``ramas/``);
- ``AdaptadorBlender`` hace las señales y las comprueba;
- cada 0,5 s, mientras el guion manda, se vuelve a comprobar la señal: si el
  alumno eligió otra herramienta, la banda lo dice y ofrece «Señálalo otra vez»;
- el historial del andamio (qué herramientas ya usa solo) se guarda por cuenta
  en la carpeta del add-on; con una cuenta de administrador vive en memoria.

Si algo del corazón falla, el guion del motor 7 sigue funcionando como antes
(``activo()`` devuelve False y el guion usa su camino de siempre).
"""
import hashlib
import json
import time
from importlib import import_module
from pathlib import Path

import bpy

from .. import _motor, ajustes

ramas = import_module(_motor.engine.__name__ + ".corazon.ramas")
andamiaje = import_module(_motor.engine.__name__ + ".corazon.andamiaje")
contrato = import_module(_motor.engine.__name__ + ".corazon.contrato")

RAMA = "blender-principiante"
VIGILAR = 0.5  # s entre comprobaciones de la señal
ESTADO = {"director": None, "practica_id": "", "guion": None, "adaptador": None, "historial": None, "cuenta": None,
          "huella_senal": None, "error": ""}


def _carpeta_ramas():
    paquete = Path(__file__).resolve().parents[1] / "ramas"  # dentro del .zip
    if paquete.is_dir():
        return paquete
    return Path(__file__).resolve().parents[3] / "practices" / "ramas"  # desde el repositorio


def _rama():
    try:
        todas = ramas.cargar_ramas(_carpeta_ramas())
        if RAMA in todas:
            return todas[RAMA], todas
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Corazón: no se leyeron las ramas ({error})")
    r = ramas.Rama(id=RAMA, software="blender", extensiones=("rescate-tras-tropiezos", "vistas-espaciales"))
    return r, {r.id: r}


def activo():
    return ESTADO["director"] is not None


def director():
    return ESTADO["director"]


def programa():
    if ESTADO["adaptador"] is None:
        from .adaptador import AdaptadorBlender

        ESTADO["adaptador"] = AdaptadorBlender()
    return ESTADO["adaptador"]


# --- El historial del andamio ------------------------------------------------------------------


def _cuenta():
    p = ajustes.prefs()
    return (getattr(p, "cuenta_id", "") or "") if p and getattr(p, "token", "") else ""


def _ruta_historial(cuenta):
    nombre = "local" if not cuenta else hashlib.sha1(cuenta.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return ajustes.carpeta_usuario() / f"corazon_andamio_{nombre}.json"


def historial():
    cuenta = _cuenta()
    if ESTADO["historial"] is not None and ESTADO["cuenta"] == cuenta:
        return ESTADO["historial"]
    h = andamiaje.Historial()
    if not ajustes.sin_progreso():
        try:
            h = andamiaje.Historial.desde_dict(json.loads(_ruta_historial(cuenta).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    ESTADO.update(historial=h, cuenta=cuenta)
    return h


def guardar_historial():
    h = ESTADO["historial"]
    if h is None or ajustes.sin_progreso():
        return  # administrador: nada se guarda en este equipo
    try:
        _ruta_historial(ESTADO["cuenta"] or "").write_text(json.dumps(h.como_dict(), ensure_ascii=False), encoding="utf-8")
    except OSError as error:
        print(f"[Amatista] Corazón: no se guardó el historial ({error})")


# --- El director de la práctica abierta --------------------------------------------------------


def al_evaluar(practica, guion, reporte):
    """El guion avanzó con un reporte nuevo: el corazón decide el turno. Devuelve el turno o None."""
    try:
        d = ESTADO["director"]
        if d is None or ESTADO["practica_id"] != practica.id or ESTADO["guion"] is not guion:
            rama, todas = _rama()
            d = ramas.crear_director(practica, rama, adaptador=programa(), todas=todas, historial=historial(),
                                     guion=guion, ahora=time.time())
            ESTADO.update(director=d, practica_id=practica.id, guion=guion)
        antes = d.historial.como_dict()
        t = d.ciclo(programa(), reporte, time.time())
        if d.historial.como_dict() != antes:
            guardar_historial()
        _vigilar_encendido(not t.completo)
        ESTADO["error"] = ""
        return t
    except Exception as error:  # noqa: BLE001 - el corazón nunca rompe el guion
        ESTADO.update(director=None, error=str(error))
        print(f"[Amatista] Corazón: {error}")
        return None


def turno():
    d = ESTADO["director"]
    return d.turno(time.time()) if d is not None else None


def pedir_pista(nivel=0):
    """La pista del corazón y, si toca, su señal ya hecha y comprobada."""
    d = ESTADO["director"]
    if d is None:
        return None, None
    ahora = time.time()
    p = d.pedir_pista(ahora, nivel)
    t = d.ciclo(programa(), None, ahora)
    return p, t


def repetir_senal():
    d = ESTADO["director"]
    if d is None:
        return None
    ahora = time.time()
    d.repetir_senal(ahora)
    return d.ciclo(programa(), None, ahora)


def evento(tipo, **datos):
    d = ESTADO["director"]
    if d is not None:
        d.evento(contrato.Evento(tipo, time.time(), datos))


def olvidar():
    """Se abrió otro archivo o se apagó el guion: el director de antes ya no vale."""
    ESTADO.update(director=None, practica_id="", guion=None, huella_senal=None)
    _vigilar_encendido(False)


# --- Comprobar la señal sin esperar a que cambie la escena ------------------------------------


def _huella(t):
    s = t.senal if t is not None else None
    return None if s is None else (s.senal.tipo, s.senal.herramienta, s.estado)


def _vigilar():
    d = ESTADO["director"]
    if d is None:
        return None
    try:
        from .. import guion

        if not guion.activo():
            return VIGILAR
        t = d.ciclo(programa(), None, time.time())
        huella = _huella(t)
        if huella != ESTADO["huella_senal"]:
            ESTADO["huella_senal"] = huella
            guion._redibujar()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Corazón (vigilar): {error}")
    return VIGILAR


def _vigilar_encendido(encendido):
    if bpy.app.background:
        return  # sin ventana nadie cambia de herramienta: las pruebas llaman a ciclo directamente
    registrado = bpy.app.timers.is_registered(_vigilar)
    if encendido and not registrado:
        bpy.app.timers.register(_vigilar, first_interval=VIGILAR, persistent=True)
    elif not encendido and registrado:
        bpy.app.timers.unregister(_vigilar)


def unregister():
    olvidar()
    ESTADO.update(adaptador=None, historial=None, cuenta=None)


__all__ = ["activo", "al_evaluar", "director", "evento", "guardar_historial", "historial", "olvidar",
           "pedir_pista", "programa", "repetir_senal", "turno", "unregister"]
