"""El guion de una práctica: los pasos en orden, cada uno dicho con claridad (motor 7).

Un paso es un objetivo de la práctica (los que no son opcionales), en el
orden en que se pueden hacer (``requires``). Cada paso dice:

- ``haz``: qué hacer, en una frase con verbo y pieza («Agrega dos cubos:
  la locomotora y el vagón»). Sale del ``tip`` del autor; si no hay, el
  motor la arma con el validador y el rol.
- ``listo``: cómo se ve cuando está hecho (el título del objetivo).
- ``herramienta``: con qué se hace (id del catálogo) y, de ahí, **dónde
  está** (donde.py), sin inventar brillos.
- ``como``: las pistas del autor y sus micro pasos con teclas.

El guion no decide nada: lo que está hecho lo dice el reporte del motor de
siempre (avance.py). Python puro: corre en Blender, en pytest y en el
servidor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from . import donde as _donde


# Una instrucción dice qué hacer: lleva un verbo en imperativo (o el atajo que lo hace).
DICE_QUE_HACER = re.compile(
    r"\b(agrega|agrégal[oa]s?|pon|ponle|ponl[oa]s?|mueve|muével[oa]|baja|bájal[oa]|sube|escala|escálal[oa]|estira|aplana|"
    r"gira|rota|duplica|guarda|guárdal[oa]|acerca|acércal[oa]|une|compara|selecciona|dale|cambia|usa|pulsa|haz|arma|crea|"
    r"entra|extruye|corta|pinta|renderiza|ilumina|anima|coloca|deja|aplica|fusiona|borra|quita|mira|elige|divide|"
    r"suaviza|agrupa|mete|apunta|encuadra|copia|cierra|activa|añade|inserta|sal|vuelve|limpia|nombra|llama|asigna)\b",
    re.I)


@dataclass(frozen=True)
class Paso:
    id: str  # el objetivo de la práctica
    numero: int
    titulo: str
    haz: str
    listo: str
    parte: str = ""  # la parte del proyecto («Las ruedas»)
    herramienta: str = ""
    primitiva: str = ""
    rol: str = ""
    como: Tuple[str, ...] = ()
    teclas: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Guion:
    practica_id: str
    titulo: str
    pasos: Tuple[Paso, ...]
    nivel: int = 1

    def paso(self, objetivo: str) -> Optional[Paso]:
        return next((p for p in self.pasos if p.id == objetivo), None)

    @property
    def total(self) -> int:
        return len(self.pasos)


def _orden(objetivos) -> List:
    """Los objetivos en el orden del archivo, pero nunca antes de lo que requieren."""
    por_id = {t.id: t for t in objetivos}
    hechos, salida = set(), []

    def poner(t, camino=()):
        if t.id in hechos or t.id in camino:
            return
        for r in t.requires:
            if r in por_id:
                poner(por_id[r], camino + (t.id,))
        hechos.add(t.id)
        salida.append(t)

    for t in objetivos:
        poner(t)
    return salida


def _etiqueta(practica, rol: str) -> str:
    for r in getattr(practica, "roles", ()) or ():
        if r.id == rol:
            return r.label
    return rol


def _primitiva(practica, objetivo) -> str:
    p = objetivo.params or {}
    if p.get("primitive"):
        return str(p["primitive"])
    rol = p.get("role", "")
    ref = getattr(practica, "reference", None)
    for parte in getattr(ref, "parts", ()) or ():
        if rol and getattr(parte, "role", "") == rol and getattr(parte, "primitive", ""):
            return parte.primitive
    return ""


FEMENINAS = {"sphere", "uv_sphere", "icosphere"}
NUMEROS = {1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho"}


def _cuantos(n: int) -> str:
    return NUMEROS.get(n, str(n))


def _plural(palabra: str) -> str:
    if not palabra or palabra.endswith("s"):
        return palabra
    return palabra + ("s" if palabra[-1] in "aeiouáéó" else "es")


def _haz_generico(practica, t) -> str:
    """Una instrucción con verbo y pieza cuando el autor no escribió ``tip``."""
    p = t.params or {}
    primitiva = _primitiva(practica, t)
    malla = _donde.MALLAS.get(primitiva, "")
    rol = _etiqueta(practica, p.get("role", "")) or (malla[0].lower() + malla[1:] if malla else "tu modelo")
    v = t.validator
    if v in ("object.count", "role.count"):
        n = int(p.get("min") or p.get("count") or 1)
        if not malla and v == "role.count":
            return (f"Selecciona tu {rol.lower()} y dile a Amatista qué es: barra lateral (N) › Amatista › Roles."
                    if n == 1 else f"Selecciona cada {rol.lower()} y dile a Amatista qué es en N › Amatista › Roles.")
        nombre = rol[0].lower() + rol[1:] if n == 1 else _plural(rol.lower())
        cuantos = ("una" if n == 1 and primitiva in FEMENINAS and not p.get("role") else _cuantos(n))
        return f"Agrega {cuantos} {nombre}" + (f" con Agregar › Malla › {malla}." if malla else ".")
    if v.startswith("spatial.grounded"):
        return f"Baja «{rol}» hasta que toque el suelo (mira de frente con 1)."
    if v.startswith("spatial.touching"):
        return f"Acerca «{rol}» hasta que toque «{_etiqueta(practica, p.get('reference_role', ''))}»."
    if v.startswith("spatial.below"):
        return f"Pon «{rol}» debajo de «{_etiqueta(practica, p.get('reference_role', ''))}», tocándolo."
    if v.startswith("spatial.on_top"):
        return f"Pon «{rol}» encima, apoyada."
    if v in ("shape.proportion", "dimension.approx"):
        return f"Cambia el tamaño de «{rol}» con Escalar (S) hasta que se parezca al modelo."
    if v == "shape.thinnest_axis":
        return f"Aplana «{rol}» (S y un eje) y ponla de pie girándola (R y un eje)."
    if v == "file.named":
        return f"Guarda tu archivo con un nombre que tenga «{p.get('contains', '')}»: Archivo › Guardar como."
    if v == "file.saved":
        return "Guarda los últimos cambios: Ctrl + S."
    if v.startswith("modifier."):
        from .. import terminos

        tipo = terminos.nombre_modificador(p.get("type", "")) if p.get("type") else "que pide el paso"
        return f"Agrega el modificador {tipo} a «{rol}»: Propiedades › Modificadores › Agregar modificador."
    if v.startswith("material."):
        return f"Dale a «{rol}» {p.get('label') or 'su material'}: Propiedades › Material."
    if v in ("scene.camera_exists",):
        return "Agrega una cámara: Agregar › Cámara."
    if v.startswith("camera."):
        return "Apunta la cámara al modelo: mira por ella con 0 del teclado numérico y muévela hasta que se vea entero."
    if v in ("scene.light_exists", "light.three_point"):
        return "Pon las luces: Agregar › Luz, una delante a cada lado del modelo y una detrás."
    if v == "render.engine":
        return f"Cambia el motor de render en Propiedades › Render a {p.get('engine', 'EEVEE')}."
    if v == "render.done":
        return "Renderiza la imagen con F12 (Renderizar › Renderizar imagen)."
    if v.startswith("animation."):
        return f"Anima «{rol}»: pon fotogramas clave con I en distintos cuadros de la línea de tiempo."
    if v == "scene.mode":
        return "Cambia de modo con Tab (modo edición ↔ modo objeto)."
    if v.startswith("mesh."):
        return f"Entra a modo edición (Tab) y arregla la malla de «{rol}»."
    if v == "transform.scale_applied":
        return f"Aplica la escala de «{rol}»: Objeto › Aplicar › Escala (Ctrl + A)."
    if v == "collection.contains":
        return f"Mete «{rol}» en su colección: selecciónalos y pulsa M › Nueva colección."
    if v.startswith("figure."):
        return "Compara tu modelo con la imagen del modelo: mira de frente (1) y de lado (3) y ajusta lo que no cuadre."
    if v == "object.exists":
        return f"Agrega «{rol}»."
    if v == "example.matches":
        return "Compara tu escena con el ejemplo resuelto («Ver el ejemplo»)."
    return f"Haz esto: {t.title or t.id}."


def _herramienta(practica, t, herramientas_actividad: Sequence[str]) -> str:
    if t.validator == "taller.molde":
        return next((h for h in herramientas_actividad if _donde.de(h) is not None), "")
    if t.validator == "role.count" and (not _primitiva(practica, t) or re.search(r"\brol\b|dile a amatista", t.tip, re.I)):
        return "amatista.rol"
    h = _donde.para_validador(t.validator, t.params)
    if t.validator.startswith("modifier.") and (t.params or {}).get("type"):
        h = f"modifier.{str(t.params['type']).lower()}"
    return h


def guion_de_practica(practica, herramientas_actividad: Sequence[str] = (), haz_actividad: str = "",
                      como_actividad: Sequence[str] = (), teclas_actividad: Sequence[str] = ()) -> Guion:
    """El guion de una práctica ``PracticeDefinition``.

    Para una actividad del taller (práctica generada con ``taller.molde``)
    se pasan sus herramientas, su frase («La caja flota: bájala…»), el
    «cómo» de la habilidad y sus teclas.
    """
    pasos: List[Paso] = []
    for t in _orden([t for t in practica.targets if not t.optional]):
        haz = (haz_actividad if t.validator == "taller.molde" and haz_actividad else "") or t.tip
        como: List[str] = []
        if not haz or not DICE_QUE_HACER.search(haz):
            # El tip del autor describe pero no dice qué hacer («Cilindros altos con el rol Pilar»):
            # la instrucción la arma el motor y el tip queda como primera ayuda.
            if haz:
                como.append(haz)
            haz = _haz_generico(practica, t)
        como += [h.text for h in sorted(t.hints, key=lambda h: h.level)]
        teclas: List[str] = []
        if t.guide is not None:
            for s in t.guide.steps:
                como.append(s.text + (f" ({' › '.join(s.keys)})" if s.keys else ""))
                teclas.extend(s.keys)
        if t.validator == "taller.molde":
            como = list(como_actividad) + como
            teclas = list(teclas_actividad) + teclas
        rol = str((t.params or {}).get("role", ""))
        pasos.append(Paso(
            id=t.id, numero=len(pasos) + 1, titulo=t.title or t.id, haz=haz, listo=t.title or haz,
            parte=t.stage, herramienta=_herramienta(practica, t, herramientas_actividad), primitiva=_primitiva(practica, t),
            rol=rol, como=tuple(dict.fromkeys(c for c in como if c)), teclas=tuple(teclas),
        ))
    return Guion(practica.id, practica.title, tuple(pasos), getattr(practica, "level", 1))


def resumen(g: Guion) -> Dict[str, object]:
    return {"practica": g.practica_id, "titulo": g.titulo,
            "pasos": [{"id": p.id, "numero": p.numero, "titulo": p.titulo, "haz": p.haz, "herramienta": p.herramienta}
                      for p in g.pasos]}


__all__ = ["DICE_QUE_HACER", "Guion", "Paso", "guion_de_practica", "resumen"]
