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
from typing import Any, Dict, List, Sequence, Tuple

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
        teclas = tuple(paso.get("teclas") or _teclas(accion, datos))
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


__all__ = ["ACCIONES", "LineaDeTiempo", "MAXIMO", "PasoDemo", "linea_de_tiempo"]
