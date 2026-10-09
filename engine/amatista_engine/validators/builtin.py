"""Catálogo de validadores incluidos en el motor.

Cada uno se registra con su etiqueta en español, sus parámetros y los
eventos que lo invalidan. El constructor de objetivos del modo
desarrollador muestra estas etiquetas como plantillas («Cantidad por rol»,
«Dimensión»...). Agregar una capacidad nueva = una función + un registro
aquí; ninguna práctica necesita código propio.
"""
from __future__ import annotations

from ..registry import ParamSpec as P
from ..registry import ValidatorRegistry
from . import (animation, example, figure, lighting, logic, materials, mesh, objects, recognize, scene, shape, silhouette,
               spatial, transforms)

# Parámetros comunes del selector de objetos (validators/base.py).
SELECTOR = (
    P("role", "role", "Rol"),
    P("name", "text", "Nombre exacto"),
    P("name_prefix", "text", "Nombre empieza con"),
    P("type", "object_type", "Tipo de objeto"),
    P("primitive", "primitive", "Primitiva (cube, cylinder…)"),
)
CANTIDAD = (
    P("equals", "int", "Exactamente"),
    P("min", "int", "Mínimo"),
    P("max", "int", "Máximo"),
)
RANGO = (P("axis", "axis", "Eje", default="z"), P("min", "float", "Mínimo"), P("max", "float", "Máximo"))

TRANSFORMACION = ("OBJECT_TRANSFORM", "OBJECT_ADDED", "ROLE_CHANGED")


