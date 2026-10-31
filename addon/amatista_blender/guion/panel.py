"""N › Amatista con el guion (motor 7): el paso, sus botones y la lista de pasos.

    Paso 3 de 10 · Las ruedas
    Las ruedas son cilindros: cuatro por vagón, dos de cada lado…
    ⚠ Tienes 3 de 8 «Rueda». Faltan 5.
    [ ¿Qué falta? ] [ ¿Dónde está? ] [ ¿Cómo se hace? ]
    [ Mírame ]                         (si hay demostración)
    ✓ Dos vagones
    ✓ Vagones alargados
    ▶ Ocho ruedas
    · Ruedas de pie y delgadas …

Botones nativos de Blender (no gizmos invisibles sobre la vista): un clic
siempre cae en el botón. La banda de arriba de la vista 3D repite el paso y
la última pista.
"""
import bpy

from ..interfaz import estilo
from . import senalar

HABILIDAD_DE = {"object.add": "bl-agregar-primitivas", "transform.move": "bl-mover", "transform.scale": "bl-escalar-eje",
                "transform.rotate": "bl-rotar", "object.duplicate": "bl-duplicar", "file.save": "bl-guardar-archivo"}
ICONO = {"hecho": "CHECKMARK", "actual": "PLAY", "pendiente": "DOT"}


def _g():
    from .. import guion

    return guion


def _habilidad_para(herramienta):
    try:
        from ..taller import datos

        c = datos.catalogo()
        hid = HABILIDAD_DE.get(herramienta, "")
        return c.habilidad(hid) if c is not None and hid else None
    except Exception:  # noqa: BLE001
        return None


class AMATISTA_PT_guion(bpy.types.Panel):
    bl_idname = "AMATISTA_PT_guion"
    bl_label = "Paso a paso"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Amatista"
    bl_parent_id = "AMATISTA_PT_principal"
    bl_options = {"HIDE_HEADER"}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return _g().activo(context.scene)

    def draw(self, context):
        g = _g()
        v = g.vista()
        layout = self.layout
        if v["modo"] == "mirando":
            cuerpo = estilo.tarjeta(layout, f"Mira · {v['titulo']}", icon="HIDE_OFF")
            estilo.parrafo(cuerpo, context, v["haz"])
            if v["teclas"]:
                estilo.teclas(cuerpo, v["teclas"])
            fila = cuerpo.row(align=True)
            fila.scale_y = 1.4
            fila.operator("amatista.taller_accion", text="Ahora tú", icon="PLAY").accion = "ahora_tu"
            fila.operator("amatista.taller_accion", text="Repetir", icon="FILE_REFRESH").accion = "repetir_demo"
            return
        if v["modo"] == "pausa":
            cuerpo = estilo.tarjeta(layout, "En pausa", icon="PAUSE")
            estilo.parrafo(cuerpo, context, v["haz"])
            estilo.boton_principal(cuerpo, "amatista.taller_accion", "Seguir", icon="PLAY", accion="seguir")
            return
        if v["completo"]:
            cuerpo = estilo.tarjeta(layout, "¡Terminado!", icon="CHECKMARK")
            estilo.parrafo(cuerpo, context, v["haz"] if v["modo"] == "logrado" else
                           "Todo lo que pedía la práctica está en tu escena.")
            from ..taller import sesion

            if sesion.activa() and sesion.cubre(context.scene):
                estilo.boton_principal(cuerpo, "amatista.taller_accion", "Siguiente", icon="FORWARD",
                                       accion="siguiente")
            if g.sin_progreso():
                estilo.parrafo(cuerpo, context, "Cuenta de administrador: esto no se guarda en tu progreso.",
                               icon="INFO")
            self._lista(layout, v)
            return
        if not v["total"]:
            estilo.parrafo(layout, context, "Revisando tu escena…", icon="TIME")
            return
        titulo = f"Paso {v['numero']} de {v['total']}" + (f" · {v['parte']}" if v["parte"] else "")
        cuerpo = estilo.tarjeta(layout, titulo, icon="PLAY")
        fila = cuerpo.row()
        fila.scale_y = 1.15
        estilo.parrafo(fila.column(), context, v["haz"])
        if v["por_que"]:
            estilo.parrafo(cuerpo, context, v["por_que"], icon="ERROR" if g.avance().pausa else "INFO", alerta=False)
        if v["pista"]:
            caja = cuerpo.box()
            estilo.parrafo(caja, context, f"{v['pista_titulo']} {v['pista']}", icon="LIGHT")
            if v["teclas"]:
                estilo.teclas(caja, v["teclas"])
        fila = cuerpo.row(align=True)
        fila.scale_y = 1.3
        for nivel, texto in ((1, "¿Qué falta?"), (2, "¿Dónde está?"), (3, "¿Cómo se hace?")):
            fila.operator("amatista.guion_pista", text=texto).nivel = nivel
        if senalar.se_puede_abrir(v["herramienta"]):
            boton = cuerpo.row()
            boton.scale_y = 1.2
            texto = "Abrir «Guardar como»" if v["herramienta"] == "file.save" else "Abrir la ventana"
            boton.operator("amatista.guion_abrir", text=texto, icon="FILE_TICK")
        if _habilidad_para(v["herramienta"]) is not None:
            cuerpo.operator("amatista.guion_mirame", text="Mírame hacerlo", icon="HIDE_OFF")
        if g.sin_progreso():
            estilo.parrafo(cuerpo, context, "Administrador: practicas sin guardar progreso.", icon="INFO")
        self._lista(layout, v)

    def _lista(self, layout, v):
        if not v["pasos"]:
            return
        col = layout.column(align=True)
        for titulo, estado in v["pasos"]:
            fila = col.row()
            fila.active = estado != "pendiente"
            fila.label(text=titulo, icon=ICONO.get(estado, "DOT"))


