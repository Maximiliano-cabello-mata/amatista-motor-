"""Temática por módulo (add-on 3.2): nombre, colores, mascota y jefe final.

La fuente es practices/blender/temas.json, la misma que usa la plataforma
(frontend/src/components/temas/temas.js). construir.py la empaqueta como
practicas/temas.json; al trabajar desde el repositorio se lee de
practices/blender/temas.json.

Todo aquí es Python puro (sin bpy): lo usan el HUD, los paneles y el
ambiente de la vista 3D, y se prueba con pytest sin Blender
(addon/tests/test_temas.py). El catálogo de prácticas y el backend ignoran
este archivo porque filtran por schema «amatista.practice/».
"""
import json
import time
from pathlib import Path

TEMA_POR_DEFECTO = "cristal"
PERIODO_MASCOTA = 12.0  # segundos entre un mensaje de la mascota y el siguiente

# Si temas.json no está (paquete viejo o roto), el add-on sigue con el estilo de Amatista.
_RESPALDO = {
    "nombre": "La cueva del cristal",
    "lema": "Cada módulo te acerca a dominar el cristal de Amatista.",
    "colores": {"acento": "#B57EDC", "suave": "#E2C6F5", "cielo": "#1E0F29", "suelo": "#0F0815"},
    "escena": "cristales",
    "mascota": {"nombre": "Ami", "especie": "cristal de amatista",
                "hola": "Soy Ami, el cristal de Amatista. Vamos paso a paso.", "consejos": [], "datos": []},
    "jefe": {"nombre": "Guardián del Cristal", "frase": "Demuestra lo que aprendiste."},
}

# Mascotas en pixel art de 10×10 (diseños originales de Amatista, de arriba abajo).
# a = acento del tema · s = suave · w = blanco · o = oscuro · . = vacío
PIXELES = {
    "taller": (  # Tuerca: robot de cuerda con su llave
        "....a.....",
        "....a.....",
        "..ssssss..",
        ".swwsswws.",
        ".swosswos.",
        "assssssssa",
        ".ss.oo.ss.",
        "..ssssss..",
        "..a....a..",
        ".aa....aa.",
    ),
    "herreria": (  # Chispa: salamandra con cresta de fuego
        "....a..a..",
        "...aa.aa..",
        "..aaaaaa..",
        ".asssssa..",
        ".swossswo.",
        ".ssssssss.",
        "..ssooss..",
        "...ssss.a.",
        "..s.ss.aa.",
        ".s......a.",
    ),
    "hangar": (  # Orbi: satélite con antena y paneles
        "....a.....",
        "....s.....",
        "...ssss...",
        "a.swwwws.a",
        "aaswowos.a",
        "aaswwwwsaa",
        "a.ssooss.a",
        "...ssss...",
        "....ss....",
        "...s..s...",
    ),
    "pintura": (  # Gotita: gota de pintura
        "....a.....",
        "....aa....",
        "...aaaa...",
        "..aaaaaa..",
        ".aawoawoa.",
        ".aaaaaaaa.",
        ".aasoosaa.",
        ".aaaaaaaa.",
        "..aaaaaa..",
        "...ssss...",
    ),
    "cine": (  # Foco: reflector con patas
        "..ssssss..",
        ".swwwwwws.",
        ".swowwows.",
        ".swwwwwws.",
        "..ssssss..",
        "....oo....",
        "....ss....",
        "...a..a...",
        "..a....a..",
        ".aa....aa.",
    ),
    "circo": (  # Boing: pelota saltarina
        "...aaaa...",
        "..aaaaaa..",
        ".aawaawaa.",
        ".aaoaaoaa.",
        ".ssssssss.",
        ".aaaooaaa.",
        "..aaaaaa..",
        "...aaaa...",
        "..........",
        ".s..ss..s.",
    ),
    "aldea": (  # Cota: castor arquitecto con casco
        "...aaaa...",
        "..aaaaaa..",
        ".ssssssss.",
        ".swosswos.",
        ".ssssssss.",
        "..ssoohss.".replace("h", "s"),
        "...swws...",
        "..ssssss..",
        ".aassssaa.",
        "..o....o..",
    ),
    "archivo": (  # Índigo: búho cartógrafo
        ".a......a.",
        ".aa....aa.",
        "awwwaawwwa",
        "awowaawowa",
        "awwwsswwwa",
        ".aaassaaa.",
        ".asssssssa",
        ".asssssssa",
        "..aaaaaaa.",
        "..o.o..o..",
    ),
    "galeria": (  # Marco: camaleón curador
        "..........",
        "...aaaa...",
        "..aaaaaaa.",
        ".aawoaaaaa",
        ".aaaaaaaa.",
        "..aassaa..",
        "...aaaasa.",
        "..a..a.sa.",
        "......ss..",
        "..........",
    ),
    "portal": (  # Píxel: gato holográfico
        ".a......a.",
        ".aa....aa.",
        ".aaaaaaaa.",
        ".awoaawoa.",
        ".aaaaaaaa.",
        ".aaasoaaa.",
        "..aaaaaa..",
        "..s.ss.s..",
        ".ssssssss.",
        "..s....s..",
    ),
    "cristal": (  # Ami: cristal de amatista
        "....ss....",
        "...saas...",
        "..saaaas..",
        ".saaaaaas.",
        ".sawoawas.",
        ".saaaaaas.",
        ".saaooaas.",
        "..saaaas..",
        "...saas...",
        "....ss....",
    ),
}

