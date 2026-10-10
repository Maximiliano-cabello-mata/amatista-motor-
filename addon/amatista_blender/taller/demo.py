"""«Mira»: Amatista hace la habilidad en tu vista 3D, con las teclas en pantalla.

Reproduce la línea de tiempo del motor (amatista_engine.taller.demo) con
objetos temporales: aparecen, se mueven, se estiran y se giran como si
alguien usara las teclas, y se borran al terminar. Nunca tocan lo del
alumno (llevan la marca ``amatista_ignore`` y el motor no los revisa) y
nunca hacen el paso por él: en «Hazlo conmigo» la escena vuelve a estar
como la dejó.

La tarjeta (vista/tarjeta.py) dibuja encima el texto del paso y sus teclas
al estilo screencast.
"""
import math
import time

import bpy
from mathutils import Euler, Vector

from .. import _motor
from . import escena

IGNORAR = "amatista_ignore"
DEMO = "amatista_demo"
FPS = 30.0

ESTADO = {
    "linea": None,  # LineaDeTiempo
    "inicio": 0.0,
    "objetos": {},  # nombre en la demo → nombre real del objeto temporal
    "hechos": set(),  # índices de pasos ya aplicados al final
    "base": {},  # estado de cada objeto al empezar su paso (para interpolar)
    "al_terminar": None,
    "escena": "",
    "vista": None,
}


def activa():
    return ESTADO["linea"] is not None


def tiempo():
    return max(0.0, time.time() - ESTADO["inicio"]) if activa() else 0.0


def paso_actual():
    linea = ESTADO["linea"]
    return linea.en(tiempo()) if linea is not None else None


def avance():
    linea = ESTADO["linea"]
    if linea is None or not linea.duracion:
        return 0.0
    return min(1.0, tiempo() / linea.duracion)


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _obj(nombre):
    real = ESTADO["objetos"].get(nombre)
    return bpy.data.objects.get(real) if real else None


def _marcar(obj):
    obj[IGNORAR] = 1
    obj[DEMO] = 1
    obj.hide_select = True
    obj.show_wire = True
    obj.color = (0.62, 0.42, 0.95, 1.0)


def _escena():
    return bpy.data.scenes.get(ESTADO["escena"]) or bpy.context.scene


def _crear(datos, nombre_demo):
    sc = _escena()
    pieza = {
        "primitive": datos.get("primitiva") or "cube",
        "size": datos.get("medidas") or (2.0, 2.0, 2.0),
        "location": datos.get("loc") or (0.0, 0.0, 0.0),
        "rotation": datos.get("giro") or (0.0, 0.0, 0.0),
    }
    obj = escena.crear_pieza(sc, pieza, f"Amatista demo · {nombre_demo}")
    _marcar(obj)
    ESTADO["objetos"][nombre_demo] = obj.name
    return obj


def _duplicar(datos):
    origen = _obj(datos.get("objeto", ""))
    if origen is None:
        return None
    copia = origen.copy()
    copia.data = origen.data.copy() if origen.data is not None else None
    _escena().collection.objects.link(copia)
    _marcar(copia)
    copia.name = f"Amatista demo · {datos.get('nombre') or 'copia'}"
    ESTADO["objetos"][datos.get("nombre") or copia.name] = copia.name
    return copia


def _base(i, obj):
    """Cómo estaba el objeto cuando empezó el paso i (se guarda una vez)."""
    clave = (i, obj.name)
    if clave not in ESTADO["base"]:
        ESTADO["base"][clave] = (Vector(obj.location), Vector(obj.dimensions), Euler(obj.rotation_euler))
    return ESTADO["base"][clave]


def _material(obj, datos, factor):
    if obj is None or obj.type != "MESH":
        return
    nombre = f"Amatista demo · {datos.get('nombre') or 'Material'}"
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    color = list(datos.get("color") or (0.8, 0.3, 0.3))[:3]
    gris = (0.8, 0.8, 0.8)
    mezcla = [g + (c - g) * factor for g, c in zip(gris, color)]
    mat.diffuse_color = (*mezcla, 1.0)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    obj.color = (*mezcla, 1.0)


