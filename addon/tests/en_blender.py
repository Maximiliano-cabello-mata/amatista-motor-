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


def _inicio_de_blender():
    """El cubo, la luz y la cámara con los que abre Blender."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    bpy.context.active_object.name = "Cube"
    bpy.ops.object.light_add(type="POINT", location=(4, 1, 6))
    bpy.context.active_object.name = "Light"
    bpy.ops.object.camera_add(location=(7, -7, 5))
    bpy.context.active_object.name = "Camera"


def probar_v3(contexto):
    """Motor v3: mapa del curso, escenas de inicio, píldoras, repaso, vigilantes y acciones nuevas."""
    from amatista_blender import aprendizaje, guia, practicas

    catalogo = practicas.catalogo()
    aprendizaje.ESTADO["avance"] = {"completadas": [], "pildoras_vistas": {}, "repaso": {}}
    revisar(aprendizaje.plan() is not None and len(aprendizaje.plan().courses) == 4, "mapa: 4 cursos")
    revisar(aprendizaje.siguiente() == "blender.bp.m1.explora", "mapa: la primera práctica es la exploración")
    revisar(aprendizaje.estados()["blender.bp.m1.tren"] == "bloqueado", "mapa: el tren espera a la exploración")
    aprendizaje.marcar_completada("blender.bp.m1.explora")
    revisar(aprendizaje.siguiente() == "blender.bp.m1.tren", "mapa: después de explorar sigue el tren")
    revisar(aprendizaje.estados()["blender.bp.m2.espada"] == "bloqueado", "mapa: la espada empieza bloqueada")

    # Tren: la escena de inicio se vacía y la primera píldora es la de los ejes.
    _limpiar()
    _inicio_de_blender()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(not bpy.data.objects, "tren: se quitan el cubo, la luz y la cámara de inicio")
    principal = aprendizaje.pildora_principal()
    revisar(principal is not None, f"tren: hay teoría desde el inicio ({principal and principal.id})")
    g = guia.guia_actual()
    revisar(g.action is not None and g.action.kind in ("add_cube", "add_primitive"),
            f"tren: Hazlo conmigo agrega una pieza ({g.action})")
    revisar(bpy.ops.amatista.hazlo_conmigo() == {"FINISHED"} and len(bpy.data.objects) == 1, "tren: se agrega la pieza")
    # Motor 3.3: «Así se debe ver» con la imagen y el plano del modelo de referencia.
    from amatista_blender.interfaz import estilo

    imagen = practicas.archivo_de_referencia("blender.bp.m1.tren", "referencia.jpg")
    revisar(imagen is not None and practicas.archivo_de_referencia("blender.bp.m1.tren", "plano.svg") is not None,
            "tren: trae la imagen y el plano del modelo de referencia")
    estilo.imagen(imagen)
    revisar(estilo._IMAGENES is not None and str(imagen) in estilo._IMAGENES, "tren: la imagen de referencia se carga como vista previa")
    bpy.ops.amatista.pildora_vista(pildora=principal.id)
    revisar(principal.id in aprendizaje.vistas("blender.bp.m1.tren"), "píldora marcada como vista")
    revisar(any(k.endswith("#" + principal.id) for k in aprendizaje.avance()["repaso"]) == (principal.check is not None),
            "la píldora con pregunta entra al repaso")
    aprendizaje.marcar_completada("blender.bp.m1.tren")
    revisar(aprendizaje.estados()["blender.bp.m2.explora"] == "disponible", "mapa: terminar el tren abre la exploración del módulo 2")
    revisar(aprendizaje.estados()["blender.bp.m2.espada"] == "bloqueado", "mapa: la espada espera a su exploración")
    aprendizaje.marcar_completada("blender.bp.m2.explora")
    revisar(aprendizaje.estados()["blender.bp.m2.espada"] == "disponible", "mapa: explorar el módulo 2 abre la espada")

    # Espada: repaso de lo anterior y vigilante de malla limpia.
    for item in aprendizaje.avance()["repaso"].values():
        item["due"] = 0  # ya toca repasar
    aprendizaje.avance()["repaso"]["blender.bp.m1.tren#grs"] = {"box": 1, "due": 0}
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    pendientes = aprendizaje.repasos_pendientes(practicas.practica_activa(contexto))
    revisar(bool(pendientes), f"espada: hay repaso del tren ({[i for i, _ in pendientes]})")
    item, pildora = pendientes[0]
    bpy.ops.amatista.responder_repaso(item=item, opcion=pildora.check.answer)
    revisar(aprendizaje.avance()["repaso"][item]["box"] == 2, "repaso correcto: sube a la caja 2")
    bpy.ops.mesh.primitive_cube_add(size=1)
    espada = contexto.active_object
    from amatista_blender import _motor

    _motor.tagger.assign_role(espada, "modelo")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.duplicate()  # caras encimadas, como E y cancelar
    bpy.ops.object.mode_set(mode="OBJECT")
    reporte = practicas.evaluar(contexto)
    revisar(reporte.paused_by == "malla-limpia", f"espada: el vigilante pausa el progreso ({reporte.paused_by})")
    g = guia.guia_actual()
    revisar(g.paused and g.action.kind == "merge_by_distance", "espada: la guía ofrece fusionar por distancia")
    revisar(aprendizaje.pildora_principal().id == "fusionar", "espada: la píldora del vigilante va primero")
    bpy.ops.amatista.hazlo_conmigo()
    reporte = practicas.evaluar(contexto)
    revisar(not reporte.paused and len(espada.data.vertices) == 8, "espada: fusionar limpia la malla y reanuda")

    # Pinta tu nave: la escena se arma con la nave básica (Espejo + Subdivisión).
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bpi.m1.pinta-nave"]["definicion"], "paquete")
    nave = bpy.data.objects.get("Nave")
    revisar(nave is not None and {m.type for m in nave.modifiers} == {"MIRROR", "SUBSURF"}, "pinta-nave: nave básica armada")
    for _ in range(3):
        guia.ejecutar_accion(contexto, _motor.guia.GuideAction("new_material", "Material", ("Nave",)), False)
    materiales = [s.material for s in nave.material_slots]
    principled = [m.node_tree.nodes.get("Principled BSDF") for m in materiales]
    principled[0].inputs["Metallic"].default_value, principled[0].inputs["Roughness"].default_value = 1.0, 0.2
    principled[1].inputs["Transmission Weight"].default_value = 1.0
    principled[2].inputs["Metallic"].default_value, principled[2].inputs["Roughness"].default_value = 0.9, 0.8
    for indice, poligono in enumerate(nave.data.polygons):
        poligono.material_index = indice % 3
    reporte = practicas.evaluar(contexto)
    revisar(reporte.current_target_id == "guardar", f"pinta-nave: cristal y dos metales listos ({reporte.current_target_id})")

    # Tres puntos: Workbench → EEVEE con «Hazlo conmigo» y F12 contado.
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bpi.m2.tres-puntos"]["definicion"], "paquete")
    revisar(contexto.scene.render.engine == "BLENDER_WORKBENCH", "tres puntos: el estudio empieza en Workbench")
    guia.ejecutar_accion(contexto, _motor.guia.GuideAction("set_engine", "EEVEE", option="EEVEE"), False)
    revisar("EEVEE" in contexto.scene.render.engine, "tres puntos: Hazlo conmigo cambia a EEVEE")
    guia.ejecutar_accion(contexto, _motor.guia.GuideAction("add_camera", "Cámara"), False)
    revisar(contexto.scene.camera is not None, "tres puntos: cámara agregada y activa")
    practicas._al_renderizar(contexto.scene)
    revisar(_motor.adapter.capture_scene(contexto.scene).renders == 1, "tres puntos: el render (F12) se cuenta")

    # Pelota: claves de posición y escala.
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bpi.m3.pelota"]["definicion"], "paquete")
    pelota = bpy.data.objects.get("Pelota")
    revisar(pelota is not None and pelota.location.z == 4.0, "pelota: escena con la pelota en el aire")
    for cuadro, z, sz in ((1, 4.0, 1.0), (12, 1.0, 0.75), (24, 4.0, 1.0)):
        contexto.scene.frame_set(cuadro)
        pelota.location.z, pelota.scale.z = z, sz
        guia.ejecutar_accion(contexto, _motor.guia.GuideAction("insert_keyframe", "I", ("Pelota",), "z",
                                                               option="location"), False)
        guia.ejecutar_accion(contexto, _motor.guia.GuideAction("insert_keyframe", "I", ("Pelota",), "z",
                                                               option="scale"), False)
    reporte = practicas.evaluar(contexto)
    revisar(reporte.current_target_id == "guardar", f"pelota: rebota y se aplasta ({reporte.current_target_id}: {reporte.result(reporte.current_target_id).message if reporte.current_target_id else ''})")
    ruta = Path(tempfile.mkdtemp()) / "mi_pelota.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(ruta))
    reporte = practicas.evaluar(contexto)
    revisar(reporte.completed, "pelota: guardada, práctica completa")
    revisar("blender.bpi.m3.pelota" in aprendizaje.avance()["completadas"], "la práctica completa queda en tu avance")

    # Author v3: plantilla, píldora y caso de prueba sin código.
    from amatista_blender import autor

    contexto.window_manager.amatista.modo = "autor"
    a = contexto.scene.amatista_autor
    a.nuevo_id, a.nuevo_titulo, a.nueva_plantilla = "blender.bp.prueba", "Prueba", "modelado"
    bpy.ops.amatista.autor_nuevo()
    a.pil_titulo, a.pil_texto, a.pil_teclas, a.pil_disparo = "Ctrl + R", "Corta un anillo.", "Ctrl + R", "start"
    bpy.ops.amatista.autor_agregar_pildora()
    revisar(autor.compilar().ok and len(autor.leer_borrador()["pills"]) == 4, "Author: plantilla + píldora compilan")
    bpy.ops.amatista.autor_caso_prueba()
    casos = autor.leer_pruebas("blender.bp.prueba")["casos"]
    revisar(len(casos) == 1 and "escena" in casos[0], "Author: caso de prueba con la foto de la escena")
    contexto.window_manager.amatista.modo = "alumno"
    dibujar_todo(contexto)
    _limpiar()


def probar_temas(contexto):
    """Add-on 3.2: temática por módulo (tema, cielo de la vista 3D, mascota, HUD y paneles)."""
    from amatista_blender import _motor, escenarios, practicas, temas
    from amatista_blender.interfaz import hud

    catalogo = practicas.catalogo()
    revisar(temas.tema_de_practica("blender.bp.m1.tren")["nombre"] == "El taller de juguetes",
            "tema: el tren es «El taller de juguetes»")
    revisar(temas.tema_de_practica("blender.n1.mesa")["id"] == "cristal", "tema: sin módulo, la cueva del cristal")

    sc = contexto.scene
    practicas.cerrar(contexto)  # las pruebas anteriores abrieron prácticas sin mundo: Amatista creó uno
    revisar(sc.world is None and escenarios.MUNDO_CREADO not in sc, "cerrar quita el mundo que creó Amatista")
    sc.world = bpy.data.worlds.new("Mundo de prueba")
    sc.world.color = (0.1, 0.2, 0.3)

    def cielo(tema_id):
        return temas.color_rgba(temas.tema(tema_id)["colores"]["cielo"], lineal=True)[:3]

    def igual(a, b):
        return all(abs(x - y) < 1e-4 for x, y in zip(a, b))

    _limpiar()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(igual(sc.world.color, cielo("taller")), "abrir el tren pinta el cielo del taller")
    revisar(not bpy.data.objects, "el ambiente del tema no agrega objetos a la escena")
    foto = _motor.foto.scene_to_dict(practicas.capturar(sc))
    sc.world.color = (1.0, 0.0, 0.0)
    revisar(_motor.foto.scene_to_dict(practicas.capturar(sc)) == foto, "el color del mundo no entra en la foto del motor")
    practicas.activar(contexto, catalogo["blender.bpi.m3.pelota"]["definicion"], "paquete")
    revisar(igual(sc.world.color, cielo("circo")), "cambiar de práctica cambia el cielo (circo)")
    pal = hud.paleta(practicas.practica_activa(contexto))
    revisar(pal["tema"]["id"] == "circo" and pal["jefe"] is not None, "la pelota es la práctica del jefe final del circo")
    dibujar_todo(contexto)  # paneles, diálogos y HUD con el tema activo
    practicas.cerrar(contexto)
    revisar(igual(sc.world.color, (0.1, 0.2, 0.3)), "cerrar la práctica devuelve el cielo original")
    revisar(escenarios.CIELO_PREVIO not in sc, "no queda rastro del cielo previo en la escena")

    sc.world = None
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(sc.world is not None and sc.world.name == escenarios.NOMBRE_MUNDO, "sin mundo: Amatista crea uno con el cielo")
    practicas.cerrar(contexto)
    revisar(sc.world is None and escenarios.NOMBRE_MUNDO not in bpy.data.worlds, "al cerrar, el mundo creado se quita")
    dibujar_vista_3d(contexto)  # sin práctica: el HUD no dibuja nada y no falla
    _limpiar()


def main():
    print(f"Blender {bpy.app.version_string}")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    modulo = addon_utils.enable("amatista_blender", default_set=True, handle_error=None)
    revisar(modulo is not None, "el add-on se registra")
    from amatista_blender import _motor, ajustes, autor, practicas

    import shutil

    shutil.rmtree(ajustes.carpeta_usuario() / "practicas", ignore_errors=True)  # caché de corridas anteriores
    (ajustes.carpeta_usuario() / "avance.json").unlink(missing_ok=True)

    revisar(bpy.context.preferences.addons.get("amatista_blender") is not None, "preferencias disponibles")
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
    practicas.evaluar(contexto)
    g = guia.guia_actual()
    revisar(g.action.kind == "assign_role" and g.highlights[0].kind == "candidato", "guía: propone el cubo como cubierta")
    bpy.ops.amatista.hazlo_conmigo()
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
    revisar(practicas.datos_intento(contexto)["ayudas"]["hazlo_conmigo"] == 3, "el intento cuenta las ayudas")
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
    revisar(datos["version_addon"] == "3.3.0", "el intento lleva la versión 3.3 del add-on")

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
    contexto.window_manager.amatista.modo = "alumno"

    probar_v3(contexto)
    probar_temas(contexto)

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
