"""Prueba del add-on DENTRO de Blender (registro, escena real, Author y limpieza).

    blender --background --factory-startup --python addon/tests/en_blender.py
    # o con el módulo bpy de PyPI (Python 3.11):
    python addon/tests/en_blender.py

Sale con código 1 si algo falla. No necesita red: el servidor no se usa.
"""
import importlib
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


def probar_v3(contexto):
    """Motor v3: mapa del curso, escenas de inicio, píldoras, repaso, vigilantes y acciones nuevas."""
    from amatista_blender import aprendizaje, guia, practicas

    catalogo = practicas.catalogo()
    aprendizaje.ESTADO["avance"] = {"completadas": [], "pildoras_vistas": {}, "repaso": {}}
    revisar(aprendizaje.plan() is not None and len(aprendizaje.plan().courses) == 4, "mapa: 4 cursos")
    # Motor 5: cada módulo enseña en su taller y cierra con su proyecto (sin la exploración de antes).
    revisar(aprendizaje.siguiente() == "blender.bp.m1.tren", "mapa: el primer proyecto es el tren")
    revisar(aprendizaje.estados()["blender.bp.m2.espada"] == "bloqueado", "mapa: la espada empieza bloqueada")

    # Tren: la escena de inicio se vacía y la primera píldora es la de los ejes.
    _limpiar()
    _escena_nueva(contexto, "Inicio")
    _inicio_de_blender()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(contexto.scene.name == "Inicio" and not bpy.data.objects,
            "tren: en un Blender recién abierto se queda en su escena y quita el cubo, la luz y la cámara")
    principal = aprendizaje.pildora_principal()
    revisar(principal is not None, f"tren: hay teoría desde el inicio ({principal and principal.id})")
    g = guia.guia_actual()
    revisar(g.action is not None and g.action.kind in ("add_cube", "add_primitive"),
            f"tren: Hazlo conmigo agrega una pieza ({g.action})")
    revisar(bpy.ops.amatista.hazlo_conmigo() == {"FINISHED"} and len(contexto.scene.objects) == 1, "tren: se agrega la pieza")
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
    revisar(aprendizaje.estados()["blender.bp.m2.espada"] == "disponible", "mapa: terminar el tren abre la espada")

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
    sc = _escena_nueva(contexto, "Temas")
    sc.world = bpy.data.worlds.new("Mundo de prueba")
    sc.world.color = (0.1, 0.2, 0.3)
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(igual(sc.world.color, cielo("taller")), "abrir el tren pinta el cielo del taller")
    revisar(not bpy.data.objects, "el ambiente del tema no agrega objetos a la escena")
    foto = _motor.foto.scene_to_dict(practicas.capturar(sc))
    sc.world.color = (1.0, 0.0, 0.0)
    revisar(_motor.foto.scene_to_dict(practicas.capturar(sc)) == foto, "el color del mundo no entra en la foto del motor")
    sc.world.color = cielo("taller")
    practicas.activar(contexto, catalogo["blender.bpi.m3.pelota"]["definicion"], "paquete")
    revisar(contexto.scene.world is not None and igual(contexto.scene.world.color, cielo("circo")),
            "cambiar de práctica cambia el cielo (circo)")
    pal = hud.paleta(practicas.practica_activa(contexto))
    revisar(pal["tema"]["id"] == "circo" and pal["jefe"] is not None, "la pelota es la práctica del jefe final del circo")
    dibujar_todo(contexto)  # paneles, diálogos y HUD con el tema activo
    practicas.cerrar(contexto)
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(contexto.scene == sc, "volver al tren vuelve a su escena")
    practicas.cerrar(contexto)
    revisar(igual(sc.world.color, (0.1, 0.2, 0.3)), "cerrar la práctica devuelve el cielo original")
    revisar(escenarios.CIELO_PREVIO not in sc, "no queda rastro del cielo previo en la escena")

    sc.world = None
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(sc.world is not None and sc.world.name.startswith(escenarios.NOMBRE_MUNDO), "sin mundo: Amatista crea uno con el cielo")
    creado = sc.world.name if sc.world else ""
    practicas.cerrar(contexto)
    revisar(sc.world is None and creado not in bpy.data.worlds, "al cerrar, el mundo creado se quita")
    dibujar_vista_3d(contexto)  # sin práctica: el HUD no dibuja nada y no falla
    _limpiar()


def probar_motor_34(contexto):
    """Motor 3.4: modo enfocado, «Tus herramientas», enlace en vivo y figura sin roles."""
    from amatista_blender import _motor, ajustes, enfoque, enlace, guia, practicas
    from amatista_blender.interfaz import herramientas

    catalogo = practicas.catalogo()
    p = ajustes.prefs()
    p.enfoque = "auto"
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    vistas = [a for v in contexto.window_manager.windows for a in v.screen.areas if a.type == "VIEW_3D"]
    revisar(enfoque.activo(), "nivel 1: Blender se enfoca al abrir la práctica")
    revisar(getattr(bpy.types.VIEW3D_MT_add.draw, "_amatista", False), "enfoque: Shift+A muestra solo las piezas del modelo")
    revisar(enfoque.ESTADO["primitivas"] == ("cube", "cylinder"), f"enfoque: piezas del tren {enfoque.ESTADO['primitivas']}")
    if vistas:
        espacio = vistas[0].spaces.active
        revisar(not espacio.show_region_toolbar and espacio.show_region_ui, "enfoque: sin barra T, con la barra lateral")
    menu = type("Menu", (), {"layout": Diseno()})()
    bpy.types.VIEW3D_MT_add.draw(menu, contexto)
    bpy.types.VIEW3D_MT_editor_menus.draw(menu, contexto)

    todas, del_paso = herramientas.actuales(practicas.practica_activa(contexto))
    revisar([t.id for t in todas][:3] == ["view.navigate", "view.numpad", "object.add"],
            f"Tus herramientas: las de la práctica ({[t.id for t in todas]})")
    revisar("object.add" in [t.id for t in del_paso], f"Tus herramientas: Agregar es la del primer paso ({[t.id for t in del_paso]})")
    revisar(bpy.ops.amatista.usar_herramienta(herramienta="object.add") == {"FINISHED"}, "«Usar» Agregar no falla sin ventana")
    bpy.ops.mesh.primitive_cube_add()
    revisar(bpy.ops.amatista.usar_herramienta(herramienta="transform.scale") == {"FINISHED"}
            and getattr(contexto.workspace.tools.from_space_view3d_mode("OBJECT"), "idname", "") == "builtin.scale",
            "«Usar» Escalar elige la herramienta Escalar")
    ayuda = type("Ayuda", (), {"layout": Diseno(), "herramienta": "transform.move"})()
    herramientas.AMATISTA_OT_herramienta_ayuda.draw(ayuda, contexto)

    # Órdenes de la plataforma (llegan en el latido) y ajustes de «Mi Blender».
    revisar(enlace.cumplir({"id": "orden1", "tipo": "ver_todo"}) and not enfoque.activo(), "orden «ver todo» de la plataforma")
    if vistas:
        revisar(vistas[0].spaces.active.show_region_toolbar, "ver todo: la barra T vuelve como estaba")
    revisar(not getattr(bpy.types.VIEW3D_MT_add.draw, "_amatista", False), "ver todo: Shift+A completo otra vez")
    revisar(enlace.ESTADO["hecha"] == "orden1" and not enlace.cumplir({"id": "orden1", "tipo": "ver_todo"}),
            "una orden repetida se cumple una sola vez")
    enlace.cumplir({"id": "orden2", "tipo": "enfocar"})
    revisar(enfoque.activo(), "orden «enfocar» de la plataforma")
    datos = enlace._datos()
    revisar(datos["practica_id"] == "blender.bp.m1.tren" and datos["enfocado"] and datos["orden_hecha"] == "orden2",
            f"el latido lleva práctica, enfoque y la orden cumplida ({datos})")
    revisar(enlace.aplicar_ajustes({"enfoque": "nunca", "tarjeta_3d": False, "acompanamiento": "tarjeta"})
            and p.enfoque == "nunca" and not p.mostrar_hud and not enfoque.activo(),
            "los ajustes de «Mi Blender» mandan: enfoque nunca y sin tarjeta 3D")
    enlace.aplicar_ajustes({"enfoque": "auto", "tarjeta_3d": True, "acompanamiento": "acompanado", "otro": 1})
    revisar(enfoque.activo(), "volver a «según el nivel» enfoca otra vez")

    # La figura sin roles: Amatista reconoce las piezas por su forma.
    _limpiar()
    practica = practicas.practica_activa(contexto)
    for parte in practica.reference.compared:
        operador = getattr(bpy.ops.mesh, f"primitive_{parte.primitive}_add")
        operador(location=parte.location, rotation=[r * 3.14159265 / 180 for r in parte.rotation])
        obj = contexto.active_object
        obj.dimensions = parte.size
        obj.name = parte.name or parte.primitive
    bpy.ops.object.select_all(action="DESELECT")
    reporte = practicas.evaluar(contexto)
    figura = reporte.result("figura")
    revisar(figura.passed, f"el tren sin roles se reconoce ({figura.message})")
    revisar(len(dict(reporte.inferred_roles)) == len(practica.reference.compared), "todas las piezas reconocidas por su forma")
    practicas.cerrar(contexto)
    revisar(not enfoque.activo(), "cerrar la práctica devuelve Blender completo")
    _ = (_motor, guia)


