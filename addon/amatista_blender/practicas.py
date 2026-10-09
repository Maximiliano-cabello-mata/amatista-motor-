"""Amatista Student Runtime: la práctica abierta, su evaluación y su progreso.

Flujo:
    catálogo (paquete + caché + servidor) → activar() → evaluar() al cambiar
    la escena o al pulsar «Comprobar» → sincronizar() con la plataforma.

La misma evaluación sirve a los tres modos (Alumno, Vista previa y Autor):
solo cambia cuánto detalle muestra la interfaz.
"""
import dataclasses
import hashlib
import json
import time
from pathlib import Path

import bpy
from bpy.app.handlers import persistent

from . import _motor, ajustes, aprendizaje, enfoque, enlace, escenarios, guia, red, temas

# Estado de la sesión de Blender (no se guarda en el .blend).
ESTADO = {
    "reporte": None,
    "clave": None,
    "practica": None,
    "sucio": False,
    "sync": "",
    "sync_detalle": "",
    "ultima_sync": 0.0,
    "catalogo_servidor": {},
    "catalogo_cargado": False,
    "aprobados_antes": {},
    "red": "",
    "ultimo_cambio": 0.0,
    # Amatista escribe sus propiedades en la escena y eso marca el archivo
    # como modificado: «guardado» se decide por los cambios del alumno.
    "cambios_desde_guardar": True,
    "motor_render": "",
}

SYNC_SIN_CUENTA = "sin_cuenta"
SYNC_ENVIANDO = "enviando"
SYNC_GUARDADO = "guardado"
SYNC_PENDIENTE = "pendiente"
SYNC_ERROR = "error"


# --- Catálogo -------------------------------------------------------------------


def carpeta_paquete():
    """Prácticas incluidas en el paquete (o las del repositorio al desarrollar)."""
    empaquetadas = Path(__file__).resolve().parent / "practicas"
    if empaquetadas.is_dir():
        return empaquetadas
    return Path(__file__).resolve().parents[2] / "practices"


_carpeta_paquete = carpeta_paquete
_CARPETAS_PRACTICA = {}


def archivo_de_referencia(practica_id, nombre):
    """referencia.jpg o plano.svg que viene en el paquete junto a la práctica (motor 3.3)."""
    if not _CARPETAS_PRACTICA:
        for ruta in carpeta_paquete().rglob("practica.json"):
            datos = _leer_json(ruta) or {}
            if datos.get("id"):
                _CARPETAS_PRACTICA[datos["id"]] = ruta.parent
    carpeta = _CARPETAS_PRACTICA.get(practica_id)
    archivo = carpeta / nombre if carpeta else None
    return archivo if archivo and archivo.is_file() else None


# Solo el modo desarrollador ve las prácticas de prueba y las archivadas (v2).
CARPETAS_DESARROLLO = ("sandbox", "archivo")


