"""El adaptador de Blender para el Corazón Amatista (``amatista.corazon/1``).

Lo único que el corazón necesita de Blender, en un solo lugar:

- ``capturar``: la foto de la escena (el adaptador del motor, ``blender/adapter.py``).
- ``ejecutar``: hacer una señal con lo que Blender muestra por sí mismo (elegir
  la herramienta, abrir su menú o su pestaña, seleccionar piezas), con las
  funciones de ``guion/senalar.py``.
- ``comprobar``: ¿la señal sigue siendo verdad? (la herramienta sigue elegida,
  la pestaña sigue abierta, las piezas siguen seleccionadas). Con esto la banda
  nunca dice «te dejé elegida…» cuando ya no lo está.

Pasa la conformidad del corazón (``corazon/conformidad.py``): probado en
``addon/tests/en_blender.py`` › ``probar_corazon``.
"""
from importlib import import_module

import bpy

from .. import _motor

_c = import_module(_motor.engine.__name__ + ".corazon")
contrato = import_module(_motor.engine.__name__ + ".corazon.contrato")
_base = import_module(_motor.engine.__name__ + ".corazon.adaptador")
perfiles = import_module(_motor.engine.__name__ + ".corazon.perfiles")

PERFIL = perfiles.perfil("blender")


def _contexto():
    return bpy.context


class AdaptadorBlender(_base.AdaptadorBase):
    def __init__(self):
        super().__init__(PERFIL, id="blender-addon", version=".".join(str(n) for n in bpy.app.version))
        self.hacer[contrato.ELEGIR_HERRAMIENTA] = self._elegir
        self.ver[contrato.ELEGIR_HERRAMIENTA] = self._sigue_elegida
        self.hacer[contrato.ABRIR_PANEL] = self._abrir_panel
        self.ver[contrato.ABRIR_PANEL] = self._sigue_abierta
        self.hacer[contrato.SELECCIONAR] = self._seleccionar
        self.ver[contrato.SELECCIONAR] = self._sigue_seleccionado
        if not bpy.app.background:
            self.hacer[contrato.ABRIR_MENU] = self._abrir_menu  # sin ventana no hay ratón ni menú

    # --- La foto -------------------------------------------------------------------------------

    def capturar(self):
        return _motor.adapter.capture_scene(getattr(_contexto(), "scene", None))

    def capacidades(self):
        cap = super().capacidades()
        try:
            idioma = _motor.terminos.idioma()
        except Exception:  # noqa: BLE001
            idioma = "es"
        return _base.Capacidades(software=cap.software, version=cap.version, senales=cap.senales, idioma=idioma)

    def herramienta_activa(self):
        from ..guion import senalar

        contexto = _contexto()
        return senalar.herramienta_elegida(contexto, "EDIT_MESH" if contexto.mode == "EDIT_MESH" else "OBJECT")

    # --- Señales -------------------------------------------------------------------------------

    def _lugar(self, senal):
        lugar = PERFIL.lugar(senal.herramienta)
        return lugar if lugar is not None and (not senal.objetivo or lugar.objetivo == senal.objetivo) else None

    def _elegir(self, senal):
        from ..guion import senalar

        lugar = self._lugar(senal)
        if lugar is None:
            return contrato.ResultadoSenal(False, "herramienta sin lugar en la barra")
        hecho = bool(senalar._elegir(_contexto(), lugar))
        return contrato.ResultadoSenal(hecho, "" if hecho else "no se pudo elegir (¿otro modo?)")

    def _sigue_elegida(self, senal):
        from ..guion import senalar

        modo = "EDIT_MESH" if senal.modo == "EDIT" else "OBJECT"
        return senalar.herramienta_elegida(_contexto(), modo) == senal.objetivo

    def _abrir_menu(self, senal):
        from ..guion import senalar

        lugar = self._lugar(senal)
        hecho = bool(lugar is not None and senalar._abrir_menu(_contexto(), lugar))
        return contrato.ResultadoSenal(hecho, "" if hecho else "no hay ventana para abrir el menú")

    def _abrir_panel(self, senal):
        from ..guion import senalar

        lugar = self._lugar(senal)
        hecho = bool(lugar is not None and senalar._abrir_pestana(_contexto(), lugar))
        return contrato.ResultadoSenal(hecho, "" if hecho else "no hay editor Propiedades abierto")

    def _sigue_abierta(self, senal):
        contexto = _contexto()
        for ventana in getattr(contexto.window_manager, "windows", ()) or ():
            for area in ventana.screen.areas:
                try:
                    if senal.objetivo == "ROLES" and area.type == "VIEW_3D" and area.spaces.active.show_region_ui:
                        return True
                    if area.type == "PROPERTIES" and area.spaces.active.context == senal.objetivo:
                        return True
                except (AttributeError, RuntimeError, TypeError):
                    continue
        return False

    def _seleccionar(self, senal):
        contexto = _contexto()
        escena = getattr(contexto, "scene", None)
        nombres = [n for n in senal.objetos if escena is not None and n in escena.objects]
        if not nombres:
            return contrato.ResultadoSenal(False, "las piezas no están en la escena")
        try:
            for obj in escena.objects:
                obj.select_set(obj.name in nombres)
            contexto.view_layer.objects.active = escena.objects[nombres[0]]
        except (RuntimeError, ReferenceError, AttributeError) as error:
            return contrato.ResultadoSenal(False, str(error))
        return contrato.ResultadoSenal(True)

    def _sigue_seleccionado(self, senal):
        escena = getattr(_contexto(), "scene", None)
        try:
            return bool(senal.objetos) and all(n in escena.objects and escena.objects[n].select_get()
                                               for n in senal.objetos)
        except (AttributeError, ReferenceError, RuntimeError):
            return False


__all__ = ["AdaptadorBlender", "PERFIL"]