def probar_motor_4(contexto):
    """Motor 4: la ruta de misiones, una tarjeta, teclas que se encienden y herramientas iluminadas."""
    from amatista_blender import ajustes, enlace, mision, practicas
    from amatista_blender.interfaz import dialogos, paneles

    catalogo = practicas.catalogo()
    p = ajustes.prefs()
    revisar(p.animaciones and p.preparar_herramienta and not p.dialogo_por_mision,
            "preferencias del motor 4: animaciones y herramienta lista, sin diálogo por paso")
    _limpiar()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    ruta = mision.ruta()
    revisar(ruta is not None and ruta.practica_id == "blender.bp.m1.tren", "al abrir la práctica hay ruta")
    revisar(ruta.mision.id == "vagones" and ruta.mision.numero == 1, f"misión 1: dos vagones ({ruta.mision.id})")
    revisar([x.titulo for x in ruta.partes] == ["La locomotora y el vagón", "Las ruedas", "Arma el tren",
                                                 "Revisa y guarda"], f"las partes del tren ({[x.titulo for x in ruta.partes]})")
    revisar("object.add" in ruta.mision.herramientas, "la misión 1 ilumina «Añadir objeto»")
    paso = next((x for x in ruta.mision.pasos if x.keys), None)
    revisar(paso is not None and not mision.paso_hecho(paso), "la tecla de la misión empieza apagada")
    revisar(bpy.ops.amatista.usar_herramienta(herramienta="object.add") == {"FINISHED"}, "«Usar» Añadir objeto")
    revisar(mision.paso_hecho(paso) and mision.estado_herramienta("object.add") == "usada",
            "usar la herramienta enciende su tecla en la tarjeta")
    revisar(mision.estado_herramienta("transform.rotate") == "despues", "Rotar se marca para después")
    dibujar_todo(contexto)  # tarjeta de la misión, «Tu ruta», «Más» y «Tu misión» con la ruta lista
    menu = type("Dialogo", (), {"layout": Diseno()})()
    dialogos.AMATISTA_OT_mision_inicio.draw(menu, contexto)
    paneles.dibujar_ruta(Diseno(), ruta)

    for nombre, x in (("Locomotora", 1.2), ("Vagon", -1.2)):
        cubo(nombre, (x, 0, 0.6), (1.1, 0.6, 0.5))
    reporte = practicas.evaluar(contexto)
    ruta = mision.ruta()
    revisar(reporte.result("vagones").passed and ruta.mision.id != "vagones", f"avanza a la misión 2 ({ruta.mision.id})")
    revisar(ruta.misiones[0].estado == "hecha" and ruta.hechas >= 1, "la misión 1 queda hecha")
    revisar(mision.ESTADO["logro"] is not None and mision.ESTADO["logro"]["numero"] == 1,
            f"la misión cumplida se celebra ({mision.ESTADO['logro']})")
    revisar(not mision.ESTADO["usadas"], "la misión nueva empieza con sus teclas apagadas")
    dibujar_vista_3d(contexto)  # con el sello «¡Misión cumplida!» y las chispas
    escalar = next((m for m in ruta.misiones if "transform.scale" in m.herramientas), None)
    revisar(escalar is not None and mision.herramienta_de_barra(escalar, "OBJECT").id == "transform.scale",
            "una misión de escalar deja lista la herramienta Escalar en la barra T")
    detalle = enlace.detalle_vivo()
    revisar(detalle["numero"] == ruta.mision.numero and detalle["total"] == ruta.total
            and detalle["titulo"] == ruta.mision.titulo, f"la plataforma ve la misma misión ({detalle['titulo']})")
    practicas.cerrar(contexto)


def probar_escena_por_practica(contexto):
    """Add-on 3.5: abrir otra práctica no arrastra lo de la anterior (cada una tiene su escena)."""
    from amatista_blender import practicas

    catalogo = practicas.catalogo()
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    escena_tren = contexto.scene
    bpy.ops.mesh.primitive_cube_add(size=1)
    contexto.active_object.name = "Locomotora"
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    revisar(contexto.scene != escena_tren, "abrir otra práctica cambia de escena")
    revisar("Locomotora" not in contexto.scene.objects,
            f"la espada empieza sin lo del tren ({[o.name for o in contexto.scene.objects]})")
    revisar(contexto.scene.amatista.practica_id == "blender.bp.m2.espada", "la escena nueva es la de la espada")
    revisar("Locomotora" in escena_tren.objects, "lo del tren sigue en su escena (nada se borra)")
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(contexto.scene == escena_tren and "Locomotora" in contexto.scene.objects,
            "volver al tren devuelve su escena con lo que hiciste")
    practicas.cerrar(contexto)
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    revisar("Locomotora" not in contexto.scene.objects, "aunque cierres el tren, la espada no lo hereda")
    practicas.cerrar(contexto)


def probar_motor_35(contexto):
    """Motor 3.5: la espada se reconoce por su silueta y el instructor dice qué parte falta."""
    from amatista_blender import _motor, ajustes, practicas
    from amatista_blender.interfaz import paneles

    silueta = importlib.import_module(_motor.engine.__name__ + ".figures.silueta")
    catalogo = practicas.catalogo()
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    practica = practicas.practica_activa(contexto)
    for obj in list(contexto.scene.objects):
        bpy.data.objects.remove(obj)

    def malla(nombre, piezas):
        verts, aristas = [], []
        for p in piezas:
            puntos, lineas = silueta.malla_de_pieza(p.primitive, p.size, p.location, p.rotation, p.segments)
            base = len(verts)
            verts.extend(puntos)
            aristas.extend((base + i, base + j) for i, j in lineas)
        datos = bpy.data.meshes.new(nombre)
        datos.from_pydata(verts, aristas, [])
        obj = bpy.data.objects.new(nombre, datos)
        contexto.scene.collection.objects.link(obj)
        return obj

    barra = malla("Espada", [p for p in practica.reference.compared if p.name != "Guarda"])
    foto = _motor.adapter.capture_scene(contexto.scene)
    revisar(foto.objects[0].silhouette is not None and foto.objects[0].silhouette.eje == 2,
            "la foto lleva la silueta de la malla (a lo largo de Z)")
    reporte = practicas.evaluar(contexto)
    figura = reporte.result("silueta")
    revisar(not figura.passed and "Guarda" in figura.message, f"sin guarda, el instructor la pide ({figura.message})")
    titulo, lista = practicas.lista_instructor(reporte)
    revisar(titulo and any(i["texto"] == "Guarda" and not i["ok"] for i in lista), f"la lista «Tu figura» marca la guarda ({lista})")
    # Add-on 5: la espada es el proyecto de un taller; el alumno ve la tarjeta del taller y no las pestañas viejas.
    revisar(not paneles.AMATISTA_PT_figura.poll(contexto), "en el proyecto del taller no aparecen las pestañas viejas")
    p = ajustes.prefs()
    wm = contexto.window_manager.amatista
    antes = (p.modo_desarrollador, wm.modo, wm.vista_previa, wm.pestana)
    p.modo_desarrollador, wm.modo, wm.vista_previa, wm.pestana = True, "autor", True, "practicar"
    revisar(paneles.AMATISTA_PT_figura.poll(contexto), "en la vista previa del autor «Tu figura» sigue en Practicar")
    p.modo_desarrollador, wm.modo, wm.vista_previa, wm.pestana = antes
    bpy.data.objects.remove(barra)
    espada = malla("Espada", practica.reference.compared)
    contexto.view_layer.objects.active = espada
    reporte = practicas.evaluar(contexto)
    revisar(reporte.result("silueta").passed, f"la espada completa se reconoce ({reporte.result('silueta').message})")
    bpy.ops.object.mode_set(mode="EDIT")
    foto = _motor.adapter.capture_scene(contexto.scene)
    revisar(foto.objects[0].silhouette is not None, "en Modo Edición también se mide la silueta (bmesh)")
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")  # desde Modo Edición
    revisar(contexto.mode == "OBJECT", "cambiar de práctica en Modo Edición vuelve antes a Modo Objeto")
    revisar(all("si" not in o for o in practicas.datos_intento(contexto)["escena"]["objetos"]),
            "el intento del tren no manda siluetas (el tren no las usa)")
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    revisar(any("si" in o for o in practicas.datos_intento(contexto)["escena"]["objetos"]),
            "el intento de la espada sí manda la silueta")
    import dataclasses
    espada = practicas.practica_activa(contexto)
    solo_ejemplo = dataclasses.replace(espada, targets=tuple(t for t in espada.targets if t.validator != "figure.silhouette"))
    revisar(any("si" in o for o in practicas._foto_para_enviar(contexto.scene, solo_ejemplo)["objetos"]),
            "example.matches conserva la silueta incluso sin un objetivo figure.silhouette")
    datos = json.loads(json.dumps(_motor.foto.scene_to_dict(foto)))
    llegada, enviada = _motor.foto.scene_from_dict(datos).objects[0].silhouette, foto.objects[0].silhouette
    revisar(llegada.eje == enviada.eje and all(abs(a - b) < 1e-3 for x, y in zip(llegada.anchos, enviada.anchos)
                                               for a, b in zip(x, y)), "la silueta viaja igual al servidor")
    # La plataforma maneja la práctica: el latido lleva al instructor y las órdenes se cumplen.
    from amatista_blender import enlace

    detalle = enlace._datos().get("detalle") or {}
    revisar(detalle.get("figura") and len(detalle.get("lista", [])) >= 5 and detalle.get("modo") == "OBJECT",
            f"el latido lleva el paso, el mensaje y la lista de la figura ({detalle})")
    revisar(enlace.cumplir({"id": "o35a", "tipo": "comprobar", "datos": {"practica_id": "blender.bp.m2.espada"}}),
            "orden «comprobar» desde la plataforma")
    pistas_antes = sum(practicas.pistas(contexto).values())
    enlace.cumplir({"id": "o35b", "tipo": "pista", "datos": {"practica_id": "blender.bp.m2.espada"}})
    revisar(sum(practicas.pistas(contexto).values()) == pistas_antes + 1, "orden «pista»: se revela la siguiente")
    revisar(not enlace.cumplir({"id": "o35c", "tipo": "pista", "datos": {"practica_id": "blender.bp.m1.tren"}}),
            "una orden para otra práctica no se aplica a la abierta")
    revisar(practicas.nombre_para_guardar(practica) == "mi_espada.blend", "guardar desde la plataforma usa mi_espada.blend")
    escena_antes = contexto.scene
    enlace.cumplir({"id": "o35d", "tipo": "reiniciar", "datos": {"practica_id": "blender.bp.m2.espada"}})
    revisar(contexto.scene != escena_antes and not contexto.scene.objects
            and contexto.scene.amatista.practica_id == "blender.bp.m2.espada",
            "«empezar de nuevo»: escena limpia con la misma práctica")
    revisar("Espada" in escena_antes.objects and escena_antes.name.endswith("(anterior)"),
            "lo anterior no se borra: queda en la escena «(anterior)»")
    enlace.cumplir({"id": "o35e", "tipo": "hazlo_conmigo", "datos": {"practica_id": "blender.bp.m2.espada"}})
    revisar(len(contexto.scene.objects) == 1 and contexto.scene.objects[0].type == "MESH",
            "«Hazlo conmigo» desde la plataforma agrega el cubo del primer paso")
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    practicas.activar(contexto, catalogo["blender.bp.m2.espada"]["definicion"], "paquete")
    revisar(contexto.scene != escena_antes, "volver a la espada abre la escena nueva, no la anterior")
    dibujar_todo(contexto)
    practicas.cerrar(contexto)