def _aplicar(i, paso, factor):
    """Lleva el paso i al punto `factor` (0 a 1) de su animación."""
    accion, datos = paso.accion, paso.datos
    if accion == "agregar":
        nombre = datos.get("nombre") or datos.get("primitiva") or "Pieza"
        obj = _obj(nombre) or _crear(datos, nombre)
        crecer = _suave(factor * 2.5)  # aparece creciendo en el primer tercio
        medidas = Vector(datos.get("medidas") or (2.0, 2.0, 2.0))
        obj.dimensions = medidas * max(0.05, crecer)
        return
    if accion == "duplicar":
        nombre = datos.get("nombre") or "copia"
        obj = _obj(nombre) or _duplicar(datos)
        if obj is None:
            return
        loc0, _, _ = _base(i, obj)
        destino = Vector(datos.get("a") or loc0)
        obj.location = loc0.lerp(destino, _suave(factor))
        return
    obj = _obj(datos.get("objeto", ""))
    if accion == "borrar":
        if obj is not None and factor >= 0.6:
            obj.hide_viewport = True
        return
    if accion == "material":
        _material(obj, datos, _suave(factor))
        return
    if accion == "luz":
        nombre = datos.get("nombre") or "Luz"
        if _obj(nombre) is None:
            luz = bpy.data.lights.new(f"Amatista demo · {nombre}", str(datos.get("tipo") or "AREA"))
            luz.energy = float(datos.get("energia") or 500.0)
            nueva = bpy.data.objects.new(f"Amatista demo · {nombre}", luz)
            _escena().collection.objects.link(nueva)
            _marcar(nueva)
            nueva.location = datos.get("loc") or (3.0, -3.0, 4.0)
            ESTADO["objetos"][nombre] = nueva.name
        return
    if accion == "camara":
        nombre = datos.get("nombre") or "Cámara"
        cam = _obj(nombre)
        if cam is None:
            datos_cam = bpy.data.cameras.new(f"Amatista demo · {nombre}")
            cam = bpy.data.objects.new(f"Amatista demo · {nombre}", datos_cam)
            _escena().collection.objects.link(cam)
            _marcar(cam)
            ESTADO["objetos"][nombre] = cam.name
        cam.location = datos.get("loc") or (6.0, -6.0, 4.0)
        mira = Vector(datos.get("mira") or (0.0, 0.0, 0.5))
        cam.rotation_euler = (mira - cam.location).to_track_quat("-Z", "Y").to_euler()
        return
    if accion == "modificador":
        if obj is not None and factor >= 0.3 and not obj.get("amatista_demo_mod_" + str(i)):
            tipo = str(datos.get("tipo") or "SUBSURF")
            try:
                mod = obj.modifiers.new(tipo.capitalize(), tipo)
            except (TypeError, RuntimeError):
                return
            if tipo == "MIRROR" and datos.get("ejes"):
                mod.use_axis = [bool(v) for v in datos["ejes"]][:3]
            elif tipo == "SUBSURF":
                mod.levels = int(datos.get("niveles") or 2)
            elif tipo == "ARRAY":
                mod.count = int(datos.get("cuenta") or 3)
            elif tipo == "BEVEL":
                mod.width = float(datos.get("ancho") or 0.1)
                mod.segments = 3
            elif tipo == "SOLIDIFY":
                mod.thickness = float(datos.get("ancho") or 0.1)
            obj["amatista_demo_mod_" + str(i)] = 1
        return
    if obj is None:
        return
    loc0, dim0, rot0 = _base(i, obj)
    t = _suave(factor)
    if accion in ("mover", "clave") and datos.get("a") is not None:
        obj.location = loc0.lerp(Vector(datos["a"]), t)
    elif accion in ("escalar", "extruir") and datos.get("medidas") is not None:
        final = Vector(datos["medidas"])
        obj.dimensions = dim0.lerp(final, t)
        if accion == "extruir" and datos.get("a") is not None:
            obj.location = loc0.lerp(Vector(datos["a"]), t)
    elif accion == "rotar":
        if datos.get("giro") is not None:
            final = Euler([math.radians(float(g)) for g in datos["giro"]], "XYZ")
        else:
            eje = "xyz".index(str(datos.get("eje") or "z").lower()[:1] or "z")
            final = Euler(rot0)
            final[eje] += math.radians(float(datos.get("grados") or 90))
        obj.rotation_euler = Euler([a + (b - a) * t for a, b in zip(rot0, final)], "XYZ")


