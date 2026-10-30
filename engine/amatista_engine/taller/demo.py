"""«Mira»: la demostración de una habilidad como línea de tiempo.

Antes, «Ver el ejemplo» abría una escena con el resultado: el alumno veía
el qué, nunca el cómo. Ahora cada habilidad trae su demostración en pasos
(el mismo idioma que ``example.steps``) y aquí se convierte en una línea de
tiempo: qué pasa, cuándo, cuánto dura y qué teclas aparecen en pantalla al
estilo screencast. El add-on la reproduce en la vista 3D con objetos
temporales que se borran al terminar (vista/demo.py del add-on).

10 a 20 segundos por habilidad: lo justo para ver el gesto (ejemplos
resueltos, ToolClips, Pause-and-Play).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Teclas y duración por acción (s). La demostración puede cambiar las teclas y el texto de cada paso.
ACCIONES: Dict[str, Tuple[Tuple[str, ...], float, str]] = {
    "agregar": (("Shift+A",), 2.2, "Agrega la forma"),
    "mover": (("G",), 2.0, "Muévela"),
    "escalar": (("S",), 2.0, "Cambia su tamaño"),
    "rotar": (("R",), 2.0, "Gírala"),
    "vista": ((), 1.6, "Cambia la vista"),
    "editar": (("Tab",), 1.2, "Entra a editar la malla"),
    "extruir": (("E",), 2.2, "Saca la cara hacia afuera"),
    "corte": (("Ctrl+R",), 2.0, "Corta un bucle"),
    "modificador": ((), 2.0, "Agrega el modificador"),
    "aplicar": (("Ctrl+A",), 1.6, "Aplica la escala"),
    "material": ((), 2.0, "Ponle un material"),
    "luz": (("Shift+A",), 2.0, "Agrega una luz"),
    "camara": ((), 2.0, "Acomoda la cámara"),
    "clave": (("I",), 1.6, "Guarda un fotograma clave"),
    "coleccion": (("M",), 1.8, "Llévalo a una colección"),
    "render": (("F12",), 2.0, "Haz el render"),
    "guardar": (("Ctrl+S",), 1.4, "Guarda el archivo"),
    "duplicar": (("Shift+D",), 1.8, "Duplícalo"),
    "borrar": (("X",), 1.2, "Bórralo"),
    "texto": ((), 2.2, ""),
}
VISTAS = {"frente": ("1",), "lado": ("3",), "arriba": ("7",), "camara": ("0",), "orbita": ("Rueda",)}
EJE = {"x": "X", "y": "Y", "z": "Z"}
PAUSA = 0.4  # entre pasos, para que el ojo alcance
MAXIMO = 24.0  # una demostración nunca pasa de esto: se acelera


@dataclass(frozen=True)
class PasoDemo:
    accion: str
    datos: Dict[str, Any]
    inicio: float  # s desde que empieza la demostración
    duracion: float
    teclas: Tuple[str, ...] = ()
    texto: str = ""

    @property
    def fin(self) -> float:
        return self.inicio + self.duracion


@dataclass(frozen=True)
class LineaDeTiempo:
    pasos: Tuple[PasoDemo, ...] = ()
    duracion: float = 0.0
    titulo: str = ""
    teclas: Tuple[str, ...] = field(default_factory=tuple)

    def en(self, t: float):
        """El paso que se está mostrando en el segundo t (o None antes de empezar o al terminar)."""
        return next((p for p in self.pasos if p.inicio <= t < p.fin + PAUSA), None)

    def a_dict(self) -> Dict[str, Any]:
        return {
            "titulo": self.titulo,
            "duracion": round(self.duracion, 2),
            "pasos": [{"accion": p.accion, "datos": p.datos, "inicio": round(p.inicio, 2), "duracion": round(p.duracion, 2),
                       "teclas": list(p.teclas), "texto": p.texto} for p in self.pasos],
        }


def _teclas(accion: str, datos: Dict[str, Any]) -> Tuple[str, ...]:
    base, _, _ = ACCIONES[accion]
    if accion == "vista":
        return VISTAS.get(str(datos.get("tipo") or "frente"), ())
    eje = EJE.get(str(datos.get("eje") or "").lower())
    if accion in ("mover", "escalar", "rotar") and eje:
        extra = (str(int(round(float(datos["grados"])))),) if accion == "rotar" and datos.get("grados") is not None else ()
        return base + (eje,) + extra
    if accion == "agregar" and datos.get("primitiva"):
        from .molde import MALLA

        nombre = MALLA.get(str(datos["primitiva"]))
        return base + (("Malla", nombre) if nombre else ())
    return base


def linea_de_tiempo(pasos: Sequence[Dict[str, Any]], titulo: str = "") -> LineaDeTiempo:
    """Los pasos de la demostración ({"agregar": {...}}, {"escalar": {...}}…) → línea de tiempo."""
    salida: List[PasoDemo] = []
    t = 0.6  # un respiro antes del primer paso
    vistas: List[str] = []
    for paso in pasos:
        from .habilidades import accion_de_paso

        acciones = accion_de_paso(paso)
        if not acciones:
            continue
        accion = acciones[0]
        datos = paso[accion] if isinstance(paso[accion], dict) else {"texto": str(paso[accion])}
        _, duracion, texto = ACCIONES[accion]
        duracion = float(paso.get("segundos") or duracion)
        teclas = tuple(paso["teclas"]) if isinstance(paso.get("teclas"), (list, tuple)) else _teclas(accion, datos)
        texto = str(paso.get("texto") or datos.get("texto") or texto)
        salida.append(PasoDemo(accion, dict(datos), t, duracion, teclas, texto))
        for k in teclas:
            if k not in vistas:
                vistas.append(k)
        t += duracion + PAUSA
    total = t
    if total > MAXIMO and salida:
        factor = MAXIMO / total
        salida = [PasoDemo(p.accion, p.datos, p.inicio * factor, p.duracion * factor, p.teclas, p.texto) for p in salida]
        total = MAXIMO
    return LineaDeTiempo(tuple(salida), total, titulo, tuple(vistas))


# --- Motor 6: la demostración de ESTA actividad ------------------------------------------------
#
# Hasta el motor 5, «Mira» y «Mírame» reproducían la demostración genérica de
# la habilidad: el alumno que tenía que agregar un cono veía aparecer una «Caja»
# y una «Lata», y en el proyecto del tren salían piezas que no eran del tren.
# Ahora la demostración se arma con las piezas de la actividad (su molde, o la
# pieza que toca en el proyecto) y el gesto de la habilidad: si la habilidad es
# mover, la pieza aparece en el centro y se lleva a su lugar; si es escalar,
# aparece con su tamaño de base y se estira; si es girar, aparece derecha y gira.

GEOMETRIA = ("agregar", "mover", "escalar", "rotar", "duplicar", "borrar", "vista", "texto")
MAX_PIEZAS = 4  # una demostración enseña el gesto, no hace el ejercicio entero
MAX_PASOS = 12
BASE = (2.0, 2.0, 2.0)  # lo que mide una primitiva recién agregada


def _distinto(a: Sequence[float], b: Sequence[float], tol: float) -> List[int]:
    return [i for i in range(3) if abs(float(a[i]) - float(b[i])) > tol]


def _eje_unico(ejes: List[int]) -> Dict[str, str]:
    return {"eje": "xyz"[ejes[0]]} if len(ejes) == 1 else {}


def _vec(valor: Any, defecto: Sequence[float]) -> List[float]:
    try:
        v = [float(x) for x in valor]
        return v if len(v) == 3 else list(defecto)
    except (TypeError, ValueError):
        return list(defecto)


def pasos_de_actividad(demo_habilidad: Sequence[Dict[str, Any]], piezas: Sequence[Dict[str, Any]],
                       inicio: Sequence[Dict[str, Any]] = ()) -> Tuple[Dict[str, Any], ...]:
    """Los pasos de la demostración para estas piezas, con el gesto de la habilidad.

    Sin piezas (habilidades de material, luz, render…) queda la demostración de
    la habilidad, pero nunca con objetos inventados que la actividad no tiene.
    """
    from .habilidades import accion_de_paso
    from .molde import MALLA

    pasos_h = [dict(p) for p in demo_habilidad or () if isinstance(p, dict)]
    gestos = {a for p in pasos_h for a in accion_de_paso(p)}
    objetivo = [p for p in piezas or () if isinstance(p, dict) and p.get("primitive")][:MAX_PIEZAS]
    if not objetivo:
        return tuple(pasos_h)
    previas = [p for p in inicio or () if isinstance(p, dict) and p.get("primitive")]
    usadas: List[int] = []

    def _previa(nombre: str, lugar: List[float]) -> Optional[Dict[str, Any]]:
        """La pieza de inicio que hay que arreglar: la del mismo nombre o la que ocupa su lugar."""
        for k, p in enumerate(previas):
            if k not in usadas and str(p.get("name") or "") == nombre:
                usadas.append(k)
                return p
        cerca = [(sum((a - b) ** 2 for a, b in zip(_vec(p.get("location"), lugar), lugar)), k)
                 for k, p in enumerate(previas) if k not in usadas]
        cerca = [c for c in cerca if c[0] <= 0.5 ** 2]
        if not cerca:
            return None
        usadas.append(min(cerca)[1])
        return previas[min(cerca)[1]]

    salida: List[Dict[str, Any]] = []
    creadas: List[Tuple[str, str, List[float]]] = []
    for i, pieza in enumerate(objetivo):
        nombre = str(pieza.get("name") or f"Pieza {i + 1}")
        prim = str(pieza["primitive"])
        medidas = _vec(pieza.get("size"), BASE)
        lugar = _vec(pieza.get("location"), (0.0, 0.0, 0.0))
        giro = _vec(pieza.get("rotation"), (0.0, 0.0, 0.0))
        malla = MALLA.get(prim, prim)
        previa = _previa(nombre, lugar)
        if previa is not None and previa.get("primitive") == prim:
            # «Arregla esta escena»: la pieza aparece como está y se lleva a como debe quedar.
            base = {"loc": _vec(previa.get("location"), lugar), "medidas": _vec(previa.get("size"), medidas),
                    "giro": _vec(previa.get("rotation"), (0.0, 0.0, 0.0))}
            salida.append({"agregar": {"primitiva": prim, "nombre": nombre, **base}, "segundos": 1.0,
                           "teclas": [], "texto": f"Así está «{nombre}»"})
        else:
            if previa is not None:
                otra = str(previa.get("name") or "") or f"{nombre} (antes)"
                otra = otra if otra != nombre else f"{nombre} (antes)"
                salida.append({"agregar": {"primitiva": previa.get("primitive") or "cube", "nombre": otra,
                                           "loc": _vec(previa.get("location"), lugar),
                                           "medidas": _vec(previa.get("size"), BASE)},
                               "segundos": 1.0, "teclas": [], "texto": f"«{otra}» no es la forma que va aquí"})
                salida.append({"borrar": {"objeto": otra}, "texto": "X borra la forma equivocada"})
            gemela = next((n for n, p, m in creadas if p == prim and not _distinto(m, medidas, 0.05)), "")
            if gemela and "duplicar" in gestos:
                salida.append({"duplicar": {"objeto": gemela, "nombre": nombre, "a": lugar},
                               "texto": f"Shift + D: otra «{gemela}» y llévala a su lugar"})
                base = {"loc": lugar, "medidas": medidas, "giro": (0.0, 0.0, 0.0)}
            else:
                base = {
                    "loc": [0.0, 0.0, 0.0] if "mover" in gestos else lugar,
                    "medidas": list(BASE) if "escalar" in gestos else medidas,
                    "giro": [0.0, 0.0, 0.0] if "rotar" in gestos else giro,
                }
                salida.append({"agregar": {"primitiva": prim, "nombre": nombre, **base},
                               "texto": f"Shift + A › Malla › {malla}: «{nombre}»"})
        ejes = _distinto(base["medidas"], medidas, 0.02)
        if ejes:
            salida.append({"escalar": {"objeto": nombre, "medidas": medidas, **_eje_unico(ejes)},
                           "texto": f"S{' y ' + 'XYZ'[ejes[0]] if len(ejes) == 1 else ''}: el tamaño de «{nombre}»"})
        ejes = _distinto(base["giro"], giro, 0.5)
        if ejes:
            datos: Dict[str, Any] = {"objeto": nombre, "giro": giro, **_eje_unico(ejes)}
            if len(ejes) == 1:
                datos["grados"] = giro[ejes[0]] - base["giro"][ejes[0]]
            salida.append({"rotar": datos, "texto": f"R: gira «{nombre}»"})
        ejes = _distinto(base["loc"], lugar, 0.02)
        if ejes:
            salida.append({"mover": {"objeto": nombre, "a": lugar, **_eje_unico(ejes)},
                           "texto": f"G{' y ' + 'XYZ'[ejes[0]] if len(ejes) == 1 else ''}: «{nombre}» a su lugar"})
        creadas.append((nombre, prim, medidas))
    # Lo que no es forma (modificador, material, clave…) se hace sobre una pieza de ESTA actividad.
    nombres = {n for n, _p, _m in creadas}
    for paso in pasos_h:
        acciones = accion_de_paso(paso)
        if not acciones or acciones[0] in GEOMETRIA:
            continue
        accion = acciones[0]
        datos = dict(paso[accion]) if isinstance(paso[accion], dict) else {}
        if datos.get("objeto") and datos["objeto"] not in nombres:
            datos["objeto"] = creadas[0][0]
        salida.append({**paso, accion: datos})
    return tuple(salida[:MAX_PASOS])


def pieza_de_revision(pieza: Any) -> Dict[str, Any]:
    """Una PiezaRevisada (la que toca en el proyecto) como pieza del molde, para su demostración."""
    return {"primitive": getattr(pieza, "primitiva", "") or "cube", "name": getattr(pieza, "nombre", "") or "Pieza",
            "size": list(getattr(pieza, "medidas", BASE)), "location": list(getattr(pieza, "centro", (0.0, 0.0, 0.0))),
            "rotation": list(getattr(pieza, "giro", (0.0, 0.0, 0.0)))}


__all__ = ["ACCIONES", "LineaDeTiempo", "MAXIMO", "PasoDemo", "linea_de_tiempo", "pasos_de_actividad",
           "pieza_de_revision"]
