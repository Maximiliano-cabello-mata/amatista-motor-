import math
# Utilidades y entorno com?n para pruebas dentro de Blender.
import sys
import traceback
from pathlib import Path

import bpy

ADDON = Path(__file__).resolve().parents[2]
if str(ADDON) not in sys.path:
    sys.path.insert(0, str(ADDON))
ARCHIVO_V2 = ADDON.parent / "practices" / "archivo" / "v2"

FALLAS = []

def revisar(condicion, mensaje):
    print(("  ✓ " if condicion else "  ✗ ") + mensaje)
    if not condicion:
        FALLAS.append(mensaje)


def cubo(nombre, ubicacion, escala):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ubicacion)
    obj = bpy.context.active_object
    obj.name = nombre
    obj.scale = escala
    return obj


class Diseno:
    """Layout falso: acepta cualquier llamada, para ejecutar los draw() sin interfaz."""

    def __getattr__(self, nombre):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __setattr__(self, nombre, valor):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        return iter((self, self))

    def __bool__(self):
        return True


def dibujar_todo(contexto):
    """Ejecuta el draw() de cada panel y diálogo en modo alumno y Author."""
    import amatista_blender
    from amatista_blender import practicas

    revelada = practicas.pedir_pista(contexto, "patas")
    for modo, pestana in (("alumno", "aprender"), ("alumno", "practicar"), ("alumno", "curso"), ("autor", "practicar")):
        contexto.window_manager.amatista.modo = modo
        contexto.window_manager.amatista.pestana = pestana
        for clase in amatista_blender.CLASES:
            if not hasattr(clase, "draw"):
                continue
            nombre = clase.__name__
            try:
                clase.draw(_Envoltura(clase, revelada), contexto)
            except Exception as error:  # noqa: BLE001
                traceback.print_exc()
                revisar(False, f"{nombre}.draw ({modo}): {error}")
    revisar(True, "todos los paneles y diálogos se dibujan sin errores")
    dibujar_vista_3d(contexto)


def dibujar_vista_3d(contexto):
    """La tarjeta guía y los resaltados 3D con gpu/blf falsos (sin pantalla)."""
    from types import SimpleNamespace

    from amatista_blender import guia
    from amatista_blender.interfaz import hud, visor3d

    falso = Diseno()
    blf_falso = SimpleNamespace(size=lambda *a: None, color=lambda *a: None, position=lambda *a: None,
                                draw=lambda *a: None, dimensions=lambda f, t: (len(t) * 6.0, 10.0))
    reemplazos = {"gpu": falso, "blf": blf_falso, "batch_for_shader": lambda *a, **k: falso,
                  "location_3d_to_region_2d": lambda region, vista, punto: SimpleNamespace(x=100.0, y=80.0)}
    originales = {}
    for modulo in (hud, visor3d):
        originales[modulo] = {k: getattr(modulo, k, None) for k in reemplazos}
        for clave, valor in reemplazos.items():
            setattr(modulo, clave, valor)
    try:
        guia.avisar("¡Listo! Prueba", "Un aviso de prueba que ocupa dos líneas en la tarjeta.", "logrado")
        class ContextoFalso:
            region = SimpleNamespace(width=800, height=600)
            region_data = object()

            def __getattr__(self, nombre):
                return getattr(contexto, nombre)

        bpy_falso = SimpleNamespace(context=ContextoFalso(), data=bpy.data, types=bpy.types, app=bpy.app)
        for modulo in (hud, visor3d):
            originales[modulo]["bpy"] = modulo.bpy
            modulo.bpy = bpy_falso
        hud.dibujar()
        visor3d.dibujar_escena()
        visor3d.dibujar_etiquetas()
        revisar(True, "la tarjeta guía y los resaltados 3D se dibujan sin errores")
    except Exception as error:  # noqa: BLE001
        traceback.print_exc()
        revisar(False, f"dibujar la vista 3D: {error}")
    finally:
        for modulo, valores in originales.items():
            for clave, valor in valores.items():
                setattr(modulo, clave, valor)


