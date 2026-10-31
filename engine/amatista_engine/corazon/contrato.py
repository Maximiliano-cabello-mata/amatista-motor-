"""El contrato del Corazón Amatista (``amatista.corazon/1``).

Todo lo que cruza la frontera entre el corazón y un programa 3D está aquí,
en datos normales de Python: qué señal pedir, qué pasó al pedirla, qué ve
el alumno ahora (el turno) y qué eventos manda el programa. Nada de este
archivo conoce Blender, A-Frame, Maya ni 3ds Max.

Regla de estabilidad: dentro de ``amatista.corazon/1`` solo se **agregan**
campos con valor por defecto, tipos de señal y tipos de evento. Quitar o
cambiar el significado de algo es ``amatista.corazon/2``. Así una rama o
una extensión escrita hoy sigue funcionando mañana sin subir versión.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

CONTRATO = "amatista.corazon/1"

# --- Lugares de la interfaz ---------------------------------------------------------------------
# Dónde vive una herramienta en la pantalla del programa. El perfil de cada
# programa (perfiles/) los llena; el corazón solo los lee.
BARRA, MENU, PESTANA, DIALOGO, TECLA, LIENZO = "barra", "menu", "pestana", "dialogo", "tecla", "lienzo"
TIPOS_LUGAR = (BARRA, MENU, PESTANA, DIALOGO, TECLA, LIENZO)


@dataclass(frozen=True)
class Lugar:
    """Dónde está una herramienta, dicho como lo ve el alumno, y cómo señalarla."""

    herramienta: str  # id neutral de Amatista («transform.move»)
    nombre: str  # como sale en pantalla («Mover»)
    lugar: str  # una frase («en la barra de herramientas, a la izquierda de la vista 3D»)
    tipo: str = TECLA
    ruta: str = ""  # ruta de menú («Agregar › Malla»)
    atajo: str = ""
    objetivo: str = ""  # lo que el adaptador usa para señalar (id de herramienta, menú, pestaña, operador)
    modo: str = "OBJECT"


# --- Señales ------------------------------------------------------------------------------------
# Lo que el corazón puede pedirle a un programa para señalar algo de verdad.
ELEGIR_HERRAMIENTA = "elegir_herramienta"  # la deja activa: el programa pinta su botón y su manipulador
ABRIR_MENU = "abrir_menu"  # abre el menú junto al ratón (dura hasta que el ratón se va)
ABRIR_PANEL = "abrir_panel"  # abre la pestaña o el panel donde está
ABRIR_DIALOGO = "abrir_dialogo"  # abre la ventana (Guardar como)
SELECCIONAR = "seleccionar"  # selecciona las piezas de las que se habla
MARCAR_ZONA = "marcar_zona"  # dibuja un marco sobre una zona de la interfaz
DECIR = "decir"  # solo texto: todo programa lo puede hacer
TIPOS_SENAL = (ELEGIR_HERRAMIENTA, ABRIR_MENU, ABRIR_PANEL, ABRIR_DIALOGO, SELECCIONAR, MARCAR_ZONA, DECIR)

# Las que se pueden hacer solas sin estorbar (no tapan nada ni roban el teclado).
SUAVES = frozenset({ELEGIR_HERRAMIENTA, ABRIR_PANEL, SELECCIONAR, MARCAR_ZONA, DECIR})
# Las que duran mientras el alumno no las cambie; un menú o una ventana se cierran solos.
DURADERAS = frozenset({ELEGIR_HERRAMIENTA, ABRIR_PANEL, SELECCIONAR, MARCAR_ZONA, DECIR})

# Ciclo de vida de una señal: nunca desaparece por reloj, solo por lo que pasa en el programa.
PROPUESTA = "propuesta"  # el corazón la quiere; el adaptador todavía no la hizo
VIGENTE = "vigente"  # se hizo y sigue siendo verdad
MOSTRADA = "mostrada"  # se hizo pero no dura (un menú): ya no se puede comprobar
PERDIDA = "perdida"  # se hizo y dejó de ser verdad (el alumno eligió otra herramienta)
FALLIDA = "fallida"  # el adaptador no pudo hacerla: solo se dice dónde está
CUMPLIDA = "cumplida"  # el paso se cumplió: la señal ya no hace falta
ESTADOS_SENAL = (PROPUESTA, VIGENTE, MOSTRADA, PERDIDA, FALLIDA, CUMPLIDA)


@dataclass(frozen=True)
class Senal:
    """Una señal que el corazón pide. ``texto_hecho`` solo se dice si el adaptador confirma."""

    tipo: str
    herramienta: str = ""
    objetivo: str = ""
    objetos: Tuple[str, ...] = ()
    modo: str = "OBJECT"
    texto_base: str = ""  # siempre verdad: dónde está y su atajo
    texto_hecho: str = ""  # verdad solo si se hizo («Te dejé elegida «Mover»…»)
    texto_perdida: str = ""  # qué decir si deja de ser verdad
    automatica: bool = False  # el corazón la hizo sin que el alumno la pidiera

    @property
    def suave(self) -> bool:
        return self.tipo in SUAVES

    @property
    def duradera(self) -> bool:
        return self.tipo in DURADERAS


@dataclass(frozen=True)
class ResultadoSenal:
    """Lo que el adaptador dice después de intentar una señal."""

    hecho: bool
    motivo: str = ""  # por qué no («la barra de herramientas no existe en este modo»)


@dataclass(frozen=True)
class EstadoSenal:
    senal: Senal
    estado: str = PROPUESTA
    desde: float = 0.0

    @property
    def texto(self) -> str:
        """Lo que se le dice al alumno: nunca algo que el programa no confirmó."""
        s = self.senal
        if self.estado == VIGENTE:
            return s.texto_hecho or s.texto_base
        if self.estado == MOSTRADA:
            return " ".join(t for t in (s.texto_hecho, f"Si se cerró: {s.texto_base}" if s.texto_base else "") if t)
        if self.estado == PERDIDA:
            return s.texto_perdida or s.texto_base
        return s.texto_base

    @property
    def se_puede_repetir(self) -> bool:
        return self.estado in (PERDIDA, MOSTRADA, FALLIDA) and self.senal.tipo != DECIR


# --- Eventos ------------------------------------------------------------------------------------
# Lo que un programa le cuenta al corazón. Son neutrales: «guardó», no «save_post».
CAMBIO_ESCENA = "cambio_escena"
GUARDADO = "guardado"
DESHACER = "deshacer"
HERRAMIENTA = "herramienta"  # eligió otra herramienta (datos: {"id": ...})
PISTA_PEDIDA = "pista_pedida"
SENAL_HECHA = "senal_hecha"
DEMO_VISTA = "demo_vista"
PRACTICA_ABIERTA = "practica_abierta"
PASO_HECHO = "paso_hecho"
PASO_DESHECHO = "paso_deshecho"
PRACTICA_TERMINADA = "practica_terminada"
TIPOS_EVENTO = (CAMBIO_ESCENA, GUARDADO, DESHACER, HERRAMIENTA, PISTA_PEDIDA, SENAL_HECHA, DEMO_VISTA,
                PRACTICA_ABIERTA, PASO_HECHO, PASO_DESHECHO, PRACTICA_TERMINADA)


@dataclass(frozen=True)
class Evento:
    tipo: str
    momento: float = 0.0
    datos: Dict[str, Any] = field(default_factory=dict)


# --- El turno: lo único que ve el alumno ---------------------------------------------------------
TRABAJANDO, TERMINADO, PAUSA, SIN_PRACTICA = "trabajando", "terminado", "pausa", "sin_practica"


@dataclass(frozen=True)
class Turno:
    """Qué ve el alumno ahora. Una sola voz: cualquier interfaz (banda de Blender,
    panel de la plataforma, A-Frame) dibuja esto y nada más."""

    practica_id: str = ""
    modo: str = SIN_PRACTICA
    titulo: str = ""
    numero: int = 0
    total: int = 0
    paso_id: str = ""
    parte: str = ""
    haz: str = ""  # qué hacer, con verbo y pieza
    por_que: str = ""  # por qué el paso todavía no está (el mensaje del objetivo)
    donde: str = ""  # dónde está la herramienta, siempre verdad
    herramienta: str = ""
    senal: Optional[EstadoSenal] = None
    nivel: str = ""  # el escalón del andamio (andamiaje.py)
    pistas: Tuple[str, ...] = ()  # títulos de las pistas que se pueden pedir
    sugerir_pista: bool = False  # lleva rato en el paso: la interfaz puede ofrecer una pista
    ultimo: str = ""  # lo último que pasó; dura hasta que pase otra cosa
    pasos: Tuple[Tuple[str, str], ...] = ()  # (título, estado) de cada paso
    completo: bool = False
    contrato: str = CONTRATO

    def como_dict(self) -> Dict[str, Any]:
        datos = asdict(self)
        datos["senal"] = None if self.senal is None else {
            "tipo": self.senal.senal.tipo, "estado": self.senal.estado, "texto": self.senal.texto,
            "herramienta": self.senal.senal.herramienta, "repetir": self.senal.se_puede_repetir}
        datos["pasos"] = [list(p) for p in self.pasos]
        datos["pistas"] = list(self.pistas)
        return datos


__all__ = [
    "ABRIR_DIALOGO", "ABRIR_MENU", "ABRIR_PANEL", "BARRA", "CAMBIO_ESCENA", "CONTRATO", "CUMPLIDA", "DECIR",
    "DEMO_VISTA", "DESHACER", "DIALOGO", "DURADERAS", "ELEGIR_HERRAMIENTA", "ESTADOS_SENAL", "EstadoSenal", "Evento",
    "FALLIDA", "GUARDADO", "HERRAMIENTA", "LIENZO", "Lugar", "MARCAR_ZONA", "MENU", "MOSTRADA", "PASO_DESHECHO",
    "PASO_HECHO", "PAUSA", "PERDIDA", "PESTANA", "PISTA_PEDIDA", "PRACTICA_ABIERTA", "PRACTICA_TERMINADA",
    "PROPUESTA", "ResultadoSenal", "SELECCIONAR", "SENAL_HECHA", "SIN_PRACTICA", "SUAVES", "Senal", "TECLA",
    "TERMINADO", "TIPOS_EVENTO", "TIPOS_LUGAR", "TIPOS_SENAL", "TRABAJANDO", "Turno", "VIGENTE",
]
