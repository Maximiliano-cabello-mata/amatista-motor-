"""Serialización canónica de prácticas a formato JSON (PracticeDefinition → JSON)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from ..models import (
    Hint,
    PillDefinition,
    PracticeDefinition,
    ReferenceModel,
    StarterDefinition,
    TargetDefinition,
)
from .referencia import (
    CON_NIVEL,
    FIGURAS,
    _etiquetas,
    _inyectados,
)


class PracticaDumper:
    """Transforma una PracticeDefinition en su estructura canónica de diccionario JSON."""

    def __init__(self, practice: PracticeDefinition):
        self.practice = practice
        self.reference = practice.reference
        self.roles = practice.roles
        self.level = practice.level
        self.inyectados = (
            _inyectados(practice.example, self.reference, self.roles, self.level)
            if practice.example is not None
            else {}
        )
        self.etiquetas = _etiquetas(self.roles)

    def to_dict(self) -> Dict[str, Any]:
        p = self.practice
        datos: Dict[str, Any] = {
            "schema": p.schema,
            "id": p.id,
            "version": p.version,
            "title": p.title,
            "level": p.level,
        }
        for clave, valor in (
            ("description", p.description),
            ("intro", p.intro),
            ("completion", p.completion),
            ("estimatedMinutes", p.estimated_minutes),
        ):
            if valor:
                datos[clave] = valor

        if p.blender_min:
            datos["blender"] = {"min": p.blender_min}
        if p.skills:
            datos["skills"] = list(p.skills)
        if p.tags:
            datos["tags"] = list(p.tags)
        if p.roles:
            datos["roles"] = {
                r.id: ({"label": r.label, "description": r.description} if r.description else {"label": r.label})
                for r in p.roles
            }
        if p.allowed_tools or p.warn_tools:
            datos["tools"] = {"allowed": list(p.allowed_tools), "warn": list(p.warn_tools)}

        if p.place.course or p.place.next:
            lugar = {
                "id": p.place.course,
                "module": p.place.module,
                "lesson": p.place.lesson,
                "next": p.place.next,
            }
            datos["course"] = {k: v for k, v in lugar.items() if v not in ("", 0)}

        if p.starter != StarterDefinition():
            inicio = {
                "scene": p.starter.scene,
                "build": p.starter.build,
                "from_practice": p.starter.from_practice,
                "note": p.starter.note,
            }
            datos["starter"] = {k: v for k, v in inicio.items() if v}

        if p.pills:
            datos["pills"] = [_dump_pildora(pil) for pil in p.pills]
        if p.review:
            datos["review"] = list(p.review)

        datos["targets"] = [
            self.dump_objetivo(t)
            for t in p.targets
            if not (p.example is not None and p.example.auto and t is p.targets[-1])
        ]
        if p.guards:
            datos["guards"] = [self.dump_objetivo(g) for g in p.guards]
        if self.reference is not None:
            datos["reference"] = _dump_referencia(self.reference)
        if p.example is not None:
            datos["example"] = self._dump_ejemplo(p.example)

        return datos

    def _dump_ejemplo(self, ejemplo) -> Dict[str, Any]:
        ej: Dict[str, Any] = {}
        if ejemplo.title:
            ej["title"] = ejemplo.title
        if ejemplo.description:
            ej["description"] = ejemplo.description
        ej["steps"] = list(ejemplo.steps)
        if ejemplo.check:
            ej["check"] = list(ejemplo.check)
        return ej

    def dump_objetivo(self, t: TargetDefinition) -> Dict[str, Any]:
        return _dump_objetivo(
            t,
            referencia=self.reference,
            roles=self.roles,
            nivel=self.level,
            inyectados=self.inyectados,
        )


def _dump_referencia(r: ReferenceModel) -> Dict[str, Any]:
    salida: Dict[str, Any] = {}
    if r.title:
        salida["title"] = r.title
    if r.description:
        salida["description"] = r.description
    salida["tolerance"] = r.tolerance
    piezas = []
    for p in r.parts:
        pieza: Dict[str, Any] = {"primitive": p.primitive, "size": list(p.size)}
        if any(p.location):
            pieza["location"] = list(p.location)
        if any(p.rotation):
            pieza["rotation"] = list(p.rotation)
        for clave in ("role", "name", "color", "join"):
            if getattr(p, clave):
                pieza[clave] = getattr(p, clave)
        if p.segments:
            pieza["segments"] = p.segments
        if p.material:
            pieza["material"] = dict(p.material)
        if not p.compare:
            pieza["compare"] = False
        piezas.append(pieza)
    salida["parts"] = piezas
    if r.objects:
        salida["objects"] = dict(r.objects)
    if r.camera:
        salida["camera"] = dict(r.camera)
    if r.flexible:
        salida["flexible"] = list(r.flexible)
    if r.lights:
        salida["lights"] = [dict(x) for x in r.lights]
    if r.strictness:
        salida["strictness"] = r.strictness
    if r.auto_roles is not None:
        salida["autoRoles"] = r.auto_roles
    return salida


def _dump_pildora(p: PillDefinition) -> Dict[str, Any]:
    salida: Dict[str, Any] = {"id": p.id, "title": p.title, "text": p.text}
    if p.keys:
        salida["keys"] = list(p.keys)
    if p.visual:
        salida["visual"] = p.visual
    disparo = {"on": p.trigger.on, "target": p.trigger.target, "mode": p.trigger.mode, "tool": p.trigger.tool}
    salida["trigger"] = {k: v for k, v in disparo.items() if v}
    if not p.once:
        salida["once"] = False
    if p.check is not None:
        salida["check"] = {"question": p.check.question, "options": list(p.check.options), "answer": p.check.answer}
    return salida


def _podar_params_figura(
    params: Dict[str, Any],
    validator: str,
    referencia: ReferenceModel,
    roles,
    nivel: int,
) -> None:
    # Las piezas viven en «reference»; el objetivo solo guarda lo propio.
    params.pop("parts", None)
    if validator in CON_NIVEL:
        for clave, valor in (
            ("level", nivel),
            ("strictness", referencia.strictness),
            ("title", referencia.title),
        ):
            if params.get(clave) == valor:
                params.pop(clave)
    if params.get("tolerance") == referencia.tolerance:
        params.pop("tolerance")
    if params.get("labels") == _etiquetas(roles):
        params.pop("labels")
    if params.get("flexible") == list(referencia.flexible):
        params.pop("flexible")


def _dump_guia(guide) -> Optional[Dict[str, Any]]:
    if guide is None or not (guide.why or guide.steps):
        return None
    guia: Dict[str, Any] = {}
    if guide.why:
        guia["why"] = guide.why
    if guide.steps:
        guia["steps"] = [
            {"text": p.text, "keys": list(p.keys)} if p.keys else p.text for p in guide.steps
        ]
    return guia


def _dump_fix(fix) -> Optional[Dict[str, Any]]:
    if fix is None:
        return None
    return {"action": fix.action, "label": fix.label} if fix.label else {"action": fix.action}


def _dump_objetivo(
    t: TargetDefinition,
    referencia: Optional[ReferenceModel] = None,
    roles=(),
    nivel: int = 1,
    inyectados: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    objetivo: Dict[str, Any] = {"id": t.id}
    if t.title:
        objetivo["title"] = t.title
    objetivo["validator"] = t.validator
    objetivo["params"] = dict(t.params)

    if t.validator == "example.matches":
        # Solo se quita lo que puso el cargador: lo que el autor escribió distinto se conserva.
        for clave, valor in (inyectados or {}).items():
            if clave in objetivo["params"] and objetivo["params"][clave] == valor:
                objetivo["params"].pop(clave)

    if t.validator in FIGURAS and referencia is not None:
        _podar_params_figura(objetivo["params"], t.validator, referencia, roles, nivel)

    objetivo["weight"] = int(t.weight) if float(t.weight).is_integer() else t.weight
    if t.requires:
        objetivo["requires"] = list(t.requires)
    if t.tip:
        objetivo["tip"] = t.tip
    if t.hints:
        objetivo["hints"] = [h.text for h in sorted(t.hints, key=lambda h: h.level)]
    if t.messages:
        objetivo["messages"] = dict(t.messages)
    if t.optional:
        objetivo["optional"] = True
    if t.stage:
        objetivo["stage"] = t.stage

    guia = _dump_guia(t.guide)
    if guia:
        objetivo["guide"] = guia

    fix = _dump_fix(t.fix)
    if fix:
        objetivo["fix"] = fix

    return objetivo


def dump_practice(practice: PracticeDefinition) -> Dict[str, Any]:
    """PracticeDefinition → dict JSON canónico (lo que exporta el compilador)."""
    return PracticaDumper(practice).to_dict()


def dumps_practice(practice: PracticeDefinition) -> str:
    """PracticeDefinition → string JSON formateado con sangría de 2 espacios."""
    return json.dumps(dump_practice(practice), ensure_ascii=False, indent=2) + "\n"