def probar_ejemplo(contexto):
    """Motor 3.5: «Ver el ejemplo» arma el ejemplo resuelto en su escena y el motor lo reconoce."""
    import dataclasses

    from amatista_blender import _motor, ejemplo, enlace, practicas

    coincide = importlib.import_module(_motor.engine.__name__ + ".validators.example").matches
    catalogo = practicas.catalogo()
    casos = (
        ("blender.bp.m2.espada", ["figura"]), ("blender.bp.m1.tren", ["figura"]),
        ("blender.bpi.m3.pelota", ["animacion"]), ("blender.bpi.m2.tres-puntos", ["luces", "camara"]),
        ("blender.bi.m2.aldea", ["figura", "materiales", "colecciones"]), ("blender.bp.m3.nave", ["modificadores"]),
        ("blender.bpi.m1.pinta-nave", ["materiales"]), ("blender.bi.m1.puente", ["figura", "modificadores"]),
    )
    for practica_id, aspectos in casos:
        _escena_nueva(contexto, f"Mia {practica_id}")
        practicas.activar(contexto, catalogo[practica_id]["definicion"], "paquete")
        mia = bpy.context.scene
        practica = practicas.practica_activa(contexto)
        revisar(ejemplo.instrucciones(practica), f"{practica_id}: el ejemplo se lee paso a paso")
        texto = ejemplo.ver_ejemplo(contexto)
        sc = bpy.context.scene
        revisar(sc != mia and ejemplo.es_ejemplo(sc) and len(sc.objects) > 0,
                f"{practica_id}: «Ver el ejemplo» lo arma en su propia escena ({texto})")
        revisar(practicas.practica_activa(bpy.context) is None, f"{practica_id}: el motor no revisa la escena del ejemplo")
        objetivo = practica.targets[-1]
        r = coincide(dataclasses.replace(objetivo, params={**objetivo.params, "aspects": aspectos}),
                     ejemplo.capturar(sc))
        revisar(r.passed, f"{practica_id}: el ejemplo armado en Blender coincide en {aspectos} ({r.message})")
        enviada = _motor.foto.scene_from_dict(practicas._foto_para_enviar(sc, practica))
        revisada = coincide(dataclasses.replace(objetivo, params={**objetivo.params, "aspects": aspectos}), enviada)
        revisar(revisada.passed, f"{practica_id}: la foto enviada conserva la evidencia del ejemplo")
        datos = enlace._datos()
        revisar(datos.get("practica_id") == practica_id and (datos.get("detalle") or {}).get("modo") == "EJEMPLO",
                f"{practica_id}: el latido dice que Blender muestra el ejemplo ({datos})")
        revisar(ejemplo.volver(contexto) and bpy.context.scene == mia, f"{practica_id}: «Volver a mi práctica»")
    ejemplo.ver_ejemplo(contexto)
    revisar(sum(1 for s in bpy.data.scenes if s.get(ejemplo.EJEMPLO) == f"{practica.id}@{practica.version}") == 1,
            "ver el ejemplo otra vez no lo arma dos veces")
    del_ejemplo = bpy.context.scene
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    revisar(bpy.context.scene != del_ejemplo and not ejemplo.es_ejemplo(bpy.context.scene),
            "abrir otra práctica desde el ejemplo no la carga en la escena del ejemplo")
    revisar(enlace.cumplir({"id": "o35ej", "tipo": "ver_ejemplo", "datos": {}}) and ejemplo.es_ejemplo(bpy.context.scene),
            "la plataforma abre el ejemplo en Blender (orden «ver_ejemplo»)")
    revisar(enlace.cumplir({"id": "o35vu", "tipo": "volver_practica", "datos": {}})
            and bpy.context.scene.amatista.practica_id == "blender.bp.m1.tren", "y vuelve a la práctica")
    dibujar_todo(contexto)
    practicas.cerrar(contexto)


def _aldea_del_alumno(contexto):
    """Tres casas en la colección «Casas» y tres techos en «Techos», hechas por el alumno en su escena."""
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


