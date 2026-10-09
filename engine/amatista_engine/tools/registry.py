"""Catálogo de herramientas de Blender y política por nivel (secciones 13 y 14).

Cada herramienta tiene nombre, atajo, nivel mínimo y descripción: las
prácticas solo citan su id. Las que declaran «detect» se reconocen en la
escena (un modificador BOOLEAN, un objeto CURVE, el modo SCULPT...) y el
motor avisa si pertenecen a un nivel posterior. La política es ADVERTIR,
no bloquear: Blender sigue abierto para experimentar.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from ..models import PracticeDefinition, SceneState, ToolWarning

CATALOGO = Path(__file__).with_name("catalogo.json")

ALLOW = "allow"
WARN = "warn"


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    shortcut: str = ""
    minimum_level: int = 1
    category: str = ""
    description: str = ""
    detect: Dict[str, object] = field(default_factory=dict)
    # Motor 3.4 (modo enfocado): teclas que la delatan en un paso, cómo se
    # usa (pasos del diálogo «¿Cómo se usa?»), el error típico y la acción
    # del botón «Usar» en Blender (tool, operator, menu, panel o tab).
    keys: Tuple[str, ...] = ()
    howto: Tuple[str, ...] = ()
    mistake: str = ""
    action: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "shortcut": self.shortcut, "level": self.minimum_level,
                "category": self.category, "description": self.description, "keys": list(self.keys),
                "howto": list(self.howto), "mistake": self.mistake, "action": dict(self.action)}


def _combos(teclas: Sequence[str]) -> set:
    """("Shift", "D", "X") → {"Shift", "D", "X", "Shift+D", "D+X"}: teclas sueltas y combinaciones."""
    teclas = [str(t).strip() for t in teclas if str(t).strip()]
    salida = {t.lower() for t in teclas}
    salida |= {f"{a}+{b}".lower() for a, b in zip(teclas, teclas[1:])}
    return salida


def _en_texto(tecla: str, texto: str) -> bool:
    """¿El texto cita la tecla? «Shift+D», «pulsa S»... (mayúsculas exactas, palabra completa)."""
    if not texto or not tecla:
        return False
    return re.search(rf"(?<![\w+.]){re.escape(tecla)}(?![\w+.])", texto) is not None


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: Dict[str, Tool] = {t.id: t for t in tools}

    @classmethod
    def default(cls) -> "ToolRegistry":
        datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
        return cls(
            Tool(
                id=t["id"],
                name=t["name"],
                shortcut=t.get("shortcut", ""),
                minimum_level=int(t.get("minimumLevel", 1)),
                category=t.get("category", ""),
                description=t.get("description", ""),
                detect=dict(t.get("detect", {})),
                keys=tuple(t.get("keys", ())),
                howto=tuple(t.get("howto", ())),
                mistake=t.get("mistake", ""),
                action=dict(t.get("action", {})),
            )
            for t in datos["tools"]
        )

    def get(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def all(self) -> Tuple[Tool, ...]:
        return tuple(sorted(self._tools.values(), key=lambda t: (t.minimum_level, t.category, t.name)))

    def for_practice(self, practice: PracticeDefinition) -> Tuple[Tool, ...]:
        """Las herramientas que la práctica permite, en el orden del autor (modo enfocado)."""
        return tuple(t for t in (self.get(i) for i in practice.allowed_tools) if t is not None)

    def for_step(self, practice: PracticeDefinition, keys: Iterable[Sequence[str]] = (),
                 text: str = "") -> Tuple[Tool, ...]:
        """Las herramientas de la práctica que usa el paso actual.

        keys: las teclas de cada micro paso de la guía; text: el consejo y los
        pasos escritos. Una herramienta cuenta si alguna de sus teclas aparece.
        """
        pulsadas = set()
        for grupo in keys:
            pulsadas |= _combos(grupo)
        salida = []
        for tool in self.for_practice(practice):
            if any(k.lower() in pulsadas or _en_texto(k, text) for k in tool.keys):
                salida.append(tool)
        return tuple(salida)

    def detect_used(self, scene: SceneState) -> Tuple[str, ...]:
        """Herramientas cuya huella aparece en la escena."""
        usados = []
        for tool in self._tools.values():
            regla = tool.detect
            if not regla:
                continue
            if "modifier" in regla and any(regla["modifier"] in o.modifiers for o in scene.objects):
                usados.append(tool.id)
            elif "object_type" in regla and any(o.object_type == regla["object_type"] for o in scene.objects):
                usados.append(tool.id)
            elif "mode" in regla and scene.mode.upper().startswith(str(regla["mode"])):
                usados.append(tool.id)
            elif regla.get("material") and any(o.materials for o in scene.objects):
                usados.append(tool.id)
            elif regla.get("animation") and any(o.animation for o in scene.objects):
                usados.append(tool.id)
        return tuple(sorted(usados))

    def policy(self, practice: PracticeDefinition, tool_id: str) -> str:
        tool = self.get(tool_id)
        if tool is None or tool_id in practice.allowed_tools:
            return ALLOW
        if tool_id in practice.warn_tools or tool.minimum_level > practice.level:
            return WARN
        return ALLOW

    def warnings(self, practice: PracticeDefinition, used: Iterable[str]) -> Tuple[ToolWarning, ...]:
        avisos = []
        for tool_id in used:
            if self.policy(practice, tool_id) != WARN:
                continue
            tool = self.get(tool_id)
            avisos.append(
                ToolWarning(
                    tool_id=tool_id,
                    tool_name=tool.name,
                    level=tool.minimum_level,
                    message=(
                        f"Detectamos que utilizaste {tool.name}. Pertenece al Nivel {tool.minimum_level}. "
                        f"Esta práctica busca que lo resuelvas con las herramientas del Nivel {practice.level}."
                    ),
                )
            )
        return tuple(avisos)
