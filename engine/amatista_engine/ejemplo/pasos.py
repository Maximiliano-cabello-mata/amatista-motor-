"""El ejemplo resuelto de una práctica, escrito en código (motor 3.5).

Cada práctica trae en «example.steps» la solución como pasos, en el mismo
idioma que pruebas.json («construir»):

    [{"esfera": {"nombre": "Pelota", "loc": [0, 0, 4]}},
     {"animar": {"objeto": "Pelota", "propiedad": "location", "eje": "z", "claves": [[1, 4], [12, 0.85], [24, 4]]}},
     {"guardado": {"archivo": "mi_pelota.blend"}}]

Con esos pasos:

- el motor arma la escena esperada (escena_esperada) y revisa la del alumno
  contra ella (ejemplo/revision.py);
- la plataforma y el add-on los muestran como instrucciones (describir);
- el add-on arma el ejemplo en Blender, en su propia escena («Ver el ejemplo»).
"""
from __future__ import annotations

import inspect
import json
import math
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..models import SceneState
from ..terminos import MODIFICADORES
from ..testing import GEOMETRIA, PASOS, Escena

# Pasos que el ejemplo puede usar (los de pruebas.json).
PASOS_EJEMPLO = tuple(sorted(PASOS))
MAX_PASOS = 120

PRIMITIVAS = {
    "cubo": ("cube", "un cubo", "Cubo"), "cilindro": ("cylinder", "un cilindro", "Cilindro"),
    "esfera": ("sphere", "una esfera", "Esfera UV"), "plano": ("plane", "un plano", "Plano"),
    "cono": ("cone", "un cono", "Cono"),
}
POR_PRIMITIVA = {v[0]: (k, v[1], v[2]) for k, v in PRIMITIVAS.items()}
POR_PRIMITIVA.update({"icosphere": ("malla", "una icoesfera", "Icoesfera"),
                      "torus": ("malla", "un toroide", "Toroide")})
LUCES = {"POINT": ("Puntual", "una luz puntual"), "SUN": ("Sol", "un sol"), "SPOT": ("Foco", "un foco"),
         "AREA": ("Área", "una luz de área")}
PROPIEDADES = {"location": "la ubicación", "rotation_euler": "la rotación", "scale": "la escala"}
MOTORES = {"CYCLES": "Cycles", "BLENDER_EEVEE_NEXT": "EEVEE", "BLENDER_EEVEE": "EEVEE",
           "BLENDER_WORKBENCH": "Workbench"}


def _num(valor: float) -> str:
    texto = f"{float(valor):.2f}".rstrip("0").rstrip(".")
    return texto if texto not in ("-0", "") else "0"


def _medidas(dims: Optional[Sequence[float]]) -> str:
    return " × ".join(_num(d) for d in dims) + " m" if dims else ""


def _argumentos(args: Any) -> Dict[str, Any]:
    return args if isinstance(args, dict) else {}


def _nombre_pieza(pieza: Dict[str, Any], etiquetas: Optional[Dict[str, str]]) -> str:
    """Cómo se llama una pieza para el alumno: su nombre, la etiqueta de su rol o su primitiva."""
    if pieza.get("name"):
        return str(pieza["name"])
    rol = str(pieza.get("role") or "")
    if rol:
        return (etiquetas or {}).get(rol) or rol.capitalize()
    primitiva = str(pieza.get("primitive") or "")
    return POR_PRIMITIVA.get(primitiva, ("", "", primitiva.capitalize()))[2]