def probar_auditoria(contexto):
    """Arreglos de la auditoría del add-on 3.5 (ejemplo, escenas por práctica, órdenes y latido)."""
    import dataclasses

    from amatista_blender import _motor, ejemplo, enlace, escenarios, guia, practicas

    coincide = importlib.import_module(_motor.engine.__name__ + ".validators.example").matches
    catalogo = practicas.catalogo()
    aldea = catalogo["blender.bi.m2.aldea"]["definicion"]

    # 1. El ejemplo primero y luego el alumno: sus colecciones conservan el nombre que pide el paso.
    _escena_nueva(contexto, "Aldea A")
    practicas.activar(contexto, aldea, "paquete")
    mia = bpy.context.scene
    ejemplo.ver_ejemplo(contexto)
    del_ejemplo = bpy.context.scene
    nombres = {c.name for c in del_ejemplo.collection.children}
    revisar(nombres and all(n.startswith(ejemplo.PREFIJO) for n in nombres)
            and all(o.name.startswith(ejemplo.PREFIJO) for o in del_ejemplo.objects),
            f"las colecciones y objetos del ejemplo llevan su prefijo ({sorted(nombres)})")
    revisar("Ya estás viendo" in ejemplo.ver_ejemplo(contexto), "«Ver el ejemplo» desde el ejemplo dice que ya lo ves")
    objetivo = practicas.ESTADO["practica"].targets[-1]
    r = coincide(dataclasses.replace(objetivo, params={**objetivo.params, "aspects": ["colecciones"]}),
                 ejemplo.capturar(del_ejemplo))
    revisar(r.passed, f"el ejemplo de la aldea sigue coincidiendo en colecciones ({r.message})")
    malla = next(o for o in del_ejemplo.objects if o.type == "MESH")
    contexto.view_layer.objects.active = malla
    bpy.ops.object.mode_set(mode="EDIT")
    revisar(ejemplo.volver(contexto) and bpy.context.scene == mia, "volver desde Modo Edición")
    revisar(malla.mode == "OBJECT", "la malla del ejemplo no se queda en Modo Edición al volver")
    cols = _aldea_del_alumno(bpy.context)
    reporte = practicas.evaluar(bpy.context)
    revisar(cols["Casas"].name == "Casas" and reporte.result("en-coleccion").passed
            and reporte.result("techos-coleccion").passed,
            f"ejemplo antes: «Casas» y «Techos» del alumno pasan ({reporte.result('en-coleccion').message})")
    practicas.cerrar(bpy.context)
    for col in cols.values():
        for obj in list(col.objects):
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(col)

    # 2. El alumno primero y luego el ejemplo (en otro archivo de la misma sesión: el ejemplo se arma de nuevo).
    for sc in [s for s in bpy.data.scenes if ejemplo.es_ejemplo(s)]:
        bpy.data.scenes.remove(sc)
    _escena_nueva(contexto, "Aldea B")
    practicas.activar(contexto, aldea, "paquete")
    mia = bpy.context.scene
    cols = _aldea_del_alumno(bpy.context)
    ejemplo.ver_ejemplo(contexto)
    r = coincide(dataclasses.replace(objetivo, params={**objetivo.params, "aspects": ["figura", "colecciones"]}),
                 ejemplo.capturar(bpy.context.scene))
    revisar(r.passed, f"alumno antes: el ejemplo se arma y coincide ({r.message})")
    # Mirando el ejemplo el latido sigue llevando el avance de la práctica.
    datos = enlace._datos()
    revisar(datos.get("progreso") is not None and datos.get("practica_id") == "blender.bi.m2.aldea",
            f"el latido lleva el progreso mientras se mira el ejemplo ({datos.get('progreso')})")
    practicas.evaluar(bpy.context, "cambio")  # el vigilante no borra el reporte de la práctica
    revisar(practicas.ESTADO["reporte"] is not None, "evaluar en la escena del ejemplo no borra el reporte")
    ejemplo.volver(contexto)
    reporte = practicas.evaluar(bpy.context)
    revisar(cols["Casas"].name == "Casas" and reporte.result("en-coleccion").passed,
            "alumno antes: sus colecciones siguen limpias")
    # Una orden «ver_ejemplo» de otra práctica no abre el de la abierta.
    revisar(not enlace.cumplir({"id": "aud1", "tipo": "ver_ejemplo", "datos": {"practica_id": "blender.bp.m1.tren"}})
            and bpy.context.scene == mia, "una orden «ver_ejemplo» de otra práctica no se aplica")
    # Abrir otra práctica desde el ejemplo: los avisos se ven y no muestran ids internos.
    ejemplo.ver_ejemplo(contexto)
    practicas.activar(bpy.context, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    textos = " ".join(a["titulo"] + " " + a["texto"] for a in guia.ESTADO["avisos"])
    revisar("Práctica nueva, escena nueva" in textos and "#" not in textos and "blender.bi" not in textos,
            f"los avisos al abrir se ven y no muestran ids internos ({textos})")
    practicas.cerrar(bpy.context)

    # 3. El estudio de foto usa la Nave de SU escena, no la de otra práctica.
    for sc in [s for s in bpy.data.scenes if practicas._practica_de_escena(s).startswith("blender.bpi.m2.tres-puntos")]:
        bpy.data.scenes.remove(sc)  # que tres puntos arme su estudio desde cero
    _escena_nueva(contexto, "Nave mia")
    nave = escenarios.nave_basica(bpy.context.scene)
    _motor.tagger.assign_role(nave, "nave")
    practicas.activar(contexto, catalogo["blender.bp.m1.tren"]["definicion"], "paquete")
    practicas.activar(bpy.context, catalogo["blender.bpi.m2.tres-puntos"]["definicion"], "paquete")
    estudio = bpy.context.scene
    revisar(any(o.type == "MESH" and _motor.tagger.get_role(o) == "modelo" for o in estudio.objects),
            f"tres puntos arma su propia nave ({[o.name for o in estudio.objects]})")
    revisar(_motor.tagger.get_role(nave) == "nave", "la nave de la otra escena no cambia de rol")
    practicas.cerrar(bpy.context)


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


def probar_taller(contexto):
    """Add-on 5 (Amatista Taller): habilidad por habilidad, molde, tarjeta, enlace, proyecto e isla."""
    from amatista_blender import enlace, practicas
    from amatista_blender.interfaz import hud, paneles
    from amatista_blender.taller import datos, demo, isla, operadores, panel, sesion
    from amatista_blender.taller.vista import tarjeta

    from amatista_blender import aprendizaje, ajustes

    taller = sesion.taller
    sesion.terminar()
    aprendizaje.ESTADO["avance"] = {"completadas": [], "pildoras_vistas": {}, "repaso": {}}  # alumno nuevo
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    datos.reiniciar_cache()
    revisar(datos.catalogo() is not None and datos.catalogo().taller("blender.bp.m1") is not None,
            f"taller: el catálogo de habilidades se carga ({datos.ESTADO['catalogo_error']})")
    revisar(datos.taller_inicial() == "blender.bp.m1", "taller: se empieza por el módulo 1 de Principiante")
    contexto.window_manager.amatista.modo = "alumno"

    # Mira: la demostración corre en la vista 3D con objetos temporales y no cuenta como trabajo del alumno.
    revisar(bpy.ops.amatista.taller_abrir(taller="blender.bp.m1") == {"FINISHED"}, "taller: «Empezar el taller»")
    a = sesion.actividad()
    revisar(a is not None and a.tipo == taller.MIRA and sesion.estado() == sesion.MIRANDO and demo.activa(),
            f"taller: la primera actividad es «Mira» ({a and a.id})")
    revisar(contexto.scene.get("amatista_taller") and sesion.cubre(contexto.scene),
            "taller: las actividades cortas pasan en la escena «Amatista · Taller»")
    revisar([b[1] for b in tarjeta.botones()] == ["repetir_demo", "ahora_tu"], f"taller: Mira ofrece Repetir y Ahora tú ({tarjeta.botones()})")
    revisar(hud.del_taller(contexto.scene), "taller: la tarjeta de la versión 4 le deja el lugar a la del taller")
    for clase in panel.CLASES:
        clase.draw(_Envoltura(clase, 0), contexto)
    revisar(operadores.ejecutar(contexto, "ahora_tu") is None, "taller: «Ahora tú» termina la demostración")
    revisar(not demo.activa() and not [o for o in contexto.scene.objects if o.get("amatista_demo")],
            "taller: la demostración no deja objetos")

    # Hazlo conmigo: el molde dice dónde va cada pieza; armarla bien la logra y la cuenta en el modelo del alumno.
    a = sesion.actividad()
    revisar(a.tipo == taller.CONMIGO and a.dibujo == "molde" and sesion.molde_visible() is not None,
            f"taller: después de Mira sigue «Hazlo conmigo» con molde ({a.id})")
    revisar(sesion.SESION["revision"] is not None and sesion.SESION["revision"].llenas == 0,
            "taller: con la escena vacía el molde está vacío")
    revisar(sesion.siguiente_pista()[0] == "Qué falta", f"taller: la primera pista es «Qué falta» ({sesion.siguiente_pista()})")
    pista = sesion.pedir_pista(contexto)
    revisar(pista is not None and pista.nivel == taller.QUE and sesion.SESION["ayuda"] == taller.QUE,
            "taller: pedir pista sube un escalón")
    _armar(contexto, a.piezas)
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA, f"taller: armar la pieza logra la actividad ({sesion.SESION['revision'].mensaje})")
    revisar([b[1] for b in tarjeta.botones()] == ["siguiente", "otra_vez"], "taller: el logro ofrece Siguiente y Otra vez")
    cola = datos.avance()["cola"]
    revisar(len(cola) == 2 and cola[0]["tipo"] == "mira" and cola[1]["correcto"] and cola[1]["ayuda"] == 1
            and cola[1]["molde"] and cola[1].get("escena"), f"taller: los intentos esperan en la cola ({len(cola)})")
    revisar(cola[1]["en"] >= cola[0]["en"], "taller: cada intento lleva su hora (el servidor no los repite)")
    latido = enlace._datos()
    revisar(latido["practica_id"].startswith("taller.") and latido["progreso"] == 100
            and latido["detalle"]["taller"]["actividad"]["tipo"] == taller.CONMIGO,
            f"taller: el latido lleva la actividad ({latido.get('practica_id')})")
    revisar(len(latido["detalle"]["taller"]["habilidades"]) == 6, "taller: la plataforma ve las 6 habilidades")

    # Órdenes de la plataforma.
    revisar(enlace.cumplir({"id": "t-1", "tipo": "taller_continuar"}) and sesion.estado() == sesion.TRABAJANDO,
            "taller: «Continuar» desde la plataforma abre la siguiente actividad")
    revisar(enlace.cumplir({"id": "t-2", "tipo": "taller_pausa"}) and sesion.estado() == sesion.PAUSA,
            "taller: «Pausa» desde la plataforma")
    revisar([b[1] for b in tarjeta.botones()] == ["seguir"], "taller: en pausa la tarjeta solo ofrece Seguir")
    revisar(enlace.cumplir({"id": "t-3", "tipo": "taller_continuar"}) and sesion.estado() == sesion.TRABAJANDO,
            "taller: «Seguir» desde la plataforma")
    revisar(not enlace.cumplir({"id": "t-3", "tipo": "taller_continuar"}), "taller: una orden repetida no se cumple dos veces")

    # Saltar dos veces la misma habilidad pasa a otra (nadie se queda atorado).
    h = sesion.actividad().habilidad
    sesion.saltar(contexto)
    sesion.saltar(contexto)
    revisar(sesion.actividad().habilidad != h, f"taller: saltar dos veces pasa a otra habilidad ({sesion.actividad().id})")

    # Recorrer el taller como un alumno que acierta: cada habilidad, luego el proyecto.
    for _vuelta in range(60):
        a = sesion.actividad()
        if a is None or sesion.SESION["proyecto"] or a.tipo == taller.RETO:
            break
        if sesion.estado() == sesion.MIRANDO:
            operadores.ejecutar(contexto, "ahora_tu")
            continue
        if a.piezas:
            _armar(contexto, a.piezas)
        else:
            bpy.ops.wm.save_as_mainfile(filepath=str(Path(tempfile.mkdtemp()) / "mi_taller.blend"))
        sesion.evaluar(contexto)
        if sesion.estado() != sesion.LOGRADA:
            revisar(False, f"taller: «{a.id}» no se logró armando su molde ({sesion.SESION['revision'] and sesion.SESION['revision'].mensaje})")
            sesion.saltar(contexto)
            continue
        sesion.siguiente(contexto)
    a = sesion.actividad()
    plan = datos.plan("blender.bp.m1")
    revisar(a is not None and a.tipo == taller.PROYECTO and plan.proyecto_abierto,
            f"taller: con las habilidades listas se abre el proyecto ({a and a.id})")
    sc = contexto.scene
    revisar(sc.amatista.practica_id == "blender.bp.m1.tren" and not sc.get("amatista_taller") and sesion.cubre(sc),
            f"taller: el proyecto tiene su propia escena ({sc.name})")
    revisar(sesion.SESION["molde_proyecto"] and "saltar" not in [b[1] for b in tarjeta.botones()],
            "taller: el proyecto de nivel 1 trae molde y no se salta")
    dibujar_todo(contexto)

    practica = practicas.practica_activa(contexto)
    for obj in list(sc.objects):
        bpy.data.objects.remove(obj)
    _armar(contexto, [{"primitive": p.primitive, "size": list(p.size), "location": list(p.location),
                       "rotation": list(p.rotation), "name": p.name} for p in practica.reference.compared])
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(tempfile.mkdtemp()) / "mi_tren.blend"))
    reporte = practicas.evaluar(contexto)
    revisar(reporte.completed and sesion.estado() == sesion.LOGRADA, f"taller: el tren armado logra el proyecto ({reporte.progress})")
    revisar("blender.bp.m1" in isla.piezas_guardadas(), "taller: el tren queda como pieza de la isla")
    revisar([b[1] for b in tarjeta.botones()] == ["siguiente", "isla"], "taller: el logro del proyecto ofrece «Ver mi isla»")
    revisar(datos.plan("blender.bp.m1").completo, "taller: el módulo queda completo")
    revisar(isla.abrir(contexto).startswith("Tu isla tiene") and contexto.scene.get(isla.MARCA),
            "taller: «Mi isla» arma la escena con la pieza")
    revisar(not paneles.secciones_v4(contexto), "taller: el alumno no ve las pestañas de la versión 4")
    probar_talleres_nuevos(contexto)
    sesion.terminar()
    practicas.cerrar(contexto)


