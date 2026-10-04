"""Amatista Author: el Motor de Desarrollo dentro de Blender.

El borrador de la práctica vive en un bloque de texto del .blend
(«amatista_practica.json»): se guarda con el archivo de la escena de
referencia y también se puede editar a mano en el Editor de texto. Las
herramientas de la interfaz (Tagger, constructor de objetivos, pistas...)
leen y escriben ese JSON con estas funciones; nada toca el texto
directamente (regla 29 de la especificación).
"""
import json
import re

import bpy

from . import _motor, ajustes, red


def _nombre_texto():
    sc = bpy.context.scene
    return (sc.amatista_autor.texto if sc else "") or "amatista_practica.json"


def texto_borrador(crear=False):
    nombre = _nombre_texto()
    texto = bpy.data.texts.get(nombre)
    if texto is None and crear:
        texto = bpy.data.texts.new(nombre)
    return texto


def leer_borrador():
    texto = texto_borrador()
    if texto is None:
        return None
    try:
        datos = json.loads(texto.as_string() or "null")
    except ValueError:
        return None
    return datos if isinstance(datos, dict) else None


def escribir_borrador(datos):
    texto = texto_borrador(crear=True)
    texto.clear()
    texto.write(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")
    return datos


def _slug(texto):
    texto = texto.strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        texto = texto.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")[:40] or "objetivo"


def nuevo_borrador(practica_id, titulo, nivel):
    datos = {
        "schema": _motor.practica.SUPPORTED_SCHEMA,
        "id": practica_id.strip().lower(),
        "version": 1,
        "title": titulo.strip() or "Nueva práctica",
        "level": int(nivel),
        "description": "",
        "roles": {},
        "targets": [],
    }
    return escribir_borrador(datos)


def borrador_desde_practica(definicion):
    return escribir_borrador(json.loads(json.dumps(definicion)))


def asegurar_rol(rol_id, etiqueta=""):
    """Declara el rol en el borrador (el Tagger solo ofrece roles declarados)."""
    datos = leer_borrador()
    if datos is None:
        return None
    rol_id = rol_id.strip().lower().replace(" ", "_")
    roles = datos.get("roles")
    if isinstance(roles, list):
        roles = {r["id"]: {"label": r.get("label", r["id"])} for r in roles if isinstance(r, dict) and r.get("id")}
    roles = roles or {}
    if rol_id not in roles:
        roles[rol_id] = {"label": etiqueta.strip() or rol_id.replace("_", " ").capitalize()}
    datos["roles"] = roles
    escribir_borrador(datos)
    return rol_id


def parametros_desde_formulario(autor):
    """Traduce el formulario del constructor a params del validador elegido."""
    spec = _motor.MOTOR.registry.spec(autor.plantilla)
    params = {}
    if spec is None:
        return params
    nombres = {p.name for p in spec.params}
    if "role" in nombres and autor.obj_rol:
        params["role"] = autor.obj_rol
    if "reference_role" in nombres and autor.obj_rol_ref:
        params["reference_role"] = autor.obj_rol_ref
    if autor.obj_nombre and "name" in nombres and "role" not in params:
        params["name"] = autor.obj_nombre
    if "equals" in nombres:
        params["equals"] = int(autor.obj_cantidad)
    if "axis" in nombres:
        params["axis"] = autor.obj_eje
        params["min"] = round(float(autor.obj_minimo), 4)
        params["max"] = round(float(autor.obj_maximo), 4)
    if "modifier" in nombres:
        params["modifier"] = autor.obj_modificador.strip().upper()
    if "collection" in nombres:
        params["collection"] = autor.obj_texto.strip()
    if "contains" in nombres:
        params["contains"] = autor.obj_texto.strip()
    if "material" in nombres and autor.obj_texto.strip():
        params["material"] = autor.obj_texto.strip()
    return params


def agregar_objetivo(autor):
    datos = leer_borrador()
    if datos is None:
        raise ValueError("Primero crea o abre un borrador de práctica.")
    objetivos = datos.setdefault("targets", [])
    base = autor.obj_id.strip() or _slug(autor.obj_titulo or autor.plantilla.split(".")[-1])
    objetivo_id, n = base, 2
    while any(t.get("id") == objetivo_id for t in objetivos):
        objetivo_id, n = f"{base}_{n}", n + 1
    objetivo = {
        "id": objetivo_id,
        "title": autor.obj_titulo.strip() or objetivo_id,
        "validator": autor.plantilla,
        "params": parametros_desde_formulario(autor),
        "weight": round(float(autor.obj_peso), 2),
    }
    if autor.obj_requiere and autor.obj_requiere != "__ninguno__":
        objetivo["requires"] = [autor.obj_requiere]
    if autor.obj_consejo.strip():
        objetivo["tip"] = autor.obj_consejo.strip()
    if autor.obj_opcional:
        objetivo["optional"] = True
    objetivos.append(objetivo)
    escribir_borrador(datos)
    return objetivo


def _objetivo(datos, objetivo_id):
    for t in datos.get("targets", []):
        if t.get("id") == objetivo_id:
            return t
    raise ValueError(f"No existe el objetivo «{objetivo_id}».")


def quitar_objetivo(objetivo_id):
    datos = leer_borrador() or {}
    datos["targets"] = [t for t in datos.get("targets", []) if t.get("id") != objetivo_id]
    for t in datos["targets"]:
        if objetivo_id in t.get("requires", []):
            t["requires"] = [r for r in t["requires"] if r != objetivo_id]
    escribir_borrador(datos)


def mover_objetivo(objetivo_id, paso):
    datos = leer_borrador() or {}
    objetivos = datos.get("targets", [])
    indice = next((i for i, t in enumerate(objetivos) if t.get("id") == objetivo_id), None)
    if indice is None:
        return
    nuevo = max(0, min(len(objetivos) - 1, indice + paso))
    objetivos.insert(nuevo, objetivos.pop(indice))
    escribir_borrador(datos)


def agregar_pista(objetivo_id, texto):
    if not texto.strip():
        raise ValueError("Escribe el texto de la pista.")
    datos = leer_borrador() or {}
    objetivo = _objetivo(datos, objetivo_id)
    objetivo.setdefault("hints", []).append(texto.strip())
    escribir_borrador(datos)
    return len(objetivo["hints"])


def quitar_pista(objetivo_id, indice):
    datos = leer_borrador() or {}
    objetivo = _objetivo(datos, objetivo_id)
    pistas = objetivo.get("hints", [])
    if 0 <= indice < len(pistas):
        pistas.pop(indice)
    escribir_borrador(datos)


def compilar():
    datos = leer_borrador()
    if datos is None:
        return None
    return _motor.practica.compile_practice(datos)


def probar_borrador(context):
    """Live validation: el borrador se vuelve la práctica activa de la escena."""
    from . import practicas

    datos = leer_borrador()
    if datos is None:
        raise ValueError("No hay borrador.")
    resultado = compilar()
    if not resultado.ok:
        raise ValueError(resultado.errors[0])
    practicas.activar(context, datos, origen="borrador")
    return resultado


def roles_en_escena(context):
    """{rol: [objetos]} para el resumen del Tagger."""
    resumen = {}
    for obj in context.scene.objects:
        rol = _motor.tagger.get_role(obj)
        if rol:
            resumen.setdefault(rol, []).append(obj.name)
    return resumen


def publicar(curso_id="", leccion_id="", nota="", al_terminar=None):
    """Registra el borrador en Amatista (Oracle). Queda en borrador hasta que un
    administrador lo publique desde la plataforma: Author nunca publica solo."""
    resultado = compilar()
    if resultado is None or not resultado.ok:
        raise ValueError(resultado.errors[0] if resultado else "No hay borrador.")
    cuerpo = {
        "definicion": leer_borrador(),
        "curso_id": curso_id.strip() or None,
        "leccion_id": leccion_id.strip() or None,
        "nota": nota.strip() or None,
        "version_addon": ajustes.VERSION_ADDON,
        "version_blender": bpy.app.version_string,
    }

    def listo(respuesta, error, estado):
        if error is None and respuesta.get("version"):
            datos = leer_borrador() or {}
            datos["version"] = respuesta["version"]
            escribir_borrador(datos)
        if al_terminar:
            al_terminar(respuesta, error)

    red.pedir("POST", "/api/addon/v1/practicas", listo, cuerpo)


def registrar_verificacion(curso_id, leccion_id, resultado, diferencias="", al_terminar=None):
    """Anota en la matriz de compatibilidad que esta lección funciona en este Blender."""
    version = ".".join(str(v) for v in bpy.app.version)
    cuerpo = {
        "curso_id": curso_id,
        "leccion_id": leccion_id,
        "version_blender": version,
        "sistema": red.sistema(),
        "resultado": resultado,
        "version_addon": ajustes.VERSION_ADDON,
        "diferencias": diferencias or None,
    }
    red.pedir("POST", "/api/blender/verificaciones", lambda r, e, s: al_terminar and al_terminar(r, e), cuerpo)


def exportar(ruta):
    resultado = compilar()
    if resultado is None or not resultado.ok:
        raise ValueError(resultado.errors[0] if resultado else "No hay borrador.")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(_motor.practica.dumps_practice(resultado.practice))
    return ruta