def describir_paso(paso: Dict[str, Any], partes: Sequence[Dict[str, Any]] = (),
                   etiquetas: Optional[Dict[str, str]] = None) -> str:
    """Un paso del ejemplo en palabras, con la tecla que lo hace (etiquetas: nombres de los roles)."""
    clave, args = next(iter(paso.items()))
    a = _argumentos(args)
    nombre = a.get("nombre") or ""
    if clave in PRIMITIVAS or clave == "malla":
        primitiva = a.get("primitiva") if clave == "malla" else PRIMITIVAS[clave][0]
        _, articulo, menu = POR_PRIMITIVA.get(primitiva, ("", f"una malla {primitiva}", primitiva.capitalize()))
        texto = f"Agrega {articulo}{f' «{nombre}»' if nombre else ''} (Shift + A › Malla › {menu})"
        if a.get("dims"):
            texto += f" de {_medidas(a['dims'])}"
        if a.get("rol"):
            texto += f", con el rol «{a['rol']}»"
        if a.get("coleccion") and a["coleccion"] != "Collection":
            texto += f", en la colección «{a['coleccion']}»"
        extras = []
        caras_base = GEOMETRIA.get(primitiva, (0, 0))[1]
        if a.get("vertices") is not None:
            extras.append(f"modélalo en Modo Edición (Tab) hasta unos {a['vertices']} vértices"
                          + (f" y {a['caras']} caras" if a.get("caras") is not None else ""))
        elif a.get("caras") is not None and a["caras"] > caras_base:
            extras.append(f"modélalo en Modo Edición (Tab), extruyendo con E, hasta unas {a['caras']} caras")
        if a.get("mitad"):
            extras.append(f"deja solo la mitad {a['mitad'][1:]}{a['mitad'][0].upper()}")
        return texto + (". Luego " + " y ".join(extras) if extras else "") + "."
    if clave == "referencia":
        nombres: List[str] = []
        for p in partes:
            if p.get("compare") is False:
                continue
            n = _nombre_pieza(p, etiquetas)
            if n and n not in nombres:
                nombres.append(n)
        unidas = any(p.get("join") for p in partes)
        texto = "Arma la figura del modelo"
        if nombres:
            texto += f": {', '.join(nombres[:8])}{'…' if len(nombres) > 8 else ''}"
        if unidas:
            texto += " (en una sola malla, desde un cubo en Modo Edición)"
        if a.get("vertices"):
            texto += f", con unos {a['vertices']} vértices"
        return texto + "."
    if clave == "luz":
        tipo = str(a.get("tipo", "POINT")).upper()
        nombre_tipo, articulo = LUCES.get(tipo, (tipo, f"una luz {tipo}"))
        return f"Agrega {articulo}{f' «{nombre}»' if nombre else ''} (Shift + A › Luz › {nombre_tipo})."
    if clave == "camara":
        return ("Agrega una cámara (Shift + A › Cámara), apúntala a tu modelo y hazla la activa "
                "(Ctrl + 0 del teclado numérico).")
    if clave == "modificador":
        tipo = str(a.get("tipo", "")).upper()
        texto = f"Ponle a «{a.get('objeto', '')}» el modificador {MODIFICADORES.get(tipo, tipo.capitalize())}"
        if tipo == "SUBSURF" and a.get("niveles"):
            texto += f" con {a['niveles']} niveles"
        if tipo == "MIRROR":
            ejes = [e for e, activo in zip("XYZ", a.get("ejes") or (True, False, False)) if activo]
            texto += f" en {' y '.join(ejes)}"
        return texto + " (pestaña Modificadores, la llave)."
    if clave == "material":
        props = []
        if float(a.get("metal", 0) or 0) >= 0.5:
            props.append(f"metálico {_num(a['metal'])}")
        if "rugosidad" in a:
            props.append(f"rugosidad {_num(a['rugosidad'])}")
        if float(a.get("transmision", 0) or 0) >= 0.5:
            props.append(f"transmisión {_num(a['transmision'])} (vidrio)")
        if a.get("color"):
            props.append("color " + ", ".join(_num(c) for c in list(a["color"])[:3]))
        detalle = f": {', '.join(props)}" if props else ""
        donde = f"«{a.get('objeto', '')}»"
        if a.get("piezas"):
            donde = " y ".join(f"«{p}»" for p in a["piezas"]) + f" de {donde} (en Modo Edición, Asignar)"
        return f"Crea el material «{a.get('nombre', '')}» en {donde}{detalle} (pestaña Material)."
    if clave == "animar":
        prop = PROPIEDADES.get(a.get("propiedad", ""), a.get("propiedad", ""))
        claves = [f"{_num(v)} en el fotograma {int(f)}" for f, v in a.get("claves") or ()]
        return (f"Anima {prop} {str(a.get('eje', '')).upper()} de «{a.get('objeto', '')}»: "
                f"{'; '.join(claves)} (mueve y pulsa I en cada fotograma).")
    if clave == "motor":
        motor = args if isinstance(args, str) else a.get("motor", "")
        return f"Cambia el motor de render a {MOTORES.get(str(motor).upper(), motor)} (pestaña Render)."
    if clave == "renders":
        return "Haz un render (F12)."
    if clave == "guardado":
        archivo = (a.get("archivo") or "practica.blend").replace("\\", "/").rsplit("/", 1)[-1]
        return f"Guarda el archivo como «{archivo}» (Ctrl + S)."
    if clave == "mover":
        return f"Mueve «{a.get('objeto', '')}» (G)."
    if clave == "quitar":
        return f"Borra «{args if isinstance(args, str) else a.get('objeto', '')}» (X)."
    if clave == "coleccion":
        objetos = a.get("objetos") or []
        return (f"Junta {', '.join(f'«{o}»' for o in objetos)} en la colección «{a.get('nombre', '')}» "
                "(selecciónalos y pulsa M › Nueva colección).")
    if clave == "rol":
        return f"Ponle a «{a.get('objeto', '')}» el rol «{a.get('rol', '')}» (pestaña Amatista)."
    if clave == "modo":
        modo = args if isinstance(args, str) else a.get("modo", "")
        return "Entra a Modo Edición (Tab)." if str(modo).upper().startswith("EDIT") else "Vuelve a Modo Objeto (Tab)."
    if clave == "inicial":
        return "Empieza con la escena de inicio de Blender (cubo, luz y cámara)."
    if clave == "seleccionar":
        return "Selecciona " + ", ".join(f"«{n}»" for n in (args if isinstance(args, list) else [args])) + "."
    return clave


