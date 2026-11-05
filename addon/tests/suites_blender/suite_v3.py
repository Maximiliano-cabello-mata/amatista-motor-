# Pruebas de motor v3, temas, motor 3.4/3.5, escenas por pr?ctica y ejemplo.
import re
import importlib
import json
import tempfile
from pathlib import Path
import bpy
from .comun import (
    revisar,
    cubo,
    Diseno,
    dibujar_todo,
    dibujar_vista_3d,
    _limpiar,
    _escena_nueva,
    _inicio_de_blender,
    _armar,
    _abrir_actividad,
    _elegir,
    _tren_del_alumno,
    _aldea_del_alumno,
    _motor_foto,
    ARCHIVO_V2,
)

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
        # Motor 7: la barra de herramientas ya no se esconde (con ella escondida, «brilla a la izquierda» mentía).
        revisar(espacio.show_region_toolbar and espacio.show_region_ui, "enfoque: con la barra T y la barra lateral")
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


