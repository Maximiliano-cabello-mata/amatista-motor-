"""«Recuérdalo»: qué habilidades toca repasar hoy.

Lo que no se vuelve a pedir sin ayuda, días después, se pierde (§4.6 de la
investigación; Cepeda et al., 2006). Una habilidad dominada entra a la caja
1 (repaso mañana); cada repaso bien hecho sin ayuda la sube de caja (3, 7,
14 y 30 días) y uno fallido la devuelve a la 1, y su P(L) baja: la próxima
vez que aparezca en un proyecto vuelve a «Hazlo conmigo».

Al abrir Amatista se ofrece un reto de un minuto con la más atrasada. Es
opcional y nunca bloquea la práctica (riesgo «que el repaso moleste»).
"""
from __future__ import annotations

from typing import Dict, Iterable, List

from .modelo import Dominio


def vencidas(estado: Dict[str, Dominio], ahora: float, entre: Iterable[str] = ()) -> List[str]:
    """Habilidades con repaso vencido (de `entre`, o todas), de la más atrasada a la más reciente."""
    candidatas = list(entre) if entre else list(estado)
    salida = [h for h in candidatas if h in estado and estado[h].caja and estado[h].proximo and estado[h].proximo <= ahora]
    return sorted(salida, key=lambda h: estado[h].proximo)


def proximas(estado: Dict[str, Dominio], ahora: float, limite: int = 5) -> List[Dict[str, float]]:
    """[{habilidad, en_dias}] de los próximos repasos (para la plataforma)."""
    futuras = [(d.proximo, h) for h, d in estado.items() if d.caja and d.proximo and d.proximo > ahora]
    futuras.sort()
    return [{"habilidad": h, "en_dias": round((cuando - ahora) / 86400.0, 1)} for cuando, h in futuras[:limite]]


__all__ = ["proximas", "vencidas"]
