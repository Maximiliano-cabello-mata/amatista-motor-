"""El catálogo de habilidades y talleres (formato ``amatista.skill/1``).

Un archivo por ruta (``practices/blender/habilidades.json``) con dos listas:

- ``habilidades``: cada una trae lo necesario para el ciclo completo: qué es
  (una frase), sus teclas, las herramientas que se iluminan, su
  demostración, dos o tres variaciones con su molde, el reto de transferencia,
  el reto de repaso y los parámetros iniciales del modelo del alumno (BKT).
- ``talleres``: uno por módulo del plan de estudios: qué habilidades enseña,
  qué proyecto las combina (una práctica ``amatista.practice/2`` de siempre),
  el reto final sin molde, qué habilidades de módulos anteriores repasa y qué
  pieza deja en la isla del alumno.

Agregar contenido deja de ser «escribir otra práctica de once misiones»: es
agregar una habilidad o un taller que combina las que ya existen. El modelo
del alumno, el repaso y la interfaz no cambian.

Lectura estricta con errores en español, como las prácticas
(practice/loader.py): un dato mal escrito sale como ``ErrorCatalogo`` con la
ruta exacta del problema, nunca como otro error.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ..errors import InvalidPracticeError

SCHEMA = "amatista.skill/1"
PATRON_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,59}$")
PRIMITIVAS = ("cube", "cylinder", "sphere", "icosphere", "cone", "torus", "plane", "circle", "suzanne")
# Lo que la demostración sabe hacer (el add-on lo anima en la vista 3D: vista/demo.py).
ACCIONES_DEMO = (
    "agregar", "mover", "escalar", "rotar", "vista", "editar", "extruir", "corte", "modificador", "aplicar",
    "material", "luz", "camara", "clave", "coleccion", "render", "guardar", "duplicar", "borrar", "texto",
)
META_DEMO = ("texto", "teclas", "segundos")  # lo que acompaña a la acción de un paso
MAX_PALABRAS = 25  # regla 5: una tarjeta, una cosa, máximo 25 palabras
MAX_VARIACIONES = 6


def accion_de_paso(paso: Any) -> List[str]:
    """Las acciones de un paso de la demostración («texto» solo cuenta si no hay otra)."""
    if not isinstance(paso, dict):
        return []
    acciones = [k for k in paso if k in ACCIONES_DEMO and k not in META_DEMO]
    return acciones or (["texto"] if "texto" in paso else [])


class ErrorCatalogo(InvalidPracticeError):
    """El catálogo de habilidades tiene datos que no se pueden usar."""


@dataclass(frozen=True)
class ParametrosBKT:
    """Rastreo bayesiano del conocimiento (Corbett y Anderson, 1995).

    L0: probabilidad de saberla antes de empezar · T: de aprenderla en cada
    oportunidad · G: de acertar sin saberla (adivinar) · S: de fallar
    sabiéndola (descuido) · olvido: cuánto se pierde por día sin repasar
    (caja 1; las cajas siguientes olvidan más despacio). Valores iniciales de
    §4.4 de la investigación: se reajustan con los datos de Amatista.
    """

    L0: float = 0.10
    T: float = 0.12
    G: float = 0.15
    S: float = 0.10
    olvido: float = 0.05


@dataclass(frozen=True)
class Variacion:
    """Un objeto chico para practicar la habilidad (1 a 3 minutos)."""

    id: str
    pide: str  # lo que se pide, en una frase («Una tabla larga y plana»)
    molde: Tuple[Dict[str, Any], ...] = ()  # piezas como reference.parts (primitive, size, location, rotation)
    objetivos: Tuple[Dict[str, Any], ...] = ()  # objetivos extra en formato de práctica (materiales, luces…)
    inicio: Dict[str, Any] = field(default_factory=dict)  # starter de la práctica que se genera
    minutos: int = 2
    nombre: str = ""  # cómo se llama la pieza en los mensajes («la tabla»)
    solo_dibujo: bool = False  # el molde solo guía (una malla editada): lo revisan los objetivos


@dataclass(frozen=True)
class Reto:
    """Transferencia sin molde: algo nuevo que combina lo aprendido."""

    id: str
    pide: str
    piezas: Tuple[Dict[str, Any], ...] = ()  # figura que debe reconocerse (en cualquier lugar y tamaño)
    objetivos: Tuple[Dict[str, Any], ...] = ()
    inicio: Dict[str, Any] = field(default_factory=dict)
    minutos: int = 3
    libre: bool = True  # la figura se revisa sin importar dónde está ni su tamaño


@dataclass(frozen=True)
class Habilidad:
    id: str
    titulo: str
    que: str  # qué es y para qué sirve, en una frase
    teclas: Tuple[str, ...] = ()  # la secuencia («S», «X|Y|Z»): se muestra solo cuando la ayuda lo permite
    como: str = ""  # la secuencia en palabras («S y luego el eje»)
    herramientas: Tuple[str, ...] = ()  # ids de tools/catalogo.json (se iluminan)
    requiere: Tuple[str, ...] = ()
    nivel: int = 1
    demo: Tuple[Dict[str, Any], ...] = ()
    variaciones: Tuple[Variacion, ...] = ()
    reto: Optional[Reto] = None  # «¿Ya sabes esto? Demuéstralo» y transferencia de la habilidad
    repaso: Optional[Reto] = None  # el reto de un minuto de «Recuérdalo»
    bkt: ParametrosBKT = field(default_factory=ParametrosBKT)
    errores: Dict[str, str] = field(default_factory=dict)  # motivo → frase sobre el modelo


@dataclass(frozen=True)
class Taller:
    """Un módulo del plan de estudios con la forma del ciclo."""

    id: str
    curso: str
    modulo: int
    titulo: str
    nivel: int
    habilidades: Tuple[str, ...]
    proyecto: str = ""  # id de la práctica del proyecto (Úsalo)
    reto: Optional[Reto] = None  # el reto final del módulo
    repasa: Tuple[str, ...] = ()  # habilidades de módulos anteriores que vuelven aquí
    isla: Dict[str, Any] = field(default_factory=dict)  # {pieza, texto, lugar: [x, y], color}
    leccion: str = ""  # lección de la plataforma donde vive el taller


@dataclass(frozen=True)
class Catalogo:
    ruta: str
    habilidades: Dict[str, Habilidad]
    talleres: Tuple[Taller, ...]

    def habilidad(self, habilidad_id: str) -> Optional[Habilidad]:
        return self.habilidades.get(habilidad_id)

    def taller(self, taller_id: str) -> Optional[Taller]:
        return next((t for t in self.talleres if t.id == taller_id), None)

    def taller_de_modulo(self, curso: str, modulo: int) -> Optional[Taller]:
        return next((t for t in self.talleres if t.curso == curso and t.modulo == int(modulo or 0)), None)

    def taller_de_proyecto(self, practica_id: str) -> Optional[Taller]:
        return next((t for t in self.talleres if t.proyecto and t.proyecto == practica_id), None)

    def anteriores(self, taller_id: str) -> Tuple[Taller, ...]:
        """Los talleres que vienen antes en el plan (el orden del archivo)."""
        ids = [t.id for t in self.talleres]
        if taller_id not in ids:
            return ()
        return self.talleres[: ids.index(taller_id)]

    def orden(self, ids: Iterable[str]) -> List[str]:
        """Las habilidades en un orden que respeta «requiere» (estable: el del taller cuando se puede)."""
        pendientes = [i for i in ids if i in self.habilidades]
        salida: List[str] = []
        while pendientes:
            for i in pendientes:
                previas = [r for r in self.habilidades[i].requiere if r in pendientes and r != i]
                if not previas:
                    salida.append(i)
                    pendientes.remove(i)
                    break
            else:  # un ciclo (lo impide la lectura): se respeta el orden dado
                salida.extend(pendientes)
                break
        return salida


# --- Lectura ---------------------------------------------------------------------------------


class _Errores:
    def __init__(self) -> None:
        self.lista: List[str] = []

    def add(self, texto: str) -> None:
        self.lista.append(texto)

    def texto(self, datos: Dict[str, Any], clave: str, donde: str, obligatorio: bool = True, maximo: int = 400) -> str:
        valor = datos.get(clave, "")
        if valor in (None, "") and not obligatorio:
            return ""
        if not isinstance(valor, str) or not valor.strip():
            self.add(f"{donde}: '{clave}' debe ser un texto")
            return ""
        if len(valor) > maximo:
            self.add(f"{donde}: '{clave}' admite como máximo {maximo} caracteres")
        return valor.strip()

    def ids(self, valor: Any, donde: str) -> Tuple[str, ...]:
        if valor in (None, []):
            return ()
        if not isinstance(valor, list) or not all(isinstance(x, str) and PATRON_ID.match(x) for x in valor):
            self.add(f"{donde} debe ser una lista de ids (minúsculas, números, punto o guion)")
            return ()
        return tuple(valor)

    def frase(self, texto: str, donde: str) -> None:
        if texto and len(texto.split()) > MAX_PALABRAS:
            self.add(f"{donde}: tiene {len(texto.split())} palabras; una tarjeta admite {MAX_PALABRAS} (regla 5)")


def _numeros(valor: Any, donde: str, e: _Errores, positivos: bool = False) -> Tuple[float, float, float]:
    if not isinstance(valor, list) or len(valor) != 3 or not all(
        isinstance(x, (int, float)) and not isinstance(x, bool) for x in valor
    ):
        e.add(f"{donde} debe ser una lista de tres números")
        return (0.0, 0.0, 0.0)
    if positivos and any(x < 0 for x in valor):
        e.add(f"{donde} no puede tener medidas negativas")
    return tuple(float(x) for x in valor)  # type: ignore[return-value]


def _piezas(valor: Any, donde: str, e: _Errores) -> Tuple[Dict[str, Any], ...]:
    """Piezas en el formato de reference.parts (las mismas que entiende el reconocedor de figuras)."""
    if valor in (None, []):
        return ()
    if not isinstance(valor, list) or len(valor) > 40:
        e.add(f"{donde} debe ser una lista de hasta 40 piezas")
        return ()
    salida = []
    for i, crudo in enumerate(valor):
        aqui = f"{donde}[{i}]"
        if not isinstance(crudo, dict):
            e.add(f"{aqui} debe ser un objeto")
            continue
        primitiva = crudo.get("primitive")
        if primitiva not in PRIMITIVAS:
            e.add(f"{aqui}.primitive debe ser una de: {', '.join(PRIMITIVAS)}")
            continue
        pieza: Dict[str, Any] = {"primitive": primitiva, "size": list(_numeros(crudo.get("size"), f"{aqui}.size", e, True))}
        if crudo.get("location") is not None:
            pieza["location"] = list(_numeros(crudo["location"], f"{aqui}.location", e))
        if crudo.get("rotation") is not None:
            pieza["rotation"] = list(_numeros(crudo["rotation"], f"{aqui}.rotation", e))
        for clave in ("name", "role", "color", "join"):
            if crudo.get(clave):
                if not isinstance(crudo[clave], str):
                    e.add(f"{aqui}.{clave} debe ser un texto")
                else:
                    pieza[clave] = crudo[clave]
        if crudo.get("compare") is False:
            pieza["compare"] = False
        salida.append(pieza)
    return tuple(salida)


def _objetivos(valor: Any, donde: str, e: _Errores) -> Tuple[Dict[str, Any], ...]:
    """Objetivos extra en el formato de práctica (los revisa el compilador al generar la práctica)."""
    if valor in (None, []):
        return ()
    if not isinstance(valor, list) or not all(isinstance(o, dict) and o.get("id") and o.get("validator") for o in valor):
        e.add(f"{donde} debe ser una lista de objetivos con id y validator")
        return ()
    return tuple(valor)


def _inicio(valor: Any, donde: str, e: _Errores) -> Dict[str, Any]:
    if valor in (None, {}):
        return {}
    if not isinstance(valor, dict):
        e.add(f"{donde} debe ser un objeto (como el starter de una práctica)")
        return {}
    return dict(valor)


def _minutos(valor: Any, donde: str, e: _Errores, defecto: int) -> int:
    if valor is None:
        return defecto
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 30:
        e.add(f"{donde} debe ser un entero entre 1 y 30")
        return defecto
    return valor


def _variacion(crudo: Any, donde: str, e: _Errores) -> Optional[Variacion]:
    if not isinstance(crudo, dict):
        e.add(f"{donde} debe ser un objeto")
        return None
    vid = crudo.get("id")
    if not isinstance(vid, str) or not PATRON_ID.match(vid):
        e.add(f"{donde}.id debe ser un id (minúsculas, números, punto o guion)")
        return None
    pide = e.texto(crudo, "pide", donde, maximo=200)
    e.frase(pide, f"{donde}.pide")
    molde = _piezas(crudo.get("molde"), f"{donde}.molde", e)
    objetivos = _objetivos(crudo.get("objetivos"), f"{donde}.objetivos", e)
    solo_dibujo = crudo.get("solo_dibujo", False)
    if not isinstance(solo_dibujo, bool):
        e.add(f"{donde}.solo_dibujo debe ser true o false")
        solo_dibujo = False
    if not objetivos and (not molde or solo_dibujo):
        e.add(f"{donde} necesita 'molde' u 'objetivos': algo que revisar")
    return Variacion(
        id=vid,
        pide=pide,
        molde=molde,
        objetivos=objetivos,
        inicio=_inicio(crudo.get("inicio"), f"{donde}.inicio", e),
        minutos=_minutos(crudo.get("minutos"), f"{donde}.minutos", e, 2),
        nombre=crudo.get("nombre") if isinstance(crudo.get("nombre"), str) else "",
        solo_dibujo=solo_dibujo,
    )


def _reto(crudo: Any, donde: str, e: _Errores, defecto_id: str) -> Optional[Reto]:
    if crudo in (None, {}):
        return None
    if not isinstance(crudo, dict):
        e.add(f"{donde} debe ser un objeto")
        return None
    rid = crudo.get("id") or defecto_id
    if not isinstance(rid, str) or not PATRON_ID.match(rid):
        e.add(f"{donde}.id debe ser un id")
        rid = defecto_id
    pide = e.texto(crudo, "pide", donde, maximo=200)
    e.frase(pide, f"{donde}.pide")
    piezas = _piezas(crudo.get("piezas"), f"{donde}.piezas", e)
    objetivos = _objetivos(crudo.get("objetivos"), f"{donde}.objetivos", e)
    if not piezas and not objetivos:
        e.add(f"{donde} necesita 'piezas' o 'objetivos'")
    libre = crudo.get("libre", True)
    if not isinstance(libre, bool):
        e.add(f"{donde}.libre debe ser true o false")
        libre = True
    return Reto(
        id=rid,
        pide=pide,
        piezas=piezas,
        objetivos=objetivos,
        inicio=_inicio(crudo.get("inicio"), f"{donde}.inicio", e),
        minutos=_minutos(crudo.get("minutos"), f"{donde}.minutos", e, 3),
        libre=libre,
    )


def _demo(crudo: Any, donde: str, e: _Errores) -> Tuple[Dict[str, Any], ...]:
    pasos = (crudo or {}).get("pasos") if isinstance(crudo, dict) else crudo
    if pasos in (None, []):
        return ()
    if not isinstance(pasos, list) or len(pasos) > 20:
        e.add(f"{donde}.pasos debe ser una lista de hasta 20 pasos")
        return ()
    salida = []
    for i, paso in enumerate(pasos):
        aqui = f"{donde}.pasos[{i}]"
        acciones = accion_de_paso(paso)
        if len(acciones) != 1:
            e.add(f"{aqui} debe tener una sola acción de: {', '.join(ACCIONES_DEMO)}")
            continue
        salida.append(dict(paso))
    return tuple(salida)


def _bkt(crudo: Any, donde: str, e: _Errores) -> ParametrosBKT:
    if crudo in (None, {}):
        return ParametrosBKT()
    if not isinstance(crudo, dict):
        e.add(f"{donde} debe ser un objeto {{L0, T, G, S}}")
        return ParametrosBKT()
    base = ParametrosBKT()
    valores = {}
    for clave, maximo in (("L0", 0.9), ("T", 0.6), ("G", 0.4), ("S", 0.3), ("olvido", 0.5)):
        valor = crudo.get(clave, getattr(base, clave))
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= maximo:
            e.add(f"{donde}.{clave} debe ser un número entre 0 y {maximo}")
            valor = getattr(base, clave)
        valores[clave] = float(valor)
    return ParametrosBKT(**valores)


def _habilidad(crudo: Any, i: int, e: _Errores) -> Optional[Habilidad]:
    donde = f"habilidades[{i}]"
    if not isinstance(crudo, dict):
        e.add(f"{donde} debe ser un objeto")
        return None
    hid = crudo.get("id")
    if not isinstance(hid, str) or not PATRON_ID.match(hid):
        e.add(f"{donde}.id debe ser un id (minúsculas, números, punto o guion)")
        return None
    donde = f"Habilidad «{hid}»"
    titulo = e.texto(crudo, "titulo", donde, maximo=80)
    que = e.texto(crudo, "que", donde, maximo=200)
    e.frase(que, f"{donde}.que")
    teclas = crudo.get("teclas") or []
    if not isinstance(teclas, list) or not all(isinstance(t, str) and t for t in teclas):
        e.add(f"{donde}.teclas debe ser una lista de teclas («Shift+A», «S», «X|Y|Z»)")
        teclas = []
    variaciones = []
    crudas = crudo.get("variaciones") or []
    if not isinstance(crudas, list) or len(crudas) > MAX_VARIACIONES:
        e.add(f"{donde}.variaciones debe ser una lista de hasta {MAX_VARIACIONES}")
        crudas = []
    vistos = set()
    for j, cruda in enumerate(crudas):
        v = _variacion(cruda, f"{donde}.variaciones[{j}]", e)
        if v is None:
            continue
        if v.id in vistos:
            e.add(f"{donde}: la variación «{v.id}» está repetida")
        vistos.add(v.id)
        variaciones.append(v)
    if not variaciones:
        e.add(f"{donde} necesita al menos una variación (Hazlo conmigo)")
    nivel = crudo.get("nivel", 1)
    if isinstance(nivel, bool) or not isinstance(nivel, int) or not 1 <= nivel <= 5:
        e.add(f"{donde}.nivel debe ser un entero entre 1 y 5")
        nivel = 1
    errores = crudo.get("errores") or {}
    if not isinstance(errores, dict) or not all(isinstance(v, str) for v in errores.values()):
        e.add(f"{donde}.errores debe ser un objeto {{motivo: frase}}")
        errores = {}
    return Habilidad(
        id=hid,
        titulo=titulo,
        que=que,
        teclas=tuple(teclas),
        como=e.texto(crudo, "como", donde, obligatorio=False, maximo=200),
        herramientas=e.ids(crudo.get("herramientas"), f"{donde}.herramientas"),
        requiere=e.ids(crudo.get("requiere"), f"{donde}.requiere"),
        nivel=nivel,
        demo=_demo(crudo.get("demo"), f"{donde}.demo", e),
        variaciones=tuple(variaciones),
        reto=_reto(crudo.get("reto"), f"{donde}.reto", e, f"{hid}.reto"),
        repaso=_reto(crudo.get("repaso"), f"{donde}.repaso", e, f"{hid}.repaso"),
        bkt=_bkt(crudo.get("bkt"), f"{donde}.bkt", e),
        errores=dict(errores),
    )


def _taller(crudo: Any, i: int, e: _Errores) -> Optional[Taller]:
    donde = f"talleres[{i}]"
    if not isinstance(crudo, dict):
        e.add(f"{donde} debe ser un objeto")
        return None
    tid = crudo.get("id")
    if not isinstance(tid, str) or not PATRON_ID.match(tid):
        e.add(f"{donde}.id debe ser un id")
        return None
    donde = f"Taller «{tid}»"
    modulo = crudo.get("modulo")
    if isinstance(modulo, bool) or not isinstance(modulo, int) or not 1 <= modulo <= 20:
        e.add(f"{donde}.modulo debe ser un entero entre 1 y 20")
        modulo = 1
    nivel = crudo.get("nivel", 1)
    if isinstance(nivel, bool) or not isinstance(nivel, int) or not 1 <= nivel <= 5:
        e.add(f"{donde}.nivel debe ser un entero entre 1 y 5")
        nivel = 1
    habilidades = e.ids(crudo.get("habilidades"), f"{donde}.habilidades")
    if not habilidades:
        e.add(f"{donde} necesita al menos una habilidad")
    isla = crudo.get("isla") or {}
    if not isinstance(isla, dict):
        e.add(f"{donde}.isla debe ser un objeto {{pieza, texto, lugar}}")
        isla = {}
    if isla.get("lugar") is not None and (
        not isinstance(isla["lugar"], list) or len(isla["lugar"]) != 2
        or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in isla["lugar"])
    ):
        e.add(f"{donde}.isla.lugar debe ser [x, y]")
        isla = {k: v for k, v in isla.items() if k != "lugar"}
    proyecto = crudo.get("proyecto") or ""
    if proyecto and (not isinstance(proyecto, str) or not PATRON_ID.match(proyecto)):
        e.add(f"{donde}.proyecto debe ser el id de una práctica")
        proyecto = ""
    return Taller(
        id=tid,
        curso=e.texto(crudo, "curso", donde, maximo=60),
        modulo=modulo,
        titulo=e.texto(crudo, "titulo", donde, maximo=120),
        nivel=nivel,
        habilidades=habilidades,
        proyecto=proyecto,
        reto=_reto(crudo.get("reto"), f"{donde}.reto", e, f"{tid}.reto"),
        repasa=e.ids(crudo.get("repasa"), f"{donde}.repasa"),
        isla=dict(isla),
        leccion=crudo.get("leccion") if isinstance(crudo.get("leccion"), str) else "",
    )


def _sin_ciclos(habilidades: Dict[str, Habilidad], e: _Errores) -> None:
    estado: Dict[str, int] = {}

    def visitar(hid: str, camino: List[str]) -> None:
        if estado.get(hid) == 2:
            return
        if estado.get(hid) == 1:
            e.add(f"«requiere» forma un ciclo: {' → '.join(camino + [hid])}")
            return
        estado[hid] = 1
        for previa in habilidades[hid].requiere:
            if previa in habilidades:
                visitar(previa, camino + [hid])
        estado[hid] = 2

    for hid in habilidades:
        visitar(hid, [])


def cargar_catalogo(datos: Dict[str, Any]) -> Catalogo:
    """JSON → Catalogo. Cualquier problema sale como ErrorCatalogo con todos los errores."""
    if not isinstance(datos, dict):
        raise ErrorCatalogo("El catálogo de habilidades debe ser un objeto JSON")
    e = _Errores()
    if datos.get("schema") != SCHEMA:
        e.add(f"'schema' debe ser «{SCHEMA}»")
    crudas = datos.get("habilidades")
    if not isinstance(crudas, list) or not crudas:
        raise ErrorCatalogo("'habilidades' debe ser una lista con al menos una habilidad")
    habilidades: Dict[str, Habilidad] = {}
    for i, crudo in enumerate(crudas):
        h = _habilidad(crudo, i, e)
        if h is None:
            continue
        if h.id in habilidades:
            e.add(f"La habilidad «{h.id}» está repetida")
        habilidades[h.id] = h
    for h in habilidades.values():
        for previa in h.requiere:
            if previa not in habilidades:
                e.add(f"Habilidad «{h.id}»: requiere «{previa}», que no existe")
    _sin_ciclos(habilidades, e)
    talleres: List[Taller] = []
    for i, crudo in enumerate(datos.get("talleres") or []):
        t = _taller(crudo, i, e)
        if t is None:
            continue
        if any(x.id == t.id for x in talleres):
            e.add(f"El taller «{t.id}» está repetido")
        for hid in t.habilidades + t.repasa:
            if hid not in habilidades:
                e.add(f"Taller «{t.id}»: la habilidad «{hid}» no existe")
        talleres.append(t)
    if e.lista:
        raise ErrorCatalogo(e.lista[0], e.lista)
    return Catalogo(ruta=str(datos.get("ruta") or ""), habilidades=habilidades, talleres=tuple(talleres))


def leer_catalogo(ruta: Union[str, Path]) -> Catalogo:
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ErrorCatalogo(f"No se pudo leer {ruta}: {error}") from error
    return cargar_catalogo(datos)


def nombre_de_pieza(pieza: Dict[str, Any], defecto: str = "") -> str:
    """Cómo se llama una pieza en los mensajes: su nombre, su rol o la primitiva."""
    from ..validators.figure import NOMBRE_PRIMITIVA

    return str(pieza.get("name") or pieza.get("role") or defecto or NOMBRE_PRIMITIVA.get(pieza.get("primitive", ""), "pieza"))


__all__ = [
    "ACCIONES_DEMO", "Catalogo", "ErrorCatalogo", "Habilidad", "MAX_PALABRAS", "ParametrosBKT", "Reto", "SCHEMA",
    "Taller", "Variacion", "cargar_catalogo", "leer_catalogo", "nombre_de_pieza",
]

