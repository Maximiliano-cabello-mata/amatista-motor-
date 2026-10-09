"""Datos de la guía (etapa 2): lo que el acompañante le muestra al alumno.

Todo es Python puro e inmutable, igual que models.py. El add-on dibuja estos
datos (tarjeta guía, teclas, resaltados y señales en la vista 3D) y el
servidor los puede devolver a la plataforma: nadie vuelve a calcularlos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# Tipo de resaltado de un objeto en la vista 3D.
RESALTE_BIEN = "bien"  # ya cumple: contorno verde y «✓ Cubierta»
RESALTE_CORREGIR = "corregir"  # hay que cambiarlo: contorno naranja y qué hacer
RESALTE_CANDIDATO = "candidato"  # podría servir: contorno punteado («¿Es la cubierta?»)

# Tono del mensaje (la interfaz elige color e ícono).
TONO_ANIMO = "animo"
TONO_CERCA = "cerca"
TONO_LOGRADO = "logrado"
TONO_OJO = "ojo"


@dataclass(frozen=True)
class GuideInstruction:
    """Un micro paso: texto corto y las teclas que hay que pulsar (en orden)."""

    text: str
    keys: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Highlight:
    object_name: str
    kind: str
    label: str = ""


@dataclass(frozen=True)
class VisualCue:
    """Ayuda visual en la vista 3D.

    kind:
        ruler   regla junto al objeto: data {object, axis, min, max, current}
        plane   plano fantasma: data {z, min_xy, max_xy}
        ghosts  cajas fantasma donde falta algo: data {boxes: [{center, size}]}
        arrow   flecha sobre un objeto: data {object, direction: up|down|in}
    """

    kind: str
    label: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GuideAction:
    """«Hazlo conmigo»: la herramienta de Blender que conviene usar ahora.

    kind: assign_role, add_cube, duplicate, scale, move, rotate, apply_scale,
    save, focus. El add-on selecciona `objects`, encuadra la vista y arranca
    la herramienta (por ejemplo Escalar restringido a `axis`); el alumno la
    termina con el ratón o escribiendo `value`.

    Motor v3: add_primitive (primitive), add_modifier (modifier), open_tab
    (tab: MODIFIER, MATERIAL, RENDER…), merge_by_distance, edit_mode,
    object_mode, add_light (light_type), add_camera, align_camera,
    set_engine, render (F12), insert_keyframe (axis), new_material y
    clear_scene. Motor 3.5: show_example (abre el ejemplo resuelto en su escena).
    """

    kind: str
    label: str
    objects: Tuple[str, ...] = ()
    axis: Optional[str] = None
    value: Optional[float] = None
    role: Optional[str] = None
    primitive: Optional[str] = None
    modifier: Optional[str] = None
    tab: Optional[str] = None
    light_type: Optional[str] = None
    option: Optional[str] = None  # set_engine: EEVEE/CYCLES; insert_keyframe: location/rotation_euler/scale


@dataclass(frozen=True)
class Guidance:
    target_id: Optional[str]
    title: str
    step_number: int
    step_total: int
    feedback: str
    tone: str = TONO_ANIMO
    why: str = ""
    instructions: Tuple[GuideInstruction, ...] = ()
    highlights: Tuple[Highlight, ...] = ()
    cues: Tuple[VisualCue, ...] = ()
    action: Optional[GuideAction] = None
    completed: bool = False
    paused: bool = False  # motor v3: un vigilante detuvo el progreso


# --- Acompañamiento ---------------------------------------------------------------

PASO_LOGRADO = "paso_logrado"
NUEVO_PASO = "nuevo_paso"
MEJORANDO = "mejorando"
RETROCESO = "retroceso"
OFRECER_AYUDA = "ofrecer_ayuda"
PRACTICA_COMPLETA = "practica_completa"
PAUSA = "pausa"  # motor v3: un vigilante detuvo el progreso
REANUDA = "reanuda"  # el vigilante volvió a cumplirse


@dataclass(frozen=True)
class Intervention:
    """Algo que el acompañante quiere decir ahora (aviso breve o diálogo)."""

    kind: str
    target_id: Optional[str]
    title: str
    text: str

    @property
    def dialog(self) -> bool:
        """True si merece una ventana; False si basta un aviso que se desvanece."""
        return self.kind in (OFRECER_AYUDA, PRACTICA_COMPLETA, PAUSA)


def guidance_to_dict(g: Optional[Guidance]) -> Optional[Dict[str, Any]]:
    """Guía → dict JSON (para la API y la plataforma)."""
    if g is None:
        return None
    return {
        "target": g.target_id,
        "title": g.title,
        "step": g.step_number,
        "steps": g.step_total,
        "feedback": g.feedback,
        "tone": g.tone,
        "why": g.why,
        "instructions": [{"text": i.text, "keys": list(i.keys)} for i in g.instructions],
        "highlights": [{"object": h.object_name, "kind": h.kind, "label": h.label} for h in g.highlights],
        "cues": [{"kind": c.kind, "label": c.label, "data": c.data} for c in g.cues],
        "action": None
        if g.action is None
        else {
            "kind": g.action.kind,
            "label": g.action.label,
            "objects": list(g.action.objects),
            "axis": g.action.axis,
            "value": g.action.value,
            "role": g.action.role,
            "primitive": g.action.primitive,
            "modifier": g.action.modifier,
            "tab": g.action.tab,
            "light_type": g.action.light_type,
            "option": g.action.option,
        },
        "paused": g.paused,
        "completed": g.completed,
    }