_CACHE = {"datos": None, "ruta": None}
ESTADO = {"extra": 0}  # «Otro dato»: lo que el alumno adelantó a la mascota


# --- Carga ---------------------------------------------------------------------------------


def carpeta_paquete():
    """La misma regla que practicas.carpeta_paquete (sin importar bpy)."""
    empaquetadas = Path(__file__).resolve().parent / "practicas"
    if empaquetadas.is_dir():
        return empaquetadas
    return Path(__file__).resolve().parents[2] / "practices"


def ruta_temas(carpeta=None):
    """practicas/temas.json en el paquete; practices/blender/temas.json en el repositorio."""
    carpeta = Path(carpeta) if carpeta is not None else carpeta_paquete()
    for candidata in (carpeta / "temas.json", carpeta / "blender" / "temas.json"):
        if candidata.is_file():
            return candidata
    return None


def cargar(ruta=None, recargar=False):
    """El contenido de temas.json (en caché). Nunca falla: sin archivo, solo el tema de respaldo."""
    if _CACHE["datos"] is not None and not recargar and ruta in (None, _CACHE["ruta"]):
        return _CACHE["datos"]
    archivo = Path(ruta) if ruta is not None else ruta_temas()
    datos = None
    if archivo is not None:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = None
    if not isinstance(datos, dict) or not isinstance(datos.get("temas"), dict):
        datos = {"temas": {}, "practicas": {}, "modulos": {}}
    datos.setdefault("practicas", {})
    datos.setdefault("modulos", {})
    _CACHE.update(datos=datos, ruta=ruta)
    return datos


# --- Consultas -------------------------------------------------------------------------------


def id_tema(practica_id):
    """Id del tema de una práctica: gana el prefijo más largo de «practicas» (blender.bp.m1 → taller)."""
    datos = cargar()
    pid = str(practica_id or "")
    if pid in datos["modulos"]:
        return datos["modulos"][pid]
    mejor, largo = TEMA_POR_DEFECTO, -1
    for prefijo, tema in datos["practicas"].items():
        if (pid == prefijo or pid.startswith(prefijo + ".")) and len(prefijo) > largo:
            mejor, largo = tema, len(prefijo)
    return mejor if mejor in datos["temas"] else TEMA_POR_DEFECTO


