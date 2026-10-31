"""Simulaciones de alumnos armando el tren en Blender real (sin ventana).

    python addon/tests/simular_alumnos.py --motor 6 --n 100 --salida /tmp/sim6.json
    python addon/tests/simular_alumnos.py --motor 7 --n 100 --salida /tmp/sim7.json

(con el módulo bpy de PyPI, Python 3.11; o ``blender --background --python
addon/tests/simular_alumnos.py -- --motor 7``).

Cada alumno simulado es un principiante distinto: arma el tren de juguete
del módulo 1 con las operaciones reales de Blender (Shift+A, S, R, G,
Shift+D, Ctrl+A, guardar), en otro orden, con otras medidas, a lo largo de
otro eje, con ruedas un poco hundidas o despegadas, guardando con otro
nombre o sin guardar. Después de cada acción se lee lo que el alumno ve
(la tarjeta, el panel, la pista). Cuando el alumno cree que terminó y
Amatista no avanza, pide pistas y hace lo que la pista dice, si la pista
dice algo que se pueda hacer.

Se mide lo que frustra:

- **brillo fantasma**: el texto dice que algo brilla o está resaltado y no
  hay nada que brille (la barra está escondida o la herramienta no está ahí).
- **señal cruzada**: la tarjeta habla de una pieza o paso distinto del que
  Amatista está revisando de verdad.
- **instrucción vaga**: lo que se le pide no nombra qué hacer (ni la acción
  ni la pieza).
- **pista inútil**: la pista no tiene que ver con lo que falta.
- **bloqueo**: el alumno hizo un tren que un profesor aceptaría y Amatista
  no lo da por terminado ni le dice algo con lo que pueda salir.
- **superposición**: más de una cosa de Amatista dibujada a la vez en la
  vista 3D o más de un panel de Amatista diciendo «lo que sigue».

Sale un resumen por consola y, con --salida, el detalle en JSON.
"""
import argparse
import json
import math
import random
import re
import sys
import tempfile
import time
from pathlib import Path

import bpy  # noqa: I001
import addon_utils

ADDON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON))

TALLER = "blender.bp.m1"
PROYECTO = "proyecto:blender.bp.m1"
VAGUEDAD = re.compile(r"\b(agrega|pon|ponle|mueve|baja|sube|escala|gira|rota|duplica|guarda|estira|aplana|"
                      r"acerca|pega|junta|selecciona|usa|pulsa|abre|elige|quita|borra|haz|arma|coloca|deja)\b", re.I)
PIEZAS = re.compile(r"(vag[oó]n|locomotora|rueda|chimenea|archivo|tren|cubo|cilindro)", re.I)
BRILLO = re.compile(r"(brilla|resaltad|iluminad|se enciende|encendid)", re.I)


# --- Blender -------------------------------------------------------------------------------------


def preparar(motor):
    bpy.ops.wm.read_factory_settings(use_empty=False)
    addon_utils.enable("amatista_blender", default_set=True, handle_error=None)
    import shutil

    from amatista_blender import ajustes

    shutil.rmtree(ajustes.carpeta_usuario() / "practicas", ignore_errors=True)  # las prácticas del repositorio
    (ajustes.carpeta_usuario() / "avance.json").unlink(missing_ok=True)

    p = ajustes.prefs()
    p.presentar_herramientas = True  # lo que ve un alumno nuevo (motor 6.1)
    p.modo_curioso = "auto"
    p.enfoque = "auto"
    bpy.context.window_manager.amatista.modo = "alumno"
    if motor == 7:
        from amatista_blender import guion  # noqa: F401  (registra el motor 7)


def _actualizar():
    bpy.context.view_layer.update()


def agregar(tipo, **kw):
    getattr(bpy.ops.mesh, f"primitive_{tipo}_add")(**kw)
    return bpy.context.active_object


def duplicar(obj):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()
    return bpy.context.active_object


def aplicar_escala(obj):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def guardar(nombre):
    carpeta = Path(tempfile.mkdtemp(prefix="amatista_sim_"))
    bpy.ops.wm.save_as_mainfile(filepath=str(carpeta / nombre))


def caja(obj):
    _actualizar()
    from mathutils import Vector

    puntos = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return [min(p[i] for p in puntos) for i in range(3)], [max(p[i] for p in puntos) for i in range(3)]


# --- Lo que haría un principiante ----------------------------------------------------------------


