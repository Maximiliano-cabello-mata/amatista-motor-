"""Modelo de referencia y resolución semántica de ejemplos y figuras (motor 3.3 - 3.5).

Separa la interpretación y validación de «reference» y «example» del cargador
estructural de prácticas.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence

from ..models import (
    ExampleDefinition,
    Hint,
    ReferenceModel,
    ReferencePart,
    TargetDefinition,
    TargetGuide,
)
from .schema import (
    CAMPOS_EJEMPLO,
    CAMPOS_PIEZA,
    CAMPOS_REFERENCIA,
    EXIGENCIAS,
    MAX_PIEZAS,
    PRIMITIVAS_REFERENCIA,
)

FIGURAS = ("figure.resembles", "figure.recognize", "figure.silhouette")
CON_NIVEL = ("figure.recognize", "figure.silhouette")  # reciben nivel, exigencia y título de la práctica

OBJETIVO_EJEMPLO = "ejemplo"
PESO_EJEMPLO = 15
INYECTADOS_EJEMPLO = ("steps", "check", "parts", "labels", "flexible", "level", "title")


def pieza_como_dict(pieza: ReferencePart) -> Dict[str, Any]:
    """Convierte una pieza de referencia al diccionario canónico usado por validadores."""
    pieza_dict = {
        "group": pieza.group,
        "role": pieza.role,
        "primitive": pieza.primitive,
        "size": list(pieza.size),
        "location": list(pieza.location),
        "rotation": list(pieza.rotation),
        "join": pieza.join,
    }
    if pieza.name:  # figure.silhouette nombra las partes («Falta la parte «Guarda»»)
        pieza_dict["name"] = pieza.name
    if pieza.segments:
        pieza_dict["segments"] = pieza.segments
    return pieza_dict


def aspectos_de(pasos: Sequence[Dict[str, Any]], partes: Sequence[Dict[str, Any]]) -> List[str]:
    """Los aspectos que tiene un ejemplo (pasos ya revisados)."""
    from ..ejemplo import aspectos_del_ejemplo, escena_esperada, lo_que_pide

    return aspectos_del_ejemplo(escena_esperada(pasos, partes), lo_que_pide(pasos))


def _etiquetas(roles) -> Dict[str, str]:
    return {r.id: r.label for r in roles or () if r.label}


def _inyectados(ejemplo: ExampleDefinition, referencia: Optional[ReferenceModel], roles, nivel: int) -> Dict[str, Any]:
    """Lo que el cargador pone en cada example.matches (y lo que dump_practice no exporta si no cambió)."""
    titulo = ejemplo.title or (referencia.title if referencia is not None else "")
    inyectados: Dict[str, Any] = {"steps": list(ejemplo.steps), "level": nivel}
    if ejemplo.check:
        inyectados["check"] = list(ejemplo.check)
    if titulo:
        inyectados["title"] = titulo
    usa_modelo = any(next(iter(p)) == "referencia" for p in ejemplo.steps)
    if usa_modelo and referencia is not None and referencia.compared:  # la figura del ejemplo es la de «reference»
        inyectados["parts"] = [pieza_como_dict(p) for p in referencia.compared]
        if referencia.flexible:
            inyectados["flexible"] = list(referencia.flexible)
        if referencia.strictness:
            inyectados["strictness"] = referencia.strictness
    if _etiquetas(roles):
        inyectados["labels"] = _etiquetas(roles)
    return inyectados


def _vector(valor: Any, donde: str, e: Any, defecto=None, positivo: bool = False):
    """Valida y convierte una terna 3D (x, y, z)."""
    if valor is None and defecto is not None:
        return defecto
    if (
        not isinstance(valor, list)
        or len(valor) != 3
        or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in valor)
    ):
        e.add(f"'{donde}' debe ser una lista de 3 números")
        return defecto or (1.0, 1.0, 1.0)
    if positivo and any(x < 0 for x in valor):
        e.add(f"'{donde}' no puede tener medidas negativas")
    return tuple(float(x) for x in valor)


def _parse_piezas_referencia(crudas: Any, e: Any) -> List[ReferencePart]:
    if not isinstance(crudas, list) or not crudas or len(crudas) > MAX_PIEZAS:
        e.add(f"'reference.parts' debe tener entre 1 y {MAX_PIEZAS} piezas")
        return []

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
        segmentos = pieza.get("segments") or 0
        if isinstance(segmentos, bool) or not isinstance(segmentos, int) or not 0 <= segmentos <= 256:
            e.add(f"'{donde}.segments' debe ser un entero entre 0 y 256 (0 = los de Blender)")
            segmentos = 0
        piezas.append(
            ReferencePart(
                primitive=primitiva,
                size=_vector(pieza.get("size"), f"{donde}.size", e, positivo=True),
                location=_vector(pieza.get("location"), f"{donde}.location", e, (0.0, 0.0, 0.0)),
                rotation=_vector(pieza.get("rotation"), f"{donde}.rotation", e, (0.0, 0.0, 0.0)),
                role=str(pieza.get("role") or ""),
                name=str(pieza.get("name") or ""),
                color=str(pieza.get("color") or ""),
                join=str(pieza.get("join") or ""),
                segments=segmentos,
                material=material,
                compare=pieza.get("compare", True) is not False,
            )
        )
    return piezas


def _parse_flexibles(raw: Any, piezas: List[ReferencePart], e: Any) -> List[str]:
    flexibles = raw or []
    if not isinstance(flexibles, list) or not all(isinstance(g, str) for g in flexibles):
        e.add("'reference.flexible' debe ser una lista de roles o primitivas")
        return []
    grupos = {p.group for p in piezas}
    for grupo in flexibles:
        if grupo not in grupos:
            e.add(f"'reference.flexible': «{grupo}» no es el rol ni la primitiva de ninguna pieza")
    return list(flexibles)


def _parse_luces(raw: Any, e: Any) -> List[Dict[str, Any]]:
    luces = raw or []
    if not isinstance(luces, list) or not all(isinstance(x, dict) for x in luces):
        e.add("'reference.lights' debe ser una lista de luces {type, location, energy}")
        return []
    return list(luces)


def _referencia(raw: Any, e: Any) -> Optional[ReferenceModel]:
    """«reference»: la figura terminada en piezas (motor 3.3). Ver docs/motor/referencia/10_modelo_de_referencia.md."""
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

    piezas = _parse_piezas_referencia(raw.get("parts"), e)
    objetos = raw.get("objects") or {}
    camara = raw.get("camera") or {}
    if not isinstance(objetos, dict) or not isinstance(camara, dict):
        e.add("'reference.objects' y 'reference.camera' deben ser objetos")
        objetos, camara = {}, {}

    flexibles = _parse_flexibles(raw.get("flexible"), piezas, e)
    luces = _parse_luces(raw.get("lights"), e)

    exigencia = raw.get("strictness") or ""
    if exigencia and exigencia not in EXIGENCIAS:
        e.add(f"'reference.strictness' debe ser una de: {', '.join(EXIGENCIAS)}")
        exigencia = ""
    auto = raw.get("autoRoles")
    if auto is not None and not isinstance(auto, bool):
        e.add("'reference.autoRoles' debe ser true o false")
        auto = None

    return ReferenceModel(
        strictness=exigencia,
        auto_roles=auto,
        lights=tuple(luces),
        flexible=tuple(flexibles),
        parts=tuple(piezas),
        title=str(raw.get("title") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        tolerance=float(tolerancia),
        objects=objetos,
        camera=camara,
    )


def _inyectar_params_figura(
    objetivo: TargetDefinition,
    referencia: ReferenceModel,
    roles,
    nivel: int,
) -> TargetDefinition:
    """Configura parámetros inyectados de modelo de referencia en objetivos de figura."""
    propios = (
        {}
        if objetivo.validator == "figure.silhouette"
        else {"tolerance": referencia.tolerance, "labels": _etiquetas(roles)}
    )
    params = {
        **propios,
        **objetivo.params,
        "parts": [pieza_como_dict(p) for p in referencia.compared],
    }
    if referencia.flexible and objetivo.validator != "figure.silhouette":
        params.setdefault("flexible", list(referencia.flexible))
    if objetivo.validator in CON_NIVEL:
        params.setdefault("level", nivel)
        if referencia.strictness:
            params.setdefault("strictness", referencia.strictness)
        if referencia.title:
            params.setdefault("title", referencia.title)
    return replace(objetivo, params=params)


def _con_referencia(
    objetivos: List[TargetDefinition],
    referencia: Optional[ReferenceModel],
    roles,
    e: Any,
    nivel: int = 1,
) -> List[TargetDefinition]:
    """figure.resembles y figure.recognize sin «parts» toman las piezas y la holgura de «reference».

    También los nombres de los roles y, para figure.recognize (motor 3.4), el nivel, la exigencia y el título.
    """
    salida = []
    for objetivo in objetivos:
        if objetivo.validator in FIGURAS and "parts" not in objetivo.params:
            if referencia is None or not referencia.compared:
                e.add(f"'{objetivo.id}': {objetivo.validator} necesita 'reference' con piezas en la práctica")
            else:
                objetivo = _inyectar_params_figura(objetivo, referencia, roles, nivel)
        salida.append(objetivo)
    return salida


def _aspectos_validos(valor: Any, donde: str, disponibles: List[str], e: Any) -> List[str]:
    """Una lista de aspectos (figura, materiales…) que el ejemplo tiene de verdad; si no, un error con la ruta."""
    from ..ejemplo import ASPECTOS

    if not isinstance(valor, list) or not all(isinstance(a, str) for a in valor):
        e.add(f"'{donde}' debe ser una lista de: {', '.join(ASPECTOS)}")
        return []
    desconocidos = [a for a in valor if a not in ASPECTOS]
    if desconocidos:
        e.add(f"'{donde}': «{desconocidos[0]}» no es un aspecto (usa: {', '.join(ASPECTOS)})")
        return []
    faltan = [a for a in valor if a not in disponibles]
    if faltan:
        e.add(f"'{donde}': el ejemplo no tiene «{faltan[0]}» que revisar (tiene: {', '.join(disponibles) or 'nada'})")
        return []
    return list(valor)


def _ejemplo(raw: Any, referencia: Optional[ReferenceModel], e: Any) -> Optional[ExampleDefinition]:
    """«example»: la solución de la práctica en pasos. Ver docs/motor/referencia/14_ejemplo_y_revision.md."""
    from ..ejemplo import revisar_pasos

    if raw is None:
        return None
    if not isinstance(raw, dict):
        e.add("'example' debe ser un objeto {title, description, steps, check}")
        return None
    extra = set(raw) - CAMPOS_EJEMPLO
    if extra:
        e.add(f"'example' no reconoce: {', '.join(sorted(extra))}")
    partes = [pieza_como_dict(p) for p in referencia.compared] if referencia is not None else []
    errores = revisar_pasos(raw.get("steps"), partes)
    for error in errores:
        e.add(error)
    if errores:
        return None
    revisa = _aspectos_validos(raw.get("check") or [], "example.check", aspectos_de(raw["steps"], partes), e)
    return ExampleDefinition(
        steps=tuple(raw["steps"]),
        title=str(raw.get("title") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        check=tuple(revisa),
    )


def _objetivo_ejemplo_auto(
    objetivo_id: str,
    inyectados: Dict[str, Any],
    objetivos: List[TargetDefinition],
) -> TargetDefinition:
    """Construye el objetivo de auto-comparación con el ejemplo cuando el autor no definió uno propio."""
    return TargetDefinition(
        id=objetivo_id,
        title="Tu práctica coincide con el ejemplo",
        validator="example.matches",
        params=inyectados,
        weight=PESO_EJEMPLO,
        # Motor 7: la comparación con el ejemplo orienta pero no traba. Era un paso obligatorio escondido:
        # con todos los pasos del autor hechos, el alumno no avanzaba porque su archivo no se llamaba igual
        # que el del ejemplo (simulaciones del 31 de octubre de 2026). Si el ejemplo es lo único que se revisa,
        # sigue siendo obligatorio.
        optional=any(not t.optional for t in objetivos),
        hints=(
            Hint(1, "Mira la lista «Comparado con el ejemplo»: cada punto que falta dice cómo hacerlo."),
            Hint(
                2,
                "Abre el ejemplo resuelto (botón «Ver el ejemplo») y compáralo con tu escena; vuelve con "
                "«Volver a mi práctica».",
            ),
        ),
        guide=TargetGuide(
            why=(
                "El ejemplo resuelto es lo que propone la plataforma: Amatista revisa que tu práctica "
                "tenga lo mismo, con libertad en los nombres, el lugar, el tamaño y los colores."
            )
        ),
    )


def _con_ejemplo(
    objetivos: List[TargetDefinition],
    ejemplo: Optional[ExampleDefinition],
    referencia: Optional[ReferenceModel],
    roles,
    nivel: int,
    e: Any,
):
    """example.matches recibe el ejemplo; si la práctica no lo usa, se agrega al final de la ruta.

    El objetivo que se agrega no cuenta para el máximo de objetivos (MAX_OBJETIVOS cuenta los del autor).
    """
    usados = [t for t in objetivos if t.validator == "example.matches"]
    if ejemplo is None:
        for t in usados:
            e.add(f"'{t.id}': example.matches necesita «example» (el ejemplo resuelto) en la práctica")
        return objetivos, ejemplo

    partes = [pieza_como_dict(p) for p in referencia.compared] if referencia is not None else []
    disponibles = aspectos_de(ejemplo.steps, partes)
    for t in usados:
        if "aspects" in t.params:
            _aspectos_validos(t.params["aspects"], f"{t.id}.params.aspects", disponibles, e)

    inyectados = _inyectados(ejemplo, referencia, roles, nivel)
    salida = [
        replace(t, params={**inyectados, **t.params}) if t.validator == "example.matches" else t
        for t in objetivos
    ]
    if any(not t.params.get("aspects") for t in usados):
        return salida, ejemplo

    ids = {t.id for t in objetivos}
    objetivo_id = OBJETIVO_EJEMPLO if OBJETIVO_EJEMPLO not in ids else "coincide-con-el-ejemplo"
    salida.append(_objetivo_ejemplo_auto(objetivo_id, inyectados, objetivos))
    return salida, replace(ejemplo, auto=True)
