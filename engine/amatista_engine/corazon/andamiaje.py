"""El andamio: cuánta ayuda da el corazón, herramienta por herramienta.

Lo que se ajusta con la investigación (ver docs/motor/referencia/23_corazon.md):

- **Inversión por experiencia** (Kalyuga y otros, 2003): lo que ayuda al
  novato estorba al que ya sabe. El andamio baja cuando el alumno usa la
  herramienta bien sin ayuda.
- **Retirada adaptativa** (Salden, Aleven, Renkl y otros, 2010): retirar
  la ayuda según el desempeño de cada alumno funciona mejor que retirarla a
  ritmo fijo. Aquí se cuenta por herramienta, no por lección.
- **Olvido**: después de una semana sin usarla, la herramienta vuelve un
  escalón atrás.
- **Lucha productiva**: en los escalones altos no se da la pista sola; se
  ofrece después de un rato sin avanzar.

Cuatro escalones, del más ayudado al más libre:

    mostrar   la señal se hace sola, se dice cómo y se ofrece «Mírame hacerlo»
    senalar   la señal se hace sola y se dice dónde está
    recordar  se dice dónde está; la señal se hace si se pide
    reto      solo el objetivo; dónde y cómo, si se piden

Python puro y serializable: el add-on guarda el historial por cuenta (y
para una cuenta de administrador lo deja en memoria).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Mapping, Optional

MOSTRAR, SENALAR, RECORDAR, RETO = "mostrar", "senalar", "recordar", "reto"
ESCALONES = (MOSTRAR, SENALAR, RECORDAR, RETO)
DIA = 86400.0


@dataclass(frozen=True)
class Umbrales:
    """Cuántos usos sin ayuda hacen falta para subir cada escalón (se cambian en la rama)."""

    senalar: int = 1
    recordar: int = 3
    reto: int = 5
    olvido_dias: float = 7.0
    espera_recordar: float = 45.0  # s en el paso antes de ofrecer una pista
    espera_reto: float = 90.0

    @staticmethod
    def desde(datos: Optional[Mapping[str, Any]]) -> "Umbrales":
        if not datos:
            return Umbrales()
        base = Umbrales()
        valores = {k: type(getattr(base, k))(v) for k, v in datos.items() if hasattr(base, k)}
        return replace(base, **valores)


@dataclass(frozen=True)
class Uso:
    """Lo que el alumno lleva con una herramienta."""

    solos: int = 0  # pasos cumplidos sin pedir ayuda
    ayudados: int = 0  # pasos cumplidos con ayuda
    tropiezos: int = 0  # pasos deshechos o pistas pedidas desde el último acierto solo
    ultimo: float = 0.0


@dataclass
class Historial:
    usos: Dict[str, Uso] = field(default_factory=dict)

    def uso(self, herramienta: str) -> Uso:
        return self.usos.get(herramienta, Uso())

    def como_dict(self) -> Dict[str, Dict[str, float]]:
        return {h: {"solos": u.solos, "ayudados": u.ayudados, "tropiezos": u.tropiezos, "ultimo": u.ultimo}
                for h, u in sorted(self.usos.items())}

    @staticmethod
    def desde_dict(datos: Any) -> "Historial":
        h = Historial()
        if not isinstance(datos, Mapping):
            return h
        for herramienta, u in datos.items():
            if not isinstance(u, Mapping):
                continue
            try:
                h.usos[str(herramienta)] = Uso(int(u.get("solos", 0)), int(u.get("ayudados", 0)),
                                               int(u.get("tropiezos", 0)), float(u.get("ultimo", 0.0)))
            except (TypeError, ValueError):
                continue
        return h


def escalon(uso: Uso, ahora: float, umbrales: Umbrales = Umbrales()) -> str:
    """El escalón de una herramienta hoy."""
    i = 0
    if uso.solos >= umbrales.reto:
        i = 3
    elif uso.solos >= umbrales.recordar:
        i = 2
    elif uso.solos >= umbrales.senalar:
        i = 1
    i -= min(i, uso.tropiezos)  # cada tropiezo baja un escalón, hasta mostrar
    if i and uso.ultimo and ahora - uso.ultimo > umbrales.olvido_dias * DIA:
        i -= 1
    return ESCALONES[i]


def registrar(h: Historial, herramienta: str, *, con_ayuda: bool, ahora: float) -> Historial:
    """Un paso de esa herramienta se cumplió."""
    if not herramienta:
        return h
    u = h.uso(herramienta)
    if con_ayuda:
        u = replace(u, ayudados=u.ayudados + 1, ultimo=ahora)
    else:
        u = replace(u, solos=u.solos + 1, tropiezos=0, ultimo=ahora)
    h.usos[herramienta] = u
    return h


def tropezar(h: Historial, herramienta: str, ahora: float) -> Historial:
    """Se deshizo un paso de esa herramienta o se pidió una pista: baja un escalón."""
    if not herramienta:
        return h
    u = h.uso(herramienta)
    h.usos[herramienta] = replace(u, tropiezos=min(u.tropiezos + 1, len(ESCALONES) - 1), ultimo=ahora or u.ultimo)
    return h


def desde_fases(fases: Mapping[str, str]) -> Historial:
    """Arranca el historial con las fases del modelo del Taller (BKT) por herramienta."""
    equivalencia = {"nueva": 0, "acompanada": 1, "sola": 3, "dominada": 5}
    h = Historial()
    for herramienta, f in fases.items():
        h.usos[herramienta] = Uso(solos=equivalencia.get(str(f), 0))
    return h


def senal_sola(nivel: str) -> bool:
    """¿El corazón hace la señal sin que la pidan?"""
    return nivel in (MOSTRAR, SENALAR)


def espera(nivel: str, umbrales: Umbrales = Umbrales()) -> float:
    """Segundos en el paso antes de ofrecer una pista (0: se ofrece desde el principio)."""
    return {RECORDAR: umbrales.espera_recordar, RETO: umbrales.espera_reto}.get(nivel, 0.0)


__all__ = ["ESCALONES", "Historial", "MOSTRAR", "RECORDAR", "RETO", "SENALAR", "Umbrales", "Uso", "desde_fases",
           "escalon", "espera", "registrar", "senal_sola", "tropezar"]