def alumno(semilla):
    """Los rasgos de un alumno simulado (sorteados con su semilla)."""
    r = random.Random(semilla)
    return {
        "semilla": semilla,
        "eje": r.choice(("x", "x", "x", "y")),  # uno de cada cuatro arma el tren a lo largo de Y
        "orden": r.choice(("vagones", "vagones", "ruedas", "chimenea")),
        "alto": r.uniform(0.8, 1.2),
        "proporcion": r.uniform(1.45, 2.4),  # «cerca del doble de largo que de alto»
        "ancho": r.uniform(1.0, 1.4),
        "radio": r.uniform(0.28, 0.42),
        "grosor": r.uniform(0.12, 0.28),
        "hundida": r.choice((0.0, 0.0, 0.0, -0.04, 0.05, 0.12)),  # rueda apenas hundida o despegada del suelo
        "separa_rueda": r.choice((0.0, 0.0, 0.03, 0.08, 0.25)),  # hueco entre la rueda y el vagón
        "separa_vagon": r.choice((0.0, 0.1, 0.2, 0.35, 0.6)),
        "chimenea": r.choice(("loco", "loco", "loco", "flota", "vagon")),
        "duplica": r.random() < 0.6,  # Shift+D en vez de agregar cada rueda
        "aplica_escala": r.random() < 0.25,  # Ctrl+A › Escala (lo vio en un video)
        "vertices": r.choice((32, 32, 32, 16, 12)),  # «Ajustar última operación» del cilindro
        "nombre": r.choice(("mi_tren.blend", "tren.blend", "mi_tren.blend", "proyecto1.blend", "", "untitled.blend")),
        "pide_pistas": r.choice((1, 2, 3)),
    }


