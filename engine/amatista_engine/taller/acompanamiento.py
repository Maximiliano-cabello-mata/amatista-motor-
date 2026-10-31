"""Cuánta luz necesita el alumno ahora (motor 6.2): el termómetro de ánimo y el andamio.

El creador lo pidió así: «en un inicio todo tiene que estar activo, pero
conforme va pasando el curso se va volviendo un poco más serio [...] y lo
que no domine nosotros se lo seguimos señalando. No quiero que se frustre
el alumno». Este módulo junta las dos mitades:

1. **El termómetro** (``leer_animo``): con lo que el add-on ve mientras el
   alumno trabaja (intentos fallidos, deshacer, ráfagas de operaciones,
   la misma operación una y otra vez, piezas que se llenan y se vacían,
   tiempo sin avanzar y saltos) dice si va tranquilo, duda, está atorado o
   se está frustrando. Nunca lee el teclado ni la pantalla: solo lo que
   Blender ya registra (el historial de operadores y los cambios de la escena).

2. **El andamio** (``luz_para``): cuánta ayuda visual se enciende sola.

   - La **fase de la habilidad** (modelo.py) manda: una habilidad nueva
     tiene todo iluminado (la pieza que toca pulsa, la herramienta brilla
     desde el principio y la tarjeta dice qué hacer y qué estás haciendo);
     con ayuda, la herramienta brilla solo si duda; una dominada, nada.
   - La **madurez del curso** (cuántas habilidades domina en total) baja el
     techo: al principio todo está encendido y con el avance la luz se
     vuelve más seria. Una habilidad que no domina **no** se apaga por la
     madurez: se le sigue señalando.
   - El **ánimo** sube la luz un rato: dudar suma un escalón, atorarse o
     frustrarse suma dos y además ofrece la siguiente pista (nunca la
     respuesta) con una frase de ánimo.

Python puro y determinista (recibe ``ahora``): el add-on lo usa en vivo y
las pruebas lo revisan sin Blender.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, List, Mapping, Optional, Tuple

from .modelo import ACOMPANADA, DOMINADA, NUEVA, SOLA

# --- El termómetro -----------------------------------------------------------------------------

TRANQUILO, DUDA, ATORADO, FRUSTRADO = "tranquilo", "duda", "atorado", "frustrado"
NIVELES_ANIMO = (TRANQUILO, DUDA, ATORADO, FRUSTRADO)

VENTANA = 30.0  # s: las ráfagas se cuentan en los últimos 30 segundos
RAFAGA = 14  # operaciones en la ventana que ya son «muchos clics»
REPETIDA = 5  # la misma operación seguida sin avanzar
SIN_AVANCE_DUDA = 45.0
SIN_AVANCE_ATORADO = 100.0
# Peso de cada señal en el puntaje (0 a 1). Calibrado para que una sola señal fuerte
# (tres fallos, una ráfaga larga) llegue a «atorado» y dos juntas a «frustrado».
PESOS = {
    "fallos": 0.22,  # por cada «Comprobar» sin éxito o pieza equivocada
    "deshacer": 0.10,  # por cada Ctrl+Z seguido
    "rafaga": 0.35,  # ráfaga de operaciones sin avanzar
    "repetida": 0.25,  # la misma operación una y otra vez
    "retroceso": 0.12,  # por cada pieza que estaba llena y se vació
    "saltos": 0.18,  # por cada salto de la misma habilidad
}
UMBRALES_ANIMO = ((0.25, TRANQUILO), (0.5, DUDA), (0.8, ATORADO))


@dataclass(frozen=True)
class Senales:
    """Lo que el add-on vio durante la actividad en curso."""

    inicio: float = 0.0
    ultimo_avance: float = 0.0
    fallos: int = 0
    deshacer: int = 0  # seguidos (se reinicia al avanzar)
    operaciones: Tuple[Tuple[float, str], ...] = ()  # (cuándo, idname) de las últimas operaciones
    retrocesos: int = 0
    saltos: int = 0
    pistas: int = 0
    max_operaciones: int = 60

    def con_operacion(self, ahora: float, idname: str) -> "Senales":
        ops = self.operaciones + ((float(ahora), str(idname or "")[:64]),)
        return replace(self, operaciones=ops[-self.max_operaciones:])


@dataclass(frozen=True)
class Animo:
    nivel: str
    puntaje: float
    razones: Tuple[str, ...] = ()

    @property
    def indice(self) -> int:
        return NIVELES_ANIMO.index(self.nivel)


def senales_nuevas(ahora: float) -> Senales:
    return Senales(inicio=ahora, ultimo_avance=ahora)


def avanzo(s: Senales, ahora: float) -> Senales:
    """Una pieza se llenó u otro objetivo se cumplió: el ánimo se calma (las ráfagas viejas ya no cuentan)."""
    return replace(s, ultimo_avance=ahora, deshacer=0, operaciones=(), fallos=max(0, s.fallos - 1))


def fallo(s: Senales) -> Senales:
    return replace(s, fallos=s.fallos + 1)


def deshizo(s: Senales) -> Senales:
    return replace(s, deshacer=s.deshacer + 1)


def retrocedio(s: Senales) -> Senales:
    return replace(s, retrocesos=s.retrocesos + 1)


def pidio_pista(s: Senales) -> Senales:
    return replace(s, pistas=s.pistas + 1)


def _recientes(s: Senales, ahora: float) -> List[str]:
    return [op for t, op in s.operaciones if ahora - t <= VENTANA and t >= s.ultimo_avance]


def _repeticion(ops: List[str]) -> int:
    """Cuántas veces seguidas se repite la última operación (deshacer no cuenta: tiene su señal)."""
    utiles = [o for o in ops if o and not o.startswith("ed.undo") and not o.startswith("ed.redo")]
    if not utiles:
        return 0
    ultima, cuenta = utiles[-1], 0
    for op in reversed(utiles):
        if op != ultima:
            break
        cuenta += 1
    return cuenta


def leer_animo(s: Senales, ahora: float) -> Animo:
    """El ánimo del alumno ahora mismo, con las razones (para la tarjeta y para la plataforma)."""
    puntaje = 0.0
    razones: List[str] = []
    if s.fallos:
        puntaje += PESOS["fallos"] * min(s.fallos, 4)
        razones.append(f"{s.fallos} intento{'s' if s.fallos != 1 else ''} sin salir")
    if s.deshacer >= 2:
        puntaje += PESOS["deshacer"] * min(s.deshacer, 6)
        razones.append(f"{s.deshacer} deshacer seguidos")
    ops = _recientes(s, ahora)
    if len(ops) >= RAFAGA:
        puntaje += PESOS["rafaga"] * min(2.0, len(ops) / RAFAGA)
        razones.append("muchos clics en poco tiempo")
    if _repeticion(ops) >= REPETIDA:
        puntaje += PESOS["repetida"]
        razones.append("la misma operación una y otra vez")
    if s.retrocesos:
        puntaje += PESOS["retroceso"] * min(s.retrocesos, 3)
        razones.append("piezas que estaban y se deshicieron")
    if s.saltos:
        puntaje += PESOS["saltos"] * min(s.saltos, 3)
        razones.append("saltó esta habilidad antes")
    quieto = ahora - max(s.ultimo_avance, s.inicio)
    if quieto >= SIN_AVANCE_ATORADO:
        puntaje += 0.5
        razones.append("mucho rato sin avanzar")
    elif quieto >= SIN_AVANCE_DUDA:
        puntaje += 0.28
        razones.append("un rato sin avanzar")
    puntaje = round(min(1.0, puntaje), 3)
    nivel = FRUSTRADO
    for umbral, nombre in UMBRALES_ANIMO:
        if puntaje < umbral:
            nivel = nombre
            break
    return Animo(nivel=nivel, puntaje=puntaje, razones=tuple(razones))


# --- El andamio --------------------------------------------------------------------------------

APAGADA, TENUE, MEDIA, PLENA = 0, 1, 2, 3
NOMBRES_LUZ = {APAGADA: "apagada", TENUE: "tenue", MEDIA: "media", PLENA: "plena"}
LUZ_POR_FASE = {NUEVA: PLENA, ACOMPANADA: MEDIA, SOLA: TENUE, DOMINADA: APAGADA}
# La madurez (fracción de habilidades del curso dominadas o que ya salen solas) baja el techo.
TECHOS_MADUREZ = ((0.25, PLENA), (0.55, MEDIA), (0.85, TENUE))
SUBE_POR_ANIMO = {TRANQUILO: 0, DUDA: 1, ATORADO: 2, FRUSTRADO: 2}

FRASES = {
    DUDA: (
        "Vas bien: mira la pieza que brilla, ahí sigue.",
        "Cada intento cuenta. La pieza que pulsa es la que toca.",
    ),
    ATORADO: (
        "Te enciendo la herramienta para que la encuentres. Tú haces el resto.",
        "Esta parte cuesta a todos al principio. Mira lo que brilla.",
    ),
    FRUSTRADO: (
        "Respira, vamos con calma: te muestro dónde está, paso a paso.",
        "Nadie nace sabiendo Blender. Probemos con la siguiente pista.",
    ),
}


@dataclass(frozen=True)
class Luz:
    """Qué se ilumina solo en la vista 3D y en la tarjeta."""

    nivel: int
    pieza: bool  # la pieza que toca pulsa en el molde (y un faro encima)
    herramienta: bool  # la herramienta brilla en la barra T o en su menú
    accion: bool  # la tarjeta dice «Te toca: <herramienta>» y «Estás haciendo: …» (nunca las teclas: esas se piden)
    pulso: float  # 0 a 1: cuánto respira el brillo (más fuerte con más dificultad)
    ofrecer_pista: bool  # el ánimo pide ofrecer (no imponer) el siguiente escalón
    frase: str = ""
    razones: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def nombre(self) -> str:
        return NOMBRES_LUZ[self.nivel]


def madurez(fases: Iterable[str]) -> float:
    """Qué tanto del curso ya sale solo (0 al principio, 1 con todo dominado)."""
    fases = list(fases)
    if not fases:
        return 0.0
    peso = {NUEVA: 0.0, ACOMPANADA: 0.35, SOLA: 0.8, DOMINADA: 1.0}
    return round(sum(peso.get(f, 0.0) for f in fases) / len(fases), 3)


def techo_por_madurez(m: float) -> int:
    for umbral, techo in TECHOS_MADUREZ:
        if m < umbral:
            return techo
    return APAGADA


def debiles(fases: Mapping[str, str], intentos: Mapping[str, int], minimo_intentos: int = 3) -> Tuple[str, ...]:
    """Las habilidades que no domina pese a haberlas practicado: se le siguen señalando siempre."""
    return tuple(sorted(h for h, f in fases.items() if f in (NUEVA, ACOMPANADA) and intentos.get(h, 0) >= minimo_intentos))


def luz_para(fase_habilidad: str, m: float, animo: Optional[Animo] = None, debil: bool = False,
             reto: bool = False, indice_frase: int = 0) -> Luz:
    """La luz de la actividad en curso.

    - ``fase_habilidad``: la fase de la habilidad que toca (nueva → plena).
    - ``m``: la madurez del curso (``madurez``): baja el techo con el avance.
    - ``debil``: la habilidad está en ``debiles``: la madurez no la apaga.
    - ``reto``: en retos y repasos la luz no pasa de tenue aunque cueste
      (son para demostrar), pero el ánimo sí ofrece la pista que haya.
    """
    base = LUZ_POR_FASE.get(fase_habilidad, PLENA)
    techo = PLENA if debil else max(techo_por_madurez(m), TENUE if base >= MEDIA else APAGADA)
    nivel = min(base, techo)
    animo = animo or Animo(TRANQUILO, 0.0)
    nivel = min(PLENA, nivel + SUBE_POR_ANIMO[animo.nivel])
    if debil:
        nivel = max(nivel, MEDIA)
    if reto:
        nivel = min(nivel, TENUE)
    frases = FRASES.get(animo.nivel, ())
    return Luz(
        nivel=nivel,
        pieza=nivel >= TENUE,
        herramienta=not reto and (nivel >= PLENA or (nivel >= MEDIA and animo.indice >= 1)),
        accion=nivel >= MEDIA and not reto,
        pulso=round(min(1.0, 0.25 + 0.25 * nivel + 0.25 * animo.indice), 3) if nivel else 0.0,
        ofrecer_pista=animo.nivel in (ATORADO, FRUSTRADO),
        frase=frases[indice_frase % len(frases)] if frases else "",
        razones=animo.razones,
    )


__all__ = [
    "APAGADA", "ATORADO", "Animo", "DUDA", "FRUSTRADO", "Luz", "MEDIA", "NIVELES_ANIMO", "PLENA", "Senales", "TENUE",
    "TRANQUILO", "avanzo", "debiles", "deshizo", "fallo", "leer_animo", "luz_para", "madurez", "pidio_pista",
    "retrocedio", "senales_nuevas", "techo_por_madurez",
]
