"""«Ver el ejemplo»: el ejemplo resuelto de la práctica, armado en Blender (motor 3.5).

Cada práctica trae su solución en pasos («example.steps», ver
engine/amatista_engine/ejemplo/). Aquí se arma en una escena propia,
«Ejemplo · <título>», para que el alumno la recorra, la gire y la compare
con la suya; «Volver a mi práctica» regresa a su escena. El motor no revisa
la escena del ejemplo (no tiene práctica) y abrir otra práctica desde ahí
no la usa.

Se arma con bmesh y bpy.data (sin operadores): funciona igual con o sin
ventana y no toca la selección de la escena del alumno. Al entrar y al
volver se pasa a Modo Objeto (una malla en edición se guarda antes de
cambiar de escena).

Los objetos, colecciones y materiales del ejemplo llevan el prefijo
«Ejemplo · »: así nunca le quitan el nombre a los del alumno (en Blender
los nombres son de todo el archivo: si el ejemplo tuviera la colección
«Casas», la del alumno sería «Casas.001» y el paso que pide «Casas» no
pasaría). capturar() quita el prefijo para comparar el ejemplo con lo
esperado.
"""
import dataclasses
import math
import time
from importlib import import_module

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import _motor, practicas

EJEMPLO = "amatista_ejemplo"  # en la escena: id de la práctica de la que es ejemplo
VOLVER = "amatista_volver"  # nombre de la escena del alumno
PREFIJO = "Ejemplo · "
DATOS = {"cube": "Cube", "cylinder": "Cylinder", "sphere": "Sphere", "uv_sphere": "Sphere", "icosphere": "Icosphere",
         "cone": "Cone", "plane": "Plane", "torus": "Torus"}

PIEZAS = {}  # objeto → caras de cada pieza (se llena al armar)
_ejemplo = import_module(_motor.engine.__name__ + ".ejemplo")
_cargador = import_module(_motor.engine.__name__ + ".practice.loader")


def es_ejemplo(sc):
    return bool(sc is not None and sc.get(EJEMPLO))


def _nombre(nombre):
    """El nombre de un dato del ejemplo: con prefijo, para no quitarle el suyo al alumno."""
    return (PREFIJO + nombre).encode("utf-8")[:63].decode("utf-8", "ignore")


def _sin_prefijo(nombre):
    return nombre[len(PREFIJO):] if isinstance(nombre, str) and nombre.startswith(PREFIJO) else nombre


def capturar(sc):
    """Foto de la escena del ejemplo con los nombres sin el prefijo «Ejemplo · » (como los esperaría el motor)."""
    foto = _motor.adapter.capture_scene(sc)
    objetos = tuple(
        dataclasses.replace(
            o, name=_sin_prefijo(o.name), parent=_sin_prefijo(o.parent),
            collections=tuple(_sin_prefijo(c) for c in o.collections),
            materials=tuple(_sin_prefijo(m) for m in o.materials),
            materials_used=tuple(_sin_prefijo(m) for m in o.materials_used) if o.materials_used is not None else None,
            material_details=tuple(dataclasses.replace(m, name=_sin_prefijo(m.name)) for m in o.material_details),
        )
        for o in foto.objects
    )
    return dataclasses.replace(foto, objects=objetos, active_object=_sin_prefijo(foto.active_object),
                               active_camera=_sin_prefijo(foto.active_camera),
                               selected=tuple(_sin_prefijo(n) for n in foto.selected))


def _partes(practica):
    referencia = getattr(practica, "reference", None)
    return [_cargador.pieza_como_dict(p) for p in referencia.compared] if referencia is not None else []


def instrucciones(practica):
    """Los pasos del ejemplo en palabras (los mismos que muestra la plataforma)."""
    if practica is None or practica.example is None:
        return []
    return _ejemplo.describir(practica.example.steps, _partes(practica))


# --- Geometría -------------------------------------------------------------------------------