def describir(pasos: Iterable[Dict[str, Any]], partes: Sequence[Dict[str, Any]] = (),
              etiquetas: Optional[Dict[str, str]] = None) -> List[str]:
    return [describir_paso(p, partes, etiquetas) for p in pasos if isinstance(p, dict) and len(p) == 1]


# Pasos que aceptan un valor suelto en vez de un objeto: {"motor": "CYCLES"}, {"renders": 1}, {"modo": "EDIT"}…
ESCALARES = ("inicial", "renders", "motor", "modo", "quitar", "seleccionar")
VECTORES = ("dims", "loc", "rot", "mira_a", "desplazar")
TEXTOS = ("nombre", "rol", "coleccion", "objeto", "tipo", "archivo", "propiedad", "eje", "primitiva", "mitad",
          "motor", "modo", "blender")
ENTEROS = ("vertices", "caras", "niveles", "encimados", "semilla", "n")
NUMEROS = ("energia", "angulo", "metal", "rugosidad", "transmision", "alfa", "variacion", "giro")
BOOLEANOS = ("activa", "encendido", "usado", "guardado", "roles")
LISTAS_DE_TEXTO = ("objetos", "piezas", "sin", "etiquetas", "nombres")
PROPIEDADES_ANIMABLES = ("location", "rotation_euler", "scale")
MITADES = ("x-", "x+", "y-", "y+", "z-", "z+")


