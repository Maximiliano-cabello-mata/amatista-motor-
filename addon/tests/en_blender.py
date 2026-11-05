"""Prueba del add-on DENTRO de Blender (registro, escena real, Author y limpieza).

    blender --background --factory-startup --python addon/tests/en_blender.py
    # o con el módulo bpy de PyPI (Python 3.11):
    python addon/tests/en_blender.py

Sale con código 1 si algo falla. No necesita red: el servidor no se usa.
"""
import importlib
import json
import re
import sys
import tempfile
import traceback
from pathlib import Path

import bpy  # noqa: I001  (bpy primero: agrega los scripts de Blender al path)
import addon_utils

ADDON = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ADDON))
sys.path.insert(0, str(TESTS))
ARCHIVO_V2 = ADDON.parent / "practices" / "archivo" / "v2"


from suites_blender.comun import (
    FALLAS,
    revisar,
    cubo,
    Diseno,
    dibujar_todo,
    dibujar_vista_3d,
    _limpiar,
    _escena_nueva,
    _inicio_de_blender,
)
from suites_blender.suite_v3 import (
    probar_escena_por_practica,
    probar_v3,
    probar_temas,
    probar_motor_34,
    probar_motor_35,
    probar_ejemplo,
)
from suites_blender.suite_motor import (
    probar_motor_4,
    probar_motor6,
    probar_motor61,
    probar_motor62,
    probar_motor7,
)
from suites_blender.suite_taller import (
    probar_taller,
    probar_talleres_nuevos,
    probar_recorrido,
)
from suites_blender.suite_integracion import (
    probar_auditoria,
    probar_idioma,
    probar_integracion,
    probar_corazon,
    probar_entrega,
)

