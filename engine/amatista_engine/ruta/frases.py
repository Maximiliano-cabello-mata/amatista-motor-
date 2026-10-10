"""Lo que el instructor dice (motor 4): frases cortas, sin decimales y sin regaños.

Psicología aplicada, en concreto:

- Una cosa a la vez: cada frase dice qué ves y qué haces, en ese orden.
- Sin medidas en los niveles 1 a 3 (contar piezas sí: «Llevas 3 de 8»):
  «flota un poquito» se entiende en la vista 3D; «Z = 0.23, debe quedar
  en 0» obliga a leer el panel N.
- Error = «casi»: nunca «mal» ni «incorrecto». El error es parte de aprender.
- Logros pequeños y frecuentes: cada misión cumplida se celebra (efecto de
  progreso), con frases que varían para que no suenen a robot.
- Autonomía: lo que el alumno hizo antes de tiempo se reconoce («¡Ya lo
  tenías!») en vez de obligarlo a repetirlo.
"""
from __future__ import annotations

from typing import Optional

from ..models import PracticeDefinition, TargetDefinition, ValidationResult

# Se eligen por el número de la misión: varían sin azar (las pruebas dan siempre lo mismo).
LOGROS = (
    "¡Misión cumplida!",
    "¡Eso es!",
    "¡Perfecto!",
    "¡Muy bien!",
    "¡Así se hace!",
    "¡Lo lograste!",
    "¡Genial!",
)
LOGRO_SIN_PISTAS = "¡Y sin pistas!"
YA_LO_TENIAS = "¡Ya lo tenías!"


def logro(numero: int, sin_pistas: bool = False) -> str:
    frase = LOGROS[(max(1, numero) - 1) % len(LOGROS)]
    return f"{frase} {LOGRO_SIN_PISTAS}" if sin_pistas else frase


def _primero(detalles: dict) -> dict:
    fallan = detalles.get("failed") or []
    return fallan[0] if fallan and isinstance(fallan[0], dict) else {}


def _nombre(practica: Optional[PracticeDefinition], target: TargetDefinition, clave: str = "role") -> str:
    rol = (target.params or {}).get(clave)
    if practica is not None and rol:
        return practica.role_label(rol)
    return str(rol or "la pieza")


def frase_amable(practica: Optional[PracticeDefinition], target: TargetDefinition,
                 resultado: Optional[ValidationResult], nivel: int) -> str:
    """El mensaje del validador dicho como lo diría un instructor (vacío = usar el del motor).

    Solo cambia los mensajes de medidas de los niveles 1 a 3; en 4 y 5 los
    números son parte de lo que se aprende y se dejan como están.
    """
    if resultado is None or resultado.passed is not False or nivel >= 4:
        return ""
    if target.messages.get("fail"):
        return ""  # el autor ya lo escribió a su manera
    d = resultado.details or {}
    f = _primero(d)
    objeto = f.get("object") or ""
    quien = f"«{objeto}»" if objeto else _nombre(practica, target)
    v = target.validator
    if v in ("object.count", "role.count") and (target.params or {}).get("role"):
        encontrados = d.get("found")
        esperado = d.get("expected")
        esperado = esperado.get("min") if isinstance(esperado, dict) else esperado
        if isinstance(encontrados, int) and isinstance(esperado, int) and encontrados < esperado:
            que = _nombre(practica, target)
            if encontrados == 0:
                return f"Todavía no hay ninguna pieza «{que}». ¡Agrega la primera!"
            faltan = esperado - encontrados
            return f"Llevas {encontrados} de {esperado} «{que}». ¡Falta{'n' if faltan > 1 else ''} {faltan}!"
    if v == "spatial.grounded":
        if f.get("reason") == "hundido":
            return f"{quien} se hunde en el suelo. Súbelo con G y luego Z hasta que apenas toque la cuadrícula."
        if f:
            return f"{quien} flota un poquito. Míralo de frente (1) y bájalo con G y luego Z hasta el suelo."
    if v == "spatial.touching" and f:
        ref = _nombre(practica, target, "reference_role")
        return f"{quien} todavía no toca {ref}. Acércalo con G hasta que se peguen (casi tocando ya cuenta)."
    if v == "spatial.on_top" and f:
        ref = _nombre(practica, target, "reference_role")
        if f.get("reason") == "lado":
            return f"{quien} está junto a {ref}, no encima. Míralo desde arriba (7) y muévelo con G."
        if f.get("reason") == "flota":
            return f"{quien} flota sobre {ref}. Bájalo con G y luego Z hasta que se apoye."
        return f"{quien} se hunde en {ref}. Súbelo con G y luego Z hasta que se apoye."
    if v == "shape.proportion" and f:
        eje = str((target.params or {}).get("axis", "")).upper() or "su eje largo"
        return f"{quien} se ve muy parejo. Estíralo a lo largo: S y luego {eje}, y mueve el ratón."
    if v == "shape.thinnest_axis" and f:
        return f"{quien} todavía se ve grueso. Aplánalo con S y el eje que quieras adelgazar."
    return ""