def _abrir_actividad(contexto, taller_id, actividad_id):
    from amatista_blender.taller import sesion

    texto = sesion.abrir(contexto, taller_id, actividad_id)
    a = sesion.actividad()
    revisar(a is not None and a.id == actividad_id and sesion.estado() == sesion.TRABAJANDO,
            f"talleres: se abre «{actividad_id}» ({texto or ''})")
    return bpy.context


def _elegir(contexto, obj):
    for otro in contexto.scene.objects:
        otro.select_set(False)
    obj.select_set(True)
    contexto.view_layer.objects.active = obj


def probar_talleres_nuevos(contexto):
    """Módulos 2 a 9: las escenas de inicio raras (puntos encimados, escala sin aplicar, media nave) en Blender real."""
    from amatista_blender.taller import sesion

    # Malla limpia: la caja empieza con puntos encimados y «M › Por distancia» la logra.
    contexto = _abrir_actividad(contexto, "blender.bp.m2", "conmigo:bl-malla-limpia:encimados")
    caja = contexto.scene.objects["Caja"]
    revisar(len(caja.data.vertices) == 16, f"talleres: la caja de inicio trae sus puntos repetidos ({len(caja.data.vertices)})")
    revisar(sesion.estado() == sesion.TRABAJANDO, "talleres: la caja sucia no está lograda al empezar")
    _elegir(contexto, caja)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.mode_set(mode="OBJECT")
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA, f"talleres: M › Por distancia la deja limpia ({len(caja.data.vertices)} puntos)")

    # Aplicar la escala: la tabla empieza estirada con S; Ctrl + A › Escala la logra sin cambiar su forma.
    contexto = _abrir_actividad(contexto, "blender.bp.m3", "conmigo:bl-aplicar-escala:tabla")
    tabla = contexto.scene.objects["Tabla"]
    revisar(tuple(round(v, 2) for v in tabla.scale) == (4.0, 1.0, 0.5), f"talleres: la tabla empieza con escala ({tuple(tabla.scale)})")
    _elegir(contexto, tabla)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA and tuple(round(v, 2) for v in tabla.dimensions) == (4.0, 1.0, 0.5),
            "talleres: Ctrl + A › Escala logra la actividad y la tabla mide lo mismo")

    # Espejo: el ala empieza con su origen en el centro de la nave; el modificador dibuja la otra.
    contexto = _abrir_actividad(contexto, "blender.bp.m3", "conmigo:bl-espejo:ala")
    ala = contexto.scene.objects["Ala"]
    revisar(tuple(round(v, 2) for v in ala.location) == (0.0, 0.0, 1.0) and min(v.co.x for v in ala.data.vertices) > 0,
            "talleres: el ala tiene su origen en el centro y la malla a un lado")
    ala.modifiers.new("Espejo", "MIRROR")
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA, "talleres: con Espejo en X se logra")

    # Render: la escena trae luz y cámara; solo falta F12 (aquí se cuenta como lo cuenta el add-on).
    contexto = _abrir_actividad(contexto, "blender.bpi.m2", "conmigo:bl-render:foto")
    sc = contexto.scene
    revisar(sc.camera is not None and any(o.type == "LIGHT" for o in sc.objects),
            "talleres: la actividad de render empieza con luz y cámara")
    sc["amatista_renders"] = int(sc.get("amatista_renders", 0)) + 1
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA, "talleres: después del render se logra")
    sesion.siguiente(contexto)
    revisar(not [o for o in sc.objects if o.type in ("LIGHT", "CAMERA") and o.get("amatista_taller")]
            or sesion.actividad().inicio, "talleres: la siguiente actividad empieza en una escena limpia")


def probar_recorrido(contexto):
    """Add-on 5.2: las tres prácticas de «Conoce Amatista Motor» (recorrido.py) en Blender real, sin ventana."""
    from types import SimpleNamespace

    from amatista_blender import ajustes, enlace, recorrido, recorrido_pasos

    p = ajustes.prefs()
    p.recorrido_hecho, p.recorridos_hechos = False, ""
    latido = recorrido.info_latido()
    revisar(latido["id"] == "pestana" and latido["total"] == 8 and not latido["activo"] and latido["hechos"] == [],
            "recorrido: el latido avisa que este add-on lo tiene, sin empezar")
    revisar(recorrido.pendiente() == "pestana", "recorrido: sin hacer nada, la que sigue es «Tu pestaña Amatista»")
    revisar(bpy.ops.amatista.recorrido(accion="empezar") == {"FINISHED"}, "recorrido: el operador la empieza")
    sc = next((s for s in bpy.data.scenes if s.get(recorrido.MARCA)), None)
    revisar(sc is not None and recorrido._cubo(sc) is not None, "recorrido: su escena trae el cubo de práctica")
    revisar(recorrido.activo() and recorrido.paso_actual()["id"] == "hola", "recorrido: empieza en «hola»")
    revisar(enlace._datos()["detalle"]["recorrido"]["activo"], "recorrido: el latido lo cuenta como activo")

    # «uso:…»: la parada se marca cuando el alumno pulsa el botón del que habla.
    ctx = SimpleNamespace(scene=sc, view_layer=sc.view_layers[0])
    indice = {q["id"]: i for i, q in enumerate(recorrido.pasos())}
    recorrido.ESTADO["indice"] = indice["guardar"]
    recorrido._al_llegar(ctx)
    revisar(not recorrido.comprobar(ctx), "recorrido: «Guardar mi avance» sin pulsar no se marca")
    bpy.ops.amatista.taller_sincronizar()
    revisar(recorrido.comprobar(ctx), "recorrido: pulsar «Guardar mi avance» marca la parada")
    recorrido.ESTADO["indice"] = recorrido_pasos.ultimo("pestana")
    recorrido.orden(ctx, "siguiente")
    revisar(not recorrido.activo() and recorrido.hecho("pestana") and p.recorrido_hecho,
            "recorrido: «siguiente» en la última parada la termina")
    revisar(recorrido.pendiente() == "vista", "recorrido: luego sigue «Muévete y usa tus herramientas»")

    # Práctica 2: la vista y el cubo se comprueban solos.
    revisar(bpy.ops.amatista.recorrido(accion="empezar", recorrido="vista") == {"FINISHED"},
            "recorrido: la plataforma (o el panel) puede abrir una práctica por su id")
    revisar(recorrido.ESTADO["rid"] == "vista" and recorrido.paso_actual()["id"] == "orbitar",
            "recorrido: «vista» empieza en «orbitar»")
    indice = {q["id"]: i for i, q in enumerate(recorrido.pasos())}
    recorrido.ESTADO["indice"] = indice["elegir"]
    recorrido._al_llegar(ctx)
    revisar(not recorrido.comprobar(ctx), "recorrido: sin elegir el cubo no se marca")
    revisar(recorrido.ir(ctx, 1) is not None, "recorrido: no deja seguir sin hacer la parada")
    cubo_practica = recorrido._cubo(sc)
    cubo_practica.select_set(True, view_layer=sc.view_layers[0])
    sc.view_layers[0].objects.active = cubo_practica
    revisar(recorrido.comprobar(ctx) and recorrido.paso_hecho(), "recorrido: elegir el cubo se comprueba solo")
    recorrido.ir(ctx, 1)
    revisar(recorrido.paso_actual()["id"] == "mover", "recorrido: pasa a «mover»")
    cubo_practica.location.x += 1.0
    revisar(recorrido.comprobar(ctx), "recorrido: mover el cubo se comprueba solo")
    recorrido.ir(ctx, 1)
    cubo_practica.rotation_euler.z += 0.6
    revisar(recorrido.paso_actual()["id"] == "girar" and recorrido.comprobar(ctx), "recorrido: girar se comprueba solo")
    recorrido.ir(ctx, 1)
    cubo_practica.scale.z *= 1.5
    revisar(recorrido.paso_actual()["id"] == "escalar" and recorrido.comprobar(ctx),
            "recorrido: escalar se comprueba solo")
    recorrido.ir(ctx, 1)
    revisar(recorrido.paso_actual()["id"] == "herramientas", "recorrido: pasa a «Tus herramientas»")
    revisar(bpy.ops.amatista.usar_herramienta(herramienta="transform.move") in ({"FINISHED"}, {"CANCELLED"}),
            "recorrido: «Usar» responde sin ventana")
    recorrido.anotar("herramienta")  # sin ventana la herramienta no arranca: el botón igual cuenta
    revisar(recorrido.comprobar(ctx), "recorrido: «Usar» marca «Tus herramientas»")
    recorrido.orden(ctx, "siguiente", "taller")
    revisar(recorrido.paso_actual()["id"] == "herramientas", "recorrido: una orden para otra práctica no se cumple")
    recorrido.orden(ctx, "salir")
    revisar(not recorrido.activo() and not recorrido.hecho("vista"), "recorrido: salir no la marca como hecha")

    recorrido.omitir()
    revisar(recorrido.hecho() and recorrido.pendiente() is None, "recorrido: «Ya lo conozco» marca las tres")
    revisar(enlace._datos()["detalle"]["recorrido"]["hechos"] == ["pestana", "vista", "taller"],
            "recorrido: el latido avisa a la plataforma cuáles se terminaron")
    p.recorrido_hecho, p.recorridos_hechos = False, ""


