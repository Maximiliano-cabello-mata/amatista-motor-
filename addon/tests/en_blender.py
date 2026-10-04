"""Prueba del add-on DENTRO de Blender (registro, escena real, Author y limpieza).

    blender --background --factory-startup --python addon/tests/en_blender.py
    # o con el módulo bpy de PyPI (Python 3.11):
    python addon/tests/en_blender.py

Sale con código 1 si algo falla. No necesita red: el servidor no se usa.
"""
import json
import sys
import tempfile
import traceback
from pathlib import Path

import bpy  # noqa: I001  (bpy primero: agrega los scripts de Blender al path)
import addon_utils

ADDON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON))

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
    for modo in ("alumno", "autor"):
        contexto.window_manager.amatista.modo = modo
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


class _Envoltura:
    """Se hace pasar por el panel/operador: layout falso y propiedades por defecto."""

    def __init__(self, clase, revelada):
        self.__dict__["_clase"] = clase
        self.__dict__["revelada"] = revelada
        self.__dict__["layout"] = Diseno()
        self.__dict__["herramienta"] = "modifier.boolean"
        self.__dict__["objetivo"] = "patas"
        self.__dict__["explicar"] = False

    def __getattr__(self, nombre):
        valor = getattr(self._clase, nombre, None)
        if callable(valor):
            return lambda *a, **k: valor(self, *a, **k)
        return valor


def main():
    print(f"Blender {bpy.app.version_string}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    modulo = addon_utils.enable("amatista_blender", default_set=True, handle_error=None)
    revisar(modulo is not None, "el add-on se registra")
    from amatista_blender import _motor, autor, practicas

    revisar(bpy.context.preferences.addons.get("amatista_blender") is not None, "preferencias disponibles")
    catalogo = practicas.catalogo()
    revisar("blender.n1.mesa" in catalogo, "la práctica de la mesa está en el catálogo")

    contexto = bpy.context
    practicas.activar(contexto, catalogo["blender.n1.mesa"]["definicion"], "paquete")
    reporte = practicas.ESTADO["reporte"]
    revisar(reporte is not None and reporte.progress == 0, "escena vacía: 0 %")
    revisar(reporte.current_target_id == "cubierta", "el primer paso es la cubierta")

    tabla = cubo("Tabla", (0, 0, 0.8), (2.0, 1.0, 0.1))
    _motor.tagger.assign_role(tabla, "cubierta")
    patas = []
    for i, (x, y) in enumerate(((-0.9, -0.4), (0.9, -0.4), (-0.9, 0.4))):
        pata = cubo(f"Pata{i}", (x, y, 0.375), (0.1, 0.1, 0.75))
        _motor.tagger.assign_role(pata, "pata")
        patas.append(pata)
    reporte = practicas.evaluar(contexto)
    revisar(reporte.result("patas").message == "Tienes 3/4 «pata». Falta 1.", "detecta 3 de 4 patas")
    revisar(reporte.current_target_id == "patas", "el paso actual son las patas")

    resultado = bpy.ops.amatista.pista(objetivo="patas")
    revisar(resultado == {"FINISHED"}, "pedir pista funciona")
    revisar(practicas.pistas(contexto) == {"patas": 1}, "la pista queda registrada en la escena")

    bpy.ops.object.select_all(action="DESELECT")
    patas[0].select_set(True)
    contexto.view_layer.objects.active = patas[0]
    bpy.ops.object.duplicate()
    copia = contexto.active_object
    copia.location = (0.9, 0.4, 0.375)
    revisar(_motor.tagger.get_role(copia) == "pata", "duplicar conserva el rol")

    ruta = Path(tempfile.mkdtemp()) / "mi_mesa.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(ruta))
    reporte = practicas.evaluar(contexto)
    revisar(reporte.completed and reporte.progress == 100, "mesa completa y guardada: 100 %")

    foto = practicas.datos_intento(contexto)["escena"]
    otra = _motor.MOTOR.evaluate(practicas.practica_activa(contexto), _motor.foto.scene_from_dict(json.loads(json.dumps(foto))))
    revisar(otra.progress == 100, "el servidor obtendría el mismo resultado con la foto")
    revisar(foto["objetos"][0].get("b") is not None, "la foto incluye cajas en coordenadas del mundo")

    tabla.modifiers.new("Bool", "BOOLEAN")
    reporte = practicas.evaluar(contexto)
    revisar([w.tool_id for w in reporte.tool_warnings] == ["modifier.boolean"], "avisa Booleano (nivel 3)")
    tabla.modifiers.remove(tabla.modifiers["Bool"])

    datos = practicas.datos_intento(contexto)
    revisar(datos["pistas"] == {"patas": 1} and datos["practica_id"] == "blender.n1.mesa", "datos del intento completos")

    # --- Amatista Author ---
    contexto.window_manager.amatista.modo = "autor"
    a = contexto.scene.amatista_autor
    a.nuevo_id, a.nuevo_titulo, a.nuevo_nivel = "blender.n1.banco", "Construir un banco", 1
    bpy.ops.amatista.autor_nuevo()
    a.nuevo_rol, a.nuevo_rol_etiqueta = "asiento", "Asiento"
    bpy.ops.amatista.declarar_rol()
    revisar("asiento" in (autor.leer_borrador() or {}).get("roles", {}), "declarar rol en el borrador")
    a.plantilla = "role.count"
    a.obj_titulo = "Crea el asiento"
    a.obj_rol = "asiento"
    a.obj_cantidad = 1
    a.obj_peso = 60
    bpy.ops.amatista.autor_agregar_objetivo()
    a.plantilla = "file.saved"
    a.obj_titulo = "Guarda"
    a.obj_peso = 40
    a.obj_requiere = "crea_el_asiento"
    bpy.ops.amatista.autor_agregar_objetivo()
    a.objetivo = "crea_el_asiento"
    a.pista = "Selecciona un cubo y asígnale el rol Asiento."
    bpy.ops.amatista.autor_agregar_pista()
    compilado = autor.compilar()
    revisar(compilado.ok, f"el borrador compila ({compilado.errors})")
    _motor.tagger.assign_role(tabla, "asiento")
    bpy.ops.amatista.autor_probar()
    revisar(practicas.ESTADO["reporte"].progress == 60, "Live Validation: 60 % (asiento sí, archivo con cambios)")
    exportado = Path(tempfile.mkdtemp()) / "banco.json"
    autor.exportar(str(exportado))
    revisar(json.loads(exportado.read_text())["targets"][0]["hints"], "exportar practice.json con pistas")

    dibujar_todo(contexto)

    addon_utils.disable("amatista_blender", default_set=True)
    revisar(not hasattr(bpy.types.Scene, "amatista"), "se desregistra limpio")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        FALLAS.append("excepción")
    print("RESULTADO:", "OK" if not FALLAS else f"{len(FALLAS)} falla(s)")
    if FALLAS:
        sys.exit(1)