class AMATISTA_OT_guion_pista(bpy.types.Operator):
    """Una pista del paso que toca: qué falta, dónde está la herramienta o cómo se hace"""

    bl_idname = "amatista.guion_pista"
    bl_label = "Pista del paso"
    bl_options = {"INTERNAL"}

    nivel: bpy.props.IntProperty(default=0, min=0, max=3)

    def execute(self, context):
        p = _g().pedir_pista(context, self.nivel)
        if p is None:
            self.report({"INFO"}, "No hay un paso pendiente.")
        return {"FINISHED"}


class AMATISTA_OT_guion_abrir(bpy.types.Operator):
    """Abre la ventana de la herramienta del paso (Guardar como, Renderizar): tú escribes y confirmas"""

    bl_idname = "amatista.guion_abrir"
    bl_label = "Abrir la ventana del paso"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        g = _g()
        paso = g.paso_actual()
        if paso is None:
            return {"CANCELLED"}
        sugerido = ""
        if paso.herramienta == "file.save":
            import re

            m = re.search(r"«([^»]+)»", paso.haz + " " + " ".join(paso.como))
            nombre = re.search(r"(mi_[a-z_]+\.blend)", paso.haz + " " + " ".join(paso.como))
            sugerido = nombre.group(1) if nombre else (f"mi_{m.group(1)}.blend" if m else "")
        if not senalar.abrir_ventana(context, paso.herramienta, sugerido):
            self.report({"WARNING"}, "No se pudo abrir: usa el atajo de la pista «¿Dónde está?».")
        return {"FINISHED"}


class AMATISTA_OT_guion_mirame(bpy.types.Operator):
    """Amatista hace este gesto en tu vista 3D con piezas temporales (no toca lo tuyo)"""

    bl_idname = "amatista.guion_mirame"
    bl_label = "Mírame hacerlo"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        from ..taller import demo, sesion

        g = _g()
        paso = g.paso_actual()
        h = _habilidad_para(paso.herramienta) if paso is not None else None
        if h is None:
            return {"CANCELLED"}
        if not demo.empezar(h, lambda _c: _g()._redibujar(), context.scene, pasos=sesion._pasos_demo(h, sesion.actividad())):
            self.report({"WARNING"}, "La demostración no se pudo mostrar.")
        return {"FINISHED"}


CLASES = (AMATISTA_PT_guion, AMATISTA_OT_guion_pista, AMATISTA_OT_guion_abrir, AMATISTA_OT_guion_mirame)


def register():
    for clase in CLASES:
        bpy.utils.register_class(clase)


def unregister():
    for clase in reversed(CLASES):
        try:
            bpy.utils.unregister_class(clase)
        except RuntimeError:
            pass


__all__ = ["CLASES", "register", "unregister"]
