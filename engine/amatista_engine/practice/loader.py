"""Lectura de prácticas: JSON → PracticeDefinition (y de vuelta).

parse_practice revisa la ESTRUCTURA (tipos, ids, pesos) y junta todos los
errores antes de fallar. Las reglas que dependen del motor instalado
(validadores conocidos, roles, dependencias, herramientas) las revisa el
compilador (compiler.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace
from typing import Any, Dict, List, Optional, Union

from ..errors import InvalidPracticeError
from ..models import (
    CoursePlace,
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
    CAMPOS_PIEZA,
    CAMPOS_REFERENCIA,
    MAX_PIEZAS,
    PRIMITIVAS_REFERENCIA,
    CAMPOS_OBJETIVO,
    CAMPOS_V2,
    DISPAROS,
    ESCENAS_INICIALES,
    MAX_PILDORAS,
    MAX_TEXTO_PILDORA,
    MAX_VIGILANTES,
    PATRON_ID,
    PESTANAS,
    SCHEMA_V1,
    SUPPORTED_SCHEMAS,
    VISUALES,
    MAX_OBJETIVOS,
    MAX_PASOS_GUIA,
    MAX_PISTAS,
    MAX_TECLAS,
    MAX_TEXTO,
    NIVEL_MAXIMO,
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


def _guia(raw: Any, donde: str, e: _Errores):
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
        if isinstance(paso, str) and paso.strip():
            pasos.append(GuideStepDefinition(paso.strip()))
            continue
        if not (isinstance(paso, dict) and isinstance(paso.get("text"), str) and paso["text"].strip()):
            e.add(f"'{donde}.steps[{i}]' debe ser texto o {{text, keys}}")
            continue
        teclas = paso.get("keys", []) or []
        if not isinstance(teclas, list) or not all(isinstance(t, str) and t.strip() for t in teclas):
            e.add(f"'{donde}.steps[{i}].keys' debe ser una lista de textos («S», «Z», «Enter»)")
            teclas = []
        if len(teclas) > MAX_TECLAS:
            e.add(f"'{donde}.steps[{i}].keys' admite como máximo {MAX_TECLAS} teclas")
        pasos.append(GuideStepDefinition(paso["text"].strip(), tuple(t.strip() for t in teclas)))
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


def _objetivo(raw: Any, index: int, e: _Errores, ids: set, lista: str = "targets"):
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
        fix=_arreglo(raw.get("fix"), f"{donde}fix", e) if lista == "guards" else None,
    )


def _arreglo(raw: Any, donde: str, e: _Errores):
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


def _pregunta(raw: Any, donde: str, e: _Errores):
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
        donde = f"pills[{i}]."
        if not isinstance(p, dict):
            e.add(f"pills[{i}] debe ser un objeto")
            continue
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
        pildoras.append(
            PillDefinition(
                id=pid,
                title=e.texto(p, "title", donde),
                text=texto,
                keys=tuple(t.strip() for t in teclas),
                visual=visual,
                trigger=_disparo(p.get("trigger"), f"{donde}trigger", e),
                once=bool(once) if isinstance(once, bool) else True,
                check=_pregunta(p.get("check"), f"{donde}check", e),
            )
        )
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


def _vector(valor: Any, donde: str, e: _Errores, defecto=None, positivo: bool = False):
    if valor is None and defecto is not None:
        return defecto
    if (not isinstance(valor, list) or len(valor) != 3
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in valor)):
        e.add(f"'{donde}' debe ser una lista de 3 números")
        return defecto or (1.0, 1.0, 1.0)
    if positivo and any(x < 0 for x in valor):
        e.add(f"'{donde}' no puede tener medidas negativas")
    return tuple(float(x) for x in valor)


def _referencia(raw: Any, e: _Errores) -> Optional[ReferenceModel]:
    """«reference»: la figura terminada en piezas (motor 3.3). Ver docs/motor/referencia/11_modelo_de_referencia.md."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        e.add("'reference' debe ser un objeto {title, description, tolerance, parts}")
        return None
    extra = set(raw) - CAMPOS_REFERENCIA
    if extra:
        e.add(f"'reference' no reconoce: {', '.join(sorted(extra))}")
    tolerancia = raw.get("tolerance", 0.35)
    if isinstance(tolerancia, bool) or not isinstance(tolerancia, (int, float)) or not 0.05 <= tolerancia <= 1.0:
        e.add("'reference.tolerance' debe ser un número entre 0.05 y 1 (0.35 = ±35 %)")
        tolerancia = 0.35
    crudas = raw.get("parts")
    if not isinstance(crudas, list) or not crudas or len(crudas) > MAX_PIEZAS:
        e.add(f"'reference.parts' debe tener entre 1 y {MAX_PIEZAS} piezas")
        crudas = []
    piezas = []
    for i, pieza in enumerate(crudas):
        donde = f"reference.parts[{i}]"
        if not isinstance(pieza, dict):
            e.add(f"'{donde}' debe ser un objeto")
            continue
        extra = set(pieza) - CAMPOS_PIEZA
        if extra:
            e.add(f"'{donde}' no reconoce: {', '.join(sorted(extra))}")
        primitiva = pieza.get("primitive")
        if primitiva not in PRIMITIVAS_REFERENCIA:
            e.add(f"'{donde}.primitive' debe ser una de: {', '.join(PRIMITIVAS_REFERENCIA)}")
            continue
        material = pieza.get("material") or {}
        if not isinstance(material, dict):
            e.add(f"'{donde}.material' debe ser un objeto")
            material = {}
        piezas.append(ReferencePart(
            primitive=primitiva,
            size=_vector(pieza.get("size"), f"{donde}.size", e, positivo=True),
            location=_vector(pieza.get("location"), f"{donde}.location", e, (0.0, 0.0, 0.0)),
            rotation=_vector(pieza.get("rotation"), f"{donde}.rotation", e, (0.0, 0.0, 0.0)),
            role=str(pieza.get("role") or ""),
            name=str(pieza.get("name") or ""),
            color=str(pieza.get("color") or ""),
            join=str(pieza.get("join") or ""),
            segments=int(pieza.get("segments") or 0),
            material=material,
            compare=pieza.get("compare", True) is not False,
        ))
    objetos = raw.get("objects") or {}
    camara = raw.get("camera") or {}
    if not isinstance(objetos, dict) or not isinstance(camara, dict):
        e.add("'reference.objects' y 'reference.camera' deben ser objetos")
        objetos, camara = {}, {}
    flexibles = raw.get("flexible") or []
    if not isinstance(flexibles, list) or not all(isinstance(g, str) for g in flexibles):
        e.add("'reference.flexible' debe ser una lista de roles o primitivas")
        flexibles = []
    grupos = {p.group for p in piezas}
    for grupo in flexibles:
        if grupo not in grupos:
            e.add(f"'reference.flexible': «{grupo}» no es el rol ni la primitiva de ninguna pieza")
    luces = raw.get("lights") or []
    if not isinstance(luces, list) or not all(isinstance(x, dict) for x in luces):
        e.add("'reference.lights' debe ser una lista de luces {type, location, energy}")
        luces = []
    return ReferenceModel(
        lights=tuple(luces),
        flexible=tuple(flexibles),
        parts=tuple(piezas),
        title=str(raw.get("title") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        tolerance=float(tolerancia),
        objects=objetos,
        camera=camara,
    )


def pieza_como_dict(pieza: ReferencePart) -> Dict[str, Any]:
    return {"group": pieza.group, "role": pieza.role, "primitive": pieza.primitive, "size": list(pieza.size),
            "location": list(pieza.location), "rotation": list(pieza.rotation), "join": pieza.join}


def _etiquetas(roles) -> Dict[str, str]:
    return {r.id: r.label for r in roles or () if r.label}


def _con_referencia(objetivos: List[TargetDefinition], referencia: Optional[ReferenceModel], roles, e: _Errores):
    """figure.resembles sin «parts» toma las piezas y la holgura de «reference» (y los nombres de los roles)."""
    salida = []
    for objetivo in objetivos:
        if objetivo.validator == "figure.resembles" and "parts" not in objetivo.params:
            if referencia is None or not referencia.compared:
                e.add(f"'{objetivo.id}': figure.resembles necesita 'reference' con piezas en la práctica")
            else:
                params = {"tolerance": referencia.tolerance, "labels": _etiquetas(roles), **objetivo.params,
                          "parts": [pieza_como_dict(p) for p in referencia.compared]}
                if referencia.flexible:
                    params.setdefault("flexible", list(referencia.flexible))
                objetivo = replace(objetivo, params=params)
        salida.append(objetivo)
    return salida


def parse_practice(data: Dict[str, Any]) -> PracticeDefinition:
    if not isinstance(data, dict):
        raise InvalidPracticeError("La práctica debe ser un objeto JSON")
    e = _Errores()

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

    vigilantes = []
    crudos_v = data.get("guards")
    if crudos_v is not None:
        if not isinstance(crudos_v, list) or len(crudos_v) > MAX_VIGILANTES:
            e.add(f"'guards' debe ser una lista de hasta {MAX_VIGILANTES} vigilantes")
        else:
            ids_v = {t.id for t in targets}
            for index, raw in enumerate(crudos_v):
                vigilante = _objetivo(raw, index, e, ids_v, "guards")
                if vigilante is not None:
                    vigilantes.append(vigilante)

    repaso = data.get("review")
    if repaso is not None and (
        not isinstance(repaso, list)
        or len(repaso) > MAX_PILDORAS
        or not all(isinstance(x, str) and "#" in x for x in repaso)
    ):
        e.add("'review' debe ser una lista de «practica#pildora»")
        repaso = []

    referencia = _referencia(data.get("reference"), e)
    roles = _roles(data.get("roles"), e)
    targets = _con_referencia(targets, referencia, roles, e)
    vigilantes = _con_referencia(vigilantes, referencia, roles, e)

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
        review=tuple(repaso or ()),
        place=_lugar(data.get("course"), e),
        starter=_inicio(data.get("starter"), e),
        reference=referencia,
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
    if practice.place.course or practice.place.next:
        lugar = {"id": practice.place.course, "module": practice.place.module, "lesson": practice.place.lesson,
                 "next": practice.place.next}
        datos["course"] = {k: v for k, v in lugar.items() if v not in ("", 0)}
    if practice.starter != StarterDefinition():
        inicio = {"scene": practice.starter.scene, "build": practice.starter.build,
                  "from_practice": practice.starter.from_practice, "note": practice.starter.note}
        datos["starter"] = {k: v for k, v in inicio.items() if v}
    if practice.pills:
        datos["pills"] = [_dump_pildora(p) for p in practice.pills]
    if practice.review:
        datos["review"] = list(practice.review)
    datos["targets"] = [_dump_objetivo(t, practice.reference, practice.roles) for t in practice.targets]
    if practice.guards:
        datos["guards"] = [_dump_objetivo(g, practice.reference, practice.roles) for g in practice.guards]
    if practice.reference is not None:
        datos["reference"] = _dump_referencia(practice.reference)
    return datos


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


def _dump_objetivo(t: TargetDefinition, referencia: Optional[ReferenceModel] = None, roles=()) -> Dict[str, Any]:
    objetivo: Dict[str, Any] = {"id": t.id}
    if t.title:
        objetivo["title"] = t.title
    objetivo["validator"] = t.validator
    objetivo["params"] = dict(t.params)
    if t.validator == "figure.resembles" and referencia is not None:
        # Las piezas viven en «reference»; el objetivo solo guarda lo propio.
        objetivo["params"].pop("parts", None)
        if objetivo["params"].get("tolerance") == referencia.tolerance:
            objetivo["params"].pop("tolerance")
        if objetivo["params"].get("labels") == _etiquetas(roles):
            objetivo["params"].pop("labels")
        if objetivo["params"].get("flexible") == list(referencia.flexible):
            objetivo["params"].pop("flexible")
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
    if t.guide is not None and (t.guide.why or t.guide.steps):
        guia: Dict[str, Any] = {}
        if t.guide.why:
            guia["why"] = t.guide.why
        if t.guide.steps:
            guia["steps"] = [
                {"text": p.text, "keys": list(p.keys)} if p.keys else p.text for p in t.guide.steps
            ]
        objetivo["guide"] = guia
    if t.fix is not None:
        objetivo["fix"] = {"action": t.fix.action, "label": t.fix.label} if t.fix.label else {"action": t.fix.action}
    return objetivo


def dumps_practice(practice: PracticeDefinition) -> str:
    return json.dumps(dump_practice(practice), ensure_ascii=False, indent=2) + "\n"
