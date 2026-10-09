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

import json
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..models import SceneState
from ..testing import PASOS, Escena

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
MODIFICADORES = {"ARRAY": "Array", "BEVEL": "Bisel", "SUBSURF": "Subdivisión", "MIRROR": "Espejo",
                 "SOLIDIFY": "Solidificar", "BOOLEAN": "Booleano", "DECIMATE": "Diezmar"}
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


def describir_paso(paso: Dict[str, Any], partes: Sequence[Dict[str, Any]] = ()) -> str:
    """Un paso del ejemplo en palabras, con la tecla que lo hace."""
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
        if a.get("vertices") is not None:
            extras.append(f"modélalo en Modo Edición (Tab) hasta unos {a['vertices']} vértices")
        if a.get("mitad"):
            extras.append(f"deja solo la mitad {a['mitad'][1:]}{a['mitad'][0].upper()}")
        return texto + (". Luego " + " y ".join(extras) if extras else "") + "."
    if clave == "referencia":
        nombres: List[str] = []
        for p in partes:
            if p.get("compare") is False:
                continue
            n = p.get("name") or p.get("role") or p.get("primitive", "")
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
        return "Agrega una cámara (Shift + A › Cámara), apúntala a tu modelo y hazla la activa (Ctrl + 0)."
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


def describir(pasos: Iterable[Dict[str, Any]], partes: Sequence[Dict[str, Any]] = ()) -> List[str]:
    return [describir_paso(p, partes) for p in pasos if isinstance(p, dict) and len(p) == 1]


def revisar_pasos(pasos: Any, partes: Sequence[Dict[str, Any]] = ()) -> List[str]:
    """Errores de forma de los pasos (vacía = bien). Arma la escena para encontrar los demás."""
    if not isinstance(pasos, list) or not pasos:
        return ["'example.steps' debe ser una lista de pasos (cubo, material, animar, guardado…)"]
    if len(pasos) > MAX_PASOS:
        return [f"'example.steps' admite como máximo {MAX_PASOS} pasos"]
    errores = []
    for i, paso in enumerate(pasos):
        if not isinstance(paso, dict) or len(paso) != 1:
            errores.append(f"example.steps[{i}] debe ser un objeto con una sola clave (cubo, luz, material…)")
        elif next(iter(paso)) not in PASOS:
            errores.append(f"example.steps[{i}]: paso desconocido «{next(iter(paso))}» "
                           f"(usa: {', '.join(PASOS_EJEMPLO)})")
        elif next(iter(paso)) == "referencia" and not partes:
            errores.append(f"example.steps[{i}]: «referencia» necesita «reference» con piezas en la práctica")
    if errores:
        return errores
    try:
        escena_esperada(pasos, partes)
    except (KeyError, TypeError, ValueError) as error:
        return [f"'example.steps' no se puede armar: {error}"]
    return []


def _armar(pasos: Sequence[Dict[str, Any]], partes: Sequence[Dict[str, Any]]) -> SceneState:
    e = Escena()
    for paso in pasos:
        clave, args = next(iter(paso.items()))
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
    return e.construir()


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
