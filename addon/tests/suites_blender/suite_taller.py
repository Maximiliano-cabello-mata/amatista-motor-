# Pruebas de talleres del alumno, actividades y recorrido guiado.
import tempfile
import json
import time
from pathlib import Path
import bpy
from .comun import (
    revisar,
    cubo,
    Diseno,
    dibujar_todo,
    dibujar_vista_3d,
    _Envoltura,
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


