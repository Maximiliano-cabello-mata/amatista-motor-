"""Plan de estudios (motor v3): cursos, módulos y prácticas en orden.

practices/blender/cursos.json (formato amatista.curriculum/1) dice qué
cursos hay (Principiante, Principiante-Intermedio, Intermedio, Avanzado),
qué módulos tiene cada uno y qué prácticas tiene cada módulo: la de
exploración («explore», a mitad del módulo, entre teoría y teoría) y la que
lo cierra («practice»). Teoría y Blender se intercalan. El add-on lo
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
    number: int
    title: str
    practice: str  # id de la práctica que lo cierra ('' si aún no existe)
    project: str = ""
    explore: str = ""  # práctica corta de exploración a mitad del módulo ('' si no tiene)

    @property
    def sequence(self) -> Tuple[str, ...]:
        """Prácticas del módulo en el orden en que se hacen: exploración y cierre."""
        return tuple(p for p in (self.explore, self.practice) if p)


@dataclass(frozen=True)
class CourseEntry:
    id: str
    title: str
    difficulty: str
    status: str  # disponible | proximamente
    modules: Tuple[ModuleEntry, ...] = ()
    requires: str = ""  # curso que conviene terminar antes
    description: str = ""


@dataclass(frozen=True)
class Curriculum:
    route: str
    title: str
    courses: Tuple[CourseEntry, ...]

    def course(self, course_id: str) -> Optional[CourseEntry]:
        return next((c for c in self.courses if c.id == course_id), None)

    def practices(self) -> Tuple[str, ...]:
        return tuple(p for c in self.courses for m in c.modules for p in m.sequence)

    def locate(self, practice_id: str) -> Optional[Tuple[CourseEntry, ModuleEntry]]:
        for c in self.courses:
            for m in c.modules:
                if practice_id in m.sequence:
                    return c, m
        return None


def load_curriculum(data: Dict[str, Any]) -> Curriculum:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise InvalidPracticeError(f"El plan de estudios debe tener schema {SCHEMA}")
    cursos = []
    for c in data.get("courses") or []:
        if c.get("difficulty") not in DIFICULTADES:
            raise InvalidPracticeError(f"Curso {c.get('id')}: dificultad inválida (usa {', '.join(DIFICULTADES)})")
        modulos = tuple(
            ModuleEntry(int(m["number"]), str(m["title"]), str(m.get("practice") or ""), str(m.get("project") or ""),
                        str(m.get("explore") or ""))
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
    estado = unlock_state(plan, completadas)
    return next((p for p in plan.practices() if estado.get(p) == DISPONIBLE), None)
