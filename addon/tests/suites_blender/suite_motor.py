# Pruebas de evoluci?n de motor (motor 4, 6, 6.1, 6.2, 7).
import traceback
import re
import sys
import tempfile
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
    revisar(saneamiento.otras_copias() == [] or all(not activa for _m, _v, activa in saneamiento.otras_copias()),
            f"autosanación: no hay otras copias activas ({saneamiento.otras_copias()})")

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



def probar_motor7(contexto):
    """Motor 7 · Guion: un paso a la vez, avanza por el resultado, señales reales y el administrador sin progreso."""
    print("Motor 7")
    from types import SimpleNamespace

    from amatista_blender import ajustes, aprendizaje, enfoque, guion, practicas
    from amatista_blender.guion import banda, panel, senalar
    from amatista_blender.interfaz import hud, turno
    from amatista_blender.taller import datos, sesion
    from amatista_blender.taller import panel as panel_taller

    bpy.ops.wm.read_homefile(use_empty=False)  # un Blender recién abierto: sin archivo guardado
    contexto = bpy.context
    p = ajustes.prefs()
    p.guion_paso_a_paso = True
    p.presentar_herramientas = True  # lo que tiene un alumno nuevo: el guion no abre fichas encima
    p.enfoque = "auto"
    contexto.window_manager.amatista.modo = "alumno"
    sesion.terminar()
    for archivo in ajustes.carpeta_usuario().glob("avance_taller_*.json"):
        archivo.unlink()
    datos.reiniciar_cache()

    # El tren, como proyecto del taller: una sola voz (el guion) y sin la barra escondida.
    _limpiar()
    sesion.abrir(contexto, "blender.bp.m1", "proyecto:blender.bp.m1")
    sc = contexto.scene
    revisar(sc.amatista.practica_id == "blender.bp.m1.tren" and guion.activo(sc), "guion: manda en el proyecto del tren")
    revisar(turno.de_quien(contexto) == turno.GUION, f"guion: el turno es del guion ({turno.de_quien(contexto)})")
    vistas = [a for v in contexto.window_manager.windows for a in v.screen.areas if a.type == "VIEW_3D"]
    if vistas:
        revisar(vistas[0].spaces.active.show_region_toolbar, "guion: la barra de herramientas se ve (nivel 1, enfocado)")
    revisar(enfoque.activo(), "guion: Shift+A sigue enfocado en las piezas del tren")
    revisar(panel.AMATISTA_PT_guion.poll(contexto) and not panel_taller.AMATISTA_PT_taller.poll(contexto),
            "guion: un solo panel dice lo que sigue (el del taller se esconde)")
    guion.revisar_ya(contexto)
    v = guion.vista()
    revisar(v["numero"] == 1 and v["total"] == 10 and v["objetivo"] == "vagones" and "cubo" in v["haz"].lower(),
            f"guion: paso 1 de 10, agregar los vagones ({v['numero']}/{v['total']}: {v['haz']})")
    revisar(not re.search(r"brilla|resaltad", v["haz"] + v["por_que"], re.I), "guion: nada dice que brilla")

    # «¿Dónde está?» del primer paso: Agregar es un menú de arriba, no la barra de la izquierda.
    pista = guion.pedir_pista(contexto, 2)
    revisar(pista is not None and "cabecera" in pista["texto"] and "izquierda" not in pista["texto"].split("atajo")[0]
            and not pista["senalado"] and not re.search(r"brilla|resaltad", pista["texto"], re.I),
            f"guion: Agregar se busca en la cabecera, sin brillos inventados ({pista and pista['texto']})")

    # Todo de una vez y en otro orden: el resultado manda, sin esperar herramientas.
    _tren_del_alumno(contexto)
    guion.revisar_ya(contexto)
    v = guion.vista()
    revisar(v["objetivo"] == "guardar" and sum(1 for _t, e in v["pasos"] if e == "hecho") == 9,
            f"guion: con el tren armado solo falta guardar ({v['objetivo']}, {v['pasos']})")
    pista = guion.pedir_pista(contexto, 2)
    revisar("Guardar como" in pista["texto"] and "arriba de todo" in pista["texto"] and "barra de herramientas" not in pista["texto"],
            f"guion: guardar se busca en Archivo, arriba ({pista['texto']})")
    revisar(senalar.se_puede_abrir("file.save"), "guion: el panel ofrece abrir «Guardar como»")

    # Deshacer una pieza la vuelve a pedir en el momento.
    rueda = next(o for o in sc.objects if o.name.startswith("Cylinder"))
    rueda.location.z += 1.0
    contexto.view_layer.update()
    guion.revisar_ya(contexto)
    revisar(guion.vista()["objetivo"] != "guardar" and guion.avance().deshechos, "guion: levantar una rueda se nota al instante")
    pista = guion.pedir_pista(contexto, 1)
    revisar(pista["senalado"] and rueda.select_get(), f"guion: «¿Qué falta?» selecciona la pieza de la que habla ({pista['texto']})")
    pista = guion.pedir_pista(contexto, 2)
    revisar(pista["senalado"] == bool(re.search(r"resaltad", pista["texto"])) and senalar.herramienta_elegida(contexto)
            in ("builtin.move", "builtin.scale", "builtin.rotate"), f"guion: la herramienta queda elegida de verdad ({pista['texto']})")
    rueda.location.z -= 1.0
    contexto.view_layer.update()

    # Guardar: el manejador de save_post revisa sin esperar al depsgraph.
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(tempfile.mkdtemp()) / "mi_tren.blend"))
    revisar(guion.ESTADO["sucio"], "guion: guardar pide revisar en el momento")
    guion.revisar_ya(contexto)
    revisar(guion.completo() and sesion.estado() == sesion.LOGRADA, f"guion: el tren guardado termina el proyecto ({guion.vista()['modo']})")

    # La banda y el panel se dibujan sin errores (gpu y blf falsos).
    falso = Diseno()
    blf_falso = SimpleNamespace(size=lambda *a: None, color=lambda *a: None, position=lambda *a: None,
                                draw=lambda *a: None, dimensions=lambda f, t: (len(t) * 6.0, 10.0))
    originales = {k: getattr(hud, k, None) for k in ("gpu", "blf", "batch_for_shader")}
    hud.gpu, hud.blf, hud.batch_for_shader = falso, blf_falso, (lambda *a, **k: falso)
    banda_gpu, banda_bpy = banda.gpu, banda.bpy
    try:
        class ContextoFalso:
            region = SimpleNamespace(width=1200, height=700, x=0, y=0)
            area = None

            def __getattr__(self, nombre):
                return getattr(contexto, nombre)

        banda.gpu = falso
        banda.bpy = SimpleNamespace(context=ContextoFalso(), app=bpy.app, types=bpy.types)
        banda.dibujar()
        panel.AMATISTA_PT_guion.draw(_Envoltura(panel.AMATISTA_PT_guion, 0), contexto)
        revisar(True, "guion: la banda y el panel se dibujan")
    except Exception as error:  # noqa: BLE001
        traceback.print_exc()
        revisar(False, f"guion: dibujar la banda o el panel: {error}")
    finally:
        banda.gpu, banda.bpy = banda_gpu, banda_bpy
        for k, val in originales.items():
            setattr(hud, k, val)

    # Una actividad corta: el paso es lo que pide la actividad y el molde se sigue dibujando.
    sesion.abrir(contexto, "blender.bp.m1", "conmigo:bl-mover:baja")
    a = sesion.actividad()
    revisar(a is not None and a.id == "conmigo:bl-mover:baja" and sesion.estado() == sesion.TRABAJANDO,
            f"guion: la actividad empieza sin una ficha encima ({sesion.estado()})")
    guion.revisar_ya(contexto)
    v = guion.vista()
    revisar(v["haz"] == a.pide and v["total"] >= 1, f"guion: el paso de la actividad es su frase ({v['haz']})")
    caja = contexto.scene.objects.get("Caja")
    if caja is not None:
        caja.location.z = 1.0
        contexto.view_layer.update()
        guion.revisar_ya(contexto)
        revisar(sesion.estado() == sesion.LOGRADA, "guion: bajar la caja al suelo logra la actividad")

    # Administrador: practica sin progreso, nada se guarda ni se envía, y arranca de cero.
    token, rol = p.token, p.rol
    p.token, p.rol = "prueba-admin", "admin"
    try:
        datos.reiniciar_cache()
        aprendizaje.ESTADO["avance_admin"] = None
        revisar(ajustes.sin_progreso() and guion.sin_progreso(), "admin: la cuenta admin practica sin progreso")
        revisar(not datos.avance()["completadas"] and not datos.avance()["cola"], "admin: el taller empieza de cero")
        sesion.abrir(contexto, "blender.bp.m1", "conmigo:bl-mover:baja")
        caja = contexto.scene.objects.get("Caja")
        if caja is not None:
            caja.location.z = 1.0
            contexto.view_layer.update()
            guion.revisar_ya(contexto)
        revisar(not datos.avance()["cola"], "admin: el intento no se guarda para enviar")
        revisar(not list(ajustes.carpeta_usuario().glob("avance_taller_*.json"))
                or all("admin" not in f.read_text(encoding="utf-8") for f in ajustes.carpeta_usuario().glob("avance_taller_*.json")),
                "admin: nada se escribe en el equipo")
        aprendizaje.marcar_completada("blender.bp.m1.tren")
        aprendizaje.ESTADO["avance_admin"] = None  # otro arranque de Blender
        revisar("blender.bp.m1.tren" not in aprendizaje.completadas(), "admin: al volver a entrar todo empieza de cero")
    finally:
        p.token, p.rol = token, rol
        datos.reiniciar_cache()
    sesion.terminar()
    practicas.cerrar(contexto)
    p.guion_paso_a_paso = False


