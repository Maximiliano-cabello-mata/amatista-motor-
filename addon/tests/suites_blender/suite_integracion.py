# Pruebas de auditor?a, idioma, integraci?n, coraz?n y entrega al servidor.
import importlib
import traceback
import json
import math
import sys
import tempfile
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
    ADDON,
)

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



def probar_corazon(contexto):
    """Corazón Amatista: el director decide, el adaptador de Blender cumple el contrato y la señal se comprueba."""
    print("Corazón Amatista")
    import re
    from importlib import import_module

    from amatista_blender import _motor, ajustes, corazon, guion
    from amatista_blender.corazon.adaptador import AdaptadorBlender
    from amatista_blender.guion import senalar
    from amatista_blender.taller import datos, sesion

    conformidad = import_module(_motor.engine.__name__ + ".corazon.conformidad")
    c = corazon.contrato

    problemas = conformidad.revisar_adaptador(AdaptadorBlender())
    revisar(problemas == [], f"corazón: el adaptador de Blender cumple el contrato ({problemas})")

    bpy.ops.wm.read_homefile(use_empty=False)
    contexto = bpy.context
    p = ajustes.prefs()
    p.guion_paso_a_paso = True
    contexto.window_manager.amatista.modo = "alumno"
    sesion.terminar()
    for archivo in ajustes.carpeta_usuario().glob("corazon_andamio_*.json"):
        archivo.unlink()
    corazon.unregister()
    datos.reiniciar_cache()
    _limpiar()
    sesion.abrir(contexto, "blender.bp.m1", "proyecto:blender.bp.m1")
    guion.revisar_ya(contexto)
    revisar(corazon.activo() and corazon.director().practica_id == "blender.bp.m1.tren",
            f"corazón: hay un director para el tren ({corazon.ESTADO['error']})")
    v = guion.vista()
    revisar(v["nivel"] == "mostrar" and "cabecera" in v["donde"],
            f"corazón: el alumno nuevo ve dónde está Agregar ({v['nivel']}: {v['donde']})")
    revisar(not v["senal"], "corazón: Agregar es un menú y no se abre solo")

    # Con el tren armado solo falta guardar; una rueda levantada vuelve al paso de las ruedas.
    _tren_del_alumno(contexto)
    guion.revisar_ya(contexto)
    rueda = next(o for o in contexto.scene.objects if o.name.startswith("Cylinder"))
    rueda.location.z += 1.0
    contexto.view_layer.update()
    guion.revisar_ya(contexto)
    pista = guion.pedir_pista(contexto, 2)
    elegida = senalar.herramienta_elegida(contexto)
    revisar(pista is not None and (pista["senalado"] == bool(re.search("resaltad", pista["texto"]))),
            f"corazón: la pista solo dice «resaltado» si Blender lo confirma ({pista and pista['texto']})")
    if pista and pista["senalado"]:
        d = corazon.director()
        revisar(d.senal.estado == c.VIGENTE and elegida == d.senal.senal.objetivo,
                f"corazón: la señal está vigente y es la herramienta elegida ({elegida})")
        # El alumno elige otra herramienta: la señal se pierde y se dice, sin reloj.
        otra = "builtin.select_box" if elegida != "builtin.select_box" else "builtin.move"
        ventana, area = senalar._primera_vista(contexto)
        try:
            region = next(r for r in area.regions if r.type == "WINDOW")
            with contexto.temp_override(window=ventana, area=area, region=region):
                bpy.ops.wm.tool_set_by_id(name=otra)
        except (RuntimeError, AttributeError, StopIteration):
            pass
        revisar(senalar.herramienta_elegida(contexto) == otra, f"corazón: el alumno eligió otra herramienta ({otra})")
        if senalar.herramienta_elegida(contexto) == otra:
            d.ciclo(corazon.programa(), None, d.inicio_paso + 1)
            v = guion.vista()
            revisar(v["senal_estado"] == "perdida" and v["senal_repetir"] and "otra herramienta" in v["senal"],
                    f"corazón: cambiar de herramienta se nota y se ofrece señalar otra vez ({v['senal']})")
            guion.repetir_senal()
            revisar(senalar.herramienta_elegida(contexto) == d.senal.senal.objetivo and d.senal.estado == c.VIGENTE,
                    "corazón: «Señálalo otra vez» la vuelve a elegir")
    rueda.location.z -= 1.0
    contexto.view_layer.update()
    guion.revisar_ya(contexto)
    h = corazon.historial()
    revisar(any(u.solos or u.ayudados for u in h.usos.values()), f"corazón: el andamio anota lo que usó ({h.como_dict()})")
    archivos = list(ajustes.carpeta_usuario().glob("corazon_andamio_*.json"))
    revisar(bool(archivos) or ajustes.sin_progreso(), "corazón: el andamio se guarda por cuenta (no para admin)")
    sesion.terminar()
    _limpiar()



def probar_entrega(contexto):
    """Panel del profesor: el modelo ligero de la escena (con modificadores) y su revisión en el servidor."""
    print("Entrega al profesor")
    import importlib.util

    from amatista_blender import entrega, modelo_ligero

    import bmesh

    # La escena de la práctica es siempre la activa (practicas.escena): se prueba en la activa.
    escena = contexto.scene
    datos_malla = bpy.data.meshes.new("Cubo entrega")
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=2.0)
    b.to_mesh(datos_malla)
    b.free()
    cubo = bpy.data.objects.new("Cubo entrega", datos_malla)
    escena.collection.objects.link(cubo)
    cubo.location = (1.0, 0.0, 1.0)
    cubo.modifiers.new("Bisel", "BEVEL")
    material = bpy.data.materials.new("Rojo")
    material.diffuse_color = (0.9, 0.1, 0.1, 1.0)
    material.use_nodes = True
    principled = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    principled.inputs["Base Color"].default_value = (0.9, 0.1, 0.1, 1.0)
    cubo.data.materials.append(material)
    luz = bpy.data.objects.new("Luz", bpy.data.lights.new("Luz", "POINT"))
    escena.collection.objects.link(luz)
    datos = entrega.extraer(escena)
    tipos = {o["nombre"]: o["tipo"] for o in datos["objetos"]}
    revisar(tipos.get(cubo.name) == "MESH" and tipos.get("Luz") == "LIGHT", f"entrega: cubo y luz ({tipos})")
    malla = next(o for o in datos["objetos"] if o["nombre"] == cubo.name)
    revisar(len(malla["t"]) // 3 > 12, "entrega: el bisel (modificador) viaja aplicado")
    xs = malla["v"][0::3]
    medio = datos["centro"][0] + (max(xs) + min(xs)) / 2 / modelo_ligero.COORDENADA * datos["escala"]
    revisar(abs(medio - 1.0) < 0.05, f"entrega: vértices en el espacio del mundo (x medio {medio:.2f})")
    rojo = datos["materiales"][malla["material"]] if malla.get("material", -1) >= 0 else {}
    revisar(rojo.get("nombre") == "Rojo" and rojo["color"][0] > 0.8, f"entrega: el material y su color ({rojo})")
    paquete = modelo_ligero.empaquetar(datos)
    revisar(len(paquete) < 20000, f"entrega: pocos KB ({len(paquete)} caracteres)")
    spec = importlib.util.spec_from_file_location(
        "servidor_modelo_ligero", ADDON.parent / "backend" / "contenido" / "modelo_ligero.py")
    servidor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(servidor)
    revisar(servidor.resumen_de(paquete)["objetos"] == len(datos["objetos"]), "entrega: el servidor acepta el modelo")
    for obj in (cubo, luz):
        bpy.data.objects.remove(obj)


