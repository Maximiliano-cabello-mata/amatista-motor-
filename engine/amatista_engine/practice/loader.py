"""Lectura de prácticas: JSON → PracticeDefinition (y de vuelta).

parse_practice revisa la ESTRUCTURA (tipos, ids, pesos) y junta todos los
errores antes de fallar. Las reglas que dependen del motor instalado
(validadores conocidos, roles, dependencias, herramientas) las revisa el
compilador (compiler.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from ..errors import InvalidPracticeError
from ..models import Hint, PracticeDefinition, RoleDefinition, TargetDefinition
from .schema import (
    CAMPOS_OBJETIVO,
    MAX_OBJETIVOS,
    MAX_PISTAS,
    MAX_TEXTO,
    NIVEL_MAXIMO,
    PATRON_ID,
    PATRON_PRACTICA,
    PATRON_VERSION,
    SUPPORTED_SCHEMA,
)


class _Errores:
    def __init__(self) -> None:
        self.lista: List[str] = []

    def add(self, mensaje: str) -> None:
        self.lista.append(mensaje)

    def texto(self, data: Dict[str, Any], key: str, donde: str = "", obligatorio: bool = True) -> str:
        valor = data.get(key)
        if valor is None and not obligatorio:
            return ""
        if not isinstance(valor, str) or (obligatorio and not valor.strip()):
            self.add(f"'{donde}{key}' debe ser texto no vacío")
            return ""
        if len(valor) > MAX_TEXTO * 4:
            self.add(f"'{donde}{key}' es demasiado largo")
        return valor.strip()

    def lista_ids(self, valor: Any, donde: str) -> tuple:
        if valor is None:
            return ()
        if not isinstance(valor, list) or not all(isinstance(x, str) and PATRON_ID.match(x) for x in valor):
            self.add(f"'{donde}' debe ser una lista de ids (letras, números, punto, guion)")
            return ()
        return tuple(valor)


def _pistas(raw: Any, donde: str, e: _Errores) -> tuple:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        e.add(f"'{donde}' debe ser una lista")
        return ()
    if len(raw) > MAX_PISTAS:
        e.add(f"'{donde}' admite como máximo {MAX_PISTAS} pistas")
    pistas = []
    for nivel, pista in enumerate(raw, start=1):
        if isinstance(pista, str) and pista.strip():
            pistas.append(Hint(level=nivel, text=pista.strip()))
        elif isinstance(pista, dict) and isinstance(pista.get("text"), str) and pista["text"].strip():
            pistas.append(Hint(level=int(pista.get("level", nivel)), text=pista["text"].strip()))
        else:
            e.add(f"'{donde}[{nivel - 1}]' debe ser texto o {{level, text}}")
    niveles = [p.level for p in pistas]
    if len(set(niveles)) != len(niveles):
        e.add(f"'{donde}' repite niveles de pista")
    return tuple(sorted(pistas, key=lambda p: p.level))


def _roles(raw: Any, e: _Errores) -> tuple:
    """Acepta {"pata": {"label": "Pata"}} o [{"id": "pata", "label": "Pata"}]."""
    if raw is None:
        return ()
    if isinstance(raw, dict):
        elementos = [{"id": k, **(v if isinstance(v, dict) else {"label": str(v)})} for k, v in raw.items()]
    elif isinstance(raw, list):
        elementos = raw
    else:
        e.add("'roles' debe ser un objeto o una lista")
        return ()
    roles = []
    for i, rol in enumerate(elementos):
        rid = rol.get("id") if isinstance(rol, dict) else None
        if not isinstance(rid, str) or not PATRON_ID.match(rid):
            e.add(f"'roles[{i}]' necesita un id válido")
            continue
        roles.append(
            RoleDefinition(id=rid, label=str(rol.get("label") or rid), description=str(rol.get("description") or ""))
        )
    if len({r.id for r in roles}) != len(roles):
        e.add("'roles' repite ids")
    return tuple(roles)


def _objetivo(raw: Any, index: int, e: _Errores, ids: set):
    donde = f"targets[{index}]."
    if not isinstance(raw, dict):
        e.add(f"targets[{index}] debe ser un objeto")
        return None
    target_id = e.texto(raw, "id", donde)
    if target_id and not PATRON_ID.match(target_id):
        e.add(f"'{donde}id' = '{target_id}' solo admite letras, números, punto, guion y guion bajo")
    if target_id in ids:
        e.add(f"Objetivo duplicado: {target_id}")
    ids.add(target_id)
    validator = e.texto(raw, "validator", donde)

    params = raw.get("params", {})
    if not isinstance(params, dict):
        e.add(f"'{donde}params' debe ser un objeto")
        params = {}
    # Atajo de la especificación: {"validator": "role.count", "role": "pata", "equals": 4}.
    extra = {k: v for k, v in raw.items() if k not in CAMPOS_OBJETIVO}
    params = {**extra, **params}

    weight = raw.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight < 0:
        e.add(f"'{donde}weight' debe ser un número >= 0")
        weight = 0.0

    mensajes = raw.get("messages", {}) or {}
    if not isinstance(mensajes, dict) or not all(isinstance(v, str) for v in mensajes.values()):
        e.add(f"'{donde}messages' debe ser {{pass, fail}} con textos")
        mensajes = {}

    optional = raw.get("optional", False)
    if not isinstance(optional, bool):
        e.add(f"'{donde}optional' debe ser true o false")
        optional = False

    return TargetDefinition(
        id=target_id,
        validator=validator,
        params=dict(params),
        weight=float(weight),
        title=str(raw.get("title", "") or "").strip(),
        requires=e.lista_ids(raw.get("requires"), f"{donde}requires"),
        tip=str(raw.get("tip", "") or "").strip(),
        hints=_pistas(raw.get("hints"), f"{donde}hints", e),
        messages={k: v.strip() for k, v in mensajes.items() if k in ("pass", "fail") and v.strip()},
        optional=optional,
    )


def parse_practice(data: Dict[str, Any]) -> PracticeDefinition:
    if not isinstance(data, dict):
        raise InvalidPracticeError("La práctica debe ser un objeto JSON")
    e = _Errores()

    schema = e.texto(data, "schema")
    if schema and schema != SUPPORTED_SCHEMA:
        raise InvalidPracticeError(f"Schema no soportado: {schema}. Esperado: {SUPPORTED_SCHEMA}")

    practice_id = e.texto(data, "id")
    if practice_id and not PATRON_PRACTICA.match(practice_id):
        e.add(f"'id' = '{practice_id}' debe usar minúsculas, números, punto, guion o guion bajo (máx. 80)")
    title = e.texto(data, "title")

    level = data.get("level")
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= NIVEL_MAXIMO:
        e.add(f"'level' debe ser entero entre 1 y {NIVEL_MAXIMO}")
        level = 1

    version = data.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        e.add("'version' debe ser un entero >= 1")
        version = 1

    minutos = data.get("estimatedMinutes")
    if minutos is not None and (isinstance(minutos, bool) or not isinstance(minutos, int) or not 1 <= minutos <= 600):
        e.add("'estimatedMinutes' debe ser un entero entre 1 y 600")
        minutos = None

    blender = data.get("blender") or {}
    blender_min = None
    if not isinstance(blender, dict):
        e.add("'blender' debe ser un objeto {min}")
    elif blender.get("min") is not None:
        blender_min = str(blender["min"])
        if not PATRON_VERSION.match(blender_min):
            e.add("'blender.min' debe ser una versión como 4.2 o 4.2.3")

    tools = data.get("tools") or {}
    if not isinstance(tools, dict):
        e.add("'tools' debe ser un objeto {allowed, warn}")
        tools = {}

    raw_targets = data.get("targets")
    targets = []
    if not isinstance(raw_targets, list) or not raw_targets:
        e.add("'targets' debe contener al menos un objetivo")
    elif len(raw_targets) > MAX_OBJETIVOS:
        e.add(f"'targets' admite como máximo {MAX_OBJETIVOS} objetivos")
    else:
        ids: set = set()
        for index, raw in enumerate(raw_targets):
            objetivo = _objetivo(raw, index, e, ids)
            if objetivo is not None:
                targets.append(objetivo)
        if targets and sum(t.weight for t in targets if not t.optional) <= 0:
            e.add("La suma total de pesos debe ser mayor que cero")

    practica = PracticeDefinition(
        schema=schema,
        id=practice_id,
        title=title,
        level=level,
        targets=tuple(targets),
        version=version,
        description=e.texto(data, "description", obligatorio=False),
        intro=e.texto(data, "intro", obligatorio=False),
        completion=e.texto(data, "completion", obligatorio=False),
        estimated_minutes=minutos,
        blender_min=blender_min,
        skills=e.lista_ids(data.get("skills"), "skills"),
        roles=_roles(data.get("roles"), e),
        tags=e.lista_ids(data.get("tags"), "tags"),
        allowed_tools=e.lista_ids(tools.get("allowed"), "tools.allowed"),
        warn_tools=e.lista_ids(tools.get("warn"), "tools.warn"),
    )
    if e.lista:
        raise InvalidPracticeError(e.lista[0], e.lista)
    return practica


def load_practice(path: Union[str, Path]) -> PracticeDefinition:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidPracticeError(f"No existe la práctica: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidPracticeError(f"JSON inválido: línea {exc.lineno}, columna {exc.colno}") from exc
    return parse_practice(raw)


def dump_practice(practice: PracticeDefinition) -> Dict[str, Any]:
    """PracticeDefinition → dict JSON canónico (lo que exporta el compilador)."""
    datos: Dict[str, Any] = {
        "schema": practice.schema,
        "id": practice.id,
        "version": practice.version,
        "title": practice.title,
        "level": practice.level,
    }
    for clave, valor in (
        ("description", practice.description),
        ("intro", practice.intro),
        ("completion", practice.completion),
        ("estimatedMinutes", practice.estimated_minutes),
    ):
        if valor:
            datos[clave] = valor
    if practice.blender_min:
        datos["blender"] = {"min": practice.blender_min}
    if practice.skills:
        datos["skills"] = list(practice.skills)
    if practice.tags:
        datos["tags"] = list(practice.tags)
    if practice.roles:
        datos["roles"] = {
            r.id: ({"label": r.label, "description": r.description} if r.description else {"label": r.label})
            for r in practice.roles
        }
    if practice.allowed_tools or practice.warn_tools:
        datos["tools"] = {"allowed": list(practice.allowed_tools), "warn": list(practice.warn_tools)}
    objetivos = []
    for t in practice.targets:
        objetivo: Dict[str, Any] = {"id": t.id}
        if t.title:
            objetivo["title"] = t.title
        objetivo["validator"] = t.validator
        objetivo["params"] = dict(t.params)
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
        objetivos.append(objetivo)
    datos["targets"] = objetivos
    return datos


def dumps_practice(practice: PracticeDefinition) -> str:
    return json.dumps(dump_practice(practice), ensure_ascii=False, indent=2) + "\n"