def _carpeta_cache():
    carpeta = ajustes.carpeta_usuario() / "practicas"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _leer_json(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _meta(datos, origen):
    return {
        "id": datos.get("id"),
        "title": datos.get("title", datos.get("id")),
        "description": datos.get("description", ""),
        "level": datos.get("level", 1),
        "minutes": datos.get("estimatedMinutes"),
        "version": datos.get("version", 1),
        "course": (datos.get("course") or {}).get("id"),
        "module": (datos.get("course") or {}).get("module"),
        "origen": origen,
        "definicion": datos,
    }


def catalogo():
    """{id: meta}. El servidor gana sobre la caché y la caché sobre el paquete."""
    resultado = {}
    for ruta in sorted(_carpeta_paquete().rglob("*.json")):
        datos = _leer_json(ruta)
        if isinstance(datos, dict) and datos.get("schema") in _motor.practica.SUPPORTED_SCHEMAS:
            if set(CARPETAS_DESARROLLO) & set(ruta.parts) and not ajustes.es_desarrollador():
                continue
            resultado[datos["id"]] = _meta(datos, "paquete")
    try:
        for ruta in sorted(_carpeta_cache().glob("*.json")):
            datos = _leer_json(ruta)
            if isinstance(datos, dict) and datos.get("id"):
                resultado[datos["id"]] = _meta(datos, "guardada")
    except OSError:
        pass
    for pid, meta in ESTADO["catalogo_servidor"].items():
        anterior = resultado.get(pid, {})
        definicion = anterior.get("definicion") if anterior.get("version") == meta.get("version") else None
        resultado[pid] = {**meta, "origen": "servidor", "definicion": definicion}
    return resultado


def refrescar_catalogo(al_terminar=None):
    def listo(respuesta, error, estado):
        if error is None:
            ESTADO["catalogo_servidor"] = {
                p["id"]: {
                    "id": p["id"],
                    "title": p.get("titulo") or p["id"],
                    "description": p.get("descripcion") or "",
                    "level": p.get("nivel", 1),
                    "minutes": p.get("minutos"),
                    "version": p.get("version", 1),
                    "estado": p.get("estado"),
                    "progreso": p.get("mi_progreso"),
                }
                for p in respuesta.get("practicas", [])
            }
            ESTADO["catalogo_cargado"] = True
            ESTADO["red"] = ""
        else:
            ESTADO["red"] = error
        redibujar()
        if al_terminar:
            al_terminar(error)

    red.pedir("GET", "/api/addon/v1/practicas", listo)


def guardar_en_cache(datos):
    try:
        nombre = "".join(c if c.isalnum() or c in "._-" else "_" for c in datos["id"])
        (_carpeta_cache() / f"{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    except OSError as error:
        print(f"[Amatista] No se pudo guardar la práctica en caché: {error}")


# --- Práctica activa -------------------------------------------------------------


def escena(context=None):
    context = context or bpy.context
    return getattr(context, "scene", None) or bpy.context.scene


def practica_activa(context=None):
    sc = escena(context)
    texto = sc.amatista.practica_json if sc else ""
    if not texto:
        return None
    clave = hashlib.sha1(texto.encode("utf-8"), usedforsecurity=False).hexdigest()
    if ESTADO["clave"] != clave:
        try:
            ESTADO["practica"] = _motor.practica.parse_practice(json.loads(texto))
        except Exception as error:  # noqa: BLE001
            print(f"[Amatista] La práctica guardada no es válida: {error}")
            ESTADO["practica"] = None
        ESTADO["clave"] = clave
        ESTADO["reporte"] = None
    return ESTADO["practica"]


def practica_borrador():
    from . import autor

    datos = autor.leer_borrador()
    if not datos:
        return None
    try:
        return _motor.practica.parse_practice(datos)
    except Exception:  # noqa: BLE001
        return None


USADA = "amatista_practica"  # marca en la escena: la práctica que se hizo en ella (aunque se cierre)
USADA_EN = "amatista_practica_en"  # cuándo se abrió (si hay dos escenas de la misma práctica, gana la última)
PREFIJO_ESCENA = "Amatista · "


def _practica_de_escena(sc):
    return sc.amatista.practica_id or sc.get(USADA, "")


def _escena_para(context, practica, origen):
    """Cada práctica tiene su propia escena de Blender (add-on 3.5).

    Antes, abrir otra práctica la cargaba en la misma escena y lo de la
    anterior seguía ahí (el tren aparecía en la práctica de la espada). Ahora:

    - la escena actual sirve si nunca tuvo práctica o ya es la de esta;
    - si la práctica sigue a la anterior (``starter.from_practice``: pintar
      la nave que modelaste), se queda en la actual;
    - si no, se vuelve a la escena de esta práctica o se crea una vacía.

    Nada se borra: lo de la práctica anterior queda en su escena (selector
    de escenas arriba a la derecha) y se recupera al volver a abrirla.
    """
    sc = escena(context)
    anterior = _practica_de_escena(sc)
    inicio = getattr(practica, "starter", None)
    continua = bool(inicio is not None and inicio.from_practice and inicio.from_practice == anterior)
    if not anterior or anterior == practica.id or origen == "borrador" or continua:
        return sc, ""
    suyas = [s for s in bpy.data.scenes if _practica_de_escena(s) == practica.id]
    destino = max(suyas, key=lambda s: float(s.get(USADA_EN, 0.0)), default=None)  # la última en que trabajaste
    creada = destino is None
    if creada:
        destino = bpy.data.scenes.new((PREFIJO_ESCENA + practica.title)[:63])
        destino.unit_settings.system = sc.unit_settings.system
    ventana = getattr(context, "window", None) or getattr(bpy.context, "window", None)
    ventanas = [ventana] if ventana is not None else list(getattr(bpy.context.window_manager, "windows", ()))
    if not ventanas:
        raise RuntimeError("No hay una ventana de Blender para cambiar de escena")
    _a_modo_objeto()  # la malla en edición se guarda antes de dejar su escena
    ventanas[0].scene = destino
    titulo = _titulo_de(anterior)
    if creada:
        return destino, f"Empiezas en una escena nueva. Lo de «{titulo}» quedó guardado en su escena."
    return destino, f"Volviste a tu escena de esta práctica. Lo de «{titulo}» sigue en la suya."


def _a_modo_objeto():
    obj = getattr(bpy.context, "active_object", None)
    if obj is not None and getattr(obj, "mode", "OBJECT") != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as error:
            print(f"[Amatista] No se pudo volver a Modo Objeto: {error}")


def _titulo_de(practica_id):
    meta = catalogo().get(practica_id) or {}
    return meta.get("title") or practica_id


def activar(context, datos, origen="paquete"):
    """Abre una práctica (dict JSON) en su propia escena y la evalúa."""
    resultado = _motor.practica.compile_practice(datos)
    if resultado.practice is None:
        raise ValueError(resultado.errors[0] if resultado.errors else "Práctica inválida")
    sc, cambio = _escena_para(context, resultado.practice, origen)
    if cambio:
        context = bpy.context  # el contexto del operador sigue apuntando a la escena anterior
    sc[USADA] = datos["id"]
    sc[USADA_EN] = time.time()
    nueva = sc.amatista.practica_id != datos["id"]
    sc.amatista.practica_id = datos["id"]
    sc.amatista.practica_json = json.dumps(datos, ensure_ascii=False)
    sc.amatista.origen = origen
    if nueva:
        sc.amatista.pistas_json = "{}"
        sc.amatista.correcciones = 0
        sc.amatista.mejor_progreso = 0.0
        sc.amatista.progreso_enviado = -1.0
        sc.amatista.completada_enviada = False
        sc.amatista.avisos_vistos = ""
        sc.amatista.celebrada = False
        ESTADO["aprobados_antes"] = {}
        ESTADO["sync"] = ""
        guia.reiniciar()
        aprendizaje.reiniciar_sesion()
    if origen != "borrador":
        guardar_en_cache(datos)
    try:
        preparada = escenarios.preparar(sc, resultado.practice)
    except Exception as error:  # noqa: BLE001 - una escena de inicio rota no impide practicar
        preparada = None
        print(f"[Amatista] No se pudo preparar la escena: {error}")
    try:
        tema = escenarios.aplicar_ambiente(sc, datos["id"])
    except Exception as error:  # noqa: BLE001 - el ambiente es decoración: nunca impide practicar
        tema = None
        print(f"[Amatista] No se pudo aplicar el ambiente del tema: {error}")
    if cambio:
        guia.avisar("Práctica nueva, escena nueva", cambio, "animo")
    if preparada:
        guia.avisar("Escena lista", temas.voz(tema, preparada) if tema else preparada, "animo")
    try:
        enfoque.al_abrir_practica(resultado.practice, nueva)
    except Exception as error:  # noqa: BLE001 - enfocar es comodidad: nunca impide practicar
        print(f"[Amatista] No se pudo enfocar Blender: {error}")
    evaluar(context, "abrir")
    if nueva:
        _abrir_teoria(resultado.practice)
    enlace.latir_pronto()
    return resultado


def reiniciar(context):
    """«Empezar de nuevo» (motor 3.5): una escena limpia para la práctica, sin borrar nada.

    La escena de antes se queda en el archivo con «(anterior)» en el nombre
    y deja de ser la de la práctica: abrirla otra vez trae la nueva.
    """
    sc = escena(context)
    practica = practica_activa(context)
    if practica is None:
        return None
    datos = json.loads(sc.amatista.practica_json)
    origen = sc.amatista.origen or "paquete"
    _a_modo_objeto()
    cerrar(context)
    sc[USADA] = f"{practica.id}#anterior"
    sc.name = (sc.name + " (anterior)")[:63]
    nueva = bpy.data.scenes.new((PREFIJO_ESCENA + practica.title)[:63])
    nueva.unit_settings.system = sc.unit_settings.system
    ventana = getattr(context, "window", None) or (bpy.context.window_manager.windows[0]
                                                   if bpy.context.window_manager.windows else None)
    if ventana is None:
        return None
    ventana.scene = nueva
    activar(bpy.context, datos, origen)
    return f"Empiezas de nuevo en una escena limpia. Lo anterior quedó en «{sc.name}»."


def nombre_para_guardar(practica):
    """mi_espada.blend: el nombre que pide el paso «Guarda tu…» (file.named) o el de la práctica."""
    for objetivo in getattr(practica, "targets", ()):
        if objetivo.validator == "file.named" and objetivo.params.get("contains"):
            return f"mi_{objetivo.params['contains']}.blend"
    return f"mi_{practica.id.split('.')[-1]}.blend"


def guardar_practica(context):
    """«Guardar» desde la plataforma: el archivo de siempre o, si es nuevo, Documentos/Amatista/mi_….blend."""
    practica = practica_activa(context)
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
        return f"Guardado en {Path(bpy.data.filepath).name}."
    if practica is None:
        return None
    carpeta = Path.home() / "Documents" / "Amatista"
    if not (Path.home() / "Documents").exists():
        carpeta = Path.home() / "Amatista"
    carpeta.mkdir(parents=True, exist_ok=True)
    base = Path(nombre_para_guardar(practica)).stem
    ruta, n = carpeta / f"{base}.blend", 1
    while ruta.exists():  # nunca pisa un archivo que ya existe
        n += 1
        ruta = carpeta / f"{base}_{n}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(ruta))
    return f"Guardado en {ruta}."


def mostrar_en_amatista(context=None):
    """Lleva la barra lateral a Amatista › Practicar (al abrir desde la plataforma)."""
    context = context or bpy.context
    wm = getattr(context, "window_manager", None)
    if wm is not None and hasattr(wm, "amatista"):
        wm.amatista.pestana = "practicar"
    for ventana in getattr(wm, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.show_region_ui = True
                for region in area.regions:
                    if region.type == "UI":
                        try:
                            region.active_panel_category = "Amatista"
                        except (AttributeError, TypeError, ValueError):
                            pass
    redibujar()


def _abrir_teoria(practica):
    """Al abrir: primero el repaso de lo anterior (si toca) y luego la píldora de inicio."""
    if guia.nivel() == guia.NIVEL_SILENCIOSO:
        return
    if aprendizaje.repasos_pendientes(practica):
        _invocar("amatista.repaso")
    elif aprendizaje.pildora_principal() is not None:
        _invocar("amatista.pildora")


def cerrar(context):
    sc = escena(context)
    try:
        escenarios.restaurar_ambiente(sc)
        escenarios._fondo_del_mundo(False)
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] No se pudo restaurar el mundo: {error}")
    sc.amatista.practica_id = ""
    sc.amatista.practica_json = ""
    ESTADO.update(reporte=None, clave=None, practica=None, sync="")
    guia.reiniciar()
    try:
        enfoque.desactivar()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] No se pudo salir del modo enfocado: {error}")
    enlace.latir_pronto()
    redibujar()


def abrir_por_id(context, practica_id, al_terminar=None):
    """Abre una práctica del catálogo; si solo está en el servidor, la descarga."""
    meta = catalogo().get(practica_id)
    if meta and meta.get("definicion"):
        activar(context, meta["definicion"], meta["origen"])
        if al_terminar:
            al_terminar(None)
        return

    def listo(respuesta, error, estado):
        if error is None:
            try:
                activar(bpy.context, respuesta["definicion"], "servidor")
            except ValueError as fallo:
                error = str(fallo)
        if al_terminar:
            al_terminar(error)

    red.pedir("GET", f"/api/addon/v1/practicas/{practica_id}", listo)


def cargar_practica_actual(al_terminar=None):
    """La práctica que el alumno abrió en la plataforma (su lección actual)."""

    def listo(respuesta, error, estado):
        if error is None and respuesta and respuesta.get("definicion"):
            sc = bpy.context.scene
            if sc and sc.amatista.practica_id in ("", respuesta["definicion"]["id"]):
                activar(bpy.context, respuesta["definicion"], "servidor")
        if al_terminar:
            al_terminar(error, respuesta)

    red.pedir("GET", "/api/addon/v1/practica-actual", listo)


# --- Evaluación --------------------------------------------------------------------


def pistas(context=None):
    try:
        return {k: int(v) for k, v in json.loads(escena(context).amatista.pistas_json or "{}").items()}
    except (ValueError, AttributeError):
        return {}


def capturar(sc):
    """Foto de la escena; «guardado» ignora lo que escribe el propio add-on."""
    estado = _motor.adapter.capture_scene(sc)
    if estado.file_path and not estado.file_saved and not ESTADO["cambios_desde_guardar"]:
        estado = dataclasses.replace(estado, file_saved=True)
    return estado


def evaluar(context=None, motivo="manual"):
    practica = practica_activa(context)
    if practica is None:
        ESTADO["reporte"] = None
        return None
    sc = escena(context)
    foto = capturar(sc)
    reporte = _motor.MOTOR.evaluate(practica, foto)
    _contar_correcciones(sc, reporte)
    anterior = ESTADO["reporte"]
    ESTADO["reporte"] = reporte
    ESTADO["sucio"] = False
    if reporte.progress > sc.amatista.mejor_progreso:
        sc.amatista.mejor_progreso = reporte.progress
    try:
        guia.actualizar(context, practica, foto, reporte, motivo)
    except Exception as error:  # noqa: BLE001 - la guía nunca impide evaluar
        print(f"[Amatista] Error en la guía: {error}")
    try:
        aprendizaje.actualizar_pildoras(practica, foto, reporte)
        nueva = aprendizaje.pildora_principal()
        if motivo != "abrir" and nueva is not None and nueva.id in aprendizaje.ESTADO["nuevas"]:
            guia.avisar(f"Teoría: {nueva.title}", "Míralo en N › Amatista › Aprender.", "cerca")
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Error en las píldoras: {error}")
    redibujar()
    _avisar_herramientas(sc, reporte)
    if reporte.completed and sc.amatista.origen != "borrador":
        aprendizaje.marcar_completada(practica.id)
    if reporte.completed and not sc.amatista.celebrada and motivo != "abrir":
        sc.amatista.celebrada = True
        _invocar("amatista.felicitar")
    if anterior is None or anterior.progress != reporte.progress or anterior.completed != reporte.completed:
        programar_sincronizacion()
        enlace.latir_pronto()  # la plataforma ve el avance en vivo
    return reporte


def lista_instructor(reporte=None):
    """(título, [{texto, ok, estado, consejo}]) de la figura (motor 3.5), o (None, []).

    La dan figure.silhouette y figure.recognize: qué partes del modelo ya
    están y qué falta, con la tecla que lo arregla. Primero la del paso
    actual; si el paso actual no es la figura, la de la figura.
    """
    reporte = reporte or ESTADO["reporte"]
    if reporte is None:
        return None, []
    resultados = list(reporte.results)
    actual = reporte.result(reporte.current_target_id) if reporte.current_target_id else None
    if actual is not None:
        resultados.insert(0, actual)
    for r in resultados:
        lista = (r.details or {}).get("checklist") if r is not None else None
        if lista:
            practica = ESTADO["practica"]
            objetivo = practica.target(r.target_id) if practica is not None else None
            return (objetivo.title if objetivo is not None and objetivo.title else r.target_id), list(lista)
    return None, []


def evaluar_pronto():
    if not bpy.app.timers.is_registered(_evaluar_ahora):
        bpy.app.timers.register(_evaluar_ahora, first_interval=0.05)


def _evaluar_ahora():
    try:
        evaluar(bpy.context, "abrir")
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Error al evaluar: {error}")
    return None


def _contar_correcciones(sc, reporte):
    """Un objetivo que estaba bien, se rompió y se volvió a arreglar = corrección."""
    antes = ESTADO["aprobados_antes"]
    for r in reporte.results:
        historia = antes.get(r.target_id, "")
        nuevo = "1" if r.passed else "0"
        if not historia.endswith(nuevo):
            historia = (historia + nuevo)[-3:]
            if historia == "101":
                sc.amatista.correcciones += 1
        antes[r.target_id] = historia


def _avisar_herramientas(sc, reporte):
    p = ajustes.prefs()
    if not reporte.tool_warnings or (p and not p.avisar_herramientas):
        return
    vistos = set(filter(None, sc.amatista.avisos_vistos.split(",")))
    nuevos = [w for w in reporte.tool_warnings if w.tool_id not in vistos]
    if not nuevos:
        return
    sc.amatista.avisos_vistos = ",".join(sorted(vistos | {w.tool_id for w in nuevos}))
    _invocar("amatista.aviso_herramienta", herramienta=nuevos[0].tool_id)


def _invocar(operador, **propiedades):
    """Abre un diálogo desde un temporizador (los manejadores no tienen ventana)."""
    if bpy.app.background:
        return

    def abrir():
        ventana = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
        if ventana is None:
            return None
        categoria, nombre = operador.split(".")
        with bpy.context.temp_override(window=ventana):
            try:
                getattr(getattr(bpy.ops, categoria), nombre)("INVOKE_DEFAULT", **propiedades)
            except RuntimeError as error:
                print(f"[Amatista] No se pudo abrir el diálogo {operador}: {error}")
        return None

    bpy.app.timers.register(abrir, first_interval=0.05)


def pedir_pista(context, target_id=None):
    practica = practica_activa(context)
    if practica is None:
        return None
    reporte = ESTADO["reporte"] or evaluar(context)
    target_id = target_id or (reporte.current_target_id if reporte else None)
    if not target_id:
        return None
    estado = pistas(context)
    revelada = _motor.pedagogia.next_hint(practica, estado, target_id)
    escena(context).amatista.pistas_json = json.dumps(estado)
    redibujar()
    return revelada


# --- Sincronización con la plataforma ------------------------------------------------


def vinculado():
    p = ajustes.prefs()
    return bool(p and p.token)


def programar_sincronizacion(segundos=3.0):
    p = ajustes.prefs()
    if not (p and p.sincronizar_solo):
        return
    if bpy.app.timers.is_registered(_sincronizar_programado):
        bpy.app.timers.unregister(_sincronizar_programado)
    bpy.app.timers.register(_sincronizar_programado, first_interval=segundos)


def _sincronizar_programado():
    sincronizar(bpy.context)
    return None


def _foto_para_enviar(sc, practica):
    """La foto del intento. La silueta de cada malla solo viaja si la práctica la usa (pesa más que lo demás)."""
    foto = _motor.foto.scene_to_dict(capturar(sc))
    if not any(t.validator == "figure.silhouette" for t in practica.targets):
        for objeto in foto.get("objetos") or ():
            objeto.pop("si", None)
    return foto


def datos_intento(context, modo="alumno"):
    sc = escena(context)
    practica = practica_activa(context)
    return {
        "practica_id": practica.id,
        "version": practica.version,
        "escena": _foto_para_enviar(sc, practica),
        "pistas": pistas(context),
        "correcciones": sc.amatista.correcciones,
        "version_addon": ajustes.VERSION_ADDON,
        "version_motor": _motor.VERSION_MOTOR,
        "sistema": red.sistema(),
        "modo": modo,
        "ayudas": dict(guia.ESTADO["ayudas"]),
    }


def sincronizar(context=None, forzar=False, al_terminar=None):
    """Envía el intento: el servidor reevalúa con el mismo motor y guarda en Oracle."""
    practica = practica_activa(context)
    reporte = ESTADO["reporte"]
    sc = escena(context)
    if practica is None or reporte is None:
        return
    if sc.amatista.origen == "borrador":
        return  # un borrador del modo desarrollador no es progreso de alumno
    if not vinculado():
        ESTADO["sync"] = SYNC_SIN_CUENTA
        redibujar()
        return
    sin_cambios = reporte.progress <= sc.amatista.progreso_enviado and (
        not reporte.completed or sc.amatista.completada_enviada
    )
    if sin_cambios and not forzar:
        return
    datos = datos_intento(context)
    ESTADO["sync"] = SYNC_ENVIANDO
    redibujar()
    enviado_progreso = reporte.progress
    enviado_completo = reporte.completed

    def listo(respuesta, error, estado):
        escena_actual = bpy.context.scene
        if error is None:
            ESTADO["sync"] = SYNC_GUARDADO
            ESTADO["sync_detalle"] = ""
            ESTADO["ultima_sync"] = time.time()
            if escena_actual and escena_actual.amatista.practica_id == datos["practica_id"]:
                escena_actual.amatista.progreso_enviado = max(escena_actual.amatista.progreso_enviado, enviado_progreso)
                escena_actual.amatista.completada_enviada |= enviado_completo
            red.vaciar_cola()
        elif estado == 401:
            ESTADO["sync"] = SYNC_SIN_CUENTA
            ESTADO["sync_detalle"] = "Tu vínculo con Amatista venció: vuelve a vincular."
            p = ajustes.prefs()
            if p:
                p.token = ""
        elif estado and 400 <= estado < 500:
            ESTADO["sync"] = SYNC_ERROR
            ESTADO["sync_detalle"] = error
        else:
            red.encolar("/api/addon/v1/intentos", datos)
            ESTADO["sync"] = SYNC_PENDIENTE
            ESTADO["sync_detalle"] = error
        redibujar()
        if al_terminar:
            al_terminar(respuesta, error)

    red.pedir("POST", "/api/addon/v1/intentos", listo, datos)


# --- Observador de la escena (sección 16: eventos, no evaluación continua) ----------------


def redibujar():
    if bpy.app.background:
        return
    for ventana in bpy.context.window_manager.windows:
        for area in ventana.screen.areas:
            if area.type in ("VIEW_3D", "PREFERENCES"):
                area.tag_redraw()


# Lo que el alumno cambia: objetos, mallas, materiales, luces, cámaras y animación (motor v3).
OBSERVADOS = (
    bpy.types.Object, bpy.types.Mesh, bpy.types.Material, bpy.types.Collection, bpy.types.Light,
    bpy.types.Camera, bpy.types.Action,
)


@persistent
def _al_renderizar(scene, *_args):
    """F12 terminado: lo cuenta para render.done (el adaptador lee scene["amatista_renders"])."""
    escena_actual = bpy.context.scene or scene
    if escena_actual is None:
        return
    escena_actual["amatista_renders"] = int(escena_actual.get("amatista_renders", 0)) + 1
    if escena_actual.amatista.practica_json:
        ESTADO["sucio"] = True
        ESTADO["ultimo_cambio"] = time.time()


@persistent
def _al_cambiar(scene, depsgraph=None):
    # Cambiar las propiedades de Amatista en la escena también avisa al
    # depsgraph: solo cuentan los cambios en objetos, mallas y materiales.
    if depsgraph is not None and not any(
        isinstance(u.id, OBSERVADOS)
        for u in depsgraph.updates
    ):
        return
    ESTADO["cambios_desde_guardar"] = True
    if not scene.amatista.practica_json:
        return
    ESTADO["sucio"] = True
    ESTADO["ultimo_cambio"] = time.time()


@persistent
def _al_guardar(*_args):
    ESTADO["cambios_desde_guardar"] = False
    if bpy.context.scene and bpy.context.scene.amatista.practica_json:
        bpy.app.timers.register(lambda: (evaluar(bpy.context, "guardar"), None)[1], first_interval=0.1)


@persistent
def _al_abrir(*_args):
    ESTADO.update(reporte=None, clave=None, practica=None, aprobados_antes={}, sync="",
                  cambios_desde_guardar=not bpy.data.filepath)
    guia.reiniciar()
    aprendizaje.reiniciar_sesion()
    if bpy.context.scene and bpy.context.scene.amatista.practica_json:
        bpy.app.timers.register(lambda: (evaluar(bpy.context, "abrir"), None)[1], first_interval=0.3)
        bpy.app.timers.register(_ambiente_al_abrir, first_interval=0.35)
    else:
        enfoque.desactivar()
    enfoque.al_abrir_archivo()


def _ambiente_al_abrir():
    """El color del cielo viaja en el .blend; el fondo de las vistas 3D se vuelve a encender."""
    sc = bpy.context.scene
    if sc is not None and sc.amatista.practica_id:
        try:
            escenarios.aplicar_ambiente(sc, sc.amatista.practica_id)
        except Exception as error:  # noqa: BLE001
            print(f"[Amatista] No se pudo aplicar el ambiente del tema: {error}")
        practica = practica_activa()
        if practica is not None:
            enfoque.al_abrir_practica(practica, nueva=False)  # las vistas del archivo nuevo
    return None


def _vigilante():
    """Cada medio segundo: si la escena cambió y ya se calmó, reevaluar."""
    p = ajustes.prefs()
    sc = bpy.context.scene
    if sc is not None and sc.amatista.practica_json:
        # El motor de render no pasa por el depsgraph: se mira aquí.
        motor = sc.render.engine
        if ESTADO["motor_render"] and motor != ESTADO["motor_render"]:
            ESTADO["sucio"] = True
            ESTADO["ultimo_cambio"] = time.time() - 1
        ESTADO["motor_render"] = motor
    if ESTADO["sucio"] and (p is None or p.comprobar_solo) and time.time() - ESTADO["ultimo_cambio"] > 0.4:
        try:
            evaluar(bpy.context, "cambio")
        except Exception as error:  # noqa: BLE001 - nunca romper el temporizador
            ESTADO["sucio"] = False
            print(f"[Amatista] Error al evaluar: {error}")
    return 0.5


def register():
    bpy.app.handlers.depsgraph_update_post.append(_al_cambiar)
    bpy.app.handlers.save_post.append(_al_guardar)
    bpy.app.handlers.load_post.append(_al_abrir)
    bpy.app.handlers.render_complete.append(_al_renderizar)
    if not bpy.app.timers.is_registered(_vigilante):
        bpy.app.timers.register(_vigilante, first_interval=1.0, persistent=True)


def unregister():
    for lista, funcion in (
        (bpy.app.handlers.depsgraph_update_post, _al_cambiar),
        (bpy.app.handlers.save_post, _al_guardar),
        (bpy.app.handlers.load_post, _al_abrir),
        (bpy.app.handlers.render_complete, _al_renderizar),
    ):
        if funcion in lista:
            lista.remove(funcion)
    for temporizador in (_vigilante, _sincronizar_programado, _ambiente_al_abrir):
        if bpy.app.timers.is_registered(temporizador):
            bpy.app.timers.unregister(temporizador)
