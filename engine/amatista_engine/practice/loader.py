"""Lectura de prácticas: JSON → PracticeDefinition (y de vuelta).

parse_practice revisa la ESTRUCTURA (tipos, ids, pesos) y junta todos los
errores antes de fallar. Las reglas que dependen del motor instalado
(validadores conocidos, roles, dependencias, herramientas) las revisa el
compilador (compiler.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ..errors import InvalidPracticeError
from ..models import (
    CoursePlace,
    ExampleDefinition,
    FixDefinition,
    GuideStepDefinition,
    Hint,
    PillCheck,
    PillDefinition,
    PillTrigger,
    PracticeDefinition,
    ReferenceModel,
    ReferencePart,
    RoleDefinition,
    StarterDefinition,
    TargetDefinition,
    TargetGuide,
)
from .schema import (
    ARREGLOS,
    CAMPOS_OBJETIVO,
    CAMPOS_V2,
    DISPAROS,
    ESCENAS_INICIALES,
    MAX_OBJETIVOS,
    MAX_PASOS_GUIA,
    MAX_PILDORAS,
    MAX_PISTAS,
    MAX_TECLAS,
    MAX_TEXTO,
    MAX_TEXTO_PILDORA,
    MAX_VIGILANTES,
    NIVEL_MAXIMO,
    PATRON_ID,
    PATRON_PRACTICA,
    PATRON_VERSION,
    PESTANAS,
    SCHEMA_V1,
    SUPPORTED_SCHEMAS,
    VISUALES,
)
from .dumper import (
    _dump_objetivo,
    _dump_pildora,
    _dump_referencia,
    dump_practice,
    dumps_practice,
)
from .referencia import (
    CON_NIVEL,
    FIGURAS,
    INYECTADOS_EJEMPLO,
    OBJETIVO_EJEMPLO,
    PESO_EJEMPLO,
    _aspectos_validos,
    _con_ejemplo,
    _con_referencia,
    _ejemplo,
    _etiquetas,
    _inyectados,
    _referencia,
    _vector,
    aspectos_de,
    pieza_como_dict,
)


class _Errores:
    """Acumula errores de estructura y sintaxis al leer una práctica JSON."""

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


def _parse_item_pista(pista: Any, nivel: int, donde: str, e: _Errores) -> Optional[Hint]:
    if isinstance(pista, str) and pista.strip():
        return Hint(level=nivel, text=pista.strip())
    if isinstance(pista, dict) and isinstance(pista.get("text"), str) and pista["text"].strip():
        nivel_pista = pista.get("level", nivel)
        if isinstance(nivel_pista, bool) or not isinstance(nivel_pista, int) or nivel_pista < 1:
            e.add(f"'{donde}[{nivel - 1}].level' debe ser un entero >= 1")
            nivel_pista = nivel
        return Hint(level=nivel_pista, text=pista["text"].strip())
    e.add(f"'{donde}[{nivel - 1}]' debe ser texto o {{level, text}}")
    return None


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
        item = _parse_item_pista(pista, nivel, donde, e)
        if item is not None:
            pistas.append(item)
    niveles = [p.level for p in pistas]
    if len(set(niveles)) != len(niveles):
        e.add(f"'{donde}' repite niveles de pista")
    return tuple(sorted(pistas, key=lambda p: p.level))


def _parse_paso_guia(paso: Any, donde: str, e: _Errores) -> Optional[GuideStepDefinition]:
    if isinstance(paso, str) and paso.strip():
        return GuideStepDefinition(paso.strip())
    if not (isinstance(paso, dict) and isinstance(paso.get("text"), str) and paso["text"].strip()):
        e.add(f"'{donde}' debe ser texto o {{text, keys}}")
        return None
    teclas = paso.get("keys", []) or []
    if not isinstance(teclas, list) or not all(isinstance(t, str) and t.strip() for t in teclas):
        e.add(f"'{donde}.keys' debe ser una lista de textos («S», «Z», «Enter»)")
        teclas = []
    if len(teclas) > MAX_TECLAS:
        e.add(f"'{donde}.keys' admite como máximo {MAX_TECLAS} teclas")
    return GuideStepDefinition(paso["text"].strip(), tuple(t.strip() for t in teclas))


def _guia(raw: Any, donde: str, e: _Errores) -> Optional[TargetGuide]:
    """{"why": "...", "steps": ["texto", {"text": "...", "keys": ["S", "Z"]}]}."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        e.add(f"'{donde}' debe ser un objeto {{why, steps}}")
        return None
    why = raw.get("why", "")
    if not isinstance(why, str):
        e.add(f"'{donde}.why' debe ser texto")
        why = ""
    pasos_raw = raw.get("steps", []) or []
    if not isinstance(pasos_raw, list):
        e.add(f"'{donde}.steps' debe ser una lista")
        pasos_raw = []
    if len(pasos_raw) > MAX_PASOS_GUIA:
        e.add(f"'{donde}.steps' admite como máximo {MAX_PASOS_GUIA} pasos")
    pasos = []
    for i, paso in enumerate(pasos_raw):
        p = _parse_paso_guia(paso, f"{donde}.steps[{i}]", e)
        if p is not None:
            pasos.append(p)
    return TargetGuide(why=why.strip(), steps=tuple(pasos))


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