def _es_numero(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _es_entero(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _vector_ok(x: Any, largos: Sequence[int] = (3,)) -> bool:
    return isinstance(x, list) and len(x) in largos and all(_es_numero(v) for v in x)


def _valor(clave: str, nombre: str, valor: Any) -> str:
    """Qué está mal en un argumento de un paso ("" = bien)."""
    if nombre == "escala":
        if clave == "referencia":
            return "" if _es_numero(valor) and valor > 0 else "un número mayor que 0"
        return "" if _vector_ok(valor) else "una lista de 3 números"
    if nombre in VECTORES:
        return "" if _vector_ok(valor) else "una lista de 3 números"
    if nombre == "color":
        return "" if _vector_ok(valor, (3, 4)) else "una lista de 3 o 4 números (R, G, B)"
    if nombre in TEXTOS:
        if not isinstance(valor, str):
            return "un texto"
        if nombre == "eje" and valor.lower() not in ("x", "y", "z"):
            return "x, y o z"
        if nombre == "propiedad" and valor not in PROPIEDADES_ANIMABLES:
            return f"una de: {', '.join(PROPIEDADES_ANIMABLES)}"
        if nombre == "mitad" and valor and valor.lower() not in MITADES:
            return f"una de: {', '.join(MITADES)}"
        if nombre == "tipo" and clave == "luz" and valor.upper() not in LUCES:
            return f"un tipo de luz: {', '.join(LUCES)}"
        if nombre == "primitiva" and valor not in GEOMETRIA:
            return f"una de: {', '.join(GEOMETRIA)}"
        return ""
    if nombre in ENTEROS:
        return "" if _es_entero(valor) and valor >= 0 else "un número entero (0 o más)"
    if nombre in NUMEROS:
        return "" if _es_numero(valor) else "un número"
    if nombre in BOOLEANOS:
        return "" if isinstance(valor, bool) else "true o false"
    if nombre in LISTAS_DE_TEXTO:
        return "" if isinstance(valor, list) and all(isinstance(v, str) for v in valor) else "una lista de textos"
    if nombre == "ejes":
        return "" if isinstance(valor, list) and len(valor) == 3 and all(isinstance(v, bool) for v in valor) else \
            "una lista de 3 true/false (X, Y, Z)"
    if nombre == "claves":
        return "" if isinstance(valor, list) and valor and all(_vector_ok(c, (2,)) for c in valor) else \
            "una lista de [fotograma, valor]"
    if nombre == "cambiar":
        return "" if isinstance(valor, dict) and all(isinstance(k, str) and _vector_ok(v) for k, v in valor.items()) \
            else "un objeto {nombre de pieza: [x, y, z]}"
    return ""


def revisar_argumentos(clave: str, args: Any, donde: str) -> List[str]:
    """Errores de los argumentos de un paso (cubo, luz, material…), en español y con la ruta del campo."""
    metodo = getattr(Escena, PASOS[clave])
    firma = [p for n, p in inspect.signature(metodo).parameters.items() if n != "self"]
    if any(p.kind is p.VAR_KEYWORD for p in firma):  # cubo, esfera…: los argumentos de malla
        propios = {p.name for p in firma}
        firma = [p for p in firma if p.kind is not p.VAR_KEYWORD] + [
            p for n, p in inspect.signature(Escena.malla).parameters.items()
            if n not in ("self", "primitiva") and n not in propios]
    if clave == "referencia":
        firma = [p for p in firma if p.name != "piezas"]  # las piezas salen de «reference»
    variadico = any(p.kind is p.VAR_POSITIONAL for p in firma)
    nombres = [p.name for p in firma if p.kind is not p.VAR_POSITIONAL]
    requeridos = [p.name for p in firma if p.default is p.empty and p.kind is not p.VAR_POSITIONAL]
    forma = (f"un objeto {{{', '.join(nombres)}}}" if nombres
             else "un nombre o una lista de nombres" if variadico else "true")
    if isinstance(args, dict) and not variadico:
        errores = [f"{donde} no admite «{k}» (usa: {', '.join(nombres)})" for k in args if k not in nombres]
        errores += [f"{donde} necesita «{r}»" for r in requeridos if r not in args]
        for nombre, valor in args.items():
            problema = _valor(clave, nombre, valor) if nombre in nombres else ""
            if problema:
                errores.append(f"{donde}.{nombre} debe ser {problema}")
        return errores
    if variadico:  # seleccionar: un nombre o una lista de nombres
        valores = args if isinstance(args, list) else [args]
        return [] if all(isinstance(v, str) for v in valores) else [f"{donde} debe ser un nombre o una lista de nombres"]
    if args is None or args is True:
        return [f"{donde} necesita «{r}»" for r in requeridos]
    if clave not in ESCALARES or isinstance(args, (list, dict)) or not nombres:
        return [f"{donde} debe ser {forma}"]
    problema = _valor(clave, nombres[0], args)
    if not problema and nombres[0] == "n" and args < 1:
        problema = "un número entero (1 o más)"
    return [f"{donde} debe ser {problema}"] if problema else []


def _texto_error(error: Exception) -> str:
    if isinstance(error, KeyError) and error.args:
        return str(error.args[0])
    return str(error) or type(error).__name__


def revisar_pasos(pasos: Any, partes: Sequence[Dict[str, Any]] = ()) -> List[str]:
    """Errores de los pasos (vacía = bien): su forma, sus argumentos y que se puedan armar y describir."""
    if not isinstance(pasos, list) or not pasos:
        return ["'example.steps' debe ser una lista de pasos (cubo, material, animar, guardado…)"]
    if len(pasos) > MAX_PASOS:
        return [f"'example.steps' admite como máximo {MAX_PASOS} pasos"]
    errores = []
    for i, paso in enumerate(pasos):
        if not isinstance(paso, dict) or len(paso) != 1:
            errores.append(f"example.steps[{i}] debe ser un objeto con una sola clave (cubo, luz, material…)")
            continue
        clave, args = next(iter(paso.items()))
        if clave not in PASOS:
            errores.append(f"example.steps[{i}]: paso desconocido «{clave}» (usa: {', '.join(PASOS_EJEMPLO)})")
        elif clave == "referencia" and not partes:
            errores.append(f"example.steps[{i}]: «referencia» necesita «reference» con piezas en la práctica")
        else:
            errores += revisar_argumentos(clave, args, f"example.steps[{i}].{clave}")
    if errores:
        return errores
    try:
        _armar(pasos, partes)
    except ValueError as error:
        return [f"'example.steps' no se puede armar: {error}"]
    for i, paso in enumerate(pasos):
        try:
            describir_paso(paso, partes)
        except Exception as error:  # noqa: BLE001 — cualquier dato raro es un error del autor, no del motor
            errores.append(f"example.steps[{i}] no se puede describir: {_texto_error(error)}")
    if not errores:
        try:
            lo_que_pide(pasos)
        except Exception as error:  # noqa: BLE001
            errores.append(f"'example.steps' no se puede revisar: {_texto_error(error)}")
    return errores


def _armar(pasos: Sequence[Dict[str, Any]], partes: Sequence[Dict[str, Any]]) -> SceneState:
    e = Escena()
    for i, paso in enumerate(pasos):
        clave, args = next(iter(paso.items()))
        try:
            metodo = getattr(e, PASOS[clave])
            if clave == "referencia":
                e.referencia(partes, **_argumentos(args))
            elif isinstance(args, dict):
                metodo(**args)
            elif isinstance(args, list):
                metodo(*args)
            elif args is None or args is True:
                metodo()
            else:
                metodo(args)
        except Exception as error:  # noqa: BLE001
            raise ValueError(f"example.steps[{i}] («{clave}»): {_texto_error(error)}") from error
    try:
        return e.construir()
    except Exception as error:  # noqa: BLE001
        raise ValueError(_texto_error(error)) from error


@lru_cache(maxsize=64)
def _armar_guardado(clave: str) -> SceneState:
    datos = json.loads(clave)
    return _armar(datos["pasos"], datos["partes"])


def escena_esperada(pasos: Sequence[Dict[str, Any]], partes: Sequence[Dict[str, Any]] = ()) -> SceneState:
    """La escena que deja el ejemplo resuelto (la misma que vería el motor en Blender)."""
    return _armar_guardado(json.dumps({"pasos": list(pasos), "partes": list(partes)}, sort_keys=True))


def lo_que_pide(pasos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Lo que el ejemplo pide de forma explícita y la escena no guarda: el motor de render y el archivo."""
    pide: Dict[str, Any] = {}
    for paso in pasos:
        clave, args = next(iter(paso.items()))
        if clave == "motor":
            pide["motor"] = str(args if isinstance(args, str) else _argumentos(args).get("motor", "")).upper()
        elif clave == "guardado":
            archivo = _argumentos(args).get("archivo") or "practica.blend"
            pide["archivo"] = archivo.replace("\\", "/").rsplit("/", 1)[-1]
        elif clave == "renders":
            pide["renders"] = True
    return pide
