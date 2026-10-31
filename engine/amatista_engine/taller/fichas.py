"""Fichas de herramientas para novatos (motor 6.1): una ayuda que enseña.

Pedido del creador: que el motor no sea «simples tarjetitas esperando a que
todo lo resuelva», sino que enseñe: que presente cada herramienta nueva como
a un novato, la ilumine en su lugar y diga para qué sirve cada cosa que el
alumno toca en sus primeros pasos.

Una ficha (practices/blender/fichas.json) dice de una herramienta: para qué
sirve, una comparación de la vida real, dónde está en la ventana de Blender
(su «zona»), cómo se usa paso a paso, el error típico y cuándo se usa. Es la
**misma ficha** en los dos lados: la plataforma la enseña en la teoría
(bloques herramienta_blender y blender_mapa) y Blender la presenta al llegar
a la práctica.

El **andamio** decide cuánta ayuda toca, y se retira con el uso:

- ``presentar``: nunca la vio → ficha completa antes de la actividad, con la
  herramienta iluminada.
- ``recordar``: la vio pocas veces y la habilidad todavía es nueva → una línea
  de recordatorio, la ficha a un clic.
- ``nada``: ya la conoce (o la marcó «Ya la conozco»).

El **modo curioso** reconoce lo que el alumno toca en Blender (la herramienta
activa o el operador que acaba de usar) y le dice qué es, las primeras veces.

Python puro: el add-on dibuja, las pruebas lo revisan sin Blender.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .modelo import ACOMPANADA, NUEVA

SCHEMA = "amatista.fichas/1"
PRESENTAR, RECORDAR, NADA = "presentar", "recordar", "nada"
VECES_RECORDAR = 3  # después de verla 3 veces, la ficha ya no se ofrece sola
VECES_CURIOSO = 2  # el modo curioso explica cada herramienta a lo más 2 veces
MAX_PRESENTAR = 2  # fichas antes de una actividad (más sería un muro de texto)
HABILIDADES_PRINCIPIANTE = 10  # el modo curioso «auto» se apaga cuando ya le salen solas 10 habilidades
LARGOS = {"para_que": 200, "analogia": 160, "donde": 160, "error": 200, "cuando": 140}


@dataclass(frozen=True)
class Zona:
    id: str
    nombre: str
    ingles: str = ""
    region: str = ""  # región de la vista 3D que se ilumina (TOOLS, HEADER, UI, WINDOW) o "" si es otro editor
    que_es: str = ""
    para_que: str = ""


@dataclass(frozen=True)
class Ficha:
    id: str
    nombre: str
    ingles: str = ""
    teclas: Tuple[str, ...] = ()
    zona: str = ""
    donde: str = ""
    para_que: str = ""
    analogia: str = ""
    como: Tuple[str, ...] = ()
    error: str = ""
    cuando: str = ""
    blender: Tuple[str, ...] = ()

    @property
    def tecla(self) -> str:
        return self.teclas[0] if self.teclas else ""

    def a_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "nombre": self.nombre, "ingles": self.ingles, "teclas": list(self.teclas),
                "zona": self.zona, "donde": self.donde, "para_que": self.para_que, "analogia": self.analogia,
                "como": list(self.como), "error": self.error, "cuando": self.cuando}


class Fichas:
    def __init__(self, fichas: Iterable[Ficha] = (), zonas: Iterable[Zona] = ()) -> None:
        self._fichas: Dict[str, Ficha] = {f.id: f for f in fichas}
        self._zonas: Dict[str, Zona] = {z.id: z for z in zonas}
        self._blender: Dict[str, str] = {}
        for f in self._fichas.values():
            for nombre in f.blender:
                self._blender.setdefault(nombre, f.id)

    def __len__(self) -> int:
        return len(self._fichas)

    def __contains__(self, ficha_id: object) -> bool:
        return ficha_id in self._fichas

    def ids(self) -> List[str]:
        return list(self._fichas)

    def ficha(self, ficha_id: str) -> Optional[Ficha]:
        return self._fichas.get(ficha_id or "")

    def zona(self, zona_id: str) -> Optional[Zona]:
        return self._zonas.get(zona_id or "")

    def zonas(self) -> List[Zona]:
        return list(self._zonas.values())

    def zona_de(self, ficha_id: str) -> Optional[Zona]:
        f = self.ficha(ficha_id)
        return self.zona(f.zona) if f is not None else None

    def de_herramientas(self, ids: Iterable[str]) -> List[Ficha]:
        """Las fichas de esas herramientas, en orden y sin repetir (las que no tienen ficha se saltan)."""
        vistas, salida = set(), []
        for hid in ids or ():
            f = self.ficha(hid)
            if f is not None and f.id not in vistas:
                vistas.add(f.id)
                salida.append(f)
        return salida

    def por_blender(self, nombre: str, propiedad: str = "") -> Optional[Ficha]:
        """La ficha de lo que el alumno tocó en Blender: herramienta activa («builtin.move») u operador
        («TRANSFORM_OT_translate»; para agregar un modificador, «OBJECT_OT_modifier_add:MIRROR»)."""
        if not nombre:
            return None
        if propiedad:
            fid = self._blender.get(f"{nombre}:{propiedad}")
            if fid:
                return self._fichas[fid]
        fid = self._blender.get(nombre)
        return self._fichas.get(fid) if fid else None


def _textos(valor: Any) -> Tuple[str, ...]:
    if not isinstance(valor, (list, tuple)):
        return ()
    return tuple(str(v).strip() for v in valor if isinstance(v, (str, int)) and str(v).strip())


def _texto(crudo: Mapping[str, Any], clave: str) -> str:
    valor = crudo.get(clave, "")
    return str(valor).strip() if isinstance(valor, (str, int, float)) else ""


def leer_fichas(datos: Mapping[str, Any]) -> Fichas:
    """Fichas desde el JSON ya leído. Nunca falla: lo que no se entiende se salta."""
    if not isinstance(datos, Mapping):
        return Fichas()
    zonas = []
    for z in datos.get("zonas") or ():
        if isinstance(z, Mapping) and _texto(z, "id") and _texto(z, "nombre"):
            zonas.append(Zona(id=_texto(z, "id"), nombre=_texto(z, "nombre"), ingles=_texto(z, "ingles"),
                              region=_texto(z, "region"), que_es=_texto(z, "que_es"), para_que=_texto(z, "para_que")))
    fichas = []
    for f in datos.get("fichas") or ():
        if not isinstance(f, Mapping) or not _texto(f, "id") or not _texto(f, "nombre"):
            continue
        fichas.append(Ficha(id=_texto(f, "id"), nombre=_texto(f, "nombre"), ingles=_texto(f, "ingles"),
                            teclas=_textos(f.get("teclas")), zona=_texto(f, "zona"), donde=_texto(f, "donde"),
                            para_que=_texto(f, "para_que"), analogia=_texto(f, "analogia"),
                            como=_textos(f.get("como")), error=_texto(f, "error"), cuando=_texto(f, "cuando"),
                            blender=_textos(f.get("blender"))))
    return Fichas(fichas, zonas)


def cargar_fichas(ruta: Optional[Path] = None) -> Fichas:
    """Lee practices/blender/fichas.json (o la copia empaquetada del add-on). Sin archivo: fichas vacías."""
    if ruta is None:
        ruta = Path(__file__).resolve().parents[3] / "practices" / "blender" / "fichas.json"
    try:
        return leer_fichas(json.loads(Path(ruta).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Fichas()


def revisar(datos: Mapping[str, Any], herramientas_validas: Iterable[str] = ()) -> List[str]:
    """Errores del archivo de fichas (para las pruebas y el validador): campos, zonas y largos."""
    errores: List[str] = []
    if not isinstance(datos, Mapping) or datos.get("schema") != SCHEMA:
        return [f"«schema» debe ser {SCHEMA}"]
    zonas = {z.get("id") for z in datos.get("zonas") or () if isinstance(z, Mapping)}
    validas = set(herramientas_validas or ())
    vistas, blender = set(), {}
    for i, f in enumerate(datos.get("fichas") or ()):
        donde = f"fichas[{i}]"
        if not isinstance(f, Mapping):
            errores.append(f"{donde} no es un objeto")
            continue
        fid = _texto(f, "id")
        if not fid:
            errores.append(f"{donde} sin id")
            continue
        if fid in vistas:
            errores.append(f"{donde}: «{fid}» repetida")
        vistas.add(fid)
        if validas and fid not in validas:
            errores.append(f"{donde}: «{fid}» no está en tools/catalogo.json")
        for clave in ("nombre", "para_que", "analogia", "donde", "error"):
            if not _texto(f, clave):
                errores.append(f"{donde}.{clave} vacío")
        for clave, maximo in LARGOS.items():
            if len(_texto(f, clave)) > maximo:
                errores.append(f"{donde}.{clave} pasa de {maximo} caracteres")
        if _texto(f, "zona") not in zonas:
            errores.append(f"{donde}.zona «{_texto(f, 'zona')}» no existe")
        como = _textos(f.get("como"))
        if not 2 <= len(como) <= 5:
            errores.append(f"{donde}.como debe tener de 2 a 5 pasos")
        for nombre in _textos(f.get("blender")):
            if nombre in blender and blender[nombre] != fid:
                errores.append(f"{donde}: «{nombre}» ya es de «{blender[nombre]}»")
            blender[nombre] = fid
    return errores


# --- El andamio: cuánta ayuda toca --------------------------------------------------------------------


def andamio(veces: int, conocida: bool = False, fase: str = NUEVA) -> str:
    """¿Presentar la ficha completa, recordarla en una línea o nada? Se retira con el uso."""
    if conocida:
        return NADA
    if veces <= 0:
        return PRESENTAR
    if veces < VECES_RECORDAR and fase in (NUEVA, ACOMPANADA):
        return RECORDAR
    return NADA


def por_presentar(fichas: Fichas, herramientas: Sequence[str], vistas: Mapping[str, int],
                  conocidas: Iterable[str] = (), fase: str = NUEVA) -> List[str]:
    """Las fichas que se presentan antes de una actividad (herramientas nuevas para el alumno), máximo 2."""
    conocidas = set(conocidas or ())
    salida = []
    for f in fichas.de_herramientas(herramientas):
        if andamio(int(vistas.get(f.id, 0) or 0), f.id in conocidas, fase) == PRESENTAR:
            salida.append(f.id)
    return salida[:MAX_PRESENTAR]


def recordatorio(fichas: Fichas, herramientas: Sequence[str], vistas: Mapping[str, int],
                 conocidas: Iterable[str] = (), fase: str = NUEVA) -> str:
    """Una línea para recordar la herramienta de la actividad («Escalar (S): cambia el tamaño…») o ""."""
    conocidas = set(conocidas or ())
    for f in fichas.de_herramientas(herramientas):
        if andamio(int(vistas.get(f.id, 0) or 0), f.id in conocidas, fase) == RECORDAR:
            tecla = f" ({f.tecla})" if f.tecla else ""
            return f"{f.nombre}{tecla}: {f.para_que}"
    return ""


def curioso_activo(modo: str, habilidades_que_salen: int) -> bool:
    """El modo curioso: «siempre», «nunca» o «auto» (solo para principiantes)."""
    if modo == "siempre":
        return True
    if modo == "nunca":
        return False
    return habilidades_que_salen < HABILIDADES_PRINCIPIANTE


def explicar_curioso(fichas: Fichas, nombre: str, propiedad: str, vistas: Mapping[str, int],
                     conocidas: Iterable[str] = ()) -> Optional[Ficha]:
    """La ficha que el modo curioso muestra por lo que el alumno acaba de tocar, o None si ya la conoce."""
    f = fichas.por_blender(nombre, propiedad)
    if f is None or f.id in set(conocidas or ()):
        return None
    if int(vistas.get(f.id, 0) or 0) >= VECES_CURIOSO:
        return None
    return f


__all__ = [
    "HABILIDADES_PRINCIPIANTE", "Ficha", "Fichas", "MAX_PRESENTAR", "NADA", "PRESENTAR", "RECORDAR", "SCHEMA",
    "VECES_CURIOSO", "VECES_RECORDAR", "Zona", "andamio", "cargar_fichas", "curioso_activo", "explicar_curioso",
    "leer_fichas", "por_presentar", "recordatorio", "revisar",
]