class _Envoltura:
    """Se hace pasar por el panel/operador: layout falso y propiedades por defecto."""

    def __init__(self, clase, revelada):
        self.__dict__["_clase"] = clase
        self.__dict__["revelada"] = revelada
        self.__dict__["layout"] = Diseno()
        self.__dict__["herramienta"] = "modifier.boolean"
        self.__dict__["objetivo"] = "patas"
        self.__dict__["explicar"] = False
        self.__dict__["pildora"] = ""

    def __getattr__(self, nombre):
        valor = getattr(self._clase, nombre, None)
        if callable(valor):
            return lambda *a, **k: valor(self, *a, **k)
        return valor


def _limpiar():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)


def _escena_nueva(contexto, nombre="Prueba"):
    """Una escena sin práctica, como la de un Blender recién abierto."""
    sc = bpy.data.scenes.new(nombre)
    contexto.window_manager.windows[0].scene = sc
    return sc


def _inicio_de_blender():
    """El cubo, la luz y la cámara con los que abre Blender."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    bpy.context.active_object.name = "Cube"
    bpy.ops.object.light_add(type="POINT", location=(4, 1, 6))
    bpy.context.active_object.name = "Light"
    bpy.ops.object.camera_add(location=(7, -7, 5))
    bpy.context.active_object.name = "Camera"




def _armar(contexto, piezas):
    """Arma a mano las piezas pedidas (como lo haría el alumno) y deja las matrices al día."""
    from amatista_blender.taller import escena

    for i, pieza in enumerate(piezas):
        nombre = pieza.get("name") or f"Pieza{i}"
        anterior = contexto.scene.objects.get(nombre)
        if anterior is not None:
            bpy.data.objects.remove(anterior)
        escena.crear_pieza(contexto.scene, pieza, f"{nombre} del alumno")
    contexto.view_layer.update()


def _abrir_actividad(contexto, taller_id, actividad_id):
    from amatista_blender.taller import sesion

    texto = sesion.abrir(contexto, taller_id, actividad_id)
    a = sesion.actividad()
    revisar(a is not None and a.id == actividad_id and sesion.estado() == sesion.TRABAJANDO,
            f"talleres: se abre «{actividad_id}» ({texto or ''})")
    return bpy.context


def _elegir(contexto, obj):
    for o in contexto.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    contexto.view_layer.objects.active = obj


def _aldea_del_alumno(contexto):
    """Tres casas en la colecci?n ?Casas? y tres techos en ?Techos?, hechas por el alumno en su escena."""
    from amatista_blender import _motor

    sc = contexto.scene
    colecciones = {}
    for nombre, rol, primitiva in (("Casas", "casa", "Cube"), ("Techos", "techo", "Cone")):
        col = bpy.data.collections.new(nombre)
        sc.collection.children.link(col)
        colecciones[nombre] = col
        for i in range(3):
            obj = bpy.data.objects.new(f"{rol.capitalize()}{i}", bpy.data.meshes.new(primitiva))
            col.objects.link(obj)
            _motor.tagger.assign_role(obj, rol)
    return colecciones

def _tren_del_alumno(contexto, eje_largo=0):
    """El tren como lo arma un principiante: Shift+A, S, R y G sobre piezas de tamaño por defecto."""
    import math

    piezas = []

    def agregar(tipo, escala, lugar, giro=(0, 0, 0)):
        getattr(bpy.ops.mesh, f"primitive_{tipo}_add")()
        obj = contexto.active_object
        obj.scale, obj.location, obj.rotation_euler = escala, lugar, giro
        piezas.append(obj)
        return obj

    agregar("cube", (1.0, 0.6, 0.5), (1.0, 0, 0.9))
    agregar("cube", (0.9, 0.6, 0.5), (-1.0, 0, 0.9))
    for x in (1.6, 0.4, -0.4, -1.6):
        for y in (0.75, -0.75):
            agregar("cylinder", (0.35, 0.35, 0.1), (x, y, 0.35), (math.radians(90), 0, 0))
    agregar("cylinder", (0.2, 0.2, 0.35), (1.5, 0, 1.75))
    contexto.view_layer.update()
    return piezas


def _motor_foto(contexto, extras):
    from amatista_blender import practicas

    for obj in list(contexto.scene.objects):
        bpy.data.objects.remove(obj)
    cubo("Caja", (0, 0, 1), (2, 2, 2))
    for i in range(extras):
        cubo(f"Suelta {i}", (5 + i, 5, 0.25), (0.5, 0.5, 0.5))
    return practicas.capturar(contexto.scene)
