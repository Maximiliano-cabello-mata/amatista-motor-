"""La diferencia: lo que hay en la escena contra el plano, pieza por pieza.

Todo se mide en la escala del alumno. Si su figura es el doble de grande que
el ejemplo, una rueda «debería medir» el doble: nunca se le pide el número
del ejemplo, sino el que hace que SU figura quede proporcionada.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .plano import PiezaEsperada, Plano

BIEN, FALTA, TAMANO, GIRADA = "bien", "falta", "tamaño", "girada"
EJES = "XYZ"


@dataclass(frozen=True)
class Ajuste:
    tipo: str  # TAMANO o GIRADA
    eje: str  # «X», «Y» o «Z»: el lado que no cuadra
    actual: float  # metros, en la escena del alumno
    esperado: float  # metros, en la escala del alumno


@dataclass(frozen=True)
class EstadoPieza:
    grupo: str
    esperada: str  # nombre de la pieza del ejemplo
    estado: str  # BIEN, FALTA, TAMANO o GIRADA
    objeto: str = ""  # el objeto del alumno («Cylinder.003»); vacío si falta
    ajuste: Optional[Ajuste] = None


@dataclass(frozen=True)
class Diferencia:
    plano: Plano
    piezas: Tuple[EstadoPieza, ...]
    escala: float  # tamaño de la figura del alumno / tamaño del ejemplo
    girada: bool  # la figura del alumno está girada un cuarto de vuelta en el suelo
    sobran: Dict[str, int] = field(default_factory=dict)  # grupo → piezas de más

    @property
    def total(self) -> int:
        return len(self.piezas)

    @property
    def bien(self) -> int:
        return sum(1 for p in self.piezas if p.estado == BIEN)

    def con_estado(self, estado: str) -> Tuple[EstadoPieza, ...]:
        return tuple(p for p in self.piezas if p.estado == estado)

    def faltan(self, grupo: str) -> int:
        return sum(1 for p in self.piezas if p.grupo == grupo and p.estado == FALTA)


def _medidas(obj) -> Tuple[float, float, float]:
    minimo, maximo = obj.caja()
    return tuple(max(0.0, maximo[i] - minimo[i]) for i in range(3))


def _orientar(medidas: Sequence[float], girada: bool) -> Tuple[float, float, float]:
    return (medidas[1], medidas[0], medidas[2]) if girada else tuple(medidas)


def _fuera(actual: float, esperado: float, tolerancia: float) -> bool:
    if esperado <= 1e-6:  # un plano: sin grosor que comparar
        return False
    razon = actual / esperado
    return razon > 1 + tolerancia or razon < 1 / (1 + tolerancia)


def _error(medidas: Sequence[float], esperadas: Sequence[float], escala: float) -> float:
    return sum(abs(a - e * escala) / (e * escala) for a, e in zip(medidas, esperadas) if e > 1e-6)


def _por_grupo(escena, reporte, plano: Plano) -> Tuple[Dict[str, List], List]:
    """Las mallas del alumno según lo que son (por su rol, puesto o deducido, o por su primitiva)
    y las que no se reconocieron como nada."""
    deducidos = dict(getattr(reporte, "inferred_roles", ()) or ()) if reporte is not None else {}
    grupos: Dict[str, List] = {g: [] for g in plano.grupos}
    sueltas: List = []
    for obj in escena.objects:
        if obj.object_type != "MESH":
            continue
        rol = (obj.roles[0] if obj.roles else "") or deducidos.get(obj.name, "")
        if rol in grupos:
            grupos[rol].append(obj)
        elif not rol and obj.primitive in grupos:
            grupos[obj.primitive].append(obj)
        else:
            sueltas.append(obj)
    return grupos, sueltas


def _escala(grupos: Dict[str, List], plano: Plano) -> float:
    """Cuánto más grande (o chica) es la figura del alumno: la mediana, pieza por pieza, de su lado mayor."""
    razones = []
    for grupo, objetos in grupos.items():
        modelo = [max(p.medidas) for p in plano.del_grupo(grupo) if max(p.medidas) > 1e-6]
        if not modelo:
            continue
        tipico = statistics.median(modelo)
        razones += [max(_medidas(o)) / tipico for o in objetos if max(_medidas(o)) > 1e-6]
    return statistics.median(razones) if razones else 1.0


def _figura_girada(grupos: Dict[str, List], plano: Plano, escala: float) -> bool:
    """¿Cuadra mejor la figura girada un cuarto de vuelta en el suelo (X por Y)?"""
    recta = girada = 0.0
    for grupo, objetos in grupos.items():
        esperadas = plano.del_grupo(grupo)
        if not esperadas:
            continue
        for obj in objetos:
            medidas = _medidas(obj)
            recta += min(_error(medidas, p.medidas, escala) for p in esperadas)
            girada += min(_error(_orientar(medidas, True), p.medidas, escala) for p in esperadas)
    return girada < recta - 1e-9


def _juzgar(obj, esperada: PiezaEsperada, escala: float, girada: bool, tolerancia: float) -> Tuple[str, Optional[Ajuste]]:
    reales = _medidas(obj)
    medidas = _orientar(reales, girada)
    quiere = tuple(m * escala for m in esperada.medidas)
    mal = [i for i in range(3) if _fuera(medidas[i], quiere[i], tolerancia)]
    if not mal:
        return BIEN, None
    peor = max(mal, key=lambda i: abs(medidas[i] - quiere[i]) / quiere[i])
    eje = EJES[(1 - peor) if girada and peor < 2 else peor]  # de vuelta a los ejes del alumno
    # ¿Tiene las medidas correctas pero en otros ejes? Entonces no hay que escalarla: hay que girarla.
    ordenadas, ordenadas_q = sorted(medidas), sorted(quiere)
    if not any(_fuera(a, q, tolerancia) for a, q in zip(ordenadas, ordenadas_q)):
        return GIRADA, Ajuste(GIRADA, eje, round(medidas[peor], 3), round(quiere[peor], 3))
    return TAMANO, Ajuste(TAMANO, eje, round(medidas[peor], 3), round(quiere[peor], 3))


def comparar(plano: Plano, escena, reporte=None, tolerancia: Optional[float] = None) -> Diferencia:
    """Empareja cada pieza del plano con un objeto del alumno y dice cómo está."""
    tol = plano.tolerancia if tolerancia is None else tolerancia
    grupos, sueltas = _por_grupo(escena, reporte, plano)
    escala = _escala(grupos, plano)
    girada = _figura_girada(grupos, plano, escala)

    def cercania(esperada: PiezaEsperada):
        return lambda o: _error(_orientar(_medidas(o), girada), esperada.medidas, escala)

    # Primera vuelta: cada pieza del ejemplo con el objeto de su grupo que mejor le queda.
    piezas: List[Optional[EstadoPieza]] = []
    faltantes: List[Tuple[int, PiezaEsperada]] = []
    restos: Dict[str, List] = {}
    for grupo in plano.grupos:
        libres = list(grupos.get(grupo, ()))
        for esperada in plano.del_grupo(grupo):
            if not libres:
                faltantes.append((len(piezas), esperada))
                piezas.append(None)
                continue
            obj = min(libres, key=cercania(esperada))
            libres.remove(obj)
            estado, ajuste = _juzgar(obj, esperada, escala, girada, tol)
            piezas.append(EstadoPieza(grupo, esperada.nombre, estado, obj.name, ajuste))
        restos[grupo] = libres

    # Segunda vuelta: una pieza que «falta» casi siempre está en la escena, deformada al punto
    # de no reconocerse (una rueda tan gruesa que parece otra cosa) o contada en otro grupo.
    # Si sobra un objeto de la misma primitiva, es esa pieza y hay que decir qué corregirle.
    for indice, esperada in faltantes:
        candidatos = [o for o in sueltas if o.primitive == esperada.primitiva]
        candidatos += [o for g, lista in restos.items() if g != esperada.grupo for o in lista
                       if o.primitive == esperada.primitiva]
        if not candidatos:
            piezas[indice] = EstadoPieza(esperada.grupo, esperada.nombre, FALTA)
            continue
        obj = min(candidatos, key=cercania(esperada))
        if obj in sueltas:
            sueltas.remove(obj)
        for lista in restos.values():
            if obj in lista:
                lista.remove(obj)
        estado, ajuste = _juzgar(obj, esperada, escala, girada, tol)
        piezas[indice] = EstadoPieza(esperada.grupo, esperada.nombre, estado, obj.name, ajuste)

    sobran = {g: len(lista) for g, lista in restos.items() if lista}
    return Diferencia(plano, tuple(p for p in piezas if p is not None), round(escala, 4), girada, sobran)
