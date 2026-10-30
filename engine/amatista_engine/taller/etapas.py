"""La plataforma marca la ruta (motor 6): qué parte del taller toca en cada lección.

La guía de aprendizaje (docs/cursos/03_ruta_de_aprendizaje_blender.md §3)
pone dos momentos en Blender por módulo, con teoría en medio:

    Gancho · **Exploración** (3 a 6 min) · Teoría · **Práctica de cierre** · Jefe

Hasta el motor 5 las dos lecciones abrían el taller entero y la primera solo
se daba por hecha al abrirse el proyecto: el alumno hacía todo el módulo en
Blender antes de ver la teoría, y Blender elegía qué venía después. Desde el
motor 6 cada lección manda su **etapa** y Blender no sale de ella:

- ``exploracion``: las primeras habilidades del taller (o las que diga la
  lección), cada una con «Mira» y un «Hazlo conmigo». Pocas, sin presión.
  Al terminarlas Blender no sigue solo: dice «vuelve a la plataforma».
- ``practica``: el ciclo completo hasta el proyecto y el reto (lo de siempre).

Python puro: el add-on lo usa para decidir qué abre y la plataforma, para
saber cuándo se da por hecha la lección (frontend/src/blender/taller.js).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from .actividades import Actividad, EstadoHabilidad, Plan, planear
from .habilidades import Catalogo, Taller
from .modelo import Dominio

EXPLORACION, PRACTICA = "exploracion", "practica"
ETAPAS = (EXPLORACION, PRACTICA)
EXPLORAR = 2  # habilidades que prueba la exploración si la lección no dice cuáles
MAX_EXPLORAR = 4


@dataclass(frozen=True)
class Etapa:
    taller: str
    nombre: str = PRACTICA
    habilidades: Tuple[str, ...] = ()  # exploración: las que se prueban (ya revisadas contra el taller)

    def a_dict(self) -> Dict[str, Any]:
        return {"taller": self.taller, "etapa": self.nombre, "habilidades": list(self.habilidades)}


def etapa_de(taller: Optional[Taller], nombre: Any = "", habilidades: Any = ()) -> Optional[Etapa]:
    """La etapa que pidió la plataforma, saneada: nada de habilidades de otro taller ni etapas inventadas."""
    if taller is None:
        return None
    nombre = nombre if nombre in ETAPAS else PRACTICA
    if nombre == PRACTICA:
        return Etapa(taller.id, PRACTICA)
    pedidas = [h for h in (habilidades or ()) if isinstance(h, str) and h in taller.habilidades]
    elegidas = tuple(dict.fromkeys(pedidas))[:MAX_EXPLORAR] or tuple(taller.habilidades[:EXPLORAR])
    return Etapa(taller.id, EXPLORACION, elegidas)


def explorada(eh: Optional[EstadoHabilidad]) -> bool:
    """Ya la vio hacer y la intentó una vez (o ya la sabía): la exploración no pide más."""
    if eh is None:
        return False
    return eh.lista or (eh.intentos > 0 and (eh.vio_demo or eh.fase != "nueva"))


def cumplida(etapa: Optional[Etapa], plan: Optional[Plan]) -> bool:
    if etapa is None or plan is None:
        return False
    if etapa.nombre == EXPLORACION:
        por_id = {h.id: h for h in plan.habilidades}
        return all(explorada(por_id.get(h)) for h in etapa.habilidades)
    return plan.proyecto_hecho


def siguiente(catalogo: Catalogo, etapa: Etapa, estado: Dict[str, Dominio], ahora: float,
              completadas: Iterable[str] = ()) -> Tuple[Optional[Actividad], Optional[Plan], bool]:
    """(la actividad que toca dentro de la etapa o None, el plan, ¿la etapa ya se cumplió?)."""
    completadas = tuple(completadas)
    plan = planear(catalogo, etapa.taller, estado, ahora, completadas)
    if plan is None:
        return None, None, False
    if etapa.nombre == PRACTICA:
        return plan.actual, plan, plan.proyecto_hecho and plan.actual is None
    por_id = {h.id: h for h in plan.habilidades}
    for hid in etapa.habilidades:
        if explorada(por_id.get(hid)):
            continue
        elegido = planear(catalogo, etapa.taller, estado, ahora, completadas, elegida=hid)
        a = elegido.actual if elegido is not None else None
        if a is not None and a.habilidad == hid:
            return a, elegido, False
    return None, plan, cumplida(etapa, plan)


def permitida(etapa: Optional[Etapa], actividad: Optional[Actividad]) -> bool:
    """¿Esta actividad cabe en la etapa? (una orden vieja o un botón no la saca de la ruta)."""
    if etapa is None or actividad is None:
        return True
    if actividad.taller != etapa.taller:
        return False
    if etapa.nombre == EXPLORACION:
        return actividad.habilidad in etapa.habilidades and actividad.tipo in ("mira", "conmigo", "tu")
    return True


def habilidades_de_etapa(etapa: Optional[Etapa], todas: Sequence[str]) -> Tuple[str, ...]:
    if etapa is None or etapa.nombre == PRACTICA:
        return tuple(todas)
    return tuple(h for h in todas if h in etapa.habilidades)


__all__ = ["ETAPAS", "EXPLORACION", "Etapa", "PRACTICA", "cumplida", "etapa_de", "explorada", "habilidades_de_etapa",
           "permitida", "siguiente"]
