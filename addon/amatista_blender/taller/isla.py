"""Tu isla: cada proyecto terminado deja su pieza en un mismo mundo.

Al terminar el proyecto de un taller, las mallas del alumno (su tren, su
espada, su nave…) se guardan en ``isla/<taller>.blend`` dentro de la
carpeta del usuario, con sus materiales. «Mi isla» arma una escena aparte,
«Amatista · Mi isla», con una isla redonda y cada pieza en su lugar
(``isla.lugar`` del taller). Las piezas se copian: lo que se haga en la
isla no cambia los proyectos ni al revés.

La isla se arma solo cuando el alumno la abre (riesgo «que la isla pese
mucho»): nada de esto corre mientras practica.
"""
import math
import re
from pathlib import Path

import bpy
from mathutils import Vector

from .. import ajustes
from . import datos, escena

NOMBRE = "Amatista · Mi isla"
MARCA = "amatista_isla"
LADO_PIEZA = 4.0  # cada pieza cabe en unos 4 m de la isla
RADIO_ISLA = 11.0


def carpeta():
    ruta = ajustes.carpeta_usuario() / "isla"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _archivo(taller_id):
    return carpeta() / (re.sub(r"[^a-z0-9._-]+", "-", taller_id.lower()) + ".blend")


def guardar_pieza(sc, taller_id):
    """Guarda las mallas del alumno de esta escena como la pieza del taller en la isla."""
    objetos = {o for o in sc.objects if o.type == "MESH" and not o.get("amatista_ignore")}
    if not objetos:
        return None
    ruta = _archivo(taller_id)
    bloques = set(objetos)
    for obj in objetos:
        if obj.data is not None:
            bloques.add(obj.data)
        for slot in obj.material_slots:
            if slot.material is not None:
                bloques.add(slot.material)
    bpy.data.libraries.write(str(ruta), bloques, fake_user=False, compress=True)
    avance = datos.avance()
    avance["isla"][taller_id] = {"archivo": ruta.name, "piezas": len(objetos)}
    datos.guardar()
    return ruta


def piezas_guardadas():
    """{taller: Path} de las piezas que ya tiene la isla."""
    salida = {}
    for tid, info in (datos.avance().get("isla") or {}).items():
        ruta = carpeta() / str((info or {}).get("archivo") or "")
        if ruta.is_file():
            salida[tid] = ruta
    return salida


def _suelo(sc):
    """La isla redonda y el agua (decorado: el motor no los revisa)."""
    for nombre, pieza, color in (
        ("Mar", {"primitive": "cylinder", "size": (RADIO_ISLA * 4, RADIO_ISLA * 4, 0.1), "location": (0, 0, -0.35)},
         (0.16, 0.42, 0.62, 1.0)),
        ("Isla", {"primitive": "cylinder", "size": (RADIO_ISLA * 2, RADIO_ISLA * 2, 0.6), "location": (0, 0, -0.3)},
         (0.45, 0.66, 0.36, 1.0)),
    ):
        obj = escena.crear_pieza(sc, pieza, f"Amatista · {nombre}")
        obj["amatista_ignore"] = 1
        obj.hide_select = True
        mat = bpy.data.materials.get(f"Amatista · {nombre}") or bpy.data.materials.new(f"Amatista · {nombre}")
        mat.diffuse_color = color
        obj.data.materials.append(mat)
        obj.color = color


def _cargar(sc, taller_id, ruta, lugar):
    with bpy.data.libraries.load(str(ruta), link=False) as (origen, destino):
        destino.objects = list(origen.objects)
    nuevos = [o for o in destino.objects if o is not None]
    if not nuevos:
        return 0
    coleccion = bpy.data.collections.new(f"Isla · {taller_id}")
    sc.collection.children.link(coleccion)
    for obj in nuevos:
        coleccion.objects.link(obj)
    # Que la pieza quepa en su lugar: se escala para que su lado mayor mida unos 4 m y se apoya en la isla.
    bpy.context.view_layer.update()
    puntos = [o.matrix_world @ Vector(c) for o in nuevos for c in o.bound_box]
    minimo = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
    maximo = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
    lado = max((maximo - minimo).x, (maximo - minimo).y, 0.01)
    factor = min(1.0, LADO_PIEZA / lado)
    centro = Vector(((minimo.x + maximo.x) / 2, (minimo.y + maximo.y) / 2, minimo.z))
    destino_xy = Vector((float(lugar[0]), float(lugar[1]), 0.0))
    for obj in nuevos:
        if obj.parent is not None:
            continue
        obj.location = destino_xy + (obj.location - centro) * factor
        obj.scale = obj.scale * factor
    return len(nuevos)


def abrir(context=None):
    """Arma la isla con las piezas guardadas y la muestra (texto para el alumno)."""
    context = context or bpy.context
    c = datos.catalogo()
    piezas = piezas_guardadas()
    sc = next((s for s in bpy.data.scenes if s.get(MARCA)), None)
    if sc is None:
        sc = bpy.data.scenes.new(NOMBRE)
        sc[MARCA] = 1
    for obj in list(sc.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for hija in list(sc.collection.children):
        sc.collection.children.unlink(hija)
        if hija.users == 0:
            bpy.data.collections.remove(hija)
    ventana = getattr(context, "window", None) or (bpy.context.window_manager.windows[0]
                                                   if bpy.context.window_manager.windows else None)
    if ventana is not None:
        ventana.scene = sc
    _suelo(sc)
    puestas = 0
    for tid, ruta in piezas.items():
        t = c.taller(tid) if c is not None else None
        lugar = (t.isla.get("lugar") if t is not None else None) or (
            RADIO_ISLA * 0.6 * math.cos(puestas), RADIO_ISLA * 0.6 * math.sin(puestas))
        try:
            if _cargar(sc, tid, ruta, lugar):
                puestas += 1
        except (OSError, RuntimeError) as error:
            print(f"[Amatista] No se pudo poner la pieza de {tid} en la isla: {error}")
    try:
        escena.encuadrar(context, [{"location": (0, 0, 0), "size": (RADIO_ISLA * 1.6,) * 3}])
    except Exception:  # noqa: BLE001
        pass
    if not puestas:
        return "Tu isla está esperando: cada proyecto que termines deja aquí su pieza."
    return f"Tu isla tiene {puestas} pieza{'s' if puestas != 1 else ''}."


def ruta_de(taller_id):
    ruta = _archivo(taller_id)
    return ruta if Path(ruta).is_file() else None
