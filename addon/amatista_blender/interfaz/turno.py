"""Una sola tarjeta a la vez (motor 6): quién dibuja en la vista 3D.

Hasta el 5.4 cada tarjeta decidía sola si se dibujaba: la del recorrido
(«Conoce Amatista Motor»), la del taller y la de la misión de una práctica
suelta. Con un recorrido abierto encima de un taller salían dos tarjetas, una
sobre la otra. Ahora hay un turno con prioridad fija:

    recorrido  >  taller (actividad o proyecto)  >  misión de la práctica

y una copia de Amatista que no es la dueña del dibujo (saneamiento.py) no
dibuja nada. Cada tarjeta pregunta ``me_toca(...)`` antes de dibujar.
"""
import bpy

RECORRIDO, TALLER, MISION = "recorrido", "taller", "mision"


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
    if escena is not None and getattr(getattr(escena, "amatista", None), "practica_json", ""):
        return MISION
    return ""


def me_toca(quien, contexto=None):
    return de_quien(contexto) == quien


__all__ = ["MISION", "RECORRIDO", "TALLER", "de_quien", "me_toca"]