def probar_idioma(contexto):
    """Motor 5.3: los menús salen como en el Blender del alumno y las «Palabras de Blender» cargan."""
    print("Idioma de los menús y palabras de Blender")
    from amatista_blender import _motor, palabras
    from amatista_blender.interfaz import hud

    vista = contexto.preferences.view
    antes = vista.use_translate_interface
    try:
        vista.use_translate_interface = False
        revisar(hud.actualizar_idioma(contexto) == "en", "Blender sin traducir: menús en inglés")
        lineas = hud._partir("Agrega un cubo (Shift + A › Malla › Cubo).", 14, 2000, 3)
        revisar(" ".join(lineas) == "Agrega un cubo (Shift + A › Mesh (Malla) › Cube (Cubo)).", f"la tarjeta traduce la ruta ({lineas})")
        revisar(_motor.terminos.tecla("Malla") == "Mesh", "las teclas de la tarjeta también")
    finally:
        vista.use_translate_interface = antes
        _motor.terminos.fijar_idioma("es")
    lista = palabras.cargar(recargar=True)
    revisar(len(lista) >= 10 and lista[0]["termino"], f"palabras de Blender: {len(lista)}")


def probar_integracion(contexto):
    """Add-on 5.4: menú Amatista arriba, botón de la vista 3D, barra de estado, espacio y amatista://."""
    print("Amatista dentro de Blender")
    from amatista_blender import integracion

    for nombre in ("AMATISTA_MT_principal", "AMATISTA_PT_rapido"):
        revisar(hasattr(bpy.types, nombre), f"{nombre} registrado")
    for nombre, funcion in integracion.AGREGADOS:
        tipo = getattr(bpy.types, nombre)
        revisar(funcion in getattr(tipo.draw, "_draw_funcs", [funcion]), f"agregado a {nombre}")
    revisar(hasattr(bpy.ops.amatista, "espacio") and hasattr(bpy.ops.amatista, "reparar_enlace"), "operadores del espacio y del enlace")
    falso = type("Falso", (), {"layout": Diseno()})()
    try:
        for clase in integracion.CLASES:
            if hasattr(clase, "draw"):
                clase.draw(_Envoltura(clase, None), contexto)
        for _nombre, funcion in integracion.AGREGADOS:
            funcion(falso, contexto)
        revisar(True, "menú, panel rápido, cabecera y barra de estado se dibujan")
    except Exception as error:  # noqa: BLE001
        traceback.print_exc()
        revisar(False, f"dibujar la integración: {error}")
    orden = integracion.orden_de_inicio(["blender", "--", "--amatista", "amatista://taller/blender.bp.m1"])
    revisar(orden["tipo"] == "taller_abrir" and orden["id"].startswith("inicio-taller_abrir-"), f"orden de amatista:// ({orden})")
    revisar(integracion.orden_de_inicio(["blender"]) is None, "Blender abierto a mano no trae orden")
    revisar(integracion.registrar_protocolo() is None, "sin ventana no se registra el enlace")
    revisar(integracion.entrar_al_espacio(contexto) is False, "sin ventana no cambia de espacio")


def probar_motor6(contexto):
    """Motor 6: autosanación, una sola tarjeta, la etapa de la plataforma, demostración propia, brillo y Blender Amatista."""
    print("Motor 6")
    from amatista_blender import ajustes, blender_amatista, cuenta, recorrido, saneamiento
    from amatista_blender.interfaz import turno
    from amatista_blender.taller import datos, demo, operadores, panel, sesion
    from amatista_blender.taller.vista import brillo, tarjeta

    taller = sesion.taller
    # Autosanación.
    revisar(saneamiento.soy_duena() and bpy.app.driver_namespace.get(saneamiento.CLAVE_DUENA) == "amatista_blender",
            "autosanación: esta copia es la dueña del dibujo")
    revisar(saneamiento.otras_copias() == [], f"autosanación: no hay otras copias ({saneamiento.otras_copias()})")

    def huerfana(*_args):
        pass

    huerfana.__module__ = "bl_ext.user_default.amatista.taller.sesion"
    bpy.app.handlers.load_post.append(huerfana)
    revisar(saneamiento.quitar_huerfanas() == 1 and huerfana not in bpy.app.handlers.load_post,
            "autosanación: quita las funciones de una copia que ya no está")

    # La etapa: la exploración de la lección solo pide las primeras habilidades y no sigue sola.
    sesion.terminar()
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    datos.reiniciar_cache()
    sesion.orden(contexto, "taller_abrir", {"taller": "blender.bp.m1", "etapa": "exploracion",
                                            "habilidades": ["bl-agregar-primitivas"], "leccion": "bp1_blender"})
    a = sesion.actividad()
    revisar(a is not None and a.habilidad == "bl-agregar-primitivas" and sesion.etapa().nombre == "exploracion",
            f"etapa: la exploración abre su habilidad ({a and a.id})")
    revisar(turno.de_quien(contexto) == turno.TALLER, "una tarjeta: la del taller")
    recorrido.ESTADO["activo"] = True
    revisar(turno.de_quien(contexto) == turno.RECORRIDO, "una tarjeta: el recorrido le gana al taller")
    recorrido.ESTADO["activo"] = False

    # «Mira» muestra la variación que viene (un cubo en el centro), no la «Caja» y la «Lata» genéricas.
    linea = demo.ESTADO["linea"]
    nombres = {p.datos.get("nombre") for p in (linea.pasos if linea else ()) if p.accion == "agregar"}
    revisar(nombres and "Caja" not in nombres and "Lata" not in nombres, f"Mira: la demostración es de esta actividad ({nombres})")
    operadores.ejecutar(contexto, "ahora_tu")
    a = sesion.actividad()
    revisar(a is not None and a.tipo == taller.CONMIGO, f"etapa: después de Mira, Hazlo conmigo ({a and a.id})")
    sesion.mirame(contexto)
    linea = demo.ESTADO["linea"]
    piezas = {str(p.get("name")) for p in a.molde or a.piezas}
    nombres = {p.datos.get("nombre") for p in (linea.pasos if linea else ()) if p.accion == "agregar"}
    revisar(nombres and nombres <= piezas | {f"{n} (antes)" for n in piezas} | {"Esfera"},
            f"Mírame: solo piezas de la actividad ({nombres} de {piezas})")
    demo.detener(completa=True)

    # Una actividad de otra habilidad no saca al alumno de la etapa.
    sesion.orden(contexto, "taller_abrir", {"taller": "blender.bp.m1", "actividad": "conmigo:bl-rotar:rueda"})
    revisar(sesion.actividad() is not None and sesion.actividad().habilidad == "bl-agregar-primitivas",
            f"etapa: una orden de otra habilidad no la saca ({sesion.actividad() and sesion.actividad().id})")

    # Armar la pieza cumple la exploración: «Volver a la plataforma», sin abrir lo que sigue.
    _armar(contexto, sesion.actividad().piezas)
    sesion.evaluar(contexto)
    revisar(sesion.estado() == sesion.LOGRADA and sesion.SESION["volver"] and sesion.RUTA["cumplida"],
            "etapa: Mira y un Hazlo conmigo cumplen la exploración")
    revisar([b[1] for b in tarjeta.botones()][0] == "volver_plataforma", f"etapa: la tarjeta manda a la plataforma ({tarjeta.botones()})")
    revisar(sesion.detalle()["etapa_cumplida"] and sesion.detalle()["etapa"] == "exploracion",
            "etapa: el latido le dice a la lección que se cumplió")
    abiertas = []
    original = cuenta.abrir_plataforma
    cuenta.abrir_plataforma = lambda ruta="": abiertas.append(ruta) or True
    try:
        operadores.ejecutar(contexto, "siguiente")
        revisar(abiertas == ["#/curso/blender_principiante/leccion/bp1_blender"] and sesion.estado() == sesion.LOGRADA,
                f"etapa: «Siguiente» vuelve a la lección, no abre otra actividad ({abiertas})")
        # Con la cuenta conectada, Blender no deja elegir módulos ni empezar talleres solo.
        p = ajustes.prefs()
        p.token = "prueba"
        sesion.terminar()
        revisar(sesion.manda_la_plataforma(), "ruta: con la cuenta conectada manda la plataforma")
        revisar(not panel.AMATISTA_PT_taller_modulos.poll(contexto) and not panel.AMATISTA_PT_taller_habilidades.poll(contexto),
                "ruta: «Otros módulos» y «Demuéstralo» quedan en la plataforma")
        revisar(bpy.ops.amatista.taller_abrir(taller="blender.bp.m2") == {"FINISHED"} and not sesion.activa(),
                "ruta: «Empezar el taller» lleva a la plataforma en vez de abrir otro módulo")
        p.token = ""
    finally:
        cuenta.abrir_plataforma = original
    sesion.RUTA.update(etapa=None, leccion="", cumplida=False)

    # La tarjeta se achica mientras trabajas y se abre al acercar el ratón.
    sesion.abrir(contexto, "blender.bp.m1", "conmigo:bl-mover:baja")
    revisar(sesion.estado() == sesion.TRABAJANDO, "tarjeta: hay una actividad en curso")
    tarjeta.RECTAS[1] = (100.0, 20.0, 600.0, 140.0)
    tarjeta.compacta(1)
    tarjeta.NOVEDAD["t"] -= 60
    revisar(tarjeta.compacta(1), "tarjeta: sin novedades se vuelve una línea")
    tarjeta.raton(1, 300.0, 80.0)
    revisar(not tarjeta.compacta(1), "tarjeta: con el ratón encima se abre")
    tarjeta.RATON.update(region=0, t=0.0)

    # La herramienta brilla: dónde está, sin decir cómo.
    revisar(brillo.donde("transform.move")[0] == "TOOLS" and brillo.donde("object.add")[0] == "HEADER",
            "brillo: sabe si la herramienta está en la barra T o en un menú")
    revisar(brillo.encender(["transform.move"]) and brillo.activo() and "barra de herramientas" in brillo.ESTADO["texto"],
            f"brillo: «{brillo.ESTADO['texto']}»")
    sesion.evaluar(contexto)
    brillo.apagar()
    revisar(not brillo.activo(), "brillo: se apaga")
    sesion.terminar()

    # El molde con cordura: un montón de piezas sueltas no llena el molde.
    revision = taller.revisar_molde(
        [{"primitive": "cube", "size": [2, 2, 2], "location": [0, 0, 1], "name": "Caja"}],
        _motor_foto(contexto, 8), "molde", 1)
    revisar(revision.revuelto and not revision.completa, "molde: con piezas de más no cuenta")

    # Blender Amatista: la plantilla se instala con su pantalla de inicio y sus colores se devuelven.
    ok, texto = blender_amatista.instalar_plantilla(forzar=True)
    revisar(ok and blender_amatista.instalada(), f"Blender Amatista: plantilla instalada ({texto})")
    import importlib.util

    spec = importlib.util.spec_from_file_location("bl_app_template_amatista", blender_amatista.destino() / "__init__.py")
    plantilla = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plantilla)
    tema = bpy.context.preferences.themes[0].view_3d
    antes = tuple(tema.object_active)
    plantilla.register()
    revisar(tuple(round(c, 2) for c in tema.object_active) == plantilla.TEMA["view_3d.object_active"],
            "Blender Amatista: los colores de Amatista se ponen")
    plantilla.unregister()
    revisar(tuple(round(c, 3) for c in tema.object_active) == tuple(round(c, 3) for c in antes),
            "Blender Amatista: al salir vuelven los colores de antes")
    revisar(not blender_amatista.devolver_tema(), "Blender Amatista: no queda nada por devolver")