def armar(a):
    """Las acciones del alumno en orden: [(nombre, función)]."""
    eje = 0 if a["eje"] == "x" else 1
    otro = 1 - eje
    alto, ancho = a["alto"], a["ancho"]
    largo = alto * a["proporcion"]
    radio, grosor = a["radio"], a["grosor"]
    hecho = {"vagones": [], "ruedas": []}

    def vector(a_lo_largo, a_lo_ancho, z):
        v = [0.0, 0.0, z]
        v[eje] = a_lo_largo
        v[otro] = a_lo_ancho
        return tuple(v)

    def escala_vagon(f=1.0):
        s = [0.0, 0.0, alto / 2]
        s[eje] = largo * f / 2
        s[otro] = ancho / 2
        return tuple(s)

    centros = (largo / 2 + a["separa_vagon"] / 2, -(largo / 2 + a["separa_vagon"] / 2))
    acciones = []

    def vagon(i):
        def hacer():
            if i == 1 and a["duplica"] and hecho["vagones"]:
                v = duplicar(hecho["vagones"][0])
            else:
                v = agregar("cube")  # Shift+A › Malla › Cubo (2 m, en el cursor)
            v.scale = escala_vagon(1.0 if i == 0 else 0.9)  # S y luego S X
            v.location = vector(centros[i], 0.0, alto / 2 + 2 * radio * 0.55)  # G
            if a["aplica_escala"]:
                aplicar_escala(v)
            hecho["vagones"].append(v)
        return (f"vagón {i + 1}", hacer)

    def rueda(i):
        def hacer():
            vi = i // 4
            lado = 1 if i % 2 == 0 else -1
            delante = 1 if (i // 2) % 2 == 0 else -1
            c = centros[vi]
            x = c + delante * largo * (0.3 if vi == 0 else 0.27)
            y = lado * (ancho / 2 + grosor / 2 + a["separa_rueda"])
            z = radio + a["hundida"]
            if a["duplica"] and hecho["ruedas"]:
                w = duplicar(hecho["ruedas"][0])
            else:
                w = agregar("cylinder", vertices=a["vertices"])
                w.scale = (radio, radio, grosor / 2)  # S 0.35 y S Z
                w.rotation_euler = (math.radians(90), 0, 0) if eje == 0 else (0, math.radians(90), 0)  # R X 90
            w.location = vector(x, y, z)
            if a["aplica_escala"] and not hecho["ruedas"]:
                aplicar_escala(w)
            hecho["ruedas"].append(w)
        return (f"rueda {i + 1}", hacer)

    def chimenea():
        def hacer():
            c = agregar("cylinder", vertices=a["vertices"])
            c.scale = (0.2, 0.2, 0.35)
            base = 2 * radio * 0.55 + alto
            sobre = {"loco": 0.0, "flota": 0.25, "vagon": 0.0}[a["chimenea"]]
            donde = centros[1] if a["chimenea"] == "vagon" else centros[0] + largo * 0.3
            c.location = vector(donde, 0.0, base + 0.35 + sobre)
        return ("chimenea", hacer)

    vagones = [vagon(0), vagon(1)]
    ruedas = [rueda(i) for i in range(8)]
    if a["orden"] == "ruedas":
        acciones += vagones[:1] + ruedas[:4] + vagones[1:] + ruedas[4:] + [chimenea()]
    elif a["orden"] == "chimenea":
        acciones += vagones[:1] + [chimenea()] + vagones[1:] + ruedas
    else:
        acciones += vagones + ruedas + [chimenea()]
    if a["nombre"]:
        acciones.append((f"guardar {a['nombre']}", lambda: guardar(a["nombre"])))
    return acciones


def profesor(escena):
    """¿Un profesor aceptaría este tren? (sin mirar el nombre del archivo)."""
    mallas = [o for o in escena.objects if o.type == "MESH" and not o.get("amatista_demo")]
    cubos = [o for o in mallas if len(o.data.vertices) == 8]
    cilindros = [o for o in mallas if len(o.data.vertices) != 8]
    if len(cubos) < 2 or len(cilindros) < 9:
        return False, "faltan piezas"
    ruedas, chimeneas = [], []
    for c in cilindros:
        lo, hi = caja(c)
        d = sorted(hi[i] - lo[i] for i in range(3))
        (chimeneas if lo[2] > 0.5 else ruedas).append((c, lo, hi, d))
    if len(ruedas) < 8 or not chimeneas:
        return False, "ruedas o chimenea"
    for _c, lo, _hi, _d in ruedas:
        if abs(lo[2]) > 0.08:
            return False, "una rueda flota o se hunde a la vista"
    for _c, lo, hi, _d in ruedas:
        cerca = False
        for v in cubos:
            vlo, vhi = caja(v)
            hueco = max(max(vlo[i] - hi[i], lo[i] - vhi[i], 0) for i in range(2))
            cerca = cerca or hueco <= 0.1
        if not cerca:
            return False, "una rueda despegada del vagón"
    lo0, hi0 = caja(cubos[0])
    lo1, hi1 = caja(cubos[1])
    hueco = max(max(lo1[i] - hi0[i], lo0[i] - hi1[i], 0) for i in range(2))
    if hueco > 0.45:
        return False, "vagones separados"
    for _c, lo, _hi, _d in chimeneas:
        if not any(abs(lo[2] - caja(v)[1][2]) < 0.1 for v in cubos):
            return False, "chimenea flotando"
    return True, "aceptable"


# --- Lo que hace el alumno con una pista ---------------------------------------------------------


def seguir_pista(texto, escena, a):
    """Si la pista dice algo concreto, el alumno lo hace. Devuelve qué hizo ("" si no supo qué hacer)."""
    t = (texto or "").lower()
    mallas = [o for o in escena.objects if o.type == "MESH"]
    if re.search(r"guarda|guardar|archivo|ctrl ?\+ ?s", t):
        nombre = "mi_tren.blend" if "tren" in t else (a["nombre"] or "untitled.blend")
        guardar(nombre)
        return f"guardó como {nombre}"
    if re.search(r"suelo|flota|apoy|hundid", t) and "rueda" in t:
        for o in mallas:
            if len(o.data.vertices) != 8:
                lo, hi = caja(o)
                if lo[2] < 0.5:
                    o.location.z -= lo[2]
        return "bajó las ruedas al suelo"
    if re.search(r"toca|pega|junta|acerca|acércal|despegad|separad", t) and re.search(r"rueda|cylinder|cilindro", t):
        cubos = [o for o in mallas if len(o.data.vertices) == 8]
        for o in mallas:
            if len(o.data.vertices) == 8:
                continue
            lo, hi = caja(o)
            if lo[2] > 0.5:
                continue
            otro = 1 if a["eje"] == "x" else 0
            v = min(cubos, key=lambda c: abs(c.location[1 - otro] - o.location[1 - otro]))
            vlo, vhi = caja(v)
            if o.location[otro] > v.location[otro]:
                o.location[otro] -= lo[otro] - vhi[otro]
            else:
                o.location[otro] += vlo[otro] - hi[otro]
        return "pegó las ruedas"
    if re.search(r"vag[oó]n|vagones|locomotora|cube", t) and re.search(r"corto en|estíralo|estira", t):
        eje = 0 if a["eje"] == "x" else 1
        for o in mallas:
            if len(o.data.vertices) == 8:
                o.scale[eje] *= 1.35
        return "estiró los vagones"
    if re.search(r"vag[oó]n|vagones|locomotora", t) and re.search(r"toca|pega|junta|acerca|acérca|engancha|fila|separad", t):
        cubos = [o for o in mallas if len(o.data.vertices) == 8]
        if len(cubos) >= 2:
            eje = 0 if a["eje"] == "x" else 1
            lo0, hi0 = caja(cubos[0])
            lo1, hi1 = caja(cubos[1])
            if cubos[1].location[eje] < cubos[0].location[eje]:
                cubos[1].location[eje] += lo0[eje] - hi1[eje]
            else:
                cubos[1].location[eje] -= lo1[eje] - hi0[eje]
            return "juntó los vagones"
    if "chimenea" in t and re.search(r"encima|apoy|baja|flota|techo|locomotora", t):
        cubos = [o for o in mallas if len(o.data.vertices) == 8]
        for o in mallas:
            if len(o.data.vertices) != 8:
                lo, hi = caja(o)
                if lo[2] > 0.5:
                    v = cubos[0]
                    o.location.z += caja(v)[1][2] - lo[2]
                    eje = 0 if a["eje"] == "x" else 1
                    o.location[eje] = v.location[eje] + 0.4
        return "puso la chimenea sobre la locomotora"
    return ""


# --- Lo que ve el alumno: motor 6 (lo de antes) --------------------------------------------------


class Motor6:
    nombre = "6.2"

    def abrir(self, C):
        from amatista_blender.taller import datos, sesion

        from amatista_blender import ajustes

        for f in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
            f.unlink()
        datos.reiniciar_cache()
        sesion.terminar()
        sesion.abrir(C, TALLER, PROYECTO)

    def evaluar(self, C):
        from amatista_blender import practicas

        _actualizar()
        return practicas.evaluar(C, "cambio")

    def completo(self, C):
        from amatista_blender.taller import sesion

        return sesion.estado() == sesion.LOGRADA

    def leer(self, C):
        from amatista_blender import practicas
        from amatista_blender.taller.vista import tarjeta
        from amatista_blender.taller import sesion
        from amatista_blender.interfaz import turno

        reporte = practicas.ESTADO["reporte"]
        a = sesion.actividad()
        linea = tarjeta._linea_pieza()[0] or ""
        pieza = sesion.pieza_actual()
        actual = reporte.current_target_id if reporte is not None else None
        return {
            "pide": a.pide if a is not None else "",
            "detalle": linea,
            "paso_real": actual,
            "habla_de": _rol_de_texto(linea),
            "rol_real": _rol_de_objetivo(practicas.practica_activa(C), actual),
            "pieza_molde": getattr(pieza, "nombre", "") if pieza is not None else "",
            "dibujan": _dibujos_en_vista(C, turno),
            "paneles": _paneles_que_guian(C),
        }

    def pistas(self, C, n):
        from amatista_blender.taller import sesion

        salida = []
        sesion.SESION["escalera"] = sesion.ayudas.avance(sesion.SESION["escalera"], time.time() - 120)
        for _ in range(n):
            sesion.SESION["escalera"] = sesion.ayudas.fallo(sesion.SESION["escalera"])  # ya lo intentó
            p = sesion.pedir_pista(C)
            if p is None:
                salida.append({"titulo": "", "texto": sesion.mensaje(), "senal_real": False, "dice_brillo": False})
                continue
            barra = _barra_visible(C)
            en_barra = _alguna_en_barra(p.herramientas)
            salida.append({"titulo": p.titulo, "texto": p.texto, "herramientas": list(p.herramientas),
                           "dice_brillo": bool(BRILLO.search(p.texto or "")),
                           "senal_real": bool(barra and en_barra)})
        return salida


# --- Lo que ve el alumno: motor 7 (Guion) --------------------------------------------------------


class Motor7:
    nombre = "7"

    def abrir(self, C):
        Motor6.abrir(self, C)

    def evaluar(self, C):
        from amatista_blender import guion

        _actualizar()
        return guion.revisar_ya(C)

    def completo(self, C):
        from amatista_blender import guion

        return guion.completo()

    def leer(self, C):
        from amatista_blender import guion, practicas
        from amatista_blender.interfaz import turno

        g = guion.vista()
        reporte = practicas.ESTADO["reporte"]
        actual = reporte.current_target_id if reporte is not None else None
        texto = (g.get("haz") or "")
        return {
            "pide": texto,
            "detalle": g.get("por_que") or "",
            "paso_real": actual,
            "paso_guion": g.get("objetivo"),
            "habla_de": _rol_de_texto(texto),
            "rol_real": _rol_de_objetivo(practicas.practica_activa(C), g.get("objetivo")),
            "dibujan": _dibujos_en_vista(C, turno),
            "paneles": _paneles_que_guian(C),
        }

    def pistas(self, C, n):
        from amatista_blender import guion

        salida = []
        for _ in range(n):
            p = guion.pedir_pista(C)
            if not p:
                break
            salida.append({"titulo": p["titulo"], "texto": p["texto"], "herramientas": p.get("herramientas", []),
                           "dice_brillo": bool(BRILLO.search(p["texto"] or "")),
                           "senal_real": bool(p.get("senalado"))})
        return salida


def _rol_de_texto(texto):
    m = PIEZAS.search(texto or "")
    if not m:
        return ""
    t = m.group(1).lower()
    return {"locomotora": "vagon", "vagón": "vagon", "vagon": "vagon", "cubo": "vagon", "rueda": "rueda",
            "chimenea": "chimenea", "cilindro": "", "archivo": "archivo", "tren": ""}.get(t, "")


def _rol_de_objetivo(practica, objetivo):
    if practica is None or not objetivo:
        return ""
    t = next((x for x in practica.targets if x.id == objetivo), None)
    if t is None:
        return ""
    if t.validator.startswith("file."):
        return "archivo"
    rol = (t.params or {}).get("role", "")
    return rol


def _barra_visible(C):
    for ventana in C.window_manager.windows:
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                return bool(area.spaces.active.show_region_toolbar)
    return False


def _alguna_en_barra(herramientas):
    from amatista_blender import _motor

    for hid in herramientas or ():
        h = _motor.MOTOR.tools.get(hid)
        if h is not None and "tool" in (h.action or {}):
            return True
    return False


def _dibujos_en_vista(C, turno):
    """Cuántas cosas de Amatista se dibujarían a la vez encima de la vista 3D."""
    cosas = []
    quien = turno.de_quien(C)
    if quien:
        cosas.append(quien)
    try:
        from amatista_blender.taller.vista import brillo

        if brillo.activo():
            cosas.append("etiqueta del brillo")
    except Exception:  # noqa: BLE001
        pass
    try:
        from amatista_blender import fichas

        if fichas.visible() is not None and quien != "ficha":
            cosas.append("ficha")
    except Exception:  # noqa: BLE001
        pass
    return cosas


def _paneles_que_guian(C):
    """Paneles de Amatista en la barra N que se muestran a la vez (poll verdadero) en modo alumno."""
    import amatista_blender

    abiertos = []
    for clase in amatista_blender.CLASES:
        if not (isinstance(clase, type) and issubclass(clase, bpy.types.Panel)):
            continue
        if getattr(clase, "bl_space_type", "") != "VIEW_3D" or getattr(clase, "bl_region_type", "") != "UI":
            continue
        try:
            if not hasattr(clase, "poll") or clase.poll(C):
                abiertos.append(clase.__name__)
        except Exception:  # noqa: BLE001
            pass
    return abiertos


# --- Una corrida ---------------------------------------------------------------------------------


def correr(motor, semilla):
    bpy.ops.wm.read_homefile(use_empty=False)  # cada alumno abre su Blender (sin archivo guardado)
    bpy.context.window_manager.amatista.modo = "alumno"
    C = bpy.context
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    motor.abrir(C)
    a = alumno(semilla)
    pasos, problemas = [], []
    motor.evaluar(C)

    def mirar(accion):
        ve = motor.leer(C)
        ve["accion"] = accion
        pasos.append(ve)
        if motor.completo(C):
            return
        if not VAGUEDAD.search(ve["pide"] or "") or not (PIEZAS.search(ve["pide"] or "")
                                                          or PIEZAS.search(ve["detalle"] or "")):
            problemas.append(("instrucción vaga", accion, ve["pide"]))
        if ve["habla_de"] and ve["rol_real"] and ve["habla_de"] != ve["rol_real"]:
            problemas.append(("señal cruzada", accion, f"dice «{ve['pide'] or ve['detalle']}» y revisa {ve['paso_real']}"))
        if len(ve["dibujan"]) > 1:
            problemas.append(("superposición", accion, " + ".join(ve["dibujan"])))
        if len(ve["paneles"]) > 2:
            problemas.append(("varios paneles", accion, ", ".join(ve["paneles"])))
        if BRILLO.search((ve["pide"] or "") + " " + (ve["detalle"] or "")) and not _barra_visible(C):
            problemas.append(("brillo fantasma", accion, ve["detalle"] or ve["pide"]))

    mirar("abrir")
    for nombre, hacer in armar(a):
        hacer()
        motor.evaluar(C)
        mirar(nombre)
    acepta, razon = profesor(C.scene)
    pistas_vistas, hizo = [], []
    rondas = 0
    while not motor.completo(C) and rondas < 4:
        rondas += 1
        pistas = motor.pistas(C, a["pide_pistas"] + 1)
        pistas_vistas += pistas
        util = ""
        for p in pistas:
            if p["dice_brillo"] and not p["senal_real"]:
                problemas.append(("brillo fantasma", "pista", p["texto"]))
            util = seguir_pista(p["texto"], C.scene, a)
            if util:
                break
        if not util:
            ve = motor.leer(C)
            util = seguir_pista(ve["detalle"] or ve["pide"], C.scene, a)
        if not util:
            problemas.append(("pista inútil", f"ronda {rondas}", " | ".join(p["texto"] for p in pistas)[:300]))
            break
        hizo.append(util)
        motor.evaluar(C)
        mirar(util)
    completo = motor.completo(C)
    acepta_final, razon_final = profesor(C.scene)
    if acepta_final and not completo:
        problemas.append(("bloqueo", "final", f"un profesor lo acepta y Amatista no avanza ({motor.leer(C)['pide']})"))
    return {
        "semilla": semilla, "alumno": a, "completo": completo, "profesor_al_terminar": [acepta, razon],
        "profesor_final": [acepta_final, razon_final], "hizo_con_pistas": hizo, "pistas": pistas_vistas,
        "problemas": [list(p) for p in problemas], "vio": pasos,
    }


def resumen(corridas):
    tipos = ("brillo fantasma", "señal cruzada", "instrucción vaga", "pista inútil", "bloqueo", "superposición",
             "varios paneles")
    salida = {"corridas": len(corridas), "completas": sum(c["completo"] for c in corridas)}
    salida["frustradas"] = sum(1 for c in corridas if not c["completo"]
                               or any(p[0] in ("brillo fantasma", "pista inútil", "bloqueo") for p in c["problemas"]))
    salida["por_tipo"] = {t: sum(1 for c in corridas if any(p[0] == t for p in c["problemas"])) for t in tipos}
    salida["avisos_por_tipo"] = {t: sum(1 for c in corridas for p in c["problemas"] if p[0] == t) for t in tipos}
    salida["acepta_profesor_y_no_avanza"] = sum(1 for c in corridas if c["profesor_final"][0] and not c["completo"])
    return salida


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--motor", type=int, default=7)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default="")
    args = ap.parse_args(argv)
    preparar(args.motor)
    motor = Motor7() if args.motor == 7 else Motor6()
    corridas = []
    for i in range(args.n):
        try:
            corridas.append(correr(motor, args.semilla + i))
        except Exception as error:  # noqa: BLE001 - una corrida rota es un hallazgo, no se esconde
            import traceback

            traceback.print_exc()
            corridas.append({"semilla": args.semilla + i, "completo": False, "error": str(error),
                             "problemas": [["error", "", str(error)]], "profesor_final": [False, "error"]})
    r = resumen([c for c in corridas if "error" not in c])
    r["errores"] = sum(1 for c in corridas if "error" in c)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if args.salida:
        Path(args.salida).write_text(json.dumps({"motor": motor.nombre, "resumen": r, "corridas": corridas},
                                                ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return r


if __name__ == "__main__":
    main()