def register_builtin_validators(registry: ValidatorRegistry) -> None:
    r = registry.register
    # --- Objetos y roles ---
    r(
        "object.exists", objects.object_exists, label="Objeto existe", category="objetos",
        description="Hay al menos un objeto que cumple el selector.",
        params=SELECTOR, watch=("OBJECT_ADDED", "ROLE_CHANGED"), selects=True,
    )
    r(
        "object.count", objects.object_count, label="Cantidad de objetos", category="objetos",
        description="Cuenta los objetos que cumplen el selector.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_ADDED", "ROLE_CHANGED"), selects=True,
    )
    r(
        "role.exists", objects.role_exists, label="Rol asignado", category="roles",
        description="Algún objeto tiene el rol educativo.",
        params=(P("role", "role", "Rol", required=True),), watch=("OBJECT_ADDED", "ROLE_CHANGED"),
    )
    r(
        "role.count", objects.role_count, label="Cantidad por rol", category="roles",
        description="Cantidad de objetos con un rol (exactamente, mínimo o máximo).",
        params=(P("role", "role", "Rol", required=True),) + CANTIDAD, watch=("OBJECT_ADDED", "ROLE_CHANGED"),
    )
    # --- Transformaciones ---
    r(
        "dimension.range", transforms.dimension_range, label="Dimensión", category="transformaciones",
        description="La medida en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    r(
        "object.position", transforms.object_position, label="Posición", category="transformaciones",
        description="La ubicación en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION, selects=True,
    )
    r(
        "object.rotation", transforms.object_rotation, label="Rotación", category="transformaciones",
        description="El giro (en grados) en un eje queda entre un mínimo y un máximo.",
        params=SELECTOR + RANGO, watch=TRANSFORMACION, selects=True,
    )
    r(
        "transform.scale_applied", transforms.scale_applied, label="Escala aplicada", category="transformaciones",
        description="La escala del objeto es 1 en los tres ejes (Ctrl+A › Escala).",
        params=SELECTOR, watch=TRANSFORMACION, selects=True,
    )
    r(
        "spatial.below", transforms.below, label="Debajo de", category="relaciones",
        description="Los objetos quedan debajo de otro (por ejemplo, patas bajo la cubierta).",
        params=SELECTOR + (
            P("reference_role", "role", "Rol de referencia", required=True),
            P("tolerance", "float", "Tolerancia", default=0.02),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Malla, modificadores y materiales ---
    r(
        "mesh.vertex_count", mesh.vertex_count, label="Vértices", category="malla",
        description="Cantidad de vértices de la malla.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "mesh.face_count", mesh.face_count, label="Caras", category="malla",
        description="Cantidad de caras de la malla.",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "modifier.exists", mesh.modifier_exists, label="Modificador", category="malla",
        description="Los objetos tienen un modificador (BEVEL, MIRROR, ARRAY...).",
        params=SELECTOR + (P("modifier", "modifier", "Modificador", required=True),),
        watch=("OBJECT_MODIFIER",), selects=True,
    )
    r(
        "material.exists", mesh.material_exists, label="Material", category="materiales",
        description="Los objetos tienen material asignado.",
        params=SELECTOR + (P("material", "text", "Nombre del material contiene"),),
        watch=("OBJECT_DATA",), selects=True,
    )
    # --- Escena y archivo ---
    r(
        "collection.contains", scene.collection_contains, label="Colección", category="organización",
        description="Una colección contiene objetos (opcionalmente de un rol).",
        params=(P("collection", "collection", "Colección", required=True), P("role", "role", "Rol")) + CANTIDAD,
        watch=("OBJECT_ADDED", "OBJECT_DATA", "ROLE_CHANGED"),
    )
    r(
        "scene.camera_exists", scene.camera_exists, label="Cámara", category="escena",
        description="La escena tiene cámara.", params=CANTIDAD, watch=("OBJECT_ADDED",),
    )
    r(
        "scene.light_exists", scene.light_exists, label="Luz", category="escena",
        description="La escena tiene luces (de un tipo, si se indica: AREA, SUN, POINT, SPOT).",
        params=CANTIDAD + (P("light_type", "light_type", "Tipo de luz"),), watch=("OBJECT_ADDED", "OBJECT_DATA"),
    )
    r(
        "file.saved", scene.file_saved, label="Archivo guardado", category="archivo",
        description="El .blend está guardado y sin cambios pendientes.", watch=("FILE_SAVED", "OBJECT_DATA"),
    )
    r(
        "file.named", scene.file_named, label="Nombre del archivo", category="archivo",
        description="El nombre del .blend incluye un texto.",
        params=(P("contains", "text", "Contiene", required=True),), watch=("FILE_SAVED",),
    )
    _registrar_v3(registry)


def _registrar_v3(registry: ValidatorRegistry) -> None:
    """Validadores del motor v3 (plan de estudios de Blender, docs/motor/etapas/etapa-3.md)."""
    r = registry.register
    # --- Forma y ensamblaje (módulo 1: tren de juguete) ---
    r(
        "shape.thinnest_axis", shape.thinnest_axis, label="Eje más delgado", category="forma",
        description="El lado más delgado del objeto está en un eje (x, y, z u horizontal): ruedas de pie, tablas planas.",
        params=SELECTOR + (P("axis", "text", "Eje (x, y, z, horizontal)", default="horizontal"),
                           P("max_ratio", "float", "Delgadez máxima", default=0.6)),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    r(
        "shape.proportion", shape.proportion, label="Proporción", category="forma",
        description="El objeto mide en un eje al menos N veces su otra medida mayor (alargado).",
        params=SELECTOR + (P("axis", "axis", "Eje", default="z"), P("min_ratio", "float", "Veces como mínimo", default=2.0),
                           P("max_ratio", "float", "Veces como máximo")),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    r(
        "spatial.grounded", spatial.grounded, label="Apoyado en el suelo", category="relaciones",
        description="La parte más baja del objeto queda a una altura (0 = el suelo).",
        params=SELECTOR + (P("height", "float", "Altura", default=0.0), P("tolerance", "float", "Tolerancia", default=0.05)),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    r(
        "spatial.touching", spatial.touching, label="Toca a", category="relaciones",
        description="Cada objeto toca (por su caja) al menos un objeto de referencia: piezas ensambladas.",
        params=SELECTOR + (
            P("reference_role", "role", "Rol de referencia"),
            P("reference", "text", "Nombre de referencia"),
            P("reference_primitive", "primitive", "Primitiva de referencia"),
            P("tolerance", "float", "Tolerancia", default=0.05),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Malla y modificadores (módulos 2 y 3) ---
    r(
        "mesh.no_duplicates", mesh.no_duplicates, label="Malla sin vértices encimados", category="malla",
        description="No hay vértices duplicados (E y cancelar). Úsalo como vigilante con el arreglo merge_by_distance.",
        params=SELECTOR + (P("max", "int", "Máximo permitido", default=0),), watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "mesh.one_side", mesh.one_side, label="Solo una mitad", category="malla",
        description="La malla base vive de un solo lado del eje: el modificador Espejo dibuja la otra mitad.",
        params=SELECTOR + (P("axis", "axis", "Eje", default="x"), P("side", "text", "Lado (negative, positive, any)"),
                           P("tolerance", "int", "Vértices de tolerancia", default=0)),
        watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "modifier.configured", mesh.modifier_configured, label="Modificador configurado", category="malla",
        description="Modificador con sus ajustes: eje del espejo, niveles de subdivisión y encendido.",
        params=SELECTOR + (
            P("modifier", "modifier", "Modificador", required=True),
            P("axis", "axis", "Eje del espejo"),
            P("only_axis", "bool", "Solo ese eje"),
            P("min_levels", "int", "Niveles mínimos"),
            P("max_levels", "int", "Niveles máximos"),
            P("enabled", "bool", "Encendido", default=True),
        ),
        watch=("OBJECT_MODIFIER",), selects=True,
    )
    # --- Materiales (módulo 4) ---
    r(
        "material.distinct", materials.distinct, label="Materiales distintos", category="materiales",
        description="Cantidad de materiales distintos que pintan caras (equals, min, max).",
        params=SELECTOR + CANTIDAD, watch=("OBJECT_DATA",), selects=True,
    )
    r(
        "material.matches", materials.matches, label="Material con propiedades", category="materiales",
        description="Hay materiales con Metálico, Rugosidad, Transmisión o Alfa en un rango (metal brillante, vidrio…).",
        params=SELECTOR + (
            P("metallic_min", "float", "Metálico mínimo"), P("metallic_max", "float", "Metálico máximo"),
            P("roughness_min", "float", "Rugosidad mínima"), P("roughness_max", "float", "Rugosidad máxima"),
            P("transmission_min", "float", "Transmisión mínima"), P("alpha_max", "float", "Alfa máximo"),
            P("count", "int", "Cuántos materiales", default=1), P("label", "text", "Nombre para el alumno"),
        ),
        watch=("OBJECT_DATA",), selects=True,
    )
    # --- Luces, cámara y render (módulo 5) ---
    luces = ("OBJECT_ADDED", "OBJECT_TRANSFORM", "OBJECT_DATA")
    r(
        "camera.active", lighting.camera_active, label="Cámara activa", category="escena",
        description="La escena tiene una cámara activa (la que usa F12).", watch=("OBJECT_ADDED", "OBJECT_DATA"),
    )
    r(
        "camera.frames", lighting.camera_frames, label="Encuadre", category="escena",
        description="La cámara mira al modelo (selector o todas las mallas).",
        params=SELECTOR + (P("margin", "float", "Margen del encuadre", default=1.0),), watch=luces, selects=True,
    )
    r(
        "light.three_point", lighting.three_point, label="Iluminación de tres puntos", category="escena",
        description="Principal y relleno delante (uno a cada lado) y contraluz detrás, vistos desde la cámara.",
        params=SELECTOR + (P("fill_weaker", "bool", "El relleno es más suave", default=True),), watch=luces, selects=True,
    )
    r(
        "render.engine", lighting.render_engine, label="Motor de render", category="escena",
        description="El motor de render es EEVEE, Cycles o Workbench.",
        params=(P("engine", "text", "Motor (EEVEE, CYCLES)", default="EEVEE"),), watch=("OBJECT_DATA",),
    )
    r(
        "render.done", lighting.render_done, label="Render hecho (F12)", category="escena",
        description="El alumno ya hizo al menos un render final con F12.",
        params=(P("min", "int", "Renders mínimos", default=1),), watch=("OBJECT_DATA",),
    )
    # --- Animación (módulo 6) ---
    anim = ("OBJECT_DATA", "OBJECT_TRANSFORM")
    r(
        "animation.keyframes", animation.keyframes, label="Fotogramas clave", category="animación",
        description="El objeto tiene al menos N fotogramas clave en una propiedad y un eje.",
        params=SELECTOR + (P("property", "text", "Propiedad (location, rotation_euler, scale)", default="location"),
                           P("axis", "axis", "Eje", default="z"), P("min", "int", "Mínimo", default=2)),
        watch=anim, selects=True,
    )
    r(
        "animation.varies", animation.varies, label="La animación cambia", category="animación",
        description="Los valores cambian en el tiempo: diferencia mínima, punto más bajo/alto y rebote.",
        params=SELECTOR + (
            P("property", "text", "Propiedad", default="location"), P("axis", "axis", "Eje", default="z"),
            P("min_delta", "float", "Cambio mínimo"), P("low_max", "float", "El más bajo llega a"),
            P("high_min", "float", "El más alto llega a"), P("bounce", "bool", "Rebota"),
            P("ground", "bool", "Toca el suelo"), P("tolerance", "float", "Tolerancia", default=0.15),
        ),
        watch=anim, selects=True,
    )
    r(
        "spatial.on_top", spatial.on_top, label="Encima de", category="relaciones",
        description="Cada objeto descansa encima de uno de referencia (un techo sobre su casa), no a un lado.",
        params=SELECTOR + (
            P("reference_role", "role", "Rol de referencia"),
            P("reference", "text", "Nombre de referencia"),
            P("reference_primitive", "primitive", "Primitiva de referencia"),
            P("tolerance", "float", "Holgura (parte de la altura del objeto)", default=0.25),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Figura con sentido (motor 3.3, docs/motor/referencia/10_modelo_de_referencia.md) ---
    r(
        "figure.resembles", figure.resembles, label="La figura se parece al modelo", category="forma",
        description=("Compara la figura con el modelo de referencia de la práctica («reference»): mismas piezas, "
                     "tamaños y lugares parecidos (±tolerancia) y proporciones de la figura. No pide medidas exactas; "
                     "acepta la figura más grande o chica, girada o en espejo."),
        params=(
            P("tolerance", "float", "Holgura de medidas (0.35 = ±35 %)", default=0.35),
            P("min_score", "float", "Parecido mínimo (0 a 1)", default=0.7),
            P("scale_range", "float", "Veces más grande o chica permitido", default=2.5),
            # Los pone el cargador desde «reference» y «roles»; no se escriben a mano.
            P("parts", "reference", "Piezas del modelo (de «reference»)"),
            P("labels", "reference", "Nombres de los roles (de «roles»)"),
            P("flexible", "reference", "Grupos con cantidad libre (de «reference»)"),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",),
    )
    # --- Motor 3.4: el motor reconoce la figura (figures/reconocer.py) ---
    r(
        "figure.recognize", recognize.recognize, label="Amatista reconoce la figura", category="forma",
        description=("Reconoce la figura del modelo de referencia sin roles: deduce qué es cada pieza por su forma, "
                     "revisa que las piezas se apoyen, se toquen y vayan a los lados como en el modelo, que nada "
                     "flote y dice qué figura parece. La exigencia sube con el nivel (forma identificable en el 1, "
                     "medidas exactas en el 5); las piezas de adorno no restan."),
        params=(
            P("strictness", "text", "Exigencia (forma, proporcion, cercana, medidas, exacta; vacío = la del nivel)"),
            P("min_score", "float", "Parecido mínimo (0 a 1; vacío = el de la exigencia)"),
            # Los pone el cargador desde «reference», «roles» y «level»; no se escriben a mano.
            P("parts", "reference", "Piezas del modelo (de «reference»)"),
            P("labels", "reference", "Nombres de los roles (de «roles»)"),
            P("flexible", "reference", "Grupos con cantidad libre (de «reference»)"),
            P("level", "reference", "Nivel de la práctica (de «level»)"),
            P("title", "reference", "Nombre de la figura (de «reference.title»)"),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",),
    )
    # --- Motor 3.5: la silueta de una figura hecha en una sola malla (figures/silueta.py) ---
    r(
        "figure.silhouette", silhouette.silhouette, label="Amatista reconoce la silueta", category="forma",
        description=("Para figuras modeladas en una sola malla (una espada): corta la malla en rebanadas a lo largo y "
                     "compara su silueta con la del modelo parte por parte (pomo, mango, guarda, hoja, punta). Dice qué "
                     "parte falta o no tiene la medida y con qué tecla se arregla, y deja una lista de revisión. Lo que "
                     "da sentido a la figura (una parte mucho más ancha que su vecina, la punta que se afila) se exige "
                     "en todos los niveles; las medidas, según el nivel."),
        params=SELECTOR + (
            P("strictness", "text", "Exigencia (forma, proporcion, cercana, medidas, exacta; vacío = la del nivel)"),
            # Los pone el cargador desde «reference» y «level»; no se escriben a mano.
            P("parts", "reference", "Piezas del modelo (de «reference»)"),
            P("level", "reference", "Nivel de la práctica (de «level»)"),
            P("title", "reference", "Nombre de la figura (de «reference.title»)"),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Motor 3.5: la revisión autónoma contra el ejemplo resuelto (ejemplo/) ---
    r(
        "example.matches", example.matches, label="Coincide con el ejemplo", category="ejemplo",
        description=("Revisa la escena del alumno contra el ejemplo resuelto de la práctica («example»), aspecto por "
                     "aspecto: la figura (o su silueta), el trabajo en la malla, los modificadores, los materiales, las "
                     "colecciones, las luces, la cámara, la animación, el render y el archivo. Solo revisa lo que el "
                     "ejemplo tiene y deja una lista con qué coincide y cómo hacer lo que falta. El cargador lo agrega "
                     "al final de toda práctica con ejemplo."),
        params=(
            P("aspects", "reference", "Aspectos que revisa este paso (vacío = todos los del ejemplo)"),
            P("strictness", "text", "Exigencia (forma, proporcion, cercana, medidas, exacta; vacío = la del nivel)"),
            # Los pone el cargador desde «example», «reference», «roles» y «level»; no se escriben a mano.
            P("steps", "reference", "Pasos del ejemplo (de «example.steps»)"),
            P("check", "reference", "Aspectos de la práctica (de «example.check»)"),
            P("parts", "reference", "Piezas del modelo (de «reference»)"),
            P("labels", "reference", "Nombres de los roles (de «roles»)"),
            P("flexible", "reference", "Grupos con cantidad libre (de «reference»)"),
            P("level", "reference", "Nivel de la práctica (de «level»)"),
            P("title", "reference", "Nombre de la figura (de «example.title»)"),
        ),
    )
    r(
        "dimension.approx", figure.approx_dimension, label="Medida aproximada", category="transformaciones",
        description="Una medida queda CERCA de un valor (±tolerancia), en un eje o en su lado más largo o más corto.",
        params=SELECTOR + (
            P("axis", "text", "Eje (x, y, z, largest, smallest)", default="largest"),
            P("value", "float", "Valor aproximado", required=True),
            P("tolerance", "float", "Holgura (0.35 = ±35 %)", default=0.35),
        ),
        watch=TRANSFORMACION + ("OBJECT_DATA",), selects=True,
    )
    # --- Lógica ---
    r(
        "logic.any", logic.make_any(registry), label="Una de varias opciones", category="lógica",
        description="Pasa si se cumple cualquiera de las opciones (cada una es un validador con sus parámetros).",
        params=(P("options", "options", "Opciones", required=True),),
    )


# Compatibilidad con el prototipo v0.1 (importaba estas funciones de aquí).
file_saved = scene.file_saved
object_exists = objects.object_exists
role_count = objects.role_count
dimension_range = transforms.dimension_range
