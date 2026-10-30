"""Lo que el taller dibuja en la vista 3D: el molde (POST_VIEW) y la tarjeta (POST_PIXEL).

Los botones de la tarjeta se tocan con el ratón gracias a un grupo de
gizmos 2D: un gizmo por botón, invisible, que responde al clic solo dentro
del rectángulo que la tarjeta dibujó (test_select) y corre
``amatista.taller_boton``. Todo lo demás sigue yendo a Blender (no hay un
operador modal que se quede escuchando el teclado o el autoguardado).
"""
import bpy

try:
    import gpu  # noqa: F401
except ImportError:  # Blender sin GPU (modo background)
    gpu = None

from ... import ajustes
from .. import sesion
from . import molde, tarjeta

_MANEJADORES = []


def redibujar():
    if bpy.app.background:
        return
    wm = getattr(bpy.context, "window_manager", None)
    for ventana in getattr(wm, "windows", ()) or ():
        for area in ventana.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def dibujar_molde():
    from ...interfaz import turno

    contexto = bpy.context
    if not turno.me_toca(turno.TALLER, contexto):
        return
    visible = sesion.molde_visible()
    if visible is None:
        return
    piezas, estados, actual, marca = visible
    p = ajustes.prefs()
    molde.dibujar(piezas, estados, actual, marca, reducir_movimiento=p is not None and not p.animaciones)


class AMATISTA_GT_boton_taller(bpy.types.Gizmo):
    """Un botón de la tarjeta: no se dibuja (lo dibuja la tarjeta), solo atrapa su clic."""

    bl_idname = "AMATISTA_GT_boton_taller"
    __slots__ = ("indice",)

    def setup(self):
        if not hasattr(self, "indice"):
            self.indice = 0

    def draw(self, context):
        pass

    def draw_select(self, context, select_id):
        pass

    def test_select(self, context, location):
        indice = tarjeta.boton_en(context.region, location[0], location[1])
        clave = context.region.as_pointer() if context.region is not None else 0
        if tarjeta.raton(clave, location[0], location[1]) and context.area is not None:
            context.area.tag_redraw()  # motor 6: la tarjeta compacta se abre al acercar el ratón
        dentro = indice == self.indice
        antes = (tarjeta.HOVER["region"], tarjeta.HOVER["indice"])
        if dentro:
            tarjeta.HOVER.update(region=clave, indice=self.indice)
        elif antes == (clave, self.indice):
            tarjeta.HOVER.update(region=0, indice=-1)
        if antes != (tarjeta.HOVER["region"], tarjeta.HOVER["indice"]) and context.area is not None:
            context.area.tag_redraw()
        return 0 if dentro else -1


class AMATISTA_GGT_tarjeta_taller(bpy.types.GizmoGroup):
    bl_idname = "AMATISTA_GGT_tarjeta_taller"
    bl_label = "Tarjeta de Amatista Taller"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SHOW_MODAL_ALL"}

    @classmethod
    def poll(cls, context):
        from ...interfaz import turno

        return turno.de_quien(context) in (turno.TALLER, turno.FICHA)  # motor 6.1: la ficha usa los mismos botones

    def setup(self, context):
        for i in range(tarjeta.MAX_BOTONES):
            gz = self.gizmos.new(AMATISTA_GT_boton_taller.bl_idname)
            gz.indice = i
            gz.use_draw_hover = False
            propiedades = gz.target_set_operator("amatista.taller_boton")
            propiedades.indice = i

    def draw_prepare(self, context):
        clave = context.region.as_pointer() if context.region is not None else 0
        cuantos = len(tarjeta.BOTONES.get(clave) or ())
        for gz in self.gizmos:
            gz.hide = getattr(gz, "indice", 0) >= cuantos


CLASES = (AMATISTA_GT_boton_taller, AMATISTA_GGT_tarjeta_taller)


def activar(encendido=True):
    if gpu is None or bpy.app.background:
        return
    from ... import saneamiento
    from . import brillo

    vista = bpy.types.SpaceView3D
    if encendido and not _MANEJADORES:
        _MANEJADORES.append(saneamiento.agregar_dibujo(vista, dibujar_molde, (), "WINDOW", "POST_VIEW"))
        _MANEJADORES.append(saneamiento.agregar_dibujo(vista, tarjeta.dibujar, (), "WINDOW", "POST_PIXEL"))
        brillo.activar(True)
    elif not encendido:
        while _MANEJADORES:
            saneamiento.quitar_dibujo(vista, _MANEJADORES.pop(), "WINDOW")
        brillo.activar(False)
    redibujar()


def register():
    activar(True)


def unregister():
    activar(False)
    tarjeta.BOTONES.clear()