def _vista(paso):
    """«1», «3», «7»: la vista cambia como si el alumno tocara el teclado numérico."""
    tipo = str(paso.datos.get("tipo") or "")
    giros = {"frente": (90, 0, 0), "lado": (90, 0, 90), "arriba": (0, 0, 0)}
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type != "VIEW_3D":
                continue
            r3d = area.spaces.active.region_3d
            if tipo in giros:
                r3d.view_rotation = Euler([math.radians(g) for g in giros[tipo]], "XYZ").to_quaternion()
            elif tipo == "orbita":
                actual = r3d.view_rotation.to_euler()
                actual.z += math.radians(35)
                r3d.view_rotation = actual.to_quaternion()
            area.tag_redraw()


def _guardar_vista():
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                r3d = area.spaces.active.region_3d
                return (r3d.view_rotation.copy(), r3d.view_location.copy(), r3d.view_distance)
    return None


def _devolver_vista(vista):
    if vista is None:
        return
    for ventana in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                r3d = area.spaces.active.region_3d
                r3d.view_rotation, r3d.view_location, r3d.view_distance = vista
                area.tag_redraw()


def empezar(habilidad, al_terminar=None, sc=None):
    """Empieza la demostración de una habilidad (Habilidad del catálogo)."""
    detener(llamar=False)
    linea = _motor.taller.linea_de_tiempo(habilidad.demo, habilidad.titulo)
    if not linea.pasos:
        if al_terminar:
            al_terminar(False)
        return False
    sc = sc or bpy.context.scene
    ESTADO.update(linea=linea, inicio=time.time(), objetos={}, hechos=set(), base={}, al_terminar=al_terminar,
                  escena=sc.name, vista=_guardar_vista())
    if not bpy.app.timers.is_registered(_cuadro):
        bpy.app.timers.register(_cuadro, first_interval=0.0)
    return True


def _cuadro():
    linea = ESTADO["linea"]
    if linea is None:
        return None
    t = tiempo()
    try:
        for i, paso in enumerate(linea.pasos):
            if t < paso.inicio:
                break
            factor = min(1.0, (t - paso.inicio) / max(0.05, paso.duracion))
            if i in ESTADO["hechos"]:
                continue
            if paso.accion == "vista":
                if factor >= 0.3:
                    _vista(paso)
                    ESTADO["hechos"].add(i)
                continue
            _aplicar(i, paso, factor)
            if factor >= 1.0:
                ESTADO["hechos"].add(i)
    except Exception as error:  # noqa: BLE001 - una demostración rota termina, nunca rompe Blender
        print(f"[Amatista] Demostración: {error}")
        detener(completa=False)
        return None
    from . import vista

    vista.redibujar()
    if t >= linea.duracion + 0.6:
        detener(completa=True)
        return None
    return 1.0 / FPS


def borrar_objetos():
    for obj in [o for o in bpy.data.objects if o.get(DEMO)]:
        datos = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        try:
            if datos is not None and datos.users == 0:
                if isinstance(datos, bpy.types.Mesh):
                    bpy.data.meshes.remove(datos)
                elif isinstance(datos, bpy.types.Light):
                    bpy.data.lights.remove(datos)
                elif isinstance(datos, bpy.types.Camera):
                    bpy.data.cameras.remove(datos)
        except ReferenceError:
            pass
    for mat in [m for m in bpy.data.materials if m.name.startswith("Amatista demo · ") and m.users == 0]:
        bpy.data.materials.remove(mat)


def detener(completa=False, llamar=True):
    """Termina la demostración y deja la escena como estaba."""
    al_terminar = ESTADO["al_terminar"]
    vista_antes = ESTADO["vista"]
    estaba = activa()
    ESTADO.update(linea=None, objetos={}, hechos=set(), base={}, al_terminar=None, vista=None)
    if bpy.app.timers.is_registered(_cuadro):
        bpy.app.timers.unregister(_cuadro)
    try:
        borrar_objetos()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] No se pudieron borrar los objetos de la demostración: {error}")
    if estaba:
        _devolver_vista(vista_antes)
    if estaba and llamar and al_terminar:
        al_terminar(completa)


def unregister():
    detener(llamar=False)
