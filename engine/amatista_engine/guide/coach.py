"""El entrenador: convierte un resultado del validador en una guía amable.

Etapa 1 decía «“Cubierta” mide 2.00 en Z: es demasiado grande». La etapa 2
dice lo mismo y además QUÉ HACER, con las teclas exactas y los números ya
calculados («Selecciona la cubierta › S › Z › escribe 0.05 › Enter»), qué
objeto mirar (resaltados), qué dibujar en la vista 3D (una regla, un plano
fantasma, las patas que faltan) y qué herramienta puede arrancar el botón
«Hazlo conmigo».

Cada validador tiene su entrenador. Si no hay uno, se usa el genérico: el
mensaje del validador y el consejo del objetivo. Si el autor escribió
`guide.steps`, sus pasos reemplazan a los generados (el resto se conserva).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..models import (
    ACTUAL,
    BLOQUEADO,
    COMPLETADO,
    EvaluationReport,
    PracticeDefinition,
    SceneObject,
    SceneState,
    TargetDefinition,
    ValidationResult,
)
from ..validators.base import EJES, describe, select, selector
from .models import (
    RESALTE_BIEN,
    RESALTE_CANDIDATO,
    RESALTE_CORREGIR,
    TONO_ANIMO,
    TONO_CERCA,
    TONO_LOGRADO,
    GuideAction,
    GuideInstruction,
    Guidance,
    Highlight,
    VisualCue,
)

Paso = GuideInstruction  # abreviatura: los entrenadores arman muchas


@dataclass(frozen=True)
class Contexto:
    practice: PracticeDefinition
    target: TargetDefinition
    result: ValidationResult
    scene: SceneState

    def etiqueta(self, rol: Optional[str]) -> str:
        return self.practice.role_label(rol) if rol else ""

    def que(self) -> str:
        """«Cubierta», «Pata», «Mesa»… para los textos."""
        sel = selector(self.target)
        return describe(sel, self.etiqueta)


@dataclass
class Parcial:
    """Lo que aporta un entrenador (lo demás lo completa build_guidance)."""

    feedback: str = ""
    tone: str = TONO_ANIMO
    instructions: Tuple[GuideInstruction, ...] = ()
    highlights: Tuple[Highlight, ...] = ()
    cues: Tuple[VisualCue, ...] = ()
    action: Optional[GuideAction] = None


# --- Ayudantes -----------------------------------------------------------------------


def _num(valor: float) -> str:
    """0.05 → «0.05», 1.0 → «1», 0.333333 → «0.33»."""
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto if texto not in ("-0", "") else "0"


def objetivo_amable(minimo: float, maximo: float) -> float:
    """Un número redondo dentro del rango: el que conviene escribir."""
    if math.isinf(minimo) and math.isinf(maximo):
        return 0.0
    if math.isinf(minimo):
        return maximo
    if math.isinf(maximo):
        return minimo
    medio = (minimo + maximo) / 2.0
    for paso in (1.0, 0.5, 0.25, 0.1, 0.05, 0.01):
        candidato = round(medio / paso) * paso
        if minimo <= candidato <= maximo:
            return round(candidato, 4)
    return round(medio, 4)


PASOS_REDONDOS = (1.0, 0.5, 0.25, 0.1, 0.05, 0.02, 0.01, 0.005)


def factor_amable(valor: float, minimo: float, maximo: float) -> float:
    """Factor de escala fácil de escribir (0.1, 0.5, 2…) que deja `valor` en el rango."""
    if not valor:
        return 1.0
    meta = objetivo_amable(minimo, maximo) / valor
    for paso in PASOS_REDONDOS:
        candidato = round(round(meta / paso) * paso, 4)
        if candidato > 0 and minimo <= valor * candidato <= maximo:
            return candidato
    return round(meta, 4)


def delta_amable(valor: float, minimo: float, maximo: float) -> float:
    """Cuánto mover (G) para quedar dentro del rango, con un número redondo."""
    meta = objetivo_amable(minimo, maximo) - valor
    for paso in PASOS_REDONDOS:
        candidato = round(round(meta / paso) * paso, 4)
        if minimo <= valor + candidato <= maximo:
            return candidato
    return round(meta, 4)


def _seleccionar(nombre: str) -> GuideInstruction:
    return Paso(f"Selecciona «{nombre}» con un clic", ("Clic",))


def _plural(n: int, singular: str, plural: Optional[str] = None) -> str:
    return singular if n == 1 else (plural or singular + "s")


def _bien(objetos: Sequence[SceneObject], etiqueta: str) -> Tuple[Highlight, ...]:
    return tuple(Highlight(o.name, RESALTE_BIEN, f"✓ {etiqueta or o.name}") for o in objetos)


def _sin_rol(scene: SceneState) -> List[SceneObject]:
    return [o for o in scene.objects if o.object_type == "MESH" and not o.roles]


# --- Entrenadores por validador -----------------------------------------------------------


def _esquinas_libres(ctx: Contexto, rol: str) -> Tuple[VisualCue, ...]:
    """Patas que faltan: si otro objetivo dice «rol debajo de referencia», se
    dibujan cajas fantasma en las esquinas libres de la referencia."""
    debajo = next(
        (
            t
            for t in ctx.practice.targets
            if t.validator == "spatial.below" and t.params.get("role") == rol and t.params.get("reference_role")
        ),
        None,
    )
    if debajo is None:
        return ()
    referencias = ctx.scene.objects_with_role(debajo.params["reference_role"])
    if not referencias:
        return ()
    ref_min, ref_max = referencias[0].caja()
    existentes = ctx.scene.objects_with_role(rol)
    lado = min(0.12, (ref_max[0] - ref_min[0]) / 6 or 0.1, (ref_max[1] - ref_min[1]) / 6 or 0.1)
    alto = max(0.1, ref_min[2])
    margen = lado
    cajas = []
    for x in (ref_min[0] + margen, ref_max[0] - margen):
        for y in (ref_min[1] + margen, ref_max[1] - margen):
            ocupada = any(
                abs((o.caja()[0][0] + o.caja()[1][0]) / 2 - x) < (ref_max[0] - ref_min[0]) / 4
                and abs((o.caja()[0][1] + o.caja()[1][1]) / 2 - y) < (ref_max[1] - ref_min[1]) / 4
                for o in existentes
            )
            if not ocupada:
                cajas.append({"center": [round(x, 3), round(y, 3), round(alto / 2, 3)], "size": [lado, lado, round(alto, 3)]})
    if not cajas:
        return ()
    return (VisualCue("ghosts", f"Aquí puede ir {'una' if len(cajas) == 1 else 'cada'} {ctx.etiqueta(rol).lower()}", {"boxes": cajas}),)


def coach_role_count(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    rol = d.get("role") or ctx.target.params.get("role")
    etiqueta = ctx.etiqueta(rol) or rol
    esperado = d.get("expected", 1)
    minimo = esperado.get("min") if isinstance(esperado, dict) else esperado
    maximo = esperado.get("max") if isinstance(esperado, dict) else esperado
    encontrados = d.get("found", 0)
    con_rol = ctx.scene.objects_with_role(rol) if rol else ()

    if ctx.result.passed:
        return Parcial(ctx.result.message, TONO_LOGRADO, highlights=_bien(con_rol, etiqueta))

    if maximo is not None and encontrados > maximo:
        sobran = list(con_rol)[maximo:]
        return Parcial(
            f"Hay {encontrados - maximo} «{etiqueta}» de más. Quédate con {maximo}.",
            TONO_CERCA,
            (
                _seleccionar(sobran[0].name),
                Paso("Quítale el rol en la pestaña Amatista, o bórralo", ("X",)),
            ),
            _bien(list(con_rol)[:maximo], etiqueta)
            + tuple(Highlight(o.name, RESALTE_CORREGIR, "Sobra") for o in sobran),
            action=GuideAction("focus", "Mostrarme cuál sobra", tuple(o.name for o in sobran)),
        )

    if encontrados == 0:
        candidatos = _sin_rol(ctx.scene)
        if candidatos:
            elegido = candidatos[0]
            return Parcial(
                f"Todavía ningún objeto es «{etiqueta}». Elige uno y cuéntaselo a Amatista.",
                TONO_ANIMO,
                (
                    _seleccionar(elegido.name),
                    Paso("Abre la barra lateral y la pestaña Amatista", ("N",)),
                    Paso(f"En «Es», elige «{etiqueta}» y pulsa Asignar rol"),
                ),
                tuple(Highlight(o.name, RESALTE_CANDIDATO, f"¿Es la {etiqueta.lower()}?") for o in candidatos[:3]),
                action=GuideAction("assign_role", f"Marcar «{elegido.name}» como {etiqueta}", (elegido.name,), role=rol),
            )
        return Parcial(
            f"Necesitas un objeto que haga de «{etiqueta}». Empieza agregando un cubo.",
            TONO_ANIMO,
            (
                Paso("Con el ratón sobre la vista 3D, abre el menú Agregar", ("Shift", "A")),
                Paso("Elige Malla › Cubo"),
                Paso(f"Luego asígnale el rol «{etiqueta}» en la pestaña Amatista", ("N",)),
            ),
            action=GuideAction("add_cube", "Agregar un cubo conmigo", role=rol),
        )

    faltan = (minimo or 0) - encontrados
    modelo = con_rol[0]
    return Parcial(
        f"¡Vas bien! Llevas {encontrados} de {minimo} {_plural(minimo, etiqueta.lower())}. "
        f"Te {'falta' if faltan == 1 else 'faltan'} {faltan}.",
        TONO_CERCA if faltan == 1 else TONO_ANIMO,
        (
            _seleccionar(modelo.name),
            Paso("Duplícalo: la copia conserva el rol", ("Shift", "D")),
            Paso("Mueve la copia con el ratón y haz clic para dejarla", ("Clic",)),
        )
        + ((Paso(f"Repite hasta tener {minimo}"),) if faltan > 1 else ()),
        _bien(con_rol, etiqueta),
        _esquinas_libres(ctx, rol),
        GuideAction("duplicate", f"Duplicar «{modelo.name}» conmigo", (modelo.name,)),
    )


def coach_role_exists(ctx: Contexto) -> Parcial:
    return coach_role_count(ctx)


def _fallo_principal(ctx: Contexto) -> Optional[Tuple[SceneObject, float]]:
    fallos = ctx.result.details.get("failed") or []
    if not fallos:
        return None
    obj = ctx.scene.object_by_name(fallos[0].get("object"))
    valor = fallos[0].get("value")
    if obj is None or not isinstance(valor, (int, float)):
        return None
    return obj, float(valor)


def coach_dimension(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    eje = (d.get("axis") or ctx.target.params.get("axis") or "z").lower()
    minimo, maximo = float(d.get("min", float("-inf"))), float(d.get("max", float("inf")))
    objetos = select(ctx.scene, selector(ctx.target))
    que = ctx.que()
    if ctx.result.passed:
        return Parcial(ctx.result.message, TONO_LOGRADO, highlights=_bien(objetos, que))
    principal = _fallo_principal(ctx)
    if principal is None:
        return Parcial(ctx.result.message, TONO_ANIMO, (Paso(ctx.target.tip),) if ctx.target.tip else ())
    obj, valor = principal
    factor = factor_amable(valor, minimo, maximo)
    meta = valor * factor
    grande = valor > maximo
    E = eje.upper()
    fallidos = {f["object"] for f in d.get("failed", [])}
    rango = f"{_num(minimo)} y {_num(maximo)}"
    return Parcial(
        f"«{obj.name}» mide {_num(valor)} en {E}. Lo buscamos entre {rango}: "
        f"{'hazlo más pequeño' if grande else 'hazlo más grande'}, por ejemplo {_num(meta)}.",
        TONO_CERCA if valor and min(abs(valor - minimo), abs(valor - maximo)) <= (maximo - minimo) else TONO_ANIMO,
        (
            _seleccionar(obj.name),
            Paso(f"Escala solo en {E}", ("S", E)),
            Paso(f"Escribe {_num(factor)} y confirma: {_num(valor)} × {_num(factor)} ≈ {_num(meta)}", (_num(factor), "Enter")),
        )
        + ((Paso(f"Haz lo mismo con {len(fallidos) - 1} más", ()),) if len(fallidos) > 1 else ()),
        tuple(
            Highlight(o.name, RESALTE_CORREGIR if o.name in fallidos else RESALTE_BIEN,
                      f"mide {_num(o.dimensions[EJES[eje]])} · busca {_num(minimo)}–{_num(maximo)}" if o.name in fallidos else f"✓ {que}")
            for o in objetos
        ),
        (VisualCue("ruler", f"Entre {rango}", {"object": obj.name, "axis": eje, "min": minimo, "max": maximo,
                                                 "current": round(valor, 4)}),),
        GuideAction("scale", f"Escalar en {E} conmigo", (obj.name,), eje, round(factor, 4)),
    )


def coach_position(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    eje = (d.get("axis") or "z").lower()
    minimo, maximo = float(d.get("min", float("-inf"))), float(d.get("max", float("inf")))
    objetos = select(ctx.scene, selector(ctx.target))
    if ctx.result.passed:
        return Parcial(ctx.result.message, TONO_LOGRADO, highlights=_bien(objetos, ctx.que()))
    principal = _fallo_principal(ctx)
    if principal is None:
        return Parcial(ctx.result.message)
    obj, valor = principal
    delta = delta_amable(valor, minimo, maximo)
    meta = valor + delta
    E = eje.upper()
    return Parcial(
        f"«{obj.name}» está en {E} = {_num(valor)}. Muévelo {_num(abs(delta))} hacia "
        f"{('arriba' if delta > 0 else 'abajo') if eje == 'z' else ('+' if delta > 0 else '−') + E}.",
        TONO_ANIMO,
        (_seleccionar(obj.name), Paso(f"Mueve solo en {E}", ("G", E)), Paso(f"Escribe {_num(delta)} y confirma", (_num(delta), "Enter"))),
        (Highlight(obj.name, RESALTE_CORREGIR, f"{E} {_num(valor)} → {_num(meta)}"),),
        (VisualCue("arrow", f"{'Sube' if delta > 0 else 'Baja'} {_num(abs(delta))}",
                   {"object": obj.name, "direction": "up" if delta > 0 else "down"}),) if eje == "z" else (),
        GuideAction("move", f"Mover en {E} conmigo", (obj.name,), eje, round(delta, 4)),
    )


def coach_rotation(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    eje = (d.get("axis") or "z").lower()
    principal = _fallo_principal(ctx)
    if ctx.result.passed or principal is None:
        return Parcial(ctx.result.message, TONO_LOGRADO if ctx.result.passed else TONO_ANIMO)
    obj, valor = principal
    meta = objetivo_amable(float(d.get("min", 0)), float(d.get("max", 0)))
    delta = round(meta - valor)
    E = eje.upper()
    return Parcial(
        f"«{obj.name}» está girado {valor:.0f}° en {E}; gíralo {abs(delta)}° más.",
        TONO_ANIMO,
        (_seleccionar(obj.name), Paso(f"Gira solo en {E}", ("R", E)), Paso(f"Escribe {delta} y confirma", (str(delta), "Enter"))),
        (Highlight(obj.name, RESALTE_CORREGIR, f"{valor:.0f}° → {meta:.0f}°"),),
        action=GuideAction("rotate", f"Girar en {E} conmigo", (obj.name,), eje, float(delta)),
    )


def coach_below(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    objetos = select(ctx.scene, selector(ctx.target))
    rol_ref = ctx.target.params.get("reference_role")
    referencias = ctx.scene.objects_with_role(rol_ref) if rol_ref else tuple(
        o for o in ctx.scene.objects if o.name == ctx.target.params.get("reference")
    )
    que, ref_txt = ctx.que(), ctx.etiqueta(rol_ref) or ctx.target.params.get("reference", "")
    if ctx.result.passed:
        return Parcial(ctx.result.message, TONO_LOGRADO, highlights=_bien(objetos, que))
    if not referencias or not objetos:
        return Parcial(ctx.result.message)
    ref_min, ref_max = referencias[0].caja()
    plano = VisualCue(
        "plane",
        f"Aquí abajo termina la {ref_txt.lower()}",
        {"z": round(ref_min[2], 4), "min_xy": [ref_min[0], ref_min[1]], "max_xy": [ref_max[0], ref_max[1]]},
    )
    fallos = {f["object"]: f.get("reason") for f in d.get("failed", [])}
    primero = next((o for o in objetos if o.name in fallos), None)
    if primero is None:
        return Parcial(ctx.result.message)
    luces = tuple(
        Highlight(o.name, RESALTE_CORREGIR if o.name in fallos else RESALTE_BIEN,
                  ("Bájala" if fallos.get(o.name) == "arriba" else "Muévela debajo") if o.name in fallos else f"✓ {que}")
        for o in objetos
    )
    if fallos[primero.name] == "arriba":
        delta = ref_min[2] - primero.caja()[1][2]
        return Parcial(
            f"«{primero.name}» se mete en la {ref_txt.lower()}: su parte de arriba sobra {_num(abs(delta))}. "
            f"Bájala hasta tocar el plano.",
            TONO_CERCA,
            (
                Paso("Mira la mesa de frente para verlo mejor", ("1",)),
                _seleccionar(primero.name),
                Paso("Muévela solo en Z", ("G", "Z")),
                Paso(f"Escribe {_num(delta)} y confirma", (_num(delta), "Enter")),
            ),
            luces,
            (plano, VisualCue("arrow", f"Baja {_num(abs(delta))}", {"object": primero.name, "direction": "down"})),
            GuideAction("move", "Bajarla conmigo", (primero.name,), "z", round(delta, 4)),
        )
    return Parcial(
        f"«{primero.name}» quedó fuera de la {ref_txt.lower()}. Llévala debajo, cerca de una esquina.",
        TONO_ANIMO,
        (
            Paso("Mira desde arriba", ("7",)),
            _seleccionar(primero.name),
            Paso("Muévela en el plano del suelo (sin cambiar la altura)", ("G", "Shift", "Z")),
            Paso("Haz clic cuando quede bajo la cubierta", ("Clic",)),
        ),
        luces,
        (plano, VisualCue("arrow", "Llévala debajo", {"object": primero.name, "direction": "in"})),
        GuideAction("move", "Moverla conmigo", (primero.name,), None, None),
    )


def coach_scale_applied(ctx: Contexto) -> Parcial:
    sin = ctx.result.details.get("not_applied") or []
    if ctx.result.passed or not sin:
        return Parcial(ctx.result.message, TONO_LOGRADO if ctx.result.passed else TONO_ANIMO)
    return Parcial(
        f"La escala de «{sin[0]}» todavía no está aplicada: Blender la guarda aparte de sus medidas.",
        TONO_ANIMO,
        (_seleccionar(sin[0]), Paso("Abre el menú Aplicar", ("Ctrl", "A")), Paso("Elige «Escala»")),
        tuple(Highlight(n, RESALTE_CORREGIR, "Aplica la escala") for n in sin),
        action=GuideAction("apply_scale", "Abrir Aplicar conmigo", tuple(sin)),
    )


def coach_file_saved(ctx: Contexto) -> Parcial:
    if ctx.result.passed:
        return Parcial("Tu archivo está guardado.", TONO_LOGRADO)
    if ctx.scene.file_path:
        return Parcial(
            "Tienes cambios sin guardar. Un atajo y listo.",
            TONO_CERCA,
            (Paso("Guarda", ("Ctrl", "S")),),
            action=GuideAction("save", "Guardar ahora"),
        )
    return Parcial(
        "Falta guardar tu trabajo. Dale un nombre que reconozcas.",
        TONO_CERCA,
        (Paso("Abre Guardar como", ("Shift", "Ctrl", "S")), Paso("Escribe un nombre, por ejemplo mi_mesa.blend"),
         Paso("Pulsa Guardar", ("Enter",))),
        action=GuideAction("save", "Guardar como…"),
    )


def coach_file_named(ctx: Contexto) -> Parcial:
    contiene = ctx.result.details.get("contains", "")
    if ctx.result.passed:
        return Parcial(ctx.result.message, TONO_LOGRADO)
    return Parcial(
        f"Guarda el archivo con un nombre que incluya «{contiene}».",
        TONO_ANIMO,
        (Paso("Abre Guardar como", ("Shift", "Ctrl", "S")), Paso(f"Escribe un nombre con «{contiene}»"), Paso("Pulsa Guardar", ("Enter",))),
        action=GuideAction("save", "Guardar como…"),
    )


def coach_material(ctx: Contexto) -> Parcial:
    sin = ctx.result.details.get("missing") or []
    if ctx.result.passed or not sin:
        return Parcial(ctx.result.message, TONO_LOGRADO if ctx.result.passed else TONO_ANIMO)
    return Parcial(
        f"«{sin[0]}» todavía no tiene material. Dale color.",
        TONO_ANIMO,
        (
            _seleccionar(sin[0]),
            Paso("En Propiedades, abre la pestaña Material (la esfera roja)"),
            Paso("Pulsa «Nuevo» y cambia el Color base"),
        ),
        tuple(Highlight(n, RESALTE_CORREGIR, "Sin material") for n in sin),
        action=GuideAction("focus", f"Mostrarme «{sin[0]}»", tuple(sin[:1])),
    )


def coach_modifier(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    sin = d.get("missing") or []
    if ctx.result.passed or not sin:
        return Parcial(ctx.result.message, TONO_LOGRADO if ctx.result.passed else TONO_ANIMO)
    nombre = d.get("modifier", "")
    return Parcial(
        f"A «{sin[0]}» le falta el modificador {nombre}.",
        TONO_ANIMO,
        (
            _seleccionar(sin[0]),
            Paso("En Propiedades, abre la pestaña Modificadores (la llave azul)"),
            Paso(f"Agregar modificador › {nombre}"),
        ),
        tuple(Highlight(n, RESALTE_CORREGIR, f"Falta {nombre}") for n in sin),
        action=GuideAction("focus", f"Mostrarme «{sin[0]}»", tuple(sin[:1])),
    )


ENTRENADORES: Dict[str, Callable[[Contexto], Parcial]] = {
    "role.count": coach_role_count,
    "role.exists": coach_role_exists,
    "dimension.range": coach_dimension,
    "object.position": coach_position,
    "object.rotation": coach_rotation,
    "spatial.below": coach_below,
    "transform.scale_applied": coach_scale_applied,
    "file.saved": coach_file_saved,
    "file.named": coach_file_named,
    "material.exists": coach_material,
    "modifier.exists": coach_modifier,
}


def coach_logic_any(ctx: Contexto) -> Parcial:
    """«Una de varias»: guía con el entrenador de la primera opción."""
    opciones = ctx.target.params.get("options") or []
    if ctx.result.passed or not opciones:
        return coach_generico(ctx)
    primera = opciones[0]
    sub = replace(ctx.target, validator=primera.get("validator", ""), params=dict(primera.get("params") or {}))
    entrenador = ENTRENADORES.get(sub.validator, coach_generico)
    return entrenador(Contexto(ctx.practice, sub, replace(ctx.result, details={}), ctx.scene))


def coach_generico(ctx: Contexto) -> Parcial:
    d = ctx.result.details
    nombres = list(d.get("missing") or []) + [f.get("object") for f in d.get("failed") or [] if f.get("object")]
    return Parcial(
        ctx.result.message,
        TONO_LOGRADO if ctx.result.passed else TONO_ANIMO,
        (Paso(ctx.target.tip),) if ctx.target.tip and not ctx.result.passed else (),
        tuple(Highlight(n, RESALTE_CORREGIR, "Revisa este") for n in nombres[:4]),
        action=GuideAction("focus", "Mostrarme dónde", tuple(nombres[:1])) if nombres else None,
    )


# --- Guía del paso actual ----------------------------------------------------------------


def guide_target(
    practice: PracticeDefinition,
    target: TargetDefinition,
    result: ValidationResult,
    scene: SceneState,
    step_number: int = 0,
    step_total: int = 0,
) -> Guidance:
    ctx = Contexto(practice, target, result, scene)
    entrenador = ENTRENADORES.get(target.validator, coach_generico)
    try:
        parcial = entrenador(ctx)
    except Exception:  # noqa: BLE001 - una guía nunca rompe la evaluación
        parcial = coach_generico(ctx)
    guia = target.guide
    instrucciones = parcial.instructions
    if guia is not None and guia.steps and not result.passed:
        instrucciones = tuple(Paso(p.text, p.keys) for p in guia.steps)
    # El mensaje propio del autor (messages.fail/pass) manda sobre el generado.
    propio = target.messages.get("pass" if result.passed else "fail")
    return Guidance(
        target_id=target.id,
        title=target.title or target.id,
        step_number=step_number,
        step_total=step_total,
        feedback=propio or parcial.feedback or result.message,
        tone=parcial.tone,
        why=(guia.why if guia and guia.why else target.tip),
        instructions=instrucciones,
        highlights=parcial.highlights,
        cues=() if result.passed else parcial.cues,
        action=None if result.passed else parcial.action,
        completed=bool(result.passed),
    )


def guide_guard(practice: PracticeDefinition, scene: SceneState, report: EvaluationReport) -> Optional[Guidance]:
    """Motor v3: si un vigilante pausó el progreso, la guía muestra cómo arreglarlo."""
    if not report.paused_by:
        return None
    guard = practice.guard(report.paused_by)
    resultado = next((r for r in report.guards if r.target_id == report.paused_by), None)
    if guard is None or resultado is None:
        return None
    total = len([s for s in report.steps if not s.optional])
    base = guide_target(practice, guard, resultado, scene, report.step_number, total)
    accion = base.action
    if guard.fix is not None:
        objetos = accion.objects if accion is not None else ()
        accion = GuideAction(guard.fix.action, guard.fix.label or (accion.label if accion else "Arreglarlo conmigo"),
                             objetos)
    return replace(
        base,
        title=f"Progreso en pausa: {guard.title or guard.id}",
        tone="ojo",
        action=accion,
        completed=False,
        paused=True,
    )


def build_guidance(practice: PracticeDefinition, scene: SceneState, report: EvaluationReport) -> Guidance:
    """Guía del paso actual. Con la práctica terminada, la tarjeta de cierre."""
    pausa = guide_guard(practice, scene, report)
    if pausa is not None:
        return pausa
    total = len([s for s in report.steps if not s.optional])
    if report.completed and (report.current_target_id is None or practice.target(report.current_target_id).optional):
        extra = practice.target(report.current_target_id) if report.current_target_id else None
        resaltes: Tuple[Highlight, ...] = ()
        for target in practice.targets:
            r = report.result(target.id)
            if r is not None and r.passed and target.validator in ("role.count", "role.exists"):
                rol = target.params.get("role")
                resaltes += _bien(scene.objects_with_role(rol), practice.role_label(rol))
        return Guidance(
            target_id=extra.id if extra else None,
            title="¡Práctica completada!",
            step_number=total,
            step_total=total,
            feedback=practice.completion or "Terminaste todos los pasos.",
            tone=TONO_LOGRADO,
            why=f"Si quieres más: {extra.title}." if extra else "",
            instructions=(Paso(extra.tip),) if extra and extra.tip else (),
            highlights=resaltes,
            completed=True,
        )
    target = practice.target(report.current_target_id) if report.current_target_id else None
    if target is None:
        bloqueado = next((s for s in report.steps if s.status == BLOQUEADO), None)
        return Guidance(None, bloqueado.title if bloqueado else practice.title, 0, total,
                        "Revisa los pasos anteriores: algo dejó de cumplirse.", TONO_ANIMO)
    numero = next((i for i, s in enumerate(report.steps, start=1) if s.target_id == target.id), 0)
    guia = guide_target(practice, target, report.result(target.id), scene, numero, total)
    # Lo que ya está bien de los pasos anteriores también se ve (contorno verde).
    hechos = []
    nombres = {h.object_name for h in guia.highlights}
    for paso in report.steps:
        if paso.status != COMPLETADO or paso.target_id == target.id:
            continue
        previo = practice.target(paso.target_id)
        if previo.validator in ("role.count", "role.exists"):
            rol = previo.params.get("role")
            for h in _bien(scene.objects_with_role(rol), practice.role_label(rol)):
                if h.object_name not in nombres:
                    hechos.append(h)
                    nombres.add(h.object_name)
    return replace(guia, highlights=guia.highlights + tuple(hechos))


from .coach_v3 import ENTRENADORES_V3  # noqa: E402  (usa los ayudantes de arriba)

ENTRENADORES.update(ENTRENADORES_V3)
ENTRENADORES["logic.any"] = coach_logic_any

__all__ = ["ACTUAL", "ENTRENADORES", "build_guidance", "guide_guard", "delta_amable", "factor_amable", "guide_target", "objetivo_amable"]
