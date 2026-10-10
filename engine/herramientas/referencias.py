"""Construye en Blender el modelo de referencia de cada práctica y lo dibuja (motor 3.3).

Por cada práctica con «reference»:

1. arma la figura en una escena vacía de Blender, pieza por pieza, como lo
   haría un alumno (primitivas, medidas, giros, roles, materiales,
   modificadores y piezas unidas);
2. la lee con el mismo adaptador del add-on y la califica con el motor: el
   modelo de referencia TIENE que pasar «La figura se parece al modelo»
   (si no, la práctica está mal escrita y la herramienta falla);
3. la renderiza con Cycles en referencia.jpg (lo que el alumno ve en
   «Así se debe ver») y escribe plano.svg con las tres vistas y las medidas
   aproximadas.

Uso, desde la raíz del repositorio (necesita el módulo bpy: `pip install bpy`
con Python 3.11, o ejecutarlo dentro de Blender con --python):

    python engine/herramientas/referencias.py                  # todas
    python engine/herramientas/referencias.py m1-tren m1-explora
    python engine/herramientas/referencias.py --sin-render     # solo armar, calificar y plano
    blender -b --python engine/herramientas/referencias.py -- m1-tren
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "engine"))

from amatista_engine import create_default_engine  # noqa: E402
from amatista_engine.practice.loader import parse_practice  # noqa: E402
from amatista_engine.practice.plano import medidas_generales, plano_svg  # noqa: E402

PRACTICAS = RAIZ / "practices" / "blender"
IMAGEN, PLANO = "referencia.jpg", "plano.svg"
INDICE = PRACTICAS / "referencias.json"  # lo lee la plataforma («Así se debe ver»)
ANCHO, ALTO = 800, 500


def _color(hexadecimal: str, alfa: float = 1.0):
    h = (hexadecimal or "#9b7bff").lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lineal = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lineal, alfa)


def _entrada(nodo, *nombres):
    for nombre in nombres:
        if nombre in nodo.inputs:
            return nodo.inputs[nombre]
    return None


def _material(bpy, nombre: str, color: str, ajustes: dict):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    alfa = float(ajustes.get("alpha", 1.0))
    bsdf.inputs["Base Color"].default_value = _color(color)
    valores = {
        ("Metallic",): ajustes.get("metallic"),
        ("Roughness",): ajustes.get("roughness", 0.55),
        ("Transmission Weight", "Transmission"): ajustes.get("transmission"),
        ("Alpha",): alfa if alfa < 1 else None,
    }
    for nombres, valor in valores.items():
        entrada = _entrada(bsdf, *nombres)
        if entrada is not None and valor is not None:
            entrada.default_value = float(valor)
    if alfa < 1 and hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


def _agregar(bpy, pieza):
    segmentos = pieza.segments or 0
    ops = bpy.ops.mesh
    if pieza.primitive == "cube":
        ops.primitive_cube_add()
    elif pieza.primitive == "cylinder":
        ops.primitive_cylinder_add(vertices=segmentos or 32)
    elif pieza.primitive == "cone":
        ops.primitive_cone_add(vertices=segmentos or 32)
    elif pieza.primitive == "sphere":
        ops.primitive_uv_sphere_add(segments=segmentos or 32, ring_count=max(4, (segmentos or 32) // 2))
    elif pieza.primitive == "icosphere":
        ops.primitive_ico_sphere_add(subdivisions=2)
    elif pieza.primitive == "torus":
        ops.primitive_torus_add()
    else:
        ops.primitive_plane_add()
    return bpy.context.active_object


def _modificadores(bpy, obj, ajustes: dict):
    if ajustes.get("bevel"):
        m = obj.modifiers.new("Bisel", "BEVEL")
        m.width = float(ajustes["bevel"])
        m.segments = 3
    if ajustes.get("subsurf"):
        m = obj.modifiers.new("Subdivisión", "SUBSURF")
        m.levels = m.render_levels = int(ajustes["subsurf"])
    if ajustes.get("smooth"):
        for poligono in obj.data.polygons:
            poligono.use_smooth = True
    if ajustes.get("wire"):  # las aristas a la vista: se ve que es UN objeto con su malla
        m = obj.modifiers.new("Aristas", "WIREFRAME")
        m.thickness = 0.025
        m.use_replace = False
        m.material_offset = len(obj.data.materials)
        obj.data.materials.append(_material(bpy, "Aristas", "#1d1530", {"roughness": 0.9}))


def _arreglo(obj, ajustes: dict, pieza):
    """Array: la medida de la pieza es la del tablero COMPLETO; se parte en «count» tablones."""
    arreglo = ajustes.get("array")
    if not arreglo:
        return
    eje = "xyz".index(arreglo.get("axis", "x"))
    cuenta = int(arreglo.get("count", 4))
    hueco = float(arreglo.get("gap", 0.05))
    total = pieza.size[eje]
    tablon = (total - hueco * (cuenta - 1)) / cuenta
    medidas = list(obj.dimensions)
    medidas[eje] = tablon
    obj.dimensions = medidas
    ubicacion = list(obj.location)
    ubicacion[eje] = pieza.location[eje] - total / 2 + tablon / 2
    obj.location = ubicacion
    m = obj.modifiers.new("Array", "ARRAY")
    m.count = cuenta
    m.use_relative_offset = False
    m.use_constant_offset = True
    desplazamiento = [0.0, 0.0, 0.0]
    desplazamiento[eje] = tablon + hueco
    m.constant_offset_displace = desplazamiento


def armar(bpy, referencia, roles: dict):
    """Arma la figura de referencia en la escena actual (vacía). Devuelve los objetos decorativos."""
    from amatista_engine.blender import tagger

    unidas, decorado = {}, []
    for i, pieza in enumerate(referencia.parts):
        obj = _agregar(bpy, pieza)
        obj.name = pieza.name or (pieza.role or pieza.primitive).capitalize()
        obj.rotation_euler = [math.radians(a) for a in pieza.rotation]
        obj.location = pieza.location
        medidas = list(pieza.size)
        if pieza.primitive == "plane":
            medidas[2] = 0
        obj.dimensions = medidas
        bpy.context.view_layer.update()
        ajustes = dict(referencia.objects.get(pieza.name, {}) if pieza.name else {})
        _arreglo(obj, ajustes, pieza)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(_material(bpy, f"{obj.name} material", pieza.color, pieza.material))
        if pieza.role:
            tagger.assign_role(obj, pieza.role)
        if not pieza.compare:
            tagger.set_ignored(obj, True)
            decorado.append(obj)
        if pieza.join:
            unidas.setdefault(pieza.join, []).append(obj)
        else:
            _modificadores(bpy, obj, ajustes)
    for nombre, objetos in unidas.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objetos:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objetos[0]
        bpy.ops.object.join()
        unido = bpy.context.active_object
        unido.name = nombre
        _modificadores(bpy, unido, dict(referencia.objects.get(nombre, {})))
    bpy.context.view_layer.update()
    return decorado


def _camara(bpy, referencia):
    from mathutils import Vector

    datos = referencia.camera or {}
    objetos = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    puntos = [o.matrix_world @ Vector(c) for o in objetos for c in o.bound_box]
    centro = sum(puntos, Vector()) / max(len(puntos), 1)
    radio = max((p - centro).length for p in puntos) if puntos else 4
    objetivo = Vector(datos.get("target") or centro)
    lugar = Vector(datos.get("location") or (centro + Vector((1.0, -1.25, 0.75)).normalized() * radio * 2.6))
    bpy.ops.object.camera_add(location=lugar)
    camara = bpy.context.active_object
    camara.rotation_euler = (objetivo - lugar).to_track_quat("-Z", "Y").to_euler()
    camara.data.lens = float(datos.get("lens", 42))
    bpy.context.scene.camera = camara


def _luces(bpy, referencia):
    from mathutils import Vector

    mundo = bpy.context.scene.world or bpy.data.worlds.new("Mundo")
    bpy.context.scene.world = mundo
    mundo.use_nodes = True
    fondo = mundo.node_tree.nodes.get("Background")
    fondo.inputs["Color"].default_value = _color("#dfe7f3")
    fondo.inputs["Strength"].default_value = 0.6 if not referencia.lights else 0.12
    luces = list(referencia.lights) or [
        {"name": "Sol", "type": "SUN", "location": [4, -4, 8], "energy": 3.2, "target": [0, 0, 0]},
        {"name": "Relleno", "type": "AREA", "location": [-6, -4, 5], "energy": 450},
    ]
    for datos in luces:
        tipo = str(datos.get("type", "AREA")).upper()
        bpy.ops.object.light_add(type=tipo, location=datos.get("location", (0, 0, 5)))
        luz = bpy.context.active_object
        luz.name = datos.get("name", tipo.title())
        luz.data.energy = float(datos.get("energy", 500))
        if tipo == "AREA":
            luz.data.size = float(datos.get("size", 3))
        objetivo = Vector(datos.get("target") or (0, 0, 0.8))
        luz.rotation_euler = (objetivo - luz.location).to_track_quat("-Z", "Y").to_euler()
        if referencia.lights:  # tres puntos: también se ve dónde está cada luz
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=luz.location)
            foco = bpy.context.active_object
            foco.name = f"Foco {luz.name}"
            mat = bpy.data.materials.new(f"Foco {luz.name}")
            mat.use_nodes = True
            emision = _entrada(mat.node_tree.nodes["Principled BSDF"], "Emission Color", "Emission")
            if emision is not None:
                emision.default_value = _color("#ffd166")
            fuerza = _entrada(mat.node_tree.nodes["Principled BSDF"], "Emission Strength")
            if fuerza is not None:
                fuerza.default_value = 8.0
            foco.data.materials.append(mat)
            from amatista_engine.blender import tagger

            tagger.set_ignored(foco, True)


def renderizar(bpy, destino: Path, muestras: int):
    escena = bpy.context.scene
    escena.render.engine = "CYCLES"
    escena.cycles.device = "CPU"
    escena.cycles.samples = muestras
    escena.cycles.use_denoising = True
    escena.render.resolution_x, escena.render.resolution_y = ANCHO, ALTO
    escena.render.resolution_percentage = 100
    escena.render.image_settings.file_format = "JPEG"
    escena.render.image_settings.quality = 82
    escena.render.filepath = str(destino)
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError:  # sin el eliminador de ruido (algunas compilaciones de bpy)
        escena.cycles.use_denoising = False
        escena.cycles.samples = muestras * 3
        bpy.ops.render.render(write_still=True)


def escribir_indice() -> None:
    """practices/blender/referencias.json: id → carpeta, textos y medidas de cada modelo (sin Blender)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from formato_json import escribir

    indice = {}
    for archivo in sorted(PRACTICAS.rglob("practica.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if "reference" not in datos:
            continue
        referencia = parse_practice(datos).reference
        carpeta = archivo.parent
        indice[datos["id"]] = {
            "carpeta": carpeta.relative_to(PRACTICAS).as_posix(),
            "titulo": referencia.title or datos.get("title", ""),
            "descripcion": referencia.description,
            "holgura": round(referencia.tolerance * 100),
            "medidas": list(medidas_generales(referencia)),
            "imagen": (carpeta / IMAGEN).is_file(),
            "plano": (carpeta / PLANO).is_file(),
        }
    escribir(INDICE, {"schema": "amatista.references/1", "practicas": indice})


# Validadores que revisan la figura, en orden de preferencia (figure.resembles queda por compatibilidad).
FIGURAS = ("figure.recognize", "figure.silhouette", "figure.resembles")


def procesar(carpeta: Path, motor, render: bool, muestras: int) -> dict:
    import bpy
    from amatista_engine.blender.adapter import capture_scene

    datos = json.loads((carpeta / "practica.json").read_text(encoding="utf-8"))
    practica = parse_practice(datos)
    referencia = practica.reference
    etiquetas = {r.id: r.label for r in practica.roles}
    (carpeta / PLANO).write_text(plano_svg(referencia, referencia.title or practica.title, etiquetas), encoding="utf-8")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    armar(bpy, referencia, etiquetas)
    escena = capture_scene()
    reporte = motor.evaluate(practica, escena)
    figura = next((r for v in FIGURAS for r in reporte.results if r.validator == v), None)
    pendientes = [r.target_id for r in reporte.results if not r.passed]
    resumen = {"practica": practica.id, "figura": None, "objetos": len(escena.objects),
               "progreso": round(reporte.progress), "pendientes": pendientes}
    if figura is not None:
        resumen["figura"] = {"pasa": figura.passed, "parecido": figura.details.get("score"), "mensaje": figura.message}
    else:  # sin validador de figura: el aspecto «La figura» de la revisión contra el ejemplo
        ejemplo = next((r for r in reporte.results if r.validator == "example.matches"), None)
        aspecto = next((a for a in (ejemplo.details.get("aspects") or []) if a.get("id") == "figura"), None) \
            if ejemplo is not None else None
        if aspecto is not None:
            resumen["figura"] = {"pasa": aspecto["ok"], "parecido": ejemplo.details.get("score"),
                                 "mensaje": f"La figura del ejemplo: {'coincide' if aspecto['ok'] else 'no coincide'}"}
    if render:
        _luces(bpy, referencia)
        _camara(bpy, referencia)
        inicio = time.perf_counter()
        renderizar(bpy, carpeta / IMAGEN, muestras)
        resumen["render_s"] = round(time.perf_counter() - inicio, 1)
        resumen["kb"] = round((carpeta / IMAGEN).stat().st_size / 1024)
    return resumen


def main(argv=None) -> int:
    if "--" in sys.argv:  # blender -b --python referencias.py -- m1-tren
        argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("practicas", nargs="*", help="carpetas (m1-tren) o ids; vacío = todas con «reference»")
    parser.add_argument("--sin-render", action="store_true", help="solo armar, calificar y escribir plano.svg")
    parser.add_argument("--muestras", type=int, default=24)
    args = parser.parse_args(argv)
    carpetas = []
    for archivo in sorted(PRACTICAS.rglob("practica.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if "reference" not in datos:
            continue
        nombre = archivo.parent.name
        if not args.practicas or nombre in args.practicas or datos["id"] in args.practicas or \
                f"{archivo.parent.parent.name}/{nombre}" in args.practicas:
            carpetas.append(archivo.parent)
    motor = create_default_engine()
    fallas = 0
    for carpeta in carpetas:
        r = procesar(carpeta, motor, not args.sin_render, args.muestras)
        figura = r["figura"]
        estado = "sin «figura»" if figura is None else ("✓" if figura["pasa"] else "✗") + f" {figura['mensaje']}"
        extra = f" · render {r['render_s']} s, {r['kb']} KB" if "render_s" in r else ""
        print(f"{carpeta.relative_to(PRACTICAS)}: {r['objetos']} objetos · {estado}{extra}")
        # Lo que el modelo solo no cumple: guardar, render, animar… (pasos del alumno, no de la forma).
        print(f"    progreso del modelo solo: {r['progreso']} % · faltan: {', '.join(r['pendientes']) or 'nada'}")
        if figura is not None and not figura["pasa"]:
            fallas += 1
    escribir_indice()
    if fallas:
        print(f"{fallas} modelos de referencia NO pasan su propia práctica: revisa «reference».")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