def probar_motor61(contexto):
    """Motor 6.1: la herramienta nueva se presenta con su ficha, brilla en su zona, el modo curioso y la plataforma."""
    print("Motor 6.1")
    from amatista_blender import ajustes, cuenta, enlace, fichas, plataforma
    from amatista_blender.interfaz import turno
    from amatista_blender.taller import datos, operadores, panel, sesion
    from amatista_blender.taller.vista import brillo, ficha, tarjeta

    p = ajustes.prefs()
    p.presentar_herramientas = True
    sesion.terminar()
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    datos.reiniciar_cache()
    revisar(len(fichas.fichas()) >= 20 and fichas.ficha("mesh.extrude").zona == "herramientas",
            "fichas: se leen las mismas de la teoría de la plataforma")

    # Presentar: la primera actividad con herramientas nuevas empieza por sus fichas, de a una.
    sesion.abrir(contexto, "blender.bp.m2", "mira:bl-extruir")
    a = sesion.actividad()
    revisar(a is not None and sesion.estado() == sesion.PRESENTANDO, f"presentar: antes de Mira, la ficha ({sesion.estado()})")
    f = fichas.visible()
    revisar(f is not None and f.id == "mesh.edit" and fichas.chip() == "HERRAMIENTA NUEVA · 1 de 2",
            f"presentar: primero Modo Edición, 1 de 2 ({f and f.id}, {fichas.chip()})")
    revisar(brillo.activo() and brillo.ESTADO["region"] == "HEADER" and "cabecera" in brillo.ESTADO["texto"],
            f"presentar: Modo Edición brilla en la cabecera ({brillo.ESTADO})")
    revisar(turno.de_quien(contexto) == turno.TALLER and [b[1] for b in tarjeta.botones()][0] == "ficha_entendido",
            f"presentar: la ficha ocupa la tarjeta del taller ({tarjeta.botones()})")
    revisar(sesion.detalle()["ficha"] == {"id": "mesh.edit", "nombre": "Modo Edición"} and
            sesion.detalle()["estado"] == "presentando", "presentar: la lección sabe qué herramienta se presenta")
    operadores.ejecutar(contexto, "ficha_como")
    pasos = [t for t, _tam, _c, _s, v in ficha.lineas(f, 500, 12, 14) if v.isdigit()]
    revisar(fichas.ESTADO["abierta"] and len(pasos) >= 3, f"presentar: «¿Cómo se usa?» abre los pasos ({pasos})")
    operadores.ejecutar(contexto, "ficha_entendido")
    revisar(fichas.visible().id == "mesh.extrude" and fichas.chip().endswith("2 de 2") and sesion.estado() == sesion.PRESENTANDO,
            "presentar: «Entendido» pasa a la siguiente herramienta nueva")
    revisar(brillo.ESTADO["region"] == "TOOLS", "presentar: Extruir brilla en la barra de herramientas")
    operadores.ejecutar(contexto, "ficha_entendido")
    revisar(fichas.visible() is None and sesion.estado() == sesion.MIRANDO, f"presentar: después de las fichas, Mira ({sesion.estado()})")
    revisar(fichas.vistas().get("mesh.edit") == 1 and fichas.vistas().get("mesh.extrude") == 1,
            "presentar: las fichas vistas quedan en el avance del alumno")

    # La segunda vez ya no se presenta: una línea de recordatorio en la tarjeta (se retira con el uso).
    sesion.abrir(contexto, "blender.bp.m2", "mira:bl-extruir")
    revisar(sesion.estado() == sesion.MIRANDO and fichas.visible() is None, "andamio: vista una vez, ya no se presenta")
    linea = fichas.recordatorio(sesion.actividad())
    revisar(linea.startswith("Modo Edición (Tab):"), f"andamio: queda un recordatorio de una línea ({linea})")
    sesion.terminar()

    # «Ya la conozco»: esa herramienta no se vuelve a presentar sola.
    sesion.abrir(contexto, "blender.bp.m2", "mira:bl-corte-bucle")
    revisar(fichas.visible() is not None and fichas.visible().id == "mesh.loopcut", "presentar: Corte de bucle es nueva")
    operadores.ejecutar(contexto, "ficha_conozco")
    revisar("mesh.loopcut" in fichas.conocidas() and sesion.estado() == sesion.MIRANDO,
            "presentar: «Ya la conozco» la guarda y sigue con la actividad")
    sesion.terminar()

    # Consulta: «¿Qué es esto?» del panel abre cualquier ficha; Propiedades también brilla.
    revisar(bpy.ops.amatista.ficha(herramienta="modifier.mirror") == {"FINISHED"} and fichas.modo() == fichas.CONSULTA,
            "consulta: «¿Qué es?» abre la ficha del Espejo")
    revisar(turno.de_quien(contexto) == turno.FICHA, "consulta: sin taller, la ficha tiene su propio turno")
    revisar(brillo.ESTADO["espacio"] == "PROPERTIES" and "Propiedades" in brillo.ESTADO["texto"],
            f"consulta: el Espejo brilla en Propiedades ({brillo.ESTADO['texto']})")
    operadores.ejecutar(contexto, "ficha_entendido")
    revisar(fichas.visible() is None and not brillo.activo(), "consulta: «Cerrar» la quita y apaga el brillo")
    revisar(bpy.ops.amatista.ficha(herramienta="no.existe") == {"CANCELLED"}, "consulta: sin ficha, no abre nada")
    revisar(len(panel.fichas_del_panel()) > 0, "panel: «¿Qué es esto?» lista las herramientas del módulo")

    # Modo curioso: lo que el alumno toca se explica las primeras veces.
    # Sin ventana Blender no anota los operadores en wm.operators: se prueba con lo que «tocó» el alumno.
    fichas.ULTIMO.update(op=None, herramienta=None, listo=False)
    revisar(fichas.tocado() is None and fichas.ULTIMO["listo"], "curioso: la primera vez solo anota lo que hay")
    original_tocado = fichas.tocado
    toques = [("MESH_OT_primitive_cube_add", ""), ("MESH_OT_primitive_cube_add", ""), ("OBJECT_OT_delete", "")]
    fichas.tocado = lambda: toques.pop(0) if toques else None
    try:
        p.modo_curioso = "auto"
        explicada = fichas.revisar_curioso()
        revisar(explicada is not None and explicada.id == "object.add" and fichas.chip() == "¿QUÉ ES ESTO?",
                f"curioso: agregar un cubo explica «Agregar formas» ({explicada and explicada.id})")
        revisar(turno.de_quien(contexto) == turno.FICHA and brillo.ESTADO["region"] == "HEADER",
                "curioso: la ficha corta se ve y Agregar brilla en la cabecera")
        operadores.ejecutar(contexto, "ficha_conozco")
        revisar(fichas.revisar_curioso() is None, "curioso: «No me lo expliques» no la repite")
        p.modo_curioso = "nunca"
        revisar(fichas.revisar_curioso() is None and fichas.visible() is None, "curioso: apagado no explica nada")
    finally:
        fichas.tocado = original_tocado
    fichas.cerrar(marcar=False)

    # La plataforma: Blender sabe en qué lección va y no abre otra pestaña al cumplir la etapa.
    enlace.cumplir({"id": "leccion-1", "tipo": "leccion", "datos": {
        "curso": "blender_principiante", "leccion": "bp1_blender", "clase": "blender", "titulo": "Explora en Blender",
        "numero": 2, "total": 5}})
    revisar(plataforma.viva() and plataforma.texto_corto().startswith("Lección 2 de 5"),
            f"plataforma: Blender sabe la lección ({plataforma.texto_corto()})")
    p.presentar_herramientas = False
    sesion.orden(contexto, "taller_abrir", {"taller": "blender.bp.m1", "etapa": "exploracion",
                                            "habilidades": ["bl-agregar-primitivas"], "leccion": "bp1_blender"})
    operadores.ejecutar(contexto, "ahora_tu")
    _armar(contexto, sesion.actividad().piezas)
    sesion.evaluar(contexto)
    revisar(sesion.SESION["volver"] and "ya lo sabe" in sesion.frase_logro(),
            f"plataforma: al cumplir la etapa, la lección del navegador sigue sola ({sesion.frase_logro()})")
    enlace.cumplir({"id": "leccion-2", "tipo": "leccion", "datos": {
        "curso": "blender_principiante", "leccion": "bp1_explora", "clase": "teoria", "titulo": "Muévete y transforma",
        "numero": 3, "total": 5}})
    revisar("«Muévete y transforma»" in sesion.frase_logro() and [b[1] for b in tarjeta.botones()] == ["otra_vez"],
            f"plataforma: Blender dice a dónde pasó la lección ({sesion.frase_logro()}, {tarjeta.botones()})")
    abiertas = []
    original = cuenta.abrir_plataforma
    cuenta.abrir_plataforma = lambda ruta="": abiertas.append(ruta) or True
    try:
        operadores.ejecutar(contexto, "volver_plataforma")
        revisar(abiertas == [], "plataforma: abierta, no se abre otra pestaña")
        operadores.ejecutar(contexto, "abrir_plataforma")
        revisar(abiertas == ["#/curso/blender_principiante/leccion/bp1_explora"],
                f"plataforma: «Mi lección» abre la lección en la que va ({abiertas})")
    finally:
        cuenta.abrir_plataforma = original
    sesion.terminar()
    sesion.RUTA.update(etapa=None, leccion="", cumplida=False)
    plataforma.reiniciar()
    p.modo_curioso = "auto"