def _agregar_primitiva(bm, primitiva, medidas, matriz, segmentos=0):
    """Agrega a bm una primitiva de medidas «medidas» (caja total) transformada por «matriz»."""
    escala = Matrix.Diagonal(Vector((max(m, 1e-4) for m in medidas))).to_4x4()
    m = matriz @ escala
    lados = int(segmentos or 0) or 32
    if primitiva == "cube":
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    elif primitiva == "cylinder":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=0.5, radius2=0.5, depth=1.0, matrix=m)
    elif primitiva == "cone":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=0.5, radius2=0.0, depth=1.0, matrix=m)
    elif primitiva in ("sphere", "uv_sphere", "torus"):
        bmesh.ops.create_uvsphere(bm, u_segments=int(segmentos or 0) or 32, v_segments=16, radius=0.5, matrix=m)
    elif primitiva == "icosphere":
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5, matrix=m)
    elif primitiva == "plane":
        escala = Matrix.Diagonal(Vector((max(medidas[0], 1e-4), max(medidas[1], 1e-4), 1.0))).to_4x4()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5, matrix=matriz @ escala)
    else:
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def _matriz(ubicacion, giro_grados):
    return Matrix.Translation(Vector(ubicacion)) @ Euler(tuple(math.radians(g) for g in giro_grados)).to_matrix().to_4x4()


def _cortes(bm, vertices):
    """Cortes a lo largo del lado más largo hasta tener «vertices» (como Ctrl + R en Modo Edición)."""
    if not bm.verts:
        return
    minimo = [min(v.co[i] for v in bm.verts) for i in range(3)]
    maximo = [max(v.co[i] for v in bm.verts) for i in range(3)]
    eje = max(range(3), key=lambda i: maximo[i] - minimo[i])
    cortes = max(0, -(-(vertices - len(bm.verts)) // 4))
    for k in range(1, cortes + 1):
        punto = [0.0, 0.0, 0.0]
        punto[eje] = minimo[eje] + (maximo[eje] - minimo[eje]) * k / (cortes + 1)
        normal = [0.0, 0.0, 0.0]
        normal[eje] = 1.0
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=punto, plane_no=normal)


def _malla(nombre, piezas, mitad="", vertices=0):
    """Un objeto malla hecho de piezas [(primitiva, medidas, ubicación, giro en grados, segmentos)].

    vertices: la malla modelada del ejemplo (más vértices que la primitiva); mitad: «x-», solo ese lado.
    """
    bm = bmesh.new()
    caras = []  # (desde, hasta) de las caras de cada pieza, para pintarlas por separado
    for primitiva, medidas, ubicacion, giro, segmentos in piezas:
        antes = len(bm.faces)
        _agregar_primitiva(bm, primitiva, medidas, _matriz(ubicacion, giro), segmentos)
        caras.append((antes, len(bm.faces)))
    if vertices and len(piezas) == 1:
        _cortes(bm, vertices)
    if mitad:  # «x-»: queda solo la mitad negativa del eje (la otra la dibuja el Espejo)
        eje = "xyz".index(mitad[0])
        normal = Vector([1.0 if i == eje else 0.0 for i in range(3)]) * (1 if mitad[1:] == "-" else -1)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                               plane_no=normal, clear_outer=True)
    # Los datos se llaman como la primitiva («Cone»), igual que al agregarla con Shift + A: así el motor la reconoce.
    primera = piezas[0][0] if len(piezas) == 1 else "cube"
    datos = bpy.data.meshes.new(DATOS.get(primera, "Cube"))
    bm.to_mesh(datos)
    bm.free()
    obj = bpy.data.objects.new(_nombre(nombre), datos)
    PIEZAS[obj.name] = caras
    return obj


# --- Materiales ------------------------------------------------------------------------------


def _entrada(nodo, *nombres):
    return next((nodo.inputs[n] for n in nombres if n in nodo.inputs), None)


def _material(nombre, color=(0.8, 0.8, 0.8, 1.0), metal=0.0, rugosidad=0.5, transmision=0.0, alfa=1.0):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    mat.diffuse_color = tuple(color)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        for valor, nombres in ((tuple(color), ("Base Color",)), (metal, ("Metallic",)), (rugosidad, ("Roughness",)),
                               (transmision, ("Transmission Weight", "Transmission")), (alfa, ("Alpha",))):
            entrada = _entrada(bsdf, *nombres)
            if entrada is not None:
                entrada.default_value = valor
    return mat


