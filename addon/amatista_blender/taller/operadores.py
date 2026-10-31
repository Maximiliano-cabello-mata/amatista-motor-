"""Operadores del taller: los botones de la tarjeta, del panel y las órdenes de la plataforma."""
import bpy

from .. import practicas
from . import datos, demo, isla, sesion
from .vista import tarjeta


def _avisar(texto):
    if texto:
        sesion.avisar(texto)


def ejecutar(context, accion):
    """Una acción de la tarjeta o del panel. Devuelve el texto que se avisa (o None)."""
    if accion == "continuar":
        if sesion.estado() == sesion.PAUSA:
            return sesion.seguir(context)
        if sesion.activa() and sesion.estado() != sesion.LOGRADA:
            return sesion.volver(context)
        if sesion.activa():
            return sesion.siguiente(context)
        # Motor 6: con la cuenta conectada, lo que sigue lo marca la lección de la plataforma.
        return sesion.volver_a_la_plataforma() if sesion.manda_la_plataforma() else sesion.abrir(context)
    if accion == "volver_amatista":
        from .. import navegar

        return navegar.volver(context)  # motor 6.2: la pastilla «Volver a mi práctica»
    if accion == "volver_plataforma":
        return sesion.volver_a_la_plataforma()
    if accion == "abrir_plataforma":
        return sesion.volver_a_la_plataforma(forzar=True)
    if accion == "siguiente":
        return sesion.siguiente(context)
    if accion == "otra_vez":
        return sesion.otra_vez(context)
    if accion == "pista":
        sesion.pedir_pista(context)
        return None
    if accion == "mirame":
        return sesion.mirame(context)
    if accion == "pausa":
        return sesion.pausar()
    if accion == "seguir":
        return sesion.seguir(context)
    if accion == "saltar":
        return sesion.saltar(context)
    if accion == "repetir_demo":
        return sesion.repetir_demo(context)
    if accion == "ahora_tu":
        demo.detener(completa=True)  # Mira termina: cuenta como vista y sigue «Hazlo conmigo»
        return sesion.siguiente(context)
    if accion == "cerrar_demo":
        demo.detener(completa=True)
        return None
    if accion == "isla":
        return isla.abrir(context)
    if accion == "terminar":
        return sesion.terminar()
    if accion == "empezar_actividad":
        return sesion.despues_de_presentar(context)
    # Motor 6.1: los botones de la ficha de una herramienta.
    if accion in ("ficha_entendido", "ficha_como", "ficha_conozco"):
        from .. import fichas

        if accion == "ficha_como":
            return fichas.como()
        if accion == "ficha_conozco":
            return fichas.ya_la_conozco(context)
        return fichas.entendido(context)
    return None


class AMATISTA_OT_taller_boton(bpy.types.Operator):
    """Un botón de la tarjeta del taller"""

    bl_idname = "amatista.taller_boton"
    bl_label = "Botón de la tarjeta"
    bl_options = {"INTERNAL"}

    indice: bpy.props.IntProperty(default=0, min=0)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        accion, activo = tarjeta.accion_de(context.region, self.indice)
        if accion is None:
            return {"CANCELLED"}
        if not activo:
            _avisar("Inténtalo un poco más antes de ver las teclas.")
            return {"FINISHED"}
        try:
            _avisar(ejecutar(context, accion))
        except Exception as error:  # noqa: BLE001 - un botón nunca rompe Blender
            print(f"[Amatista] Taller ({accion}): {error}")
            self.report({"WARNING"}, f"Amatista: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class AMATISTA_OT_taller_accion(bpy.types.Operator):
    """Continuar, pausar, pedir una pista o saltar la actividad del taller"""

    bl_idname = "amatista.taller_accion"
    bl_label = "Taller"
    bl_options = {"INTERNAL"}

    accion: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        return {
            "continuar": "Sigue con lo que toca en el taller",
            "pausa": "Pausa la actividad (tu trabajo queda como está)",
            "seguir": "Sigue la actividad en pausa",
            "pista": "El siguiente escalón de ayuda: qué falta, con qué, cómo y, al final, mírame",
            "saltar": "Pasa a la siguiente actividad (cuenta como un intento sin terminar)",
            "isla": "Abre tu isla: cada proyecto terminado deja su pieza",
            "mirame": "Mira cómo se hace, sin que Amatista toque lo que hiciste",
        }.get(properties.accion, "Amatista Taller")

    def execute(self, context):
        try:
            _avisar(ejecutar(context, self.accion))
        except Exception as error:  # noqa: BLE001
            print(f"[Amatista] Taller ({self.accion}): {error}")
            self.report({"WARNING"}, f"Amatista: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class AMATISTA_OT_taller_abrir(bpy.types.Operator):
    """Abre el taller en lo que toca (o en el módulo elegido)"""

    bl_idname = "amatista.taller_abrir"
    bl_label = "Abrir el taller"

    taller: bpy.props.StringProperty()
    actividad: bpy.props.StringProperty()
    habilidad: bpy.props.StringProperty(description="Practicar esta habilidad")
    probar: bpy.props.BoolProperty(description="«¿Ya sabes esto? Demuéstralo»: el reto sin ayuda")
    repasar: bpy.props.BoolProperty(description="«Recuérdalo»: un minuto con esta habilidad")

    def execute(self, context):
        if sesion.manda_la_plataforma() and not sesion.activa():
            # Motor 6: el alumno no elige módulos en Blender; la plataforma abre lo que toca.
            texto = sesion.volver_a_la_plataforma()
            self.report({"INFO"}, texto)
            return {"FINISHED"}
        try:
            if self.probar and self.habilidad:
                texto = sesion.probar(context, self.taller, self.habilidad)
            elif self.repasar and self.habilidad:
                texto = sesion.repasar(context, self.taller, self.habilidad)
            else:
                texto = sesion.abrir(context, self.taller, self.actividad, self.habilidad)
        except Exception as error:  # noqa: BLE001
            print(f"[Amatista] No se pudo abrir el taller: {error}")
            self.report({"ERROR"}, f"No se pudo abrir el taller: {error}")
            return {"CANCELLED"}
        if texto:
            self.report({"INFO"}, texto)
            sesion.avisar(texto)
        practicas.mostrar_en_amatista(context)
        return {"FINISHED"}


class AMATISTA_OT_taller_sincronizar(bpy.types.Operator):
    """Envía ahora tu avance del taller a tu cuenta"""

    bl_idname = "amatista.taller_sincronizar"
    bl_label = "Guardar mi avance"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        from .. import recorrido

        recorrido.anotar("guardar")
        if not datos.sincronizar():
            self.report({"INFO"}, "Tu avance se guarda en esta computadora y se envía al vincular tu cuenta.")
        return {"FINISHED"}


CLASES = (AMATISTA_OT_taller_boton, AMATISTA_OT_taller_accion, AMATISTA_OT_taller_abrir, AMATISTA_OT_taller_sincronizar)
