"""El modelo del alumno: cuánto domina cada habilidad (BKT con olvido).

Por cada habilidad y alumno se guarda la probabilidad de que la sepa, P(L).
Cada intento la actualiza con el rastreo bayesiano del conocimiento (BKT,
Corbett y Anderson, 1995), el mismo que se ajustó con 421 318 respuestas de
ASSISTments y 16 851 pasos de Cognitive Tutor en la investigación (§4.4):
predijo el siguiente intento con AUC 0.72 en alumnos que nunca vio.

Dos cosas que BKT no trae y Amatista necesita:

- **La ayuda cuenta.** Acertar con el molde o con la pista «qué falta»
  todavía dice algo (se sube la probabilidad de adivinar, G). Acertar
  después de ver las teclas («cómo») o la demostración («mírame») casi no
  dice nada: en los datos, quien recibe la respuesta no mejora en el
  siguiente intento (§4.2). Esos aciertos solo suman la oportunidad de
  aprender, no la evidencia de que ya sabe.
- **Lo que no se repasa se olvida** (§4.6). P(L) baja con los días sin
  practicar y baja más despacio cuanto más alta es su caja de repaso
  (cajas de Leitner: 1, 3, 7, 14 y 30 días, pedagogy/spaced.py).

El estado es un dict JSON {habilidad: {...}}: lo guarda el add-on sin
conexión (avance del taller) y el servidor en HABILIDADES_ALUMNO (sql/012).
Funciones puras y deterministas (reciben ``ahora``).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, Optional

from ..pedagogy.spaced import CAJA_MAXIMA, DIA, INTERVALOS_DIAS
from .habilidades import ParametrosBKT

# Fases del ciclo según P(L) (§6.4 de la investigación).
NUEVA = "nueva"  # < 0.3: Mira y luego Hazlo conmigo con molde
ACOMPANADA = "acompanada"  # 0.3 a 0.7: Hazlo conmigo, teclas a pedido
SOLA = "sola"  # 0.7 a 0.95: Hazlo tú, sin molde
DOMINADA = "dominada"  # ≥ 0.95: entra al calendario de repaso
UMBRALES = ((0.3, NUEVA), (0.7, ACOMPANADA), (0.95, SOLA))

# Niveles de ayuda (ayudas.py): 0 sin ayuda · 1 qué falta · 2 con qué · 3 cómo (teclas) · 4 mírame (demostración).
AYUDA_QUE_DICE_LA_RESPUESTA = 3
MOLDE = 0.10  # el molde dice dónde y de qué tamaño: un acierto con molde se adivina más fácil
PISTA = 0.08  # cada nivel de pista 1 o 2 suma a G
G_MAXIMO = 0.5
APRENDE_CON_RESPUESTA = 0.5  # con la respuesta a la vista se aprende la mitad (sigue siendo una oportunidad)
PRUEBAS_PARA_SALTAR = 2  # camino rápido: dos retos sin ayuda bien hechos
SALTO = 0.9


@dataclass(frozen=True)
class Dominio:
    """Lo que el motor sabe de una habilidad de un alumno."""

    p: float  # P(L) después del último intento (sin olvido)
    intentos: int = 0
    aciertos: int = 0
    sin_ayuda: int = 0  # aciertos sin ninguna ayuda
    ultimo: float = 0.0  # epoch del último intento
    caja: int = 0  # 0 = todavía no entra al repaso
    proximo: float = 0.0  # epoch del próximo repaso (0 = ninguno)
    pruebas: int = 0  # retos del camino rápido aprobados sin ayuda
    vio_demo: bool = False
    ayuda_max: int = 0  # la ayuda más alta usada en el último intento

    def a_dict(self) -> Dict[str, Any]:
        salida = asdict(self)
        salida["p"] = round(self.p, 4)
        return salida


def nuevo(param: ParametrosBKT) -> Dominio:
    return Dominio(p=param.L0)


def estado_desde_dict(datos: Any, param_por_habilidad: Optional[Dict[str, ParametrosBKT]] = None) -> Dict[str, Dominio]:
    """El estado guardado (JSON) → {habilidad: Dominio}. Lo que no se entiende se ignora."""
    salida: Dict[str, Dominio] = {}
    if not isinstance(datos, dict):
        return salida
    campos = set(Dominio.__dataclass_fields__)
    for hid, valor in datos.items():
        if not isinstance(hid, str) or not isinstance(valor, dict):
            continue
        limpio = {k: v for k, v in valor.items() if k in campos}
        try:
            d = Dominio(**limpio) if "p" in limpio else nuevo((param_por_habilidad or {}).get(hid, ParametrosBKT()))
            d = replace(d, p=min(0.9999, max(0.0001, float(d.p))))
        except (TypeError, ValueError):
            continue
        salida[hid] = d
    return salida


def estado_a_dict(estado: Dict[str, Dominio]) -> Dict[str, Dict[str, Any]]:
    return {hid: d.a_dict() for hid, d in estado.items()}


def _retencion(d: Dominio, param: ParametrosBKT, ahora: float) -> float:
    """Qué parte de lo aprendido sigue ahí (1 = todo) según los días sin practicar y la caja."""
    if not d.ultimo or ahora <= d.ultimo:
        return 1.0
    dias = (ahora - d.ultimo) / DIA
    estabilidad = INTERVALOS_DIAS[max(1, min(CAJA_MAXIMA, d.caja or 1)) - 1]
    return math.exp(-param.olvido * dias / estabilidad)


def dominio(d: Optional[Dominio], param: ParametrosBKT, ahora: float) -> float:
    """P(L) hoy: el último valor con el olvido de los días sin practicar."""
    if d is None:
        return param.L0
    return param.L0 + (d.p - param.L0) * _retencion(d, param, ahora) if d.p > param.L0 else d.p


def fase(p: float) -> str:
    for umbral, nombre in UMBRALES:
        if p < umbral:
            return nombre
    return DOMINADA


def _posterior(p: float, correcto: bool, g: float, s: float) -> float:
    if correcto:
        num, den = p * (1 - s), p * (1 - s) + (1 - p) * g
    else:
        num, den = p * s, p * s + (1 - p) * (1 - g)
    return num / den if den > 0 else p


def registrar_intento(d: Optional[Dominio], param: ParametrosBKT, correcto: bool, ayuda: int, ahora: float,
                      molde: bool = False, tipo: str = "") -> Dominio:
    """Un intento de la habilidad: correcto o no, con qué ayuda (0 a 4), si tenía molde y de qué tipo era.

    tipo «repaso» mueve la caja de Leitner; «prueba» cuenta para el camino rápido.
    """
    d = d or nuevo(param)
    p = dominio(d, param, ahora)  # el olvido de los días sin practicar ya cuenta en este intento
    ayuda = max(0, min(4, int(ayuda or 0)))
    if ayuda >= AYUDA_QUE_DICE_LA_RESPUESTA and correcto:
        # Con las teclas o la demostración a la vista, acertar no prueba que sepa: solo cuenta la oportunidad.
        post = p
        aprende = param.T * APRENDE_CON_RESPUESTA
    else:
        g = min(G_MAXIMO, param.G + (MOLDE if molde else 0.0) + PISTA * min(ayuda, 2))
        post = _posterior(p, correcto, g, param.S)
        aprende = param.T
    p_nueva = post + (1 - post) * aprende
    p_nueva = min(0.9999, max(0.0001, p_nueva))

    caja, proximo = d.caja, d.proximo
    limpio = correcto and ayuda == 0 and not molde
    if tipo == "repaso":
        caja = min(caja + 1, CAJA_MAXIMA) if limpio else 1
        proximo = ahora + INTERVALOS_DIAS[caja - 1] * DIA
    elif caja == 0 and fase(p_nueva) == DOMINADA:
        caja, proximo = 1, ahora + INTERVALOS_DIAS[0] * DIA  # recién dominada: primer repaso mañana
    elif caja and limpio and proximo and ahora >= proximo:
        caja = min(caja + 1, CAJA_MAXIMA)  # la usó bien sola cuando ya tocaba repasar: cuenta como repaso
        proximo = ahora + INTERVALOS_DIAS[caja - 1] * DIA

    pruebas = d.pruebas + (1 if tipo == "prueba" and limpio else 0)
    if tipo == "prueba" and pruebas >= PRUEBAS_PARA_SALTAR:
        p_nueva = max(p_nueva, SALTO)  # «¿Ya sabes esto? Demuéstralo»: se salta su guía

    return Dominio(
        p=p_nueva,
        intentos=d.intentos + 1,
        aciertos=d.aciertos + (1 if correcto else 0),
        sin_ayuda=d.sin_ayuda + (1 if limpio else 0),
        ultimo=ahora,
        caja=caja,
        proximo=proximo,
        pruebas=pruebas,
        vio_demo=d.vio_demo,
        ayuda_max=ayuda,
    )


def marcar_demo(d: Optional[Dominio], param: ParametrosBKT) -> Dominio:
    """Vio la demostración (Mira): no cambia P(L), pero ya no se le muestra sola."""
    return replace(d or nuevo(param), vio_demo=True)


__all__ = [
    "ACOMPANADA", "DOMINADA", "Dominio", "NUEVA", "SOLA", "UMBRALES", "dominio", "estado_a_dict", "estado_desde_dict",
    "fase", "marcar_demo", "nuevo", "registrar_intento",
]
