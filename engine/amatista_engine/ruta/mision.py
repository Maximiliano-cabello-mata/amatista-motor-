"""La ruta del alumno (motor 4): la práctica como misiones en fila, una a la vez.

Antes el alumno veía todo a la vez: diez objetivos, la lista del ejemplo, la
teoría, el globo de la mascota y los avisos. Ahora la práctica se recorre
como una ruta:

    Parte 1 · Arma las piezas    ● Dos vagones  ● Ocho ruedas
    Parte 2 · Dale forma         ◉ Ruedas de pie   ← la misión de ahora
    Parte 3 · Acomoda las piezas ○ Ruedas en el suelo  ○ …
    Parte 4 · Revisa tu figura   ○ Amatista reconoce tu tren
    Parte 5 · Guarda             ○ Guarda tu tren

- La misión actual es el primer objetivo obligatorio sin cumplir, en el orden
  de la práctica (respeta «requires»). Es la única que se explica.
- Lo que el alumno hizo antes de tiempo queda «adelantado»: se celebra y no
  se repite.
- Cada misión dice qué hacer en una frase, sus teclas (máximo tres pasos) y
  las herramientas que usa. La interfaz ilumina esas herramientas y deja las
  que vienen después marcadas con borde.
- Las partes salen solas de lo que revisa cada objetivo (ver PARTES); el
  autor puede nombrarlas con "stage" en cada objetivo.

Python puro: el add-on lo dibuja, el servidor lo puede devolver a la
plataforma y las pruebas lo revisan sin Blender.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from ..guide.models import TONO_LOGRADO, GuideInstruction, Guidance
from ..models import COMPLETADO, EvaluationReport, PracticeDefinition, TargetDefinition
from ..pedagogy.graph import ordered
from .frases import YA_LO_TENIAS, frase_amable, logro
from .partes import PARTES, titulo_parte, titulos_partes

HECHA = "hecha"
ACTUAL = "actual"
SIGUIENTE = "siguiente"
ADELANTADA = "adelantada"  # cumplida antes de llegar a ella

MAX_PASOS = 3

@dataclass(frozen=True)
class Mision:
    id: str
    numero: int
    titulo: str
    objetivo: str  # qué hacer, en una frase
    parte: int  # índice en Ruta.partes
    estado: str  # hecha | actual | siguiente | adelantada
    por_que: str = ""
    pasos: Tuple[GuideInstruction, ...] = ()
    herramientas: Tuple[str, ...] = ()  # ids del catálogo (tools/catalogo.json)
    mensaje: str = ""  # lo que dice el instructor ahora (solo la actual)
    tono: str = ""
    cerca: bool = False
    pistas: int = 0  # cuántas pistas tiene


@dataclass(frozen=True)
class Parte:
    titulo: str
    desde: int  # número de su primera misión
    hasta: int  # número de su última misión


@dataclass(frozen=True)
class Ruta:
    practica_id: str
    titulo: str
    misiones: Tuple[Mision, ...]
    partes: Tuple[Parte, ...]
    actual: Optional[int]  # índice en misiones (None = terminada o en pausa sin misión)
    hechas: int
    completada: bool
    herramientas: Tuple[str, ...] = ()  # las de la práctica, en el orden en que se usan
    pausa: str = ""  # un vigilante detuvo el progreso: qué pasó
    celebracion: str = ""  # la misión anterior quedó cumplida («¡Eso es!»)
    nivel: int = 1

    @property
    def total(self) -> int:
        return len(self.misiones)

    @property
    def mision(self) -> Optional[Mision]:
        return self.misiones[self.actual] if self.actual is not None else None

    @property
    def parte_actual(self) -> Optional[Parte]:
        m = self.mision
        return self.partes[m.parte] if m is not None else None

    def siguientes(self, cuantas: int = 2) -> Tuple[Mision, ...]:
        if self.actual is None:
            return ()
        return tuple(m for m in self.misiones[self.actual + 1:] if m.estado == SIGUIENTE)[:cuantas]


def _pasos_de(target: TargetDefinition) -> Tuple[GuideInstruction, ...]:
    if target.guide is not None and target.guide.steps:
        return tuple(GuideInstruction(p.text, tuple(p.keys)) for p in target.guide.steps[:MAX_PASOS])
    return ()


# Herramientas cuya tecla es también una palabra común: solo cuentan si la misión la pide como tecla
# («Rueda» = botón central del ratón, no las ruedas del tren).
SOLO_POR_TECLA = {"view.navigate"}


def _herramientas(tools, practica: PracticeDefinition, pasos: Sequence[GuideInstruction], texto: str) -> Tuple[str, ...]:
    if tools is None:
        return ()
    por_tecla = [t.id for t in tools.for_step(practica, [p.keys for p in pasos], "")]
    por_texto = [t.id for t in tools.for_step(practica, (), texto) if t.id not in SOLO_POR_TECLA]
    orden = [t.id for t in tools.for_practice(practica)]
    elegidas = set(por_tecla) | set(por_texto)
    return tuple(i for i in orden if i in elegidas)


def construir_ruta(practica: PracticeDefinition, reporte: EvaluationReport, guia: Optional[Guidance] = None,
                   tools=None, pistas: Optional[Dict[str, int]] = None, anterior: Optional[str] = None) -> Ruta:
    """La ruta de la práctica según el último reporte (y la guía del paso actual, si la hay).

    pistas: {objetivo: pistas usadas}, para celebrar «sin pistas».
    anterior: id de la misión que era actual antes; si ya quedó cumplida, la
    ruta trae su celebración.
    """
    pistas = pistas or {}
    orden = [t for t in ordered(practica.targets) if not t.optional]
    aprobados = {r.target_id for r in reporte.results if r.passed is True}
    # Un validador que este motor no conoce (práctica más nueva) no frena la ruta.
    desconocidos = {r.target_id for r in reporte.results if r.passed is None}
    actual_id = reporte.current_target_id
    if actual_id is not None and (practica.target(actual_id) is None or practica.target(actual_id).optional):
        actual_id = None
    if actual_id is None and not reporte.completed:
        actual_id = next((t.id for t in orden if t.id not in aprobados and t.id not in desconocidos), None)

    partes = []
    misiones = []
    indice_actual = None
    visto_actual = False
    nombres = titulos_partes(orden)
    for numero, target in enumerate(orden, start=1):
        nombre = nombres[numero - 1]
        if not partes or partes[-1]["titulo"] != nombre:
            partes.append({"titulo": nombre, "desde": numero, "hasta": numero})
        else:
            partes[-1]["hasta"] = numero
        es_actual = target.id == actual_id
        if es_actual:
            estado = ACTUAL
            visto_actual = True
            indice_actual = numero - 1
        elif target.id in aprobados or target.id in desconocidos:
            estado = ADELANTADA if visto_actual else HECHA
        else:
            estado = SIGUIENTE
        pasos = _pasos_de(target)
        mensaje, tono, cerca = "", "", False
        if es_actual and guia is not None and guia.target_id == target.id and not guia.completed:
            if guia.instructions:
                pasos = tuple(guia.instructions[:MAX_PASOS])
            amable = frase_amable(practica, target, reporte.result(target.id), practica.level)
            mensaje = amable or guia.feedback
            tono, cerca = guia.tone, guia.tone == "cerca"
        elif es_actual:
            r = reporte.result(target.id)
            mensaje = frase_amable(practica, target, r, practica.level) or (r.message if r else "")
        elif estado == ADELANTADA:
            mensaje = YA_LO_TENIAS
        texto = " ".join(x for x in (target.tip, *(p.text for p in pasos)) if x)
        misiones.append(Mision(
            id=target.id,
            numero=numero,
            titulo=target.title or target.id,
            objetivo=target.tip,
            parte=len(partes) - 1,
            estado=estado,
            por_que=target.guide.why if target.guide is not None else "",
            pasos=pasos,
            herramientas=_herramientas(tools, practica, pasos, texto),
            mensaje=mensaje,
            tono=tono,
            cerca=cerca,
            pistas=len(target.hints),
        ))

    # Las herramientas de la práctica en el orden en que aparecen en la ruta; luego las demás.
    vistas = []
    for m in misiones:
        for h in m.herramientas:
            if h not in vistas:
                vistas.append(h)
    if tools is not None:
        for t in tools.for_practice(practica):
            if t.id not in vistas:
                vistas.append(t.id)

    celebracion = ""
    if anterior and anterior != actual_id and anterior in aprobados:
        previa = next((m for m in misiones if m.id == anterior), None)
        if previa is not None:
            celebracion = logro(previa.numero, sin_pistas=not pistas.get(anterior))

    pausa = ""
    if reporte.paused:
        vigilante = practica.guard(reporte.paused_by)
        pausa = (vigilante.title if vigilante is not None and vigilante.title else "Algo se rompió")
        if guia is not None and guia.paused and guia.feedback:
            pausa += f": {guia.feedback}"

    hechas = sum(1 for m in misiones if m.estado in (HECHA, ADELANTADA))
    return Ruta(
        practica_id=practica.id,
        titulo=practica.title,
        misiones=tuple(misiones),
        partes=tuple(Parte(p["titulo"], p["desde"], p["hasta"]) for p in partes),
        actual=None if reporte.completed else indice_actual,
        hechas=hechas,
        completada=reporte.completed,
        herramientas=tuple(vistas),
        pausa=pausa,
        celebracion=celebracion,
        nivel=practica.level,
    )


def ruta_a_dict(ruta: Optional[Ruta]) -> Optional[Dict[str, Any]]:
    """Ruta → dict JSON (latido del enlace, API y pruebas)."""
    if ruta is None:
        return None
    m = ruta.mision
    return {
        "practica": ruta.practica_id,
        "titulo": ruta.titulo,
        "total": ruta.total,
        "hechas": ruta.hechas,
        "completada": ruta.completada,
        "actual": None if m is None else {
            "id": m.id, "numero": m.numero, "titulo": m.titulo, "objetivo": m.objetivo,
            "mensaje": m.mensaje, "tono": m.tono,
            "pasos": [{"text": p.text, "keys": list(p.keys)} for p in m.pasos],
            "herramientas": list(m.herramientas),
            "parte": ruta.partes[m.parte].titulo,
        },
        "partes": [{"titulo": p.titulo, "desde": p.desde, "hasta": p.hasta} for p in ruta.partes],
        "misiones": [{"id": x.id, "numero": x.numero, "titulo": x.titulo, "estado": x.estado} for x in ruta.misiones],
        "herramientas": list(ruta.herramientas),
        "pausa": ruta.pausa,
        "celebracion": ruta.celebracion,
    }


__all__ = ["ACTUAL", "ADELANTADA", "COMPLETADO", "HECHA", "MAX_PASOS", "Mision", "PARTES", "Parte", "Ruta",
           "SIGUIENTE", "TONO_LOGRADO", "construir_ruta", "ruta_a_dict", "titulo_parte"]