def main():
    print(f"Blender {bpy.app.version_string}")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    modulo = addon_utils.enable("amatista_blender", default_set=True, handle_error=None)
    revisar(modulo is not None, "el add-on se registra")
    from amatista_blender import _motor, ajustes, autor, practicas

    import shutil

    shutil.rmtree(ajustes.carpeta_usuario() / "practicas", ignore_errors=True)  # caché de corridas anteriores
    (ajustes.carpeta_usuario() / "avance.json").unlink(missing_ok=True)
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    shutil.rmtree(ajustes.carpeta_usuario() / "isla", ignore_errors=True)

    revisar(bpy.context.preferences.addons.get("amatista_blender") is not None, "preferencias disponibles")
    # Motor 6.1: las pruebas de antes no esperan fichas ni el modo curioso (probar_motor61 los prueba).
    ajustes.prefs().presentar_herramientas = False
    ajustes.prefs().modo_curioso = "nunca"
    # Motor 7: las pruebas de antes prueban la interfaz del motor 6 (probar_motor7 prueba el guion).
    ajustes.prefs().guion_paso_a_paso = False
    catalogo = practicas.catalogo()
    revisar("blender.bp.m1.tren" in catalogo and "blender.bpi.m3.pelota" in catalogo,
            "las 6 prácticas del plan de estudios están en el catálogo")
    revisar("blender.n1.mesa" not in catalogo, "las prácticas archivadas (v2) no se muestran al alumno")

    contexto = bpy.context

    # --- Compatibilidad: la práctica v2 de la mesa (archivada) sigue funcionando ---
    mesa = json.loads((ARCHIVO_V2 / "mesa.json").read_text(encoding="utf-8"))
    practicas.activar(contexto, mesa, "paquete")
    reporte = practicas.ESTADO["reporte"]
    revisar(reporte is not None and reporte.progress == 0, "escena vacía: 0 %")
    revisar(reporte.current_target_id == "cubierta", "el primer paso es la cubierta")

    # --- Etapa 2: guía y «Hazlo conmigo» (sin ventana se aplica el valor sugerido) ---
    from amatista_blender import guia

    g = guia.guia_actual()
    revisar(g is not None and g.action.kind == "add_cube", "guía: escena vacía propone agregar un cubo")
    revisar(bpy.ops.amatista.hazlo_conmigo() == {"FINISHED"}, "Hazlo conmigo agrega el cubo")
    # Motor 3.4: el cubo que agrega «Hazlo conmigo» ya llega con el rol del paso (antes se perdía).
    revisar(_motor.tagger.get_role(contexto.active_object) == "cubierta", "Hazlo conmigo: el cubo ya es la cubierta")
    practicas.evaluar(contexto)
    g = guia.guia_actual()
    revisar(g.target_id == "grosor" and g.action.kind == "scale" and g.action.value == 0.1,
            f"guía: escalar en Z por 0.1 ({g.action})")
    revisar([i.keys for i in g.instructions][1] == ("S", "Z"), "guía: teclas S › Z")
    dibujar_vista_3d(contexto)  # con regla y resaltado naranja
    bpy.ops.amatista.hazlo_conmigo()
    reporte = practicas.evaluar(contexto)
    revisar(reporte.result("grosor").passed, "Hazlo conmigo deja la cubierta delgada")
    revisar(practicas.pistas(contexto).get("grosor") == 3, "Hazlo conmigo cuenta como guía paso a paso")
    revisar(any(a["titulo"].startswith("¡Listo!") for a in guia.ESTADO["avisos"]), "el acompañante celebra el paso")
    revisar(bpy.ops.amatista.mostrarme() == {"FINISHED"}, "Muéstrame selecciona lo del paso")
    revisar(practicas.datos_intento(contexto)["ayudas"]["hazlo_conmigo"] == 2, "el intento cuenta las ayudas")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    contexto.scene.amatista.pistas_json = "{}"
    practicas.evaluar(contexto)

    tabla = cubo("Tabla", (0, 0, 0.8), (2.0, 1.0, 0.1))
    _motor.tagger.assign_role(tabla, "cubierta")
    patas = []
    for i, (x, y) in enumerate(((-0.9, -0.4), (0.9, -0.4), (-0.9, 0.4))):
        pata = cubo(f"Pata{i}", (x, y, 0.375), (0.1, 0.1, 0.75))
        _motor.tagger.assign_role(pata, "pata")
        patas.append(pata)
    reporte = practicas.evaluar(contexto)
    revisar(reporte.result("patas").message == "Tienes 3/4 «Pata». Falta 1.", "detecta 3 de 4 patas")
    revisar(reporte.current_target_id == "patas", "el paso actual son las patas")
    g = guia.guia_actual()
    revisar(g.action.kind == "duplicate" and any(c.kind == "ghosts" for c in g.cues),
            "guía: duplicar y la pata que falta como fantasma")
    dibujar_vista_3d(contexto)  # con fantasmas y contornos verdes

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
    revisar(datos["version_addon"] == "7.1.0", "el intento lleva la versión 7.1 del add-on")

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
    revisar(practicas.ESTADO["reporte"].progress in (60, 100), "Live Validation: el borrador valida en vivo con la escena")
    exportado = Path(tempfile.mkdtemp()) / "banco.json"
    autor.exportar(str(exportado))
    revisar(json.loads(exportado.read_text())["targets"][0]["hints"], "exportar practice.json con pistas")
    contexto.window_manager.amatista.modo = "alumno"

    probar_escena_por_practica(contexto)
    probar_v3(contexto)
    probar_temas(contexto)
    probar_motor_34(contexto)
    probar_motor_35(contexto)
    probar_ejemplo(contexto)
    probar_auditoria(contexto)
    probar_motor_4(contexto)
    probar_taller(contexto)
    probar_recorrido(contexto)
    probar_idioma(contexto)
    probar_integracion(contexto)
    probar_motor6(contexto)
    probar_motor61(contexto)
    probar_motor62(contexto)
    probar_motor7(contexto)
    probar_corazon(contexto)
    probar_entrega(contexto)

    addon_utils.disable("amatista_blender", default_set=True)
    revisar(not hasattr(bpy.types.Scene, "amatista"), "se desregistra limpio")
    revisar(not getattr(bpy.types.VIEW3D_MT_editor_menus.draw, "_amatista", False), "desregistrar devuelve los menús de Blender")
    revisar(not hasattr(bpy.types, "AMATISTA_MT_principal"), "desregistrar quita el menú Amatista de arriba")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        FALLAS.append("excepción")
    print("RESULTADO:", "OK" if not FALLAS else f"{len(FALLAS)} falla(s)")
    if FALLAS:
        sys.exit(1)
