"""Datos del motor: escena normalizada, práctica, resultados y reporte.

Todo son dataclasses inmutables de Python puro (sin bpy): el mismo código
corre dentro de Blender, en las pruebas y en el servidor FastAPI.

Motor v3: la escena trae también modificadores con sus ajustes, materiales
(Principled BSDF), luces, cámaras, animación, la salud de la malla y el
render; la práctica trae píldoras de teoría, vigilantes y su lugar en el
curso. Todo campo nuevo es opcional: una foto o una práctica de la v2 sigue
siendo válida.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

Vector = Tuple[float, float, float]
Color = Tuple[float, float, float, float]


@dataclass(frozen=True)
class ModifierInfo:
    """Un modificador con lo que importa para enseñar (motor v3).

    axes: ejes activos de MIRROR (X, Y, Z); levels: niveles de SUBSURF en la
    vista; enabled: si se ve en la vista 3D (el «ojo» del modificador).
    """

    type: str
    name: str = ""
    axes: Tuple[bool, bool, bool] = (False, False, False)
    levels: Optional[int] = None
    enabled: bool = True


@dataclass(frozen=True)
class MaterialInfo:
    """Lo que el alumno mueve del Principled BSDF: color, metálico, rugosidad,
    transmisión (vidrio) y alfa (transparencia)."""

    name: str
    base_color: Color = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5
    transmission: float = 0.0
    alpha: float = 1.0


@dataclass(frozen=True)
class AnimationChannel:
    """Fotogramas clave de una propiedad: location, rotation_euler o scale y su eje."""

    path: str
    index: int
    keys: Tuple[Tuple[float, float], ...] = ()  # (fotograma, valor)

    @property
    def values(self) -> Tuple[float, ...]:
        return tuple(v for _, v in self.keys)


@dataclass(frozen=True)
class SceneObject:
    """Un objeto de la escena tal como lo entiende Amatista.

    bbox_min y bbox_max son la caja envolvente en coordenadas del mundo. Si
    no se capturaron (pruebas, versiones viejas del add-on) se calculan con
    location ± dimensions / 2, que vale para primitivas con el origen al centro.
    """

    name: str
    object_type: str
    roles: Tuple[str, ...] = ()
    location: Vector = (0.0, 0.0, 0.0)
    rotation: Vector = (0.0, 0.0, 0.0)  # radianes (Euler XYZ)
    scale: Vector = (1.0, 1.0, 1.0)
    dimensions: Vector = (0.0, 0.0, 0.0)
    modifiers: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()
    materials: Tuple[str, ...] = ()
    collections: Tuple[str, ...] = ()
    vertices: Optional[int] = None
    faces: Optional[int] = None
    bbox_min: Optional[Vector] = None
    bbox_max: Optional[Vector] = None
    parent: Optional[str] = None
    # --- Motor v3 (todos opcionales) ---
    data_name: Optional[str] = None  # nombre de la malla/luz/cámara: «Cylinder.001»
    modifier_details: Tuple[ModifierInfo, ...] = ()
    material_details: Tuple[MaterialInfo, ...] = ()
    materials_used: Optional[Tuple[str, ...]] = None  # materiales que de verdad pintan caras
    light_type: Optional[str] = None  # POINT, SUN, SPOT, AREA
    light_energy: Optional[float] = None
    camera_angle: Optional[float] = None  # campo de visión horizontal en radianes
    forward: Optional[Vector] = None  # hacia dónde mira (cámaras y luces), en el mundo
    duplicate_vertices: Optional[int] = None  # vértices encimados (E y luego cancelar)
    side_counts: Optional[Tuple[Tuple[int, int], ...]] = None  # vértices (-, +) por eje local
    animation: Tuple[AnimationChannel, ...] = ()

    @property
    def role(self) -> Optional[str]:
        return self.roles[0] if self.roles else None

    def modifier(self, tipo: str) -> Optional[ModifierInfo]:
        tipo = tipo.upper()
        return next((m for m in self.modifier_details if m.type == tipo), None)

    def channel(self, path: str, index: int) -> Optional[AnimationChannel]:
        return next((c for c in self.animation if c.path == path and c.index == index), None)

    @property
    def primitive(self) -> str:
        """«cylinder» para Cylinder.003: de qué primitiva salió la malla."""
        base = (self.data_name or "").split(".")[0].strip().lower()
        return base

    def caja(self) -> Tuple[Vector, Vector]:
        """(mínimo, máximo) de la caja envolvente en el mundo."""
        if self.bbox_min is not None and self.bbox_max is not None:
            return self.bbox_min, self.bbox_max
        medio = tuple(d / 2.0 for d in self.dimensions)
        return (
            tuple(c - m for c, m in zip(self.location, medio)),
            tuple(c + m for c, m in zip(self.location, medio)),
        )


@dataclass(frozen=True)
class SceneState:
    blender_version: str
    file_path: str
    file_saved: bool
    objects: Tuple[SceneObject, ...] = ()
    mode: str = "OBJECT"
    # --- Motor v3 ---
    active_object: Optional[str] = None
    selected: Tuple[str, ...] = ()
    active_camera: Optional[str] = None
    render_engine: str = ""
    renders: int = 0  # renders terminados (F12) desde que se abrió la práctica
    frame_range: Tuple[int, int] = (1, 250)

    def objects_with_role(self, role: str) -> Tuple[SceneObject, ...]:
        return tuple(obj for obj in self.objects if role in obj.roles)

    def object_by_name(self, name: str) -> Optional[SceneObject]:
        return next((obj for obj in self.objects if obj.name == name), None)

    @property
    def file_name(self) -> str:
        return self.file_path.replace("\\", "/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Hint:
    level: int
    text: str


@dataclass(frozen=True)
class GuideStepDefinition:
    """Micro paso escrito por el autor: texto y teclas («S», «Z», «0.1»)."""

    text: str
    keys: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetGuide:
    """Bloque opcional «guide» de un objetivo (etapa 2 del motor).

    why: por qué importa el paso (lo muestra la tarjeta guía).
    steps: micro pasos; si faltan, el motor los genera según el validador.
    """

    why: str = ""
    steps: Tuple[GuideStepDefinition, ...] = ()


@dataclass(frozen=True)
class FixDefinition:
    """Arreglo que ofrece un vigilante: la acción de «Hazlo conmigo» y su texto."""

    action: str
    label: str = ""


@dataclass(frozen=True)
class TargetDefinition:
    id: str
    validator: str
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    title: str = ""
    requires: Tuple[str, ...] = ()
    tip: str = ""
    hints: Tuple[Hint, ...] = ()
    messages: Dict[str, str] = field(default_factory=dict)
    optional: bool = False
    guide: Optional[TargetGuide] = None
    fix: Optional[FixDefinition] = None  # solo vigilantes (guards)


@dataclass(frozen=True)
class PillCheck:
    """Pregunta corta de una píldora (repaso espaciado)."""

    question: str
    options: Tuple[str, ...]
    answer: int


@dataclass(frozen=True)
class PillTrigger:
    """Cuándo aparece una píldora.

    on: start (al abrir), target (cuando ese objetivo es el actual), mode
    (al entrar a un modo: EDIT, OBJECT, SCULPT...), selection (al seleccionar
    un objeto), tool (al detectar una herramienta del catálogo), guard
    (cuando un vigilante pausa el progreso), complete (al terminar).
    """

    on: str = "start"
    target: str = ""
    mode: str = ""
    tool: str = ""


@dataclass(frozen=True)
class PillDefinition:
    """Píldora de teoría: una idea, pocas palabras y algo que ver en Blender.

    visual: axes (ejes X rojo, Y verde, Z azul sobre la vista 3D), keys
    (teclas grandes junto al objeto), tab:<PESTAÑA> (abre y señala una
    pestaña de Propiedades: MODIFIER, MATERIAL, RENDER, OUTPUT, DATA,
    OBJECT), mode (Objeto vs Edición), image:<archivo> o vacío.
    """

    id: str
    title: str
    text: str
    keys: Tuple[str, ...] = ()
    visual: str = ""
    trigger: PillTrigger = field(default_factory=PillTrigger)
    once: bool = True
    check: Optional[PillCheck] = None


@dataclass(frozen=True)
class CoursePlace:
    """Dónde vive la práctica en la plataforma (motor v3)."""

    course: str = ""
    module: int = 0
    lesson: str = ""
    next: str = ""  # práctica que se desbloquea al terminar


@dataclass(frozen=True)
class ReferencePart:
    """Una pieza del modelo de referencia (motor 3.3).

    size son las medidas del objeto (como la «Dimensión» de Blender, antes de
    girarlo) y rotation va en GRADOS. join junta varias piezas en un solo
    objeto (una espada modelada en una sola malla). Lo usan figure.resembles
    (comparar la figura del alumno) y engine/herramientas/referencias.py
    (dibujar la imagen y el plano de referencia).
    """

    primitive: str
    size: Tuple[float, float, float]
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    role: str = ""
    name: str = ""
    color: str = ""
    join: str = ""
    segments: int = 0
    material: Dict[str, Any] = field(default_factory=dict)
    compare: bool = True  # False: solo decora la imagen (suelo, fantasmas de una animación)

    @property
    def group(self) -> str:
        """Con qué objetos del alumno se compara: su rol o, si no tiene, su primitiva."""
        return self.role or self.primitive


@dataclass(frozen=True)
class ReferenceModel:
    """Cómo debe verse la figura terminada: piezas, holgura y textos para el alumno."""

    parts: Tuple[ReferencePart, ...] = ()
    title: str = ""
    description: str = ""
    tolerance: float = 0.35  # ±35 % en las medidas: «medianamente cercanas, no exactas»
    objects: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # modificadores por objeto unido
    camera: Dict[str, Any] = field(default_factory=dict)
    flexible: Tuple[str, ...] = ()  # grupos donde la cantidad es libre (2 o 4 pilares, 3 o 5 casas)
    lights: Tuple[Dict[str, Any], ...] = ()  # luces para la imagen (tres puntos); no se comparan
    # --- Motor 3.4: reconocimiento de figuras ---
    strictness: str = ""  # forma | proporcion | cercana | medidas | exacta ("" = la del nivel)
    auto_roles: Optional[bool] = None  # deducir roles por la forma (None = sí, si la práctica usa figure.recognize)

    @property
    def compared(self) -> Tuple[ReferencePart, ...]:
        return tuple(p for p in self.parts if p.compare)


@dataclass(frozen=True)
class StarterDefinition:
    """Cómo empieza la escena: vacía, con lo que hay o armada por el add-on.

    build: nombre de un escenario del add-on (nave_basica, estudio_foto,
    pelota_y_suelo); from_practice: práctica cuyo archivo conviene reabrir.
    """

    scene: str = "keep"  # keep | empty
    build: str = ""
    from_practice: str = ""
    note: str = ""


@dataclass(frozen=True)
class RoleDefinition:
    id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class PracticeDefinition:
    schema: str
    id: str
    title: str
    level: int
    targets: Tuple[TargetDefinition, ...]
    version: int = 1
    description: str = ""
    intro: str = ""
    completion: str = ""
    estimated_minutes: Optional[int] = None
    blender_min: Optional[str] = None
    skills: Tuple[str, ...] = ()
    roles: Tuple[RoleDefinition, ...] = ()
    tags: Tuple[str, ...] = ()
    allowed_tools: Tuple[str, ...] = ()
    warn_tools: Tuple[str, ...] = ()
    # --- Motor v3 (amatista.practice/2) ---
    guards: Tuple[TargetDefinition, ...] = ()
    pills: Tuple[PillDefinition, ...] = ()
    review: Tuple[str, ...] = ()  # «practica#pildora» de prácticas anteriores
    place: CoursePlace = field(default_factory=CoursePlace)
    starter: StarterDefinition = field(default_factory=StarterDefinition)
    # --- Motor 3.3: modelo de referencia (cómo debe verse la figura) ---
    reference: Optional[ReferenceModel] = None

    def target(self, target_id: str) -> Optional[TargetDefinition]:
        return next((t for t in self.targets if t.id == target_id), None)

    def guard(self, guard_id: str) -> Optional[TargetDefinition]:
        return next((g for g in self.guards if g.id == guard_id), None)

    def pill(self, pill_id: str) -> Optional[PillDefinition]:
        return next((p for p in self.pills if p.id == pill_id), None)

    def role_label(self, role_id: str) -> str:
        rol = next((r for r in self.roles if r.id == role_id), None)
        return rol.label if rol else role_id

    @property
    def infers_roles(self) -> bool:
        """Motor 3.4: ¿el motor deduce los roles por la forma (el alumno no los pone)?

        reference.autoRoles lo decide; si falta, solo donde el motor reconoce
        la figura (figure.recognize).
        """
        if self.reference is None or not self.roles:
            return False
        if self.reference.auto_roles is not None:
            return bool(self.reference.auto_roles)
        return any(t.validator == "figure.recognize" for t in self.targets)

    def reference_primitive(self, role_id: str) -> str:
        """La primitiva con que el modelo arma ese rol («cube», «cylinder»…), o vacío."""
        if self.reference is None:
            return ""
        return next((p.primitive for p in self.reference.parts if p.role == role_id and p.primitive), "")


@dataclass(frozen=True)
class ValidationResult:
    target_id: str
    validator: str
    passed: Optional[bool]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# Estado de cada objetivo en el recorrido del alumno (pedagogy/graph.py).
COMPLETADO = "completado"
ACTUAL = "actual"
PENDIENTE = "pendiente"
BLOQUEADO = "bloqueado"
DESCONOCIDO = "desconocido"


@dataclass(frozen=True)
class TargetStatus:
    target_id: str
    title: str
    status: str
    passed: Optional[bool]
    message: str
    weight: float
    optional: bool = False
    hints_available: int = 0


@dataclass(frozen=True)
class ToolWarning:
    tool_id: str
    tool_name: str
    level: int
    message: str


@dataclass(frozen=True)
class EvaluationReport:
    practice_id: str
    practice_title: str
    progress: float
    completed: bool
    results: Tuple[ValidationResult, ...]
    steps: Tuple[TargetStatus, ...] = ()
    current_target_id: Optional[str] = None
    tool_warnings: Tuple[ToolWarning, ...] = ()
    tools_used: Tuple[str, ...] = ()
    needs_update: bool = False
    # --- Motor 3.4: roles que el motor dedujo por la forma ({objeto: rol}) ---
    inferred_roles: Tuple[Tuple[str, str], ...] = ()
    # --- Motor v3: vigilantes ---
    guards: Tuple[ValidationResult, ...] = ()
    paused_by: Optional[str] = None  # id del vigilante que pausa el progreso

    @property
    def paused(self) -> bool:
        return self.paused_by is not None

    def result(self, target_id: str) -> Optional[ValidationResult]:
        return next((r for r in self.results if r.target_id == target_id), None)

    @property
    def step_number(self) -> int:
        """Número (1..n) del objetivo actual; n+1 si ya no queda ninguno."""
        for indice, paso in enumerate(self.steps, start=1):
            if paso.target_id == self.current_target_id:
                return indice
        return len(self.steps) + 1 if self.steps else 0