def _objetivo(raw: Any, index: int, e: _Errores, ids: set, lista: str = "targets") -> Optional[TargetDefinition]:
    donde = f"{lista}[{index}]."
    if not isinstance(raw, dict):
        e.add(f"{lista}[{index}] debe ser un objeto")
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
    extra = {k: v for k, v in raw.items() if k not in CAMPOS_OBJETIVO | {"fix"}}
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
        guide=_guia(raw.get("guide"), f"{donde}guide", e),
        fix=_arreglo(raw.get("fix"), f"{donde}fix", e),
        stage=str(raw.get("stage", "") or "").strip()[:40],
    )


def _arreglo(raw: Any, donde: str, e: _Errores) -> Optional[FixDefinition]:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = {"action": raw}
    if not isinstance(raw, dict) or raw.get("action") not in ARREGLOS:
        e.add(f"'{donde}' debe ser {{action, label}} con action en: {', '.join(ARREGLOS)}")
        return None
    return FixDefinition(action=raw["action"], label=str(raw.get("label") or "").strip())


def _disparo(raw: Any, donde: str, e: _Errores) -> PillTrigger:
    if raw is None:
        return PillTrigger()
    if isinstance(raw, str):
        raw = {"on": raw}
    if not isinstance(raw, dict) or raw.get("on", "start") not in DISPAROS:
        e.add(f"'{donde}' debe ser {{on, ...}} con on en: {', '.join(DISPAROS)}")
        return PillTrigger()
    disparo = PillTrigger(
        on=str(raw.get("on", "start")),
        target=str(raw.get("target") or ""),
        mode=str(raw.get("mode") or "").upper(),
        tool=str(raw.get("tool") or ""),
    )
    if disparo.on in ("target", "guard") and not disparo.target:
        e.add(f"'{donde}.target' es obligatorio cuando on = {disparo.on}")
    if disparo.on == "mode" and not disparo.mode:
        e.add(f"'{donde}.mode' es obligatorio cuando on = mode (EDIT, OBJECT…)")
    if disparo.on == "tool" and not disparo.tool:
        e.add(f"'{donde}.tool' es obligatorio cuando on = tool (id del catálogo de herramientas)")
    return disparo


def _pregunta(raw: Any, donde: str, e: _Errores) -> Optional[PillCheck]:
    if raw is None:
        return None
    opciones = raw.get("options") if isinstance(raw, dict) else None
    respuesta = raw.get("answer") if isinstance(raw, dict) else None
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("question"), str)
        or not isinstance(opciones, list)
        or not 2 <= len(opciones) <= 4
        or not all(isinstance(o, str) and o.strip() for o in opciones)
        or isinstance(respuesta, bool)
        or not isinstance(respuesta, int)
        or not 0 <= respuesta < len(opciones)
    ):
        e.add(f"'{donde}' debe ser {{question, options (2 a 4), answer (índice)}}")
        return None
    return PillCheck(raw["question"].strip(), tuple(o.strip() for o in opciones), respuesta)