def tema(tema_id):
    """Un tema completo por id (con el respaldo si no existe)."""
    datos = cargar()
    base = datos["temas"].get(tema_id)
    if base is None:
        tema_id = TEMA_POR_DEFECTO
        base = datos["temas"].get(TEMA_POR_DEFECTO, _RESPALDO)
    resultado = {**_RESPALDO, **base, "id": tema_id}
    resultado["colores"] = {**_RESPALDO["colores"], **(base.get("colores") or {})}
    resultado["mascota"] = {**_RESPALDO["mascota"], **(base.get("mascota") or {})}
    resultado["jefe"] = {**_RESPALDO["jefe"], **(base.get("jefe") or {})}
    return resultado


def tema_de_practica(practica_id):
    """El tema de la práctica (dict con id, nombre, lema, colores, escena, mascota y jefe)."""
    return tema(id_tema(practica_id))


def hex_a_rgb(hexadecimal):
    """'#F5A524' → (0.96, 0.65, 0.14). Acepta #RGB; si no se entiende, gris medio."""
    texto = str(hexadecimal or "").strip().lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    try:
        return tuple(int(texto[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except (ValueError, IndexError):
        return (0.5, 0.5, 0.5)


def srgb_a_lineal(valor):
    """Un canal sRGB (0–1) en espacio lineal (para colores de escena como World.color)."""
    if valor <= 0.04045:
        return valor / 12.92
    return ((valor + 0.055) / 1.055) ** 2.4


def color_rgba(hexadecimal, alfa=1.0, lineal=False):
    """Color para gpu/blf (sRGB, como el resto del HUD) o lineal para la escena."""
    rgb = hex_a_rgb(hexadecimal)
    if lineal:
        rgb = tuple(srgb_a_lineal(c) for c in rgb)
    return (*rgb, float(alfa))


def mezclar(color_a, color_b, factor):
    """Mezcla dos colores RGBA (factor 0 → a, 1 → b)."""
    return tuple(a + (b - a) * factor for a, b in zip(color_a, color_b))


def mensajes_mascota(tema_dict):
    """[(tipo, texto)]: el saludo y luego consejos y datos curiosos intercalados."""
    mascota = (tema_dict or {}).get("mascota") or {}
    lista = []
    if mascota.get("hola"):
        lista.append(("hola", mascota["hola"]))
    consejos = list(mascota.get("consejos") or [])
    datos = list(mascota.get("datos") or [])
    for i in range(max(len(consejos), len(datos))):
        if i < len(consejos):
            lista.append(("consejo", consejos[i]))
        if i < len(datos):
            lista.append(("dato", datos[i]))
    return lista or [("hola", _RESPALDO["mascota"]["hola"])]


def mensaje_mascota(tema_dict, indice):
    """(tipo, texto) del mensaje número `indice` (da la vuelta; el 0 es el saludo)."""
    lista = mensajes_mascota(tema_dict)
    return lista[int(indice) % len(lista)]


def indice_actual(ahora=None, periodo=PERIODO_MASCOTA):
    """Qué mensaje toca ahora: cambia cada `periodo` segundos (más lo que adelantó el alumno)."""
    ahora = time.time() if ahora is None else ahora
    return int(ahora // periodo) + ESTADO["extra"]


def siguiente_mensaje():
    ESTADO["extra"] += 1


ETIQUETA_TIPO = {"hola": "", "consejo": "Consejo", "dato": "¿Sabías que…?"}


def voz(tema_dict, texto):
    """El texto dicho por la mascota del tema: «Tuerca: …»."""
    nombre = ((tema_dict or {}).get("mascota") or {}).get("nombre")
    return f"{nombre}: {texto}" if nombre and texto else texto


def pixeles(tema_id):
    """El dibujo 10×10 de la mascota (filas de arriba abajo)."""
    return PIXELES.get(tema_id) or PIXELES[TEMA_POR_DEFECTO]