def _color_hex(texto):
    texto = (texto or "").lstrip("#")
    if len(texto) != 6:
        return None
    try:
        rgb = [int(texto[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    except ValueError:
        return None
    return tuple(c ** 2.2 for c in rgb) + (1.0,)  # sRGB → lineal, como lo guarda Blender


# --- Armar -----------------------------------------------------------------------------------


def _nombres_del_modelo(partes):
    """Los grupos de piezas tal como los arma el motor (Escena.referencia): sueltas y luego unidas."""
    usados = {}

    def nombre(base):
        n = usados.get(base, 0)
        usados[base] = n + 1
        return base if n == 0 else f"{base}.{n:03d}"

    sueltas, unidas = [], {}
    for p in partes:
        if p.get("join"):
            unidas.setdefault(p["join"], []).append(p)
        else:
            sueltas.append([p])
    grupos = []
    for grupo in sueltas + list(unidas.values()):
        primera = grupo[0]
        grupos.append((nombre(primera.get("name") or (primera.get("role") or primera["primitive"]).capitalize()),
                       grupo))
    return grupos


def _partir(pieza, arreglo):
    """Array: la medida de la pieza es la del tablero COMPLETO; se arma el primer tablón (como referencias.py)."""
    eje = "xyz".index(arreglo.get("axis", "x"))
    cuenta = max(1, int(arreglo.get("count", 4)))
    hueco = float(arreglo.get("gap", 0.05))
    medidas, ubicacion = list(pieza["size"]), list(pieza["location"])
    total = medidas[eje]
    tablon = (total - hueco * (cuenta - 1)) / cuenta
    medidas[eje] = tablon
    ubicacion[eje] = ubicacion[eje] - total / 2 + tablon / 2
    return medidas, ubicacion, {"eje": eje, "cuenta": cuenta, "paso": tablon + hueco}


def _desde_modelo(practica, ajustes):
    """{nombre en la escena esperada: objeto} con la figura de «reference» (piezas unidas en una malla).

    ajustes recibe, por nombre, cómo se ve cada modificador en la imagen del modelo (reference.objects).
    """
    referencia = practica.reference
    objetos = {}
    comparadas = [p for p in referencia.parts if p.compare]
    for nombre, grupo in _nombres_del_modelo([_cargador.pieza_como_dict(p) for p in comparadas]):
        piezas = [(p["primitive"], p["size"], p["location"], p["rotation"], p.get("segments", 0)) for p in grupo]
        opciones = dict(referencia.objects.get(nombre) or referencia.objects.get(grupo[0].get("join") or "") or {})
        if opciones.get("array") and len(grupo) == 1:
            medidas, ubicacion, opciones["array"] = _partir(grupo[0], opciones["array"])
            piezas = [(grupo[0]["primitive"], medidas, ubicacion, grupo[0]["rotation"], grupo[0].get("segments", 0))]
        ajustes[nombre] = opciones
        if len(piezas) == 1:  # pieza suelta: el objeto lleva el lugar y el giro, como la deja el alumno
            primitiva, medidas, ubicacion, giro, segmentos = piezas[0]
            obj = _malla(nombre, [(primitiva, medidas, (0, 0, 0), (0, 0, 0), segmentos)])
            obj.location = ubicacion
            obj.rotation_euler = [math.radians(g) for g in giro]
        else:
            obj = _malla(nombre, piezas)
            PIEZAS[obj.name] = dict(zip((p.get("name") or "" for p in grupo), PIEZAS.get(obj.name, [])))
        original = next(p for p in comparadas if (p.name or "") == (grupo[0].get("name") or "")
                        and p.primitive == grupo[0]["primitive"])
        color = _color_hex(original.color)
        if color is not None:
            extra = original.material or {}
            obj.data.materials.append(_material(_nombre(nombre), color, extra.get("metallic", 0.0),
                                                extra.get("roughness", 0.5), extra.get("transmission", 0.0),
                                                extra.get("alpha", 1.0)))
        objetos[nombre] = obj
    # La decoración de la imagen (el piso, las orillas) no se arma: se confundiría con piezas de la figura.
    return objetos


def _pintar_piezas(obj, pintadas):
    """Cada material del ejemplo pinta sus piezas; el resto queda con el primero (como «Asignar» en Edición)."""
    rangos = PIEZAS.get(obj.name)
    if not pintadas or not isinstance(rangos, dict):
        return
    nombres = [m.name.replace(PREFIJO, "", 1) for m in obj.data.materials]
    for material, piezas in pintadas.items():
        if material not in nombres:
            continue
        indice = nombres.index(material)
        for pieza in piezas:
            desde, hasta = rangos.get(pieza, (0, 0))
            for i in range(desde, min(hasta, len(obj.data.polygons))):
                obj.data.polygons[i].material_index = indice


def _mirar(objeto, hacia):
    if hacia:
        objeto.rotation_euler = Vector(hacia).to_track_quat("-Z", "Y").to_euler()


def _armar(sc, practica):
    pasos = list(practica.example.steps)
    partes = _partes(practica)
    esperada = _ejemplo.escena_esperada(pasos, partes)
    ajustes = {}
    objetos = _desde_modelo(practica, ajustes) if any("referencia" in p for p in pasos) else {}
    mitades, modeladas, pintadas = {}, {}, {}
    for p in pasos:
        clave, args = next(iter(p.items()))
        if clave == "material" and isinstance(args, dict) and args.get("piezas"):
            pintadas.setdefault(args.get("objeto", ""), {})[args.get("nombre", "")] = list(args["piezas"])
        if isinstance(args, dict) and args.get("nombre"):
            if args.get("mitad"):
                mitades[args["nombre"]] = args["mitad"]
            if args.get("vertices") or args.get("caras"):  # en una caja cortada, vértices = caras + 2
                modeladas[args["nombre"]] = max(int(args.get("vertices") or 0), int(args.get("caras") or 0) + 2)
    colecciones = {}
    for o in esperada.objects:
        obj = objetos.get(o.name)
        if obj is None:
            if o.object_type == "MESH":
                primitiva = (o.primitive or "cube").replace("uv_sphere", "sphere")
                obj = _malla(o.name, [(primitiva, o.dimensions, (0, 0, 0), (0, 0, 0), 0)], mitades.get(o.name, ""),
                             modeladas.get(o.name, 0))
                obj.location = o.location
                obj.rotation_euler = o.rotation
            elif o.object_type == "LIGHT":
                luz = bpy.data.lights.new(_nombre(o.name), (o.light_type or "POINT").upper())
                luz.energy = float(o.light_energy or 1000.0)
                if luz.type == "AREA":
                    luz.size = 2.0
                obj = bpy.data.objects.new(_nombre(o.name), luz)
                obj.location = o.location
                _mirar(obj, o.forward)
            elif o.object_type == "CAMERA":
                obj = bpy.data.objects.new(_nombre(o.name), bpy.data.cameras.new(_nombre(o.name)))
                obj.location = o.location
                _mirar(obj, o.forward)
            else:
                continue
            objetos[o.name] = obj
        for nombre_col in o.collections:
            if nombre_col.lower() in ("collection", "scene collection", ""):
                continue
            if nombre_col not in colecciones:
                colecciones[nombre_col] = bpy.data.collections.new(_nombre(nombre_col))
                sc.collection.children.link(colecciones[nombre_col])
            if obj.name not in colecciones[nombre_col].objects:
                colecciones[nombre_col].objects.link(obj)
        if o.material_details and obj.type == "MESH":
            obj.data.materials.clear()
            for m in o.material_details:
                obj.data.materials.append(_material(_nombre(m.name), m.base_color, m.metallic, m.roughness,
                                                    m.transmission, m.alpha))
            _pintar_piezas(obj, pintadas.get(o.name, {}))
        if o.role:  # el rol que el motor esperaría (en la pestaña Amatista se ve qué es cada pieza)
            _motor.tagger.assign_role(obj, o.role)
        opciones = ajustes.get(o.name, {})
        for m in o.modifier_details:
            mod = obj.modifiers.new(m.name or m.type.capitalize(), m.type)
            if m.type == "MIRROR":
                mod.use_axis = tuple(bool(e) for e in m.axes)
                mod.use_clip = True
            elif m.type == "SUBSURF":
                mod.levels = mod.render_levels = int(m.levels or 1)
            elif m.type == "ARRAY" and isinstance(opciones.get("array"), dict) and "paso" in opciones["array"]:
                arreglo = opciones["array"]
                mod.count = arreglo["cuenta"]
                mod.use_relative_offset = False
                mod.use_constant_offset = True
                desplazamiento = [0.0, 0.0, 0.0]
                desplazamiento[arreglo["eje"]] = arreglo["paso"]
                mod.constant_offset_displace = desplazamiento
            elif m.type == "ARRAY":
                mod.count = 3
            elif m.type == "BEVEL":
                mod.width = float(opciones.get("bevel") or 0.05)
                mod.segments = 2
        for canal in o.animation:
            for fotograma, valor in canal.keys:
                getattr(obj, canal.path)[canal.index] = valor
                obj.keyframe_insert(canal.path, index=canal.index, frame=fotograma)
        if o.object_type == "CAMERA" and esperada.active_camera == o.name:
            sc.camera = obj
    for obj in objetos.values():
        if not obj.users_collection:
            sc.collection.objects.link(obj)
    pide = _ejemplo.lo_que_pide(pasos)
    if pide.get("motor"):
        try:
            sc.render.engine = pide["motor"]
        except TypeError:
            pass
    if any(o.animation for o in esperada.objects):
        fin = max(int(f) for o in esperada.objects for c in o.animation for f, _ in c.keys)
        sc.frame_start, sc.frame_end = 1, max(fin, 2)
        sc.frame_set(1)
    return len(objetos)


# --- Ver y volver ----------------------------------------------------------------------------


def _ventana(context):
    ventana = getattr(context, "window", None) or getattr(bpy.context, "window", None)
    if ventana is None and bpy.context.window_manager.windows:
        ventana = bpy.context.window_manager.windows[0]
    return ventana


def ver_ejemplo(context):
    """Abre (o arma) la escena del ejemplo. Devuelve el mensaje para el alumno."""
    sc = practicas.escena(context)
    if es_ejemplo(sc):
        return "Ya estás viendo el ejemplo resuelto. «Volver a mi práctica» te regresa a tu escena."
    practica = practicas.practica_activa(context)
    if practica is None or practica.example is None:
        return "Esta práctica no tiene ejemplo resuelto."
    ventana = _ventana(context)
    if ventana is None:
        return "No hay una ventana de Blender para mostrar el ejemplo."
    version = f"{practica.id}@{practica.version}"
    destino = next((s for s in bpy.data.scenes if s.get(EJEMPLO) == version), None)
    if destino is None:
        destino = bpy.data.scenes.new((PREFIJO + practica.title)[:63])
        destino.unit_settings.system = sc.unit_settings.system
        destino[EJEMPLO] = version
        destino[practicas.USADA] = f"{practica.id}#ejemplo"  # abrir otra práctica desde aquí no usa esta escena
        destino[practicas.USADA_EN] = time.time()
        if sc.world is not None:
            destino.world = sc.world
        cuantos = _armar(destino, practica)
    else:
        cuantos = len(destino.objects)
    destino[VOLVER] = sc.name
    practicas._a_modo_objeto()
    ventana.scene = destino
    practicas.redibujar()
    return (f"Este es el ejemplo resuelto ({cuantos} objetos). Gíralo y míralo; nada de aquí cuenta para tu "
            "práctica. «Volver a mi práctica» te regresa a tu escena.")


def volver(context):
    sc = practicas.escena(context)
    if not es_ejemplo(sc):
        return None
    ventana = _ventana(context)
    destino = bpy.data.scenes.get(sc.get(VOLVER, ""))
    if destino is None:
        practica_id = str(sc.get(EJEMPLO, "")).split("@")[0]
        suyas = [s for s in bpy.data.scenes if s.amatista.practica_id == practica_id]
        destino = max(suyas, key=lambda s: float(s.get(practicas.USADA_EN, 0.0)), default=None)
    if ventana is None or destino is None:
        return "No encontramos tu escena: elígela en el selector de escenas (arriba a la derecha)."
    practicas._a_modo_objeto()  # lo editado en el ejemplo no se queda en Modo Edición en su escena
    ventana.scene = destino
    practicas.redibujar()
    practicas.evaluar_pronto()
    return "Volviste a tu práctica."
