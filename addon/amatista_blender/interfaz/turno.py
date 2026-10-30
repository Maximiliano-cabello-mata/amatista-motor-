"""Una sola tarjeta a la vez (motor 6): quién dibuja en la vista 3D.

Hasta el 5.4 cada tarjeta decidía sola si se dibujaba: la del recorrido
(«Conoce Amatista Motor»), la del taller y la de la misión de una práctica
suelta. Con un recorrido abierto encima de un taller salían dos tarjetas, una
sobre la otra. Ahora hay un turno con prioridad fija:

    recorrido  >  taller (actividad o proyecto)  >  ficha  >  misión de la práctica

(motor 6.1: la **ficha** de una herramienta que el alumno tocó fuera de un
taller, en el modo curioso; dentro del taller la ficha va en la tarjeta del
taller) y una copia de Amatista que no es la dueña del dibujo (saneamiento.py) no
dibuja nada. Cada tarjeta pregunta ``me_toca(...)`` antes de dibujar.
"""
import bpy

RECORRIDO, TALLER, FICHA, MISION = "recorrido", "taller", "ficha", "mision"


def de_quien(contexto=None):
    """La tarjeta que se dibuja ahora en la vista 3D ("" si ninguna)."""
    from .. import recorrido, saneamiento

    if not saneamiento.soy_duena():
        return ""
    if recorrido.activo():
        return RECORRIDO
    contexto = contexto or bpy.context
    escena = getattr(contexto, "scene", None)
    try:
        from ..taller import sesion

        if sesion.cubre(escena):
            return TALLER
    except Exception:  # noqa: BLE001 - sin catálogo no hay taller
        pass
    try:
        from .. import fichas

        if fichas.visible() is not None:
            return FICHA
    except Exception:  # noqa: BLE001 - sin fichas no hay ficha
        pass
    if escena is not None and getattr(getattr(escena, "amatista", None), "practica_json", ""):
        return MISION
    return ""


def me_toca(quien, contexto=None):
    return de_quien(contexto) == quien


__all__ = ["FICHA", "MISION", "RECORRIDO", "TALLER", "de_quien", "me_toca"]
