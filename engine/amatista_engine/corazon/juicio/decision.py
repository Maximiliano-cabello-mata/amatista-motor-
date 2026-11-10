"""La decisión: de todo lo que falta, UNA sola indicación, elegida por reglas en orden fijo.

El orden es pedagógico y es un dato (``ORDEN``), no código repartido:

1. Girar lo que ya existe y está mal orientado.
2. Corregir el tamaño de lo que ya existe.
   (Antes de pedir más piezas: una rueda mal hecha, duplicada siete veces,
   son ocho ruedas por arreglar.)
3. Agregar lo que falta, en el orden del ejemplo.
4. Con todas las piezas bien, seguir con lo que diga el motor (juntarlas,
   guardar, materiales…).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from .diferencia import FALTA, GIRADA, TAMANO, Diferencia, EstadoPieza
from .plano import NOMBRE_PRIMITIVA

GIRAR, AJUSTAR_TAMANO, AGREGAR, SEGUIR, LISTO = "girar", "ajustar_tamaño", "agregar", "seguir", "listo"


@dataclass(frozen=True)
class Decision:
    accion: str  # GIRAR, AJUSTAR_TAMANO, AGREGAR, SEGUIR o LISTO
    texto: str  # lo que se le dice al alumno, con medidas
    objeto: str = ""  # el objeto del alumno a resaltar, si lo hay
    grupo: str = ""
    motivo: str = ""  # por qué se eligió esto (para depurar y para el registro)


def _num(metros: float) -> str:
    return f"{metros:.2f}".rstrip("0").rstrip(".") + " m"


def _quien(d: Diferencia, pieza: EstadoPieza) -> str:
    etiqueta = d.plano.etiqueta(pieza.grupo)
    return f"«{pieza.objeto}» ({etiqueta})" if pieza.objeto.split(".")[0].lower() != etiqueta.lower() else f"«{pieza.objeto}»"


def _girar(d: Diferencia) -> Optional[Decision]:
    pieza = next(iter(d.con_estado(GIRADA)), None)
    if pieza is None:
        return None
    a = pieza.ajuste
    return Decision(GIRAR, f"{_quien(d, pieza)} tiene las medidas correctas pero está girada: mide {_num(a.actual)} en "
                           f"{a.eje} y ahí debería medir cerca de {_num(a.esperado)}. Gírala con R.",
                    pieza.objeto, pieza.grupo, "una pieza con las medidas bien y los ejes cambiados")


def _tamano(d: Diferencia) -> Optional[Decision]:
    pieza = next(iter(d.con_estado(TAMANO)), None)
    if pieza is None:
        return None
    a = pieza.ajuste
    verbo = "Redúcela" if a.actual > a.esperado else "Agrándala"
    return Decision(AJUSTAR_TAMANO, f"{_quien(d, pieza)} mide {_num(a.actual)} en {a.eje}; en tu figura debería medir "
                                    f"cerca de {_num(a.esperado)}. {verbo} con S y luego {a.eje}.",
                    pieza.objeto, pieza.grupo, "una pieza que ya existe con un lado fuera de proporción")


def _agregar(d: Diferencia) -> Optional[Decision]:
    falta = next(iter(d.con_estado(FALTA)), None)
    if falta is None:
        return None
    cuantas = d.faltan(falta.grupo)
    etiqueta = d.plano.etiqueta(falta.grupo)
    esperada = next(p for p in d.plano.piezas if p.grupo == falta.grupo)
    forma = NOMBRE_PRIMITIVA.get(esperada.primitiva, esperada.primitiva)
    medidas = " × ".join(_num(m * d.escala).replace(" m", "") for m in esperada.medidas) + " m"
    hechas = sum(1 for p in d.piezas if p.grupo == falta.grupo) - cuantas
    if hechas:
        texto = (f"Llevas {hechas} de {hechas + cuantas} «{etiqueta}». Te {'falta' if cuantas == 1 else 'faltan'} "
                 f"{cuantas}: duplica una con Shift + D.")
    else:
        piezas = "1 pieza" if cuantas == 1 else f"{cuantas} piezas"
        texto = (f"Agrega {piezas} «{etiqueta}»: un {forma} de cerca de {medidas} (X × Y × Z). Shift + A › Malla.")
    return Decision(AGREGAR, texto, "", falta.grupo, "falta una pieza del ejemplo")


ORDEN: Tuple[Callable[[Diferencia], Optional[Decision]], ...] = (_girar, _tamano, _agregar)


def decidir(d: Diferencia, reporte=None) -> Decision:
    """La primera regla de ORDEN que tenga algo que decir; si ninguna, lo que diga el motor."""
    for regla in ORDEN:
        decision = regla(d)
        if decision is not None:
            return decision
    actual = getattr(reporte, "current_target_id", None) if reporte is not None else None
    if actual:
        resultado = reporte.result(actual)
        return Decision(SEGUIR, getattr(resultado, "message", "") or "", "", "", f"las piezas están bien; sigue «{actual}»")
    return Decision(LISTO, "Todas las piezas están como en el ejemplo.", "", "", "nada que corregir")