def _parse_item_pildora(p: Any, i: int, e: _Errores, ids: set) -> Optional[PillDefinition]:
    donde = f"pills[{i}]."
    if not isinstance(p, dict):
        e.add(f"pills[{i}] debe ser un objeto")
        return None
    pid = e.texto(p, "id", donde)
    if pid and not PATRON_ID.match(pid):
        e.add(f"'{donde}id' = '{pid}' solo admite letras, números, punto, guion y guion bajo")
    if pid in ids:
        e.add(f"Píldora duplicada: {pid}")
    ids.add(pid)
    texto = e.texto(p, "text", donde)
    if len(texto) > MAX_TEXTO_PILDORA:
        e.add(f"'{donde}text' es demasiado largo para una píldora (máx. {MAX_TEXTO_PILDORA})")
    teclas = p.get("keys", []) or []
    if not isinstance(teclas, list) or not all(isinstance(t, str) and t.strip() for t in teclas):
        e.add(f"'{donde}keys' debe ser una lista de textos")
        teclas = []
    visual = str(p.get("visual") or "")
    if not (
        visual in VISUALES
        or (visual.startswith("tab:") and visual[4:] in PESTANAS)
        or (visual.startswith("image:") and len(visual) > 6)
    ):
        e.add(f"'{donde}visual' = '{visual}' no es válido (axes, keys, mode, tab:MODIFIER, image:archivo)")
    once = p.get("once", True)
    return PillDefinition(
        id=pid,
        title=e.texto(p, "title", donde),
        text=texto,
        keys=tuple(t.strip() for t in teclas),
        visual=visual,
        trigger=_disparo(p.get("trigger"), f"{donde}trigger", e),
        once=bool(once) if isinstance(once, bool) else True,
        check=_pregunta(p.get("check"), f"{donde}check", e),
    )


def _pildoras(raw: Any, e: _Errores) -> tuple:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        e.add("'pills' debe ser una lista")
        return ()
    if len(raw) > MAX_PILDORAS:
        e.add(f"'pills' admite como máximo {MAX_PILDORAS} píldoras")
    pildoras, ids = [], set()
    for i, p in enumerate(raw):
        pil = _parse_item_pildora(p, i, e, ids)
        if pil is not None:
            pildoras.append(pil)
    return tuple(pildoras)


def _lugar(raw: Any, e: _Errores) -> CoursePlace:
    if raw is None:
        return CoursePlace()
    if not isinstance(raw, dict):
        e.add("'course' debe ser un objeto {id, module, lesson, next}")
        return CoursePlace()
    modulo = raw.get("module", 0)
    if isinstance(modulo, bool) or not isinstance(modulo, int) or modulo < 0:
        e.add("'course.module' debe ser un entero >= 0")
        modulo = 0
    siguiente = str(raw.get("next") or "")
    if siguiente and not PATRON_PRACTICA.match(siguiente):
        e.add("'course.next' debe ser el id de otra práctica")
    return CoursePlace(
        course=str(raw.get("id") or ""), module=modulo, lesson=str(raw.get("lesson") or ""), next=siguiente
    )


def _inicio(raw: Any, e: _Errores) -> StarterDefinition:
    if raw is None:
        return StarterDefinition()
    if not isinstance(raw, dict) or raw.get("scene", "keep") not in ESCENAS_INICIALES:
        e.add("'starter' debe ser {scene: keep|empty, build, from_practice, note}")
        return StarterDefinition()
    return StarterDefinition(
        scene=str(raw.get("scene", "keep")),
        build=str(raw.get("build") or ""),
        from_practice=str(raw.get("from_practice") or ""),
        note=str(raw.get("note") or "").strip(),
    )


def _validar_encabezado(
    data: Dict[str, Any], e: _Errores
) -> tuple[str, str, str, int, int, Optional[int]]:
    schema = e.texto(data, "schema")
    if schema and schema not in SUPPORTED_SCHEMAS:
        raise InvalidPracticeError(
            f"Schema no soportado: {schema}. Esperado: {' o '.join(SUPPORTED_SCHEMAS)}"
        )
    if schema == SCHEMA_V1:
        usados = [c for c in CAMPOS_V2 if c in data]
        if usados:
            e.add(f"{', '.join(usados)} necesita{'n' if len(usados) > 1 else ''} \"schema\": \"amatista.practice/2\"")

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
    if minutos is not None and (
        isinstance(minutos, bool) or not isinstance(minutos, int) or not 1 <= minutos <= 600
    ):
        e.add("'estimatedMinutes' debe ser un entero entre 1 y 600")
        minutos = None

    return schema, practice_id, title, level, version, minutos


def _validar_herramientas(data: Dict[str, Any], e: _Errores) -> tuple[Optional[str], Dict[str, Any]]:
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

    return blender_min, tools


