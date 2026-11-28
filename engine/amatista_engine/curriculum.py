"""Plan de estudios (motor v3): cursos, módulos y prácticas en orden.

practices/blender/cursos.json (formato amatista.curriculum/1) dice qué
cursos hay (Principiante, Principiante-Intermedio, Intermedio, Avanzado),
qué módulos tiene cada uno y qué prácticas tiene cada módulo: la que lo
cierra («practice», el proyecto) y, desde el motor 5, su taller («taller»:
las habilidades del módulo, en practices/blender/habilidades.json), que
reemplaza a la exploración de antes («explore», que sigue leyéndose para
planes viejos). Teoría y Blender se intercalan. El add-on lo
usa para dibujar el mapa del curso y decidir qué se desbloquea; la
plataforma usa los mismos ids.

    plan = load_curriculum(datos)
    estado = unlock_state(plan, completadas={"blender.bp.m1.tren"})
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from .errors import InvalidPracticeError

SCHEMA = "amatista.curriculum/1"
DIFICULTADES = ("principiante", "principiante_intermedio", "intermedio", "avanzado")

COMPLETADO = "completado"
DISPONIBLE = "disponible"
BLOQUEADO = "bloqueado"
PROXIMAMENTE = "proximamente"


@dataclass(frozen=True)
class ModuleEntry:
    """Módulo de un curso: número, título, la práctica que lo cierra y sus extras (proyecto, exploración, taller)."""
    number: int
    title: str
    practice: str  # id de la práctica que lo cierra ('' si aún no existe)
    project: str = ""
    explore: str = ""  # práctica corta de exploración a mitad del módulo ('' si no tiene; motor 5: el taller)
    taller: str = ""  # motor 5: el taller del módulo (practices/blender/habilidades.json)

    @property
    def sequence(self) -> Tuple[str, ...]:
        """Prácticas del módulo en el orden en que se hacen: exploración y cierre."""
        return tuple(p for p in (self.explore, self.practice) if p)


@dataclass(frozen=True)
class CourseEntry:
    """Curso del plan de estudios: id, título, dificultad, estado (disponible/próximamente), módulos y curso previo recomendado."""
    id: str
    title: str
    difficulty: str
    status: str  # disponible | proximamente
    modules: Tuple[ModuleEntry, ...] = ()
    requires: str = ""  # curso que conviene terminar antes
    description: str = ""


@dataclass(frozen=True)
class Curriculum:
    """Plan de estudios completo de una ruta (p. ej. Blender): cursos en orden con sus módulos y prácticas."""
    route: str
    title: str
    courses: Tuple[CourseEntry, ...]

    def course(self, course_id: str) -> Optional[CourseEntry]:
        """Curso con ese id, o None si no está en el plan."""
        return next((c for c in self.courses if c.id == course_id), None)

    def practices(self) -> Tuple[str, ...]:
        """Ids de todas las prácticas del plan en el orden en que el alumno las recorre (curso → módulo → secuencia)."""
        return tuple(p for c in self.courses for m in c.modules for p in m.sequence)

    def locate(self, practice_id: str) -> Optional[Tuple[CourseEntry, ModuleEntry]]:
        """Curso y módulo al que pertenece una práctica, o None si no figura en el plan."""
        for c in self.courses:
            for m in c.modules:
                if practice_id in m.sequence:
                    return c, m
        return None


def load_curriculum(data: Dict[str, Any]) -> Curriculum:
    """Construye el Curriculum desde el JSON del plan de estudios (schema SCHEMA).

    Raises:
        InvalidPracticeError: si el schema no coincide o un curso tiene una dificultad no admitida.
    """
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise InvalidPracticeError(f"El plan de estudios debe tener schema {SCHEMA}")
    cursos = []
    for c in data.get("courses") or []:
        if c.get("difficulty") not in DIFICULTADES:
            raise InvalidPracticeError(f"Curso {c.get('id')}: dificultad inválida (usa {', '.join(DIFICULTADES)})")
        modulos = tuple(
            ModuleEntry(int(m["number"]), str(m["title"]), str(m.get("practice") or ""), str(m.get("project") or ""),
                        str(m.get("explore") or ""), str(m.get("taller") or ""))
            for m in c.get("modules") or []
        )
        cursos.append(CourseEntry(
            id=str(c["id"]), title=str(c["title"]), difficulty=c["difficulty"],
            status=str(c.get("status") or "disponible"), modules=modulos, requires=str(c.get("requires") or ""),
            description=str(c.get("description") or ""),
        ))
    return Curriculum(route=str(data.get("route") or ""), title=str(data.get("title") or ""), courses=tuple(cursos))


def unlock_state(plan: Curriculum, completadas: Iterable[str]) -> Dict[str, str]:
    """Estado de cada práctica: completado, disponible o bloqueado.

    Dentro de un curso los módulos van en orden (el primero sin terminar
    está disponible, los siguientes bloqueados). Un curso no se bloquea
    por el anterior: quien ya sabe lo básico puede empezar en
    Principiante-Intermedio (la plataforma solo lo recomienda).
    """
    hechas = set(completadas)
    estado: Dict[str, str] = {}
    for curso in plan.courses:
        abierto = curso.status != PROXIMAMENTE
        for practica in (p for modulo in curso.modules for p in modulo.sequence):
            if practica in hechas:
                estado[practica] = COMPLETADO
            elif abierto:
                estado[practica] = DISPONIBLE
                abierto = False
            else:
                estado[practica] = BLOQUEADO if curso.status != PROXIMAMENTE else PROXIMAMENTE
    return estado


def next_practice(plan: Curriculum, completadas: Iterable[str]) -> Optional[str]:
    """Primera práctica del plan que el alumno tiene disponible (desbloqueada y sin completar), o None."""
    estado = unlock_state(plan, completadas)
    return next((p for p in plan.practices() if estado.get(p) == DISPONIBLE), None)
