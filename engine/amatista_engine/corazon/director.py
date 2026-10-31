"""El director: el corazón que decide, momento a momento, qué ve el alumno.

Hasta el motor 7 esta decisión vivía repartida en el add-on de Blender
(``ESTADO`` globales en el guion, el brillo, las fichas y la sesión del
taller), así que no se podía probar sin Blender ni reusar en otro programa.
El director la junta en un objeto de Python puro, uno por práctica abierta:

1. **Observa** el reporte del motor (``observar``): avanza el guion por lo
   que hay en la escena, anota qué herramienta se usó sola o con ayuda y
   cierra la señal del paso cumplido.
2. **Decide** el turno (``turno``): el paso, la instrucción, dónde está la
   herramienta, el escalón del andamio y, si toca, una señal.
3. **Pide** la señal al adaptador (``pendiente`` → ``ejecutada``) y la
   **vuelve a comprobar** en cada revisión (``revisar_senal``).

``ciclo`` hace las tres cosas con un adaptador. Las extensiones entran en
los puntos de ``extensiones.PUNTOS``; la rama (``ramas.py``) elige cuáles.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Dict, List, Optional

from ..guion import ACTUAL, COMO, DONDE, QUE_FALTA, TITULOS, Avance, Guion, Paso, Pista, avanzar, guion_de_practica
from . import andamiaje, senales
from .adaptador import Adaptador, Capacidades, Perfil
from .contrato import (
    DEMO_VISTA, DESHACER, GUARDADO, HERRAMIENTA, PASO_DESHECHO, PASO_HECHO, PAUSA, PISTA_PEDIDA, PRACTICA_ABIERTA,
    PRACTICA_TERMINADA, PROPUESTA, SENAL_HECHA, SIN_PRACTICA, TERMINADO, TRABAJANDO, EstadoSenal, Evento,
    ResultadoSenal, Senal, Turno,
)
from .extensiones import Extensiones

NOMBRE_EN_TEXTO = re.compile(r"«([^»]{1,63})»")


class Director:
    def __init__(self, practica, perfil: Perfil, capacidades: Capacidades, *, guion: Optional[Guion] = None,
                 extensiones: Optional[Extensiones] = None, historial: Optional[andamiaje.Historial] = None,
                 umbrales: Optional[andamiaje.Umbrales] = None, senal_sola: bool = True, idioma: str = "",
                 ahora: float = 0.0) -> None:
        self.practica = practica
        self.perfil = perfil
        self.capacidades = capacidades
        self.extensiones = extensiones or Extensiones()
        self.historial = historial if historial is not None else andamiaje.Historial()
        self.umbrales = umbrales or andamiaje.Umbrales()
        self.senal_sola = senal_sola
        self.idioma = idioma or capacidades.idioma
        g = guion if guion is not None else guion_de_practica(practica)
        pasos = tuple(self.extensiones.encadenar("pasos", p, practica) for p in g.pasos)
        self.guion = replace(g, pasos=pasos)
        self.avance: Optional[Avance] = None
        self.senal: Optional[EstadoSenal] = None
        self.pista: Optional[Pista] = None
        self.nivel_pista = 0
        self.con_ayuda: set = set()  # pasos en los que se pidió ayuda
        self.inicio_paso = ahora
        self.ultimo = ""
        self.tropiezos_seguidos = 0
        self._paso_id = ""
        self._terminado_avisado = False
        self._contadas: set = set()
        self.notificar(Evento(PRACTICA_ABIERTA, ahora, {"practica": getattr(practica, "id", "")}))

    # --- Lo que se lee -----------------------------------------------------------------------

    @property
    def practica_id(self) -> str:
        return self.guion.practica_id

    def paso_actual(self) -> Optional[Paso]:
        if self.avance is None or not self.avance.actual:
            return None
        return self.guion.paso(self.avance.actual)

    def contexto(self, ahora: float = 0.0) -> Dict[str, Any]:
        """Lo que reciben las extensiones (datos, no el director)."""
        return {"practica": self.practica_id, "software": self.perfil.software, "idioma": self.idioma,
                "tiempo_en_paso": max(0.0, ahora - self.inicio_paso), "tropiezos_seguidos": self.tropiezos_seguidos,
                "nivel_pista": self.nivel_pista, "capacidades": self.capacidades, "perfil": self.perfil}

    def escalon(self, herramienta: str, ahora: float = 0.0) -> str:
        base = andamiaje.escalon(self.historial.uso(herramienta), ahora, self.umbrales)
        otro = self.extensiones.primera("andamio", herramienta, base, self.historial, self.contexto(ahora))
        return otro if otro in andamiaje.ESCALONES else base

    # --- Observar ------------------------------------------------------------------------------

    def observar(self, reporte, ahora: float) -> Turno:
        """El motor revisó la escena: el guion avanza y se decide lo que sigue."""
        anterior = self.avance
        nuevo = avanzar(self.guion, reporte, anterior)
        self.avance = nuevo
        for paso_id in nuevo.recien:
            p = self.guion.paso(paso_id)
            if p is None:
                continue
            ayudado = paso_id in self.con_ayuda
            if p.herramienta not in self._contadas:
                # Una vez por práctica y herramienta: lo que retira la ayuda es volver a hacerlo otra vez, no
                # repetir el gesto tres veces en el mismo tren.
                self._contadas.add(p.herramienta)
                andamiaje.registrar(self.historial, p.herramienta, con_ayuda=ayudado, ahora=ahora)
            if not ayudado:
                self.tropiezos_seguidos = 0
            self.notificar(Evento(PASO_HECHO, ahora, {"paso": paso_id, "herramienta": p.herramienta,
                                                      "con_ayuda": ayudado}))
        for paso_id in nuevo.deshechos:
            p = self.guion.paso(paso_id)
            if p is not None:
                andamiaje.tropezar(self.historial, p.herramienta, ahora)
                self.tropiezos_seguidos += 1
                self.notificar(Evento(PASO_DESHECHO, ahora, {"paso": paso_id}))
        if nuevo.completo and not self._terminado_avisado:
            self._terminado_avisado = True
            self.ultimo = "¡Terminado! Todo lo que pedía la práctica está en tu escena."
            self.notificar(Evento(PRACTICA_TERMINADA, ahora, {"practica": self.practica_id}))
        elif not nuevo.completo:
            self._terminado_avisado = False
            if nuevo.recien:
                p = self.guion.paso(nuevo.recien[-1])
                self.ultimo = (f"Listo: {p.titulo[0].lower() + p.titulo[1:]}." if len(nuevo.recien) == 1 and p
                               else f"Listos {len(nuevo.recien)} pasos de una vez.")
            elif nuevo.deshechos:
                p = self.guion.paso(nuevo.deshechos[0])
                if p is not None:
                    self.ultimo = f"Se deshizo: {p.titulo[0].lower() + p.titulo[1:]}. Vuelve a hacerlo cuando quieras."
        actual = nuevo.actual or ""
        if actual != self._paso_id:
            self._cambiar_de_paso(actual, ahora)
        return self.turno(ahora)

    def _cambiar_de_paso(self, actual: str, ahora: float) -> None:
        self.senal = None  # la del paso anterior quedó cumplida: no se arrastra
        self.pista, self.nivel_pista = None, 0
        self._paso_id = actual
        self.inicio_paso = ahora
        p = self.paso_actual()
        if p is None or not self.senal_sola:
            return
        if andamiaje.senal_sola(self.escalon(p.herramienta, ahora)):
            self._proponer(p, a_pedido=False, ahora=ahora)

    def _proponer(self, p: Paso, *, a_pedido: bool, ahora: float) -> Optional[Senal]:
        lugar = self.perfil.lugar(p.herramienta)
        s = senales.elegir(lugar, self.perfil, self.capacidades, a_pedido=a_pedido, primitiva=p.primitiva,
                           idioma=self.idioma, automatica=not a_pedido)
        otra = self.extensiones.primera("senal", p, lugar, s, self.contexto(ahora))
        if isinstance(otra, Senal):
            s = otra
        if s is not None:
            self.senal = senales.iniciar(s, ahora)
        return s

    # --- La señal ------------------------------------------------------------------------------

    def pendiente(self) -> Optional[Senal]:
        """La señal que el adaptador tiene que hacer ahora (None si no hay)."""
        if self.senal is not None and self.senal.estado == PROPUESTA:
            return self.senal.senal
        return None

    def ejecutada(self, resultado: ResultadoSenal, ahora: float) -> None:
        if self.senal is None:
            return
        self.senal = senales.tras_ejecutar(self.senal, resultado, ahora)
        self.notificar(Evento(SENAL_HECHA, ahora, {"tipo": self.senal.senal.tipo, "estado": self.senal.estado,
                                                   "motivo": resultado.motivo}))

    def revisar_senal(self, sigue: bool, ahora: float) -> None:
        self.senal = senales.revisar(self.senal, sigue, ahora)

    def repetir_senal(self, ahora: float) -> Optional[Senal]:
        """«Señálalo otra vez»: la misma señal vuelve a pedirse."""
        if self.senal is None:
            p = self.paso_actual()
            return self._proponer(p, a_pedido=True, ahora=ahora) if p is not None else None
        self.senal = senales.iniciar(self.senal.senal, ahora)
        return self.senal.senal

    # --- Pistas --------------------------------------------------------------------------------

    def _extras(self, ahora: float) -> List[Pista]:
        """Las pistas que aportan las extensiones para el paso que toca (niveles 4 en adelante)."""
        p = self.paso_actual()
        if p is None:
            return []
        return [x for x in self.extensiones.correr("pistas", p, self.avance, self.contexto(ahora))
                if isinstance(x, Pista)]

    def _titulos(self, ahora: float) -> List[str]:
        return [TITULOS[QUE_FALTA], TITULOS[DONDE], TITULOS[COMO]] + [x.titulo for x in self._extras(ahora)]

    def pedir_pista(self, ahora: float, nivel: int = 0) -> Optional[Pista]:
        """La pista de ese nivel (o la siguiente) para el paso que toca; puede proponer una señal."""
        p, av = self.paso_actual(), self.avance
        if p is None or av is None or av.completo:
            return None
        extras = self._extras(ahora)
        total = 3 + len(extras)
        nivel = nivel or (self.nivel_pista % total) + 1
        self.con_ayuda.add(p.id)
        self.tropiezos_seguidos += 1 if nivel == total else 0
        pista: Optional[Pista]
        if nivel == QUE_FALTA:
            texto = av.pausa or av.por_que or p.listo
            pista = Pista(QUE_FALTA, TITULOS[QUE_FALTA], self.perfil.en_pantalla(texto, self.idioma), p.herramienta)
            nombres = NOMBRE_EN_TEXTO.findall(texto)
            sel = senales.seleccionar(nombres, self.capacidades, texto_base="")
            if sel is not None:
                self.senal = senales.iniciar(sel, ahora)
        elif nivel == DONDE:
            lugar = self.perfil.lugar(p.herramienta)
            texto = (self.perfil.frase(lugar, self.idioma, p.primitiva) if lugar is not None else
                     "Esto se hace con lo que ya tienes en la escena: " + (p.como[0] if p.como else p.haz))
            pista = Pista(DONDE, TITULOS[DONDE], texto, p.herramienta)
            self._proponer(p, a_pedido=True, ahora=ahora)
        elif nivel == COMO:
            lineas = list(p.como) or [p.haz]
            pista = Pista(COMO, TITULOS[COMO], self.perfil.en_pantalla(" ".join(lineas[:3]), self.idioma),
                          p.herramienta, p.teclas)
        else:
            pista = extras[nivel - 4] if 0 <= nivel - 4 < len(extras) else None
        if pista is not None:
            self.pista, self.nivel_pista = pista, nivel
            self.notificar(Evento(PISTA_PEDIDA, ahora, {"paso": p.id, "nivel": nivel}))
        return pista

    # --- Eventos del programa ------------------------------------------------------------------

    def evento(self, ev: Evento) -> None:
        """Un evento neutral del programa (guardado, deshacer, herramienta elegida, demo vista)."""
        if ev.tipo == DEMO_VISTA:
            p = self.paso_actual()
            if p is not None:
                self.con_ayuda.add(p.id)
        self.notificar(ev)

    def notificar(self, ev: Evento) -> None:
        if not self.extensiones.de("observadores"):
            return
        t = self.turno(ev.momento) if getattr(self, "avance", None) is not None else None
        self.extensiones.correr("observadores", ev, t)

    # --- El turno ------------------------------------------------------------------------------

    def turno(self, ahora: float = 0.0) -> Turno:
        av = self.avance
        if av is None:
            return Turno(practica_id=self.practica_id, modo=SIN_PRACTICA, titulo=self.guion.titulo,
                         total=self.guion.total)
        p = self.paso_actual()
        pasos = tuple((x.titulo, av.estado(x.id)) for x in self.guion.pasos)
        if av.completo or p is None:
            t = Turno(practica_id=self.practica_id, modo=TERMINADO, titulo=self.guion.titulo, numero=self.guion.total,
                      total=self.guion.total, haz="¡Terminado! Todo lo que pedía está en tu escena.",
                      ultimo=self.ultimo, pasos=pasos, completo=True)
            return self.extensiones.encadenar("turno", t)
        nivel = self.escalon(p.herramienta, ahora)
        lugar = self.perfil.lugar(p.herramienta)
        donde = self.perfil.frase(lugar, self.idioma, p.primitiva) if lugar is not None else ""
        espera = andamiaje.espera(nivel, self.umbrales)
        t = Turno(
            practica_id=self.practica_id, modo=PAUSA if av.pausa else TRABAJANDO, titulo=self.guion.titulo,
            numero=p.numero, total=self.guion.total, paso_id=p.id, parte=p.parte,
            haz=self.perfil.en_pantalla(p.haz, self.idioma),
            por_que=self.perfil.en_pantalla(av.pausa or (av.por_que if av.por_que != p.listo else ""), self.idioma),
            donde=donde if nivel != andamiaje.RETO else "", herramienta=p.herramienta, senal=self.senal, nivel=nivel,
            pistas=tuple(self._titulos(ahora)), sugerir_pista=self.pista is None and ahora - self.inicio_paso >= espera > 0,
            ultimo=self.ultimo, pasos=pasos, completo=False,
        )
        return self.extensiones.encadenar("turno", t)

    # --- El ciclo con un adaptador -------------------------------------------------------------

    def ciclo(self, adaptador: Adaptador, reporte, ahora: float) -> Turno:
        """Observa, hace la señal pendiente y comprueba la vigente. Devuelve el turno."""
        if reporte is not None:
            self.observar(reporte, ahora)
        s = self.pendiente()
        if s is not None:
            self.ejecutada(adaptador.ejecutar(s), ahora)
        elif self.senal is not None:
            self.revisar_senal(adaptador.comprobar(self.senal.senal), ahora)
        return self.turno(ahora)


EVENTOS_DEL_PROGRAMA = (GUARDADO, DESHACER, HERRAMIENTA, DEMO_VISTA)

__all__ = ["ACTUAL", "Director", "EVENTOS_DEL_PROGRAMA"]
