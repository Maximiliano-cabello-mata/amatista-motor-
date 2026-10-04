"""Lo que el alumno aprende (motor v3): mapa del curso, píldoras y repaso.

- El mapa sale de practicas/cursos.json (amatista.curriculum/1): cursos
  Principiante y Principiante-Intermedio con sus módulos; cada módulo se
  cierra con una práctica en Blender.
- avance.json, en la carpeta del usuario, guarda lo que vive fuera del
  .blend: prácticas terminadas, píldoras vistas y el repaso espaciado
  (cajas de Leitner, pedagogy/spaced.py). Si hay cuenta vinculada, el
  servidor también lo sabe; este archivo permite trabajar sin conexión.
- Después de cada evaluación, practicas.py llama a actualizar_pildoras():
  la píldora que toca se muestra en la pestaña «Aprender», en la tarjeta de
  la vista 3D y, la primera vez, como ventana.
"""
import json
import time
from pathlib import Path

from . import _motor, ajustes

spaced = _motor.repaso
curriculo = _motor.curriculo

ESTADO = {
    "pildoras": (),  # PillDefinition que tocan ahora (la primera es la principal)
    "nuevas": (),  # ids que aparecieron en la última evaluación
    "plan": None,
    "avance": None,
}


# --- Archivo de avance -----------------------------------------------------------------


def _ruta_avance():
    return ajustes.carpeta_usuario() / "avance.json"


def avance():
    if ESTADO["avance"] is None:
        try:
            datos = json.loads(_ruta_avance().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        datos.setdefault("completadas", [])
        datos.setdefault("pildoras_vistas", {})
        datos.setdefault("repaso", {})
        ESTADO["avance"] = datos
    return ESTADO["avance"]


def guardar_avance():
    try:
        _ruta_avance().write_text(json.dumps(avance(), ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as error:
        print(f"[Amatista] No se pudo guardar tu avance: {error}")


def marcar_completada(practica_id):
    datos = avance()
    if practica_id not in datos["completadas"]:
        datos["completadas"].append(practica_id)
        guardar_avance()


def completadas():
    """Terminadas en este equipo o, según el servidor, en la cuenta."""
    from . import practicas

    hechas = set(avance()["completadas"])
    for pid, meta in practicas.ESTADO["catalogo_servidor"].items():
        progreso = meta.get("progreso") or {}
        if progreso.get("completada") or (progreso.get("progreso") or 0) >= 100:
            hechas.add(pid)
    return hechas


# --- Mapa de cursos ----------------------------------------------------------------------


def _ruta_plan():
    from . import practicas

    carpeta = practicas.carpeta_paquete()
    for ruta in (carpeta / "cursos.json", carpeta / "blender" / "cursos.json"):
        if ruta.exists():
            return ruta
    return None


def plan():
    if ESTADO["plan"] is None:
        ruta = _ruta_plan()
        try:
            ESTADO["plan"] = curriculo.load_curriculum(json.loads(Path(ruta).read_text(encoding="utf-8"))) if ruta else None
        except (OSError, ValueError, Exception) as error:  # noqa: BLE001 - un plan roto no rompe Blender
            print(f"[Amatista] No se pudo leer el plan de estudios: {error}")
            ESTADO["plan"] = None
    return ESTADO["plan"]


def estados():
    """{practica_id: completado | disponible | bloqueado | proximamente}."""
    p = plan()
    if p is None:
        return {}
    estado = curriculo.unlock_state(p, completadas())
    if ajustes.es_desarrollador():
        # Quien diseña prácticas puede abrir cualquiera.
        estado = {k: (v if v != curriculo.BLOQUEADO else curriculo.DISPONIBLE) for k, v in estado.items()}
    return estado


def siguiente():
    p = plan()
    return curriculo.next_practice(p, completadas()) if p else None


def lugar(practica):
    """(curso, módulo) del plan para una práctica, o (None, None)."""
    p = plan()
    if p is None or practica is None:
        return None, None
    encontrado = p.locate(practica.id)
    return encontrado if encontrado else (None, None)


# --- Píldoras ----------------------------------------------------------------------------


def vistas(practica_id):
    return set(avance()["pildoras_vistas"].get(practica_id, []))


def actualizar_pildoras(practica, foto, reporte):
    """Después de evaluar: qué píldoras tocan y cuáles son nuevas."""
    if not practica.pills:
        ESTADO.update(pildoras=(), nuevas=())
        return ()
    anteriores = {p.id for p in ESTADO["pildoras"]}
    tocan = _motor.MOTOR.pills(practica, foto, reporte, seen=vistas(practica.id))
    ESTADO["pildoras"] = tocan
    ESTADO["nuevas"] = tuple(p.id for p in tocan if p.id not in anteriores)
    return tocan


def pildora_principal():
    return ESTADO["pildoras"][0] if ESTADO["pildoras"] else None


def marcar_vista(practica, pildora_id, ahora=None):
    """«Entendido»: no vuelve a aparecer sola (salvo once=false) y entra al repaso si trae pregunta."""
    datos = avance()
    lista = datos["pildoras_vistas"].setdefault(practica.id, [])
    if pildora_id not in lista:
        lista.append(pildora_id)
    pildora = practica.pill(pildora_id)
    if pildora is not None and pildora.check is not None and spaced is not None:
        datos["repaso"] = spaced.introduce(datos["repaso"], spaced.item_id(practica.id, pildora_id), ahora or time.time())
    ESTADO["pildoras"] = tuple(p for p in ESTADO["pildoras"] if p.id != pildora_id or not p.once)
    guardar_avance()


# --- Repaso espaciado --------------------------------------------------------------------


def repasos_pendientes(practica, ahora=None, catalogo=None):
    """[(item, PillDefinition)] que toca repasar al abrir esta práctica (máx. 3)."""
    if spaced is None or practica is None or not practica.review:
        return []
    from . import practicas

    estado = avance()["repaso"]
    ahora = ahora or time.time()
    catalogo = catalogo if catalogo is not None else practicas.catalogo()
    pendientes = []
    for ref in practica.review:
        origen, _, pildora_id = ref.partition("#")
        if ref in estado and estado[ref].get("due", 0) > ahora:
            continue  # todavía no toca
        definicion = (catalogo.get(origen) or {}).get("definicion")
        if not definicion:
            continue
        try:
            otra = _motor.practica.parse_practice(definicion)
        except Exception:  # noqa: BLE001
            continue
        pildora = otra.pill(pildora_id)
        if pildora is not None and pildora.check is not None:
            pendientes.append((ref, pildora))
    return pendientes[:3]


def responder(item, correcto, ahora=None):
    datos = avance()
    if spaced is not None:
        datos["repaso"] = spaced.answer(datos["repaso"], item, bool(correcto), ahora or time.time())
        guardar_avance()


def dominadas():
    return spaced.mastered(avance()["repaso"]) if spaced is not None else []


def reiniciar_sesion():
    ESTADO.update(pildoras=(), nuevas=())
