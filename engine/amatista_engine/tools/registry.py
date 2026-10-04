"""Catálogo de herramientas de Blender y política por nivel (secciones 13 y 14).

Cada herramienta tiene nombre, atajo, nivel mínimo y descripción: las
prácticas solo citan su id. Las que declaran «detect» se reconocen en la
escena (un modificador BOOLEAN, un objeto CURVE, el modo SCULPT...) y el
motor avisa si pertenecen a un nivel posterior. La política es ADVERTIR,
no bloquear: Blender sigue abierto para experimentar.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

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
            )
            for t in datos["tools"]
        )

    def get(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def all(self) -> Tuple[Tool, ...]:
        return tuple(sorted(self._tools.values(), key=lambda t: (t.minimum_level, t.category, t.name)))

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