def probar_motor62(contexto):
    """Motor 6.2: cambiar de práctica sale limpio, «Volver a mi práctica» y el acompañamiento según el ánimo."""
    print("Motor 6.2")
    from amatista_blender import ajustes, navegar, practicas
    from amatista_blender.interfaz import turno
    from amatista_blender.taller import acompanar, datos, escena, operadores, sesion
    from amatista_blender.taller.vista import brillo, tarjeta

    p = ajustes.prefs()
    p.presentar_herramientas = False
    sesion.terminar()
    catalogo = practicas.catalogo()
    c = datos.catalogo()

    # Una escena sin práctica pero con cosas del alumno no se usa: la práctica empieza limpia.
    sc_suelta = _escena_nueva(contexto, "Mis pruebas")
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3, 0, 0))
    contexto.active_object.name = "Mi cosa"
    suelta = next(pid for pid in sorted(catalogo) if c.taller_de_proyecto(pid) is None
                  and catalogo[pid].get("definicion"))
    practicas.activar(contexto, catalogo[suelta]["definicion"], "paquete")
    revisar(contexto.scene != sc_suelta and "Mi cosa" not in contexto.scene.objects,
            f"cambio limpio: lo suelto del alumno no entra a la práctica ({[o.name for o in contexto.scene.objects]})")
    revisar("Mi cosa" in sc_suelta.objects, "cambio limpio: lo del alumno sigue en su escena")

    # El proyecto de un taller y luego otra práctica: el molde del proyecto ya no se queda dibujado.
    t = next(t for t in c.talleres if t.proyecto and t.proyecto in catalogo)
    practicas.activar(contexto, catalogo[t.proyecto]["definicion"], "paquete")
    revisar(sesion.SESION["proyecto"] and sesion.actividad() is not None, f"cambio limpio: el proyecto de {t.id} abre el taller")
    practicas.activar(contexto, catalogo[suelta]["definicion"], "paquete")
    revisar(sesion.actividad() is None and sesion.molde_visible() is None,
            "cambio limpio: otra práctica suelta el proyecto anterior y su molde")
    practicas.cerrar(contexto)

    # Acompañamiento: una habilidad nueva tiene todo encendido; los fallos suben el ánimo a «atorado».
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    datos.reiniciar_cache()
    contexto = _abrir_actividad(contexto, "blender.bp.m3", "conmigo:bl-espejo:ala")
    revisar(sesion.estado() == sesion.TRABAJANDO, f"acompañar: trabajando en el taller ({sesion.estado()})")
    luz = acompanar.calcular()
    revisar(luz is not None and luz.nivel == 3 and luz.pieza and luz.accion,
            f"acompañar: habilidad nueva al principio del curso, luz plena ({luz})")
    revisar(acompanar.te_toca() == "Espejo" and tarjeta._linea_accion() is not None,
            f"acompañar: la tarjeta dice qué herramienta toca ({acompanar.te_toca()})")
    revisar(acompanar.pulso() > 0, "acompañar: la pieza que toca lleva faro")
    for _ in range(3):
        acompanar.fallo()
    brillo.apagar()
    acompanar.ESTADO["leido"] = 0.0
    acompanar.vigilar()
    animo = acompanar.animo()
    revisar(animo is not None and animo.nivel in ("atorado", "frustrado"), f"acompañar: tres fallos, atorado ({animo})")
    revisar(sesion.mensaje() != "" and brillo.activo(), f"acompañar: se ofrece ayuda y brilla la herramienta ({sesion.mensaje()})")
    detalle = sesion.detalle()["acompanamiento"]
    revisar(detalle["animo"] == animo.nivel and detalle["luz"] == "plena" and detalle["razones"],
            f"acompañar: la plataforma recibe el ánimo, no los errores ({detalle})")
    acompanar.avanzo()
    revisar(acompanar.calcular() is not None and acompanar.animo().indice < 2, "acompañar: avanzar calma el ánimo")

    # Volver: en otra escena aparece «Volver a mi práctica» y un clic regresa a la actividad.
    del_taller = contexto.scene
    revisar(escena.es_del_taller(del_taller), "volver: la actividad está en la escena del taller")
    otra = _escena_nueva(contexto, "Me perdí")
    revisar(navegar.hace_falta(contexto) and turno.de_quien(contexto) == turno.VOLVER,
            f"volver: fuera de la actividad sale la pastilla ({turno.de_quien(contexto)})")
    texto = operadores.ejecutar(contexto, "volver_amatista")
    revisar(contexto.scene == del_taller and texto.startswith("Aquí sigues"),
            f"volver: un clic regresa a la escena del taller ({contexto.scene.name}, {texto})")
    revisar(not navegar.hace_falta(contexto) and turno.de_quien(contexto) == turno.TALLER,
            "volver: de vuelta, la tarjeta del taller otra vez")
    revisar(bpy.ops.amatista.volver() == {"FINISHED"}, "volver: el operador existe para el menú y la cabecera")
    sesion.terminar()
    sesion.RUTA.update(etapa=None, leccion="", cumplida=False)
    bpy.data.scenes.remove(otra)
    bpy.data.scenes.remove(sc_suelta)


def _motor_foto(contexto, extras):
    from amatista_blender import practicas

    for obj in list(contexto.scene.objects):
        bpy.data.objects.remove(obj)
    cubo("Caja", (0, 0, 1), (2, 2, 2))
    for i in range(extras):
        cubo(f"Suelta {i}", (5 + i, 5, 0.25), (0.5, 0.5, 0.5))
    return practicas.capturar(contexto.scene)


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
    revisar(datos["version_addon"] == "6.2.0", "el intento lleva la versión 6.2 del add-on")

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