def _validar_targets(raw_targets: Any, e: _Errores) -> List[TargetDefinition]:
    targets = []
    if not isinstance(raw_targets, list) or not raw_targets:
        e.add("'targets' debe contener al menos un objetivo")
        return targets
    if len(raw_targets) > MAX_OBJETIVOS:
        e.add(f"'targets' admite como máximo {MAX_OBJETIVOS} objetivos")
        return targets

    ids: set = set()
    for index, raw in enumerate(raw_targets):
        objetivo = _objetivo(raw, index, e, ids)
        if objetivo is not None:
            targets.append(objetivo)
    if targets and sum(t.weight for t in targets if not t.optional) <= 0:
        e.add("La suma total de pesos debe ser mayor que cero")
    return targets


def _validar_vigilantes(crudos_v: Any, targets: List[TargetDefinition], e: _Errores) -> List[TargetDefinition]:
    if crudos_v is None:
        return []
    if not isinstance(crudos_v, list) or len(crudos_v) > MAX_VIGILANTES:
        e.add(f"'guards' debe ser una lista de hasta {MAX_VIGILANTES} vigilantes")
        return []

    vigilantes = []
    ids_v = {t.id for t in targets}
    for index, raw in enumerate(crudos_v):
        vigilante = _objetivo(raw, index, e, ids_v, "guards")
        if vigilante is not None:
            vigilantes.append(vigilante)
    return vigilantes


def _validar_repaso(repaso: Any, e: _Errores) -> tuple:
    if repaso is None:
        return ()
    if (
        not isinstance(repaso, list)
        or len(repaso) > MAX_PILDORAS
        or not all(isinstance(x, str) and "#" in x for x in repaso)
    ):
        e.add("'review' debe ser una lista de «practica#pildora»")
        return ()
    return tuple(repaso)


def parse_practice(data: Dict[str, Any]) -> PracticeDefinition:
    """JSON → PracticeDefinition. Cualquier dato mal escrito sale como InvalidPracticeError, nunca como otro error."""
    try:
        return _parse_practice(data)
    except InvalidPracticeError:
        raise
    except (TypeError, ValueError, AttributeError, IndexError, KeyError, RecursionError) as error:
        detalle = error.args[0] if isinstance(error, KeyError) and error.args else error
        raise InvalidPracticeError(f"La práctica tiene un dato que no se puede leer: {detalle}") from error


def _parse_practice(data: Dict[str, Any]) -> PracticeDefinition:
    if not isinstance(data, dict):
        raise InvalidPracticeError("La práctica debe ser un objeto JSON")
    e = _Errores()

    schema, practice_id, title, level, version, minutos = _validar_encabezado(data, e)
    blender_min, tools = _validar_herramientas(data, e)
    targets = _validar_targets(data.get("targets"), e)
    vigilantes = _validar_vigilantes(data.get("guards"), targets, e)
    repaso = _validar_repaso(data.get("review"), e)

    referencia = _referencia(data.get("reference"), e)
    roles = _roles(data.get("roles"), e)
    targets = _con_referencia(targets, referencia, roles, e, level)
    vigilantes = _con_referencia(vigilantes, referencia, roles, e, level)
    ejemplo = _ejemplo(data.get("example"), referencia, e)
    if targets:
        targets, ejemplo = _con_ejemplo(targets, ejemplo, referencia, roles, level, e)

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
        roles=roles,
        tags=e.lista_ids(data.get("tags"), "tags"),
        allowed_tools=e.lista_ids(tools.get("allowed"), "tools.allowed"),
        warn_tools=e.lista_ids(tools.get("warn"), "tools.warn"),
        guards=tuple(vigilantes),
        pills=_pildoras(data.get("pills"), e),
        review=repaso,
        place=_lugar(data.get("course"), e),
        starter=_inicio(data.get("starter"), e),
        reference=referencia,
        example=ejemplo,
    )
    if e.lista:
        raise InvalidPracticeError(e.lista[0], e.lista)
    return practica


def load_practice(path: Union[str, Path]) -> PracticeDefinition:
    """Carga y parsea una práctica desde un archivo JSON en disco."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidPracticeError(f"No existe la práctica: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidPracticeError(f"JSON inválido: línea {exc.lineno}, columna {exc.colno}") from exc
    return parse_practice(raw)
