"""El molde: qué pieza del modelo ya llenó el alumno y, si no, por qué.

En «Hazlo conmigo» (niveles 1 y 2) cada pieza del modelo se dibuja
translúcida en la vista 3D, en su lugar y con su tamaño. Este módulo decide
de qué color va cada una:

- **llena** (verde): una pieza del alumno con la misma forma la ocupa;
- **casi** (ámbar): la forma es la correcta, pero está girada, le falta o le
  sobra tamaño en un eje, o va en otro lugar;
- **equivocada** (coral): hay algo en su lugar, pero es otra forma (un cubo
  donde va un cilindro);
- **vacía** (azul): todavía no hay nada.

Y lo dice sobre el modelo, sin números (regla 7 de la investigación): «a la
chimenea le falta altura», «la rueda va de pie, no acostada», «el vagón
flota». Es la diferencia mostrada sobre el modelo, como en CADuBoost.

Dos modos:

- ``molde``: el alumno construye dentro del molde; importan el lugar y el
  tamaño (con la holgura de su nivel).
- ``libre``: sin molde (Hazlo tú, retos y repasos); la figura se acomoda
  sola al modelo (se centra, se apoya en el suelo, se prueba girada de a 90°
  y, hasta el nivel 3, se lleva al tamaño del modelo). Importan la forma de
  cada pieza, sus proporciones y cómo se acomodan entre sí.

Python puro y determinista: el add-on lo dibuja, el validador
``taller.molde`` lo usa para aprobar y las pruebas lo revisan sin Blender.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..models import SceneObject, SceneState
from ..validators.base import primitiva
from ..validators.figure import NOMBRE_PRIMITIVA, caja_de_pieza

LLENA = "llena"
CASI = "casi"
EQUIVOCADA = "equivocada"
VACIA = "vacia"
ESTADOS = (LLENA, CASI, EQUIVOCADA, VACIA)

FALTA, FORMA, GIRO, TAMANO, LUGAR, FLOTA = "falta", "forma", "giro", "tamano", "lugar", "flota"

# Holgura por nivel: tamaño (veces), lugar (en «unidades» de la pieza) y altura sobre el suelo.
# Motor 6: más estrictas en los niveles 1 a 3 (con 1.8 veces, un cubo de 2 m pasaba por uno de 3,6 m).
TAMANO_POR_NIVEL = {1: 1.5, 2: 1.4, 3: 1.3, 4: 1.2, 5: 1.1}
LUGAR_POR_NIVEL = {1: 0.8, 2: 0.7, 3: 0.55, 4: 0.45, 5: 0.3}
# Cordura (motor 6): con demasiadas piezas sueltas, llenar el molde puede ser casualidad.
SOBRAN_MAXIMO = 3
# Vértices y caras de cada primitiva recién agregada: reconoce la forma aunque la malla se renombre.
FIRMAS = {(8, 6): "cube", (4, 1): "plane", (32, 0): "circle", (64, 34): "cylinder", (33, 33): "cone",
          (482, 480): "sphere", (42, 80): "sphere", (576, 576): "torus", (507, 500): "suzanne"}
SUELO = 0.03  # una pieza del modelo cuya base está a menos de esto va apoyada en el suelo

# La habilidad que arregla cada motivo (las del módulo 1 de Blender); un taller puede usar otras.
HABILIDAD_DE_MOTIVO = {
    FALTA: "bl-agregar-primitivas",
    FORMA: "bl-agregar-primitivas",
    GIRO: "bl-rotar",
    TAMANO: "bl-escalar-eje",
    LUGAR: "bl-mover",
    FLOTA: "bl-mover",
}
EJES = "XYZ"
MEDIDA_EJE = {0: "largo", 1: "ancho", 2: "altura"}
HACIA = {(0, 1): "más a la derecha", (0, -1): "más a la izquierda", (1, 1): "más atrás", (1, -1): "más adelante",
         (2, 1): "más arriba", (2, -1): "más abajo"}
MALLA = {"cube": "Cubo", "cylinder": "Cilindro", "sphere": "Esfera UV", "icosphere": "Icoesfera", "cone": "Cono",
         "torus": "Toroide", "plane": "Plano", "circle": "Círculo", "suzanne": "Mono"}
UN = {"cube": "un cubo", "cylinder": "un cilindro", "sphere": "una esfera", "icosphere": "una esfera", "cone": "un cono",
      "torus": "una dona", "plane": "un plano", "circle": "un círculo", "suzanne": "un mono"}
PARECIDAS = {"icosphere": "sphere"}


@dataclass(frozen=True)
class PiezaRevisada:
    indice: int
    nombre: str
    primitiva: str
    estado: str  # llena | casi | equivocada | vacia
    motivo: str = ""  # falta | forma | giro | tamano | lugar | flota
    mensaje: str = ""  # la frase sobre el modelo, sin números
    objeto: str = ""  # la pieza del alumno que la ocupa
    eje: int = -1
    teclas: Tuple[str, ...] = ()  # cómo se arregla (solo se muestra si la ayuda lo permite)
    habilidad: str = ""  # la habilidad que arregla este motivo
    centro: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # dónde se dibuja el molde (mundo)
    medidas: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    giro: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # grados, como reference.parts


@dataclass(frozen=True)
class RevisionMolde:
    piezas: Tuple[PiezaRevisada, ...]
    modo: str
    nivel: int
    actual: Optional[int] = None  # la pieza que toca (la que el alumno está haciendo o la siguiente vacía)
    adornos: int = 0  # piezas del alumno que no ocupan ninguna pieza del modelo (libertad creativa)
    giro_z: int = 0  # libre: grados que se giró la figura del alumno para acomodarla
    escala: float = 1.0  # libre: veces que se agrandó (>1) o achicó la figura para acomodarla
    detalles: Dict[str, Any] = field(default_factory=dict)
    revuelto: bool = False  # motor 6: tantas piezas de más que llenar el molde no prueba nada

    @property
    def total(self) -> int:
        return len(self.piezas)

    @property
    def llenas(self) -> int:
        return sum(1 for p in self.piezas if p.estado == LLENA)

    @property
    def completa(self) -> bool:
        return bool(self.piezas) and self.llenas == self.total and not self.revuelto

    @property
    def pieza_actual(self) -> Optional[PiezaRevisada]:
        return self.piezas[self.actual] if self.actual is not None else None

    @property
    def mensaje(self) -> str:
        if self.revuelto:
            return "Hay muchas piezas de más: borra las que sobran (X) y deja solo las del molde."
        p = self.pieza_actual
        if p is None:
            return "Listo: cada pieza está en su lugar." if self.completa else ""
        return p.mensaje

    def a_dict(self) -> Dict[str, Any]:
        return {
            "modo": self.modo,
            "nivel": self.nivel,
            "total": self.total,
            "llenas": self.llenas,
            "completa": self.completa,
            "actual": self.actual,
            "mensaje": self.mensaje,
            "adornos": self.adornos,
            "revuelto": self.revuelto,
            "piezas": [
                {"indice": p.indice, "nombre": p.nombre, "primitiva": p.primitiva, "estado": p.estado, "motivo": p.motivo,
                 "mensaje": p.mensaje, "objeto": p.objeto, "teclas": list(p.teclas), "habilidad": p.habilidad,
                 "centro": [round(x, 4) for x in p.centro], "medidas": [round(x, 4) for x in p.medidas],
                 "giro": list(p.giro)}
                for p in self.piezas
            ],
        }


# --- Geometría ---------------------------------------------------------------------------------


@dataclass
class _Caja:
    centro: Tuple[float, float, float]
    medidas: Tuple[float, float, float]
    familia: str
    nombre: str = ""

    @property
    def largo(self) -> float:
        return max(self.medidas) or 0.01

    @property
    def base(self) -> float:
        return self.centro[2] - self.medidas[2] / 2


def _familia(nombre: str) -> str:
    base = primitiva(nombre)
    return PARECIDAS.get(base, base)


def _caja_modelo(pieza: Dict[str, Any]) -> _Caja:
    minimo, maximo = caja_de_pieza(pieza)
    return _Caja(tuple((a + b) / 2 for a, b in zip(minimo, maximo)), tuple(b - a for a, b in zip(minimo, maximo)),
                 _familia(pieza.get("primitive", "")))


def _familia_de_objeto(obj: SceneObject) -> str:
    familia = _familia(obj.primitive)
    if familia in UN or obj.vertices is None:
        return familia
    return FIRMAS.get((int(obj.vertices), int(obj.faces or 0)), familia)


def _caja_alumno(obj: SceneObject) -> _Caja:
    minimo, maximo = obj.caja()
    return _Caja(tuple((a + b) / 2 for a, b in zip(minimo, maximo)), tuple(max(0.0, b - a) for a, b in zip(minimo, maximo)),
                 _familia_de_objeto(obj), obj.name)


def _union(cajas: Sequence[_Caja]) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    minimo = tuple(min(c.centro[i] - c.medidas[i] / 2 for c in cajas) for i in range(3))
    maximo = tuple(max(c.centro[i] + c.medidas[i] / 2 for c in cajas) for i in range(3))
    return minimo, maximo


def _acomodar(alumno: Sequence[_Caja], modelo: Sequence[_Caja], giros: int, escala_libre: bool):
    """La figura del alumno girada `giros` cuartos de vuelta, en el lugar (y el tamaño) del modelo."""
    (amin, amax), (mmin, mmax) = _union(alumno), _union(modelo)
    acentro = ((amin[0] + amax[0]) / 2, (amin[1] + amax[1]) / 2)
    mcentro = ((mmin[0] + mmax[0]) / 2, (mmin[1] + mmax[1]) / 2)
    largo_a = max(b - a for a, b in zip(amin, amax)) or 1.0
    largo_m = max(b - a for a, b in zip(mmin, mmax)) or 1.0
    escala = min(2.5, max(0.4, largo_m / largo_a)) if escala_libre else 1.0
    salida = []
    for c in alumno:
        x, y = c.centro[0] - acentro[0], c.centro[1] - acentro[1]
        dx, dy = c.medidas[0], c.medidas[1]
        for _ in range(giros % 4):
            x, y = -y, x
            dx, dy = dy, dx
        z = c.centro[2] - amin[2]
        salida.append(_Caja(
            (mcentro[0] + x * escala, mcentro[1] + y * escala, mmin[2] + z * escala),
            (dx * escala, dy * escala, c.medidas[2] * escala),
            c.familia,
            c.nombre,
        ))
    return salida, escala


def _error_tamano(a: Sequence[float], b: Sequence[float], largo: float) -> Tuple[float, int, float]:
    """(peor error en log, eje, signo) entre medidas por eje. signo > 0: al alumno le sobra."""
    eps = 0.06 * largo + 0.02
    peor, eje, signo = 0.0, -1, 0.0
    for i in range(3):
        e = math.log((a[i] + eps) / (b[i] + eps))
        if abs(e) > peor:
            peor, eje, signo = abs(e), i, e
    return peor, eje, signo


def _error_tamano_sin_giro(a: Sequence[float], b: Sequence[float], largo: float) -> float:
    eps = 0.06 * largo + 0.02
    return max(abs(math.log((x + eps) / (y + eps))) for x, y in zip(sorted(a), sorted(b)))


def _misma_forma(a: _Caja, m: _Caja, estricta: bool = False) -> bool:
    """La misma primitiva; una malla sin primitiva conocida (unida o editada) puede ser cualquiera.

    Motor 6: en los niveles 1 y 2 (estricta) el alumno solo agrega primitivas, así que una malla
    que no se reconoce ni por nombre ni por sus vértices no llena ninguna pieza.
    """
    return a.familia == m.familia or (a.familia not in UN and not estricta)


def _unidad(m: _Caja) -> float:
    return 0.35 * m.largo + 0.15


def _error_lugar(a: _Caja, m: _Caja) -> float:
    return math.dist(a.centro, m.centro) / _unidad(m)


# --- Emparejar -------------------------------------------------------------------------------


def _emparejar(alumno: Sequence[_Caja], modelo: Sequence[_Caja], tol_lugar: float, tol_tamano: float,
               estricta: bool = False):
    """{índice de pieza: índice de caja del alumno} con el menor costo total (codicioso, determinista)."""
    pares = []
    for j, m in enumerate(modelo):
        for i, a in enumerate(alumno):
            lugar = _error_lugar(a, m)
            if lugar > 3.0 * tol_lugar + 1.0:
                continue
            mismo = _misma_forma(a, m, estricta)
            tam = min(_error_tamano_sin_giro(a.medidas, m.medidas, m.largo), 2.0)
            costo = lugar / max(tol_lugar, 0.01) + 0.8 * tam / max(tol_tamano, 0.01) + (0.0 if mismo else 6.0)
            pares.append((costo, j, i))
    pares.sort()
    asignadas: Dict[int, int] = {}
    usadas = set()
    costo_total = 0.0
    for costo, j, i in pares:
        if j in asignadas or i in usadas:
            continue
        asignadas[j] = i
        usadas.add(i)
        costo_total += costo
    return asignadas, costo_total


# --- Mensajes sobre el modelo ----------------------------------------------------------------


def _nombre(pieza: Dict[str, Any], indice: int, etiquetas: Dict[str, str]) -> str:
    if pieza.get("name"):
        return str(pieza["name"])
    rol = pieza.get("role") or ""
    if rol:
        return etiquetas.get(rol) or rol.replace("_", " ").replace("-", " ").capitalize()
    return NOMBRE_PRIMITIVA.get(pieza.get("primitive", ""), "Pieza").capitalize()


def _delgado(medidas: Sequence[float]) -> int:
    return min(range(3), key=lambda i: medidas[i])


def _frase_giro(nombre: str, alumno: Sequence[float], modelo: Sequence[float]) -> str:
    a, m = _delgado(alumno), _delgado(modelo)
    if m != 2 and a == 2:
        return f"«{nombre}» va de pie, no acostada."
    if m == 2 and a != 2:
        return f"«{nombre}» va acostada, no de pie."
    largo_a = max(range(3), key=lambda i: alumno[i])
    largo_m = max(range(3), key=lambda i: modelo[i])
    if largo_m == 2 and largo_a != 2:
        return f"«{nombre}» va parada, apuntando hacia arriba."
    if largo_m != 2 and largo_a == 2:
        return f"«{nombre}» va echada, no parada."
    return f"«{nombre}» va girada de otra forma: dale un cuarto de vuelta."


def _girada(alumno: Sequence[float], modelo: Sequence[float]) -> bool:
    """¿La pieza está girada? Su eje más delgado (o más largo) apunta a otro lado que en el modelo.

    Solo cuentan los ejes que se distinguen de verdad: un cilindro corto y uno
    alto apuntan igual (los dos de pie); solo cambia la altura.
    """
    def clave(d):
        orden = sorted(range(3), key=lambda i: d[i])
        e = [d[i] + 0.01 for i in orden]
        return (orden[0] if e[1] / e[0] > 1.3 else None), (orden[2] if e[2] / e[1] > 1.3 else None)

    (chico_a, largo_a), (chico_m, largo_m) = clave(alumno), clave(modelo)
    return (chico_a is not None and chico_m is not None and chico_a != chico_m) or (
        largo_a is not None and largo_m is not None and largo_a != largo_m)


def _eje_del_giro(alumno: Sequence[float], modelo: Sequence[float]) -> int:
    """El eje sobre el que hay que girar: el que no cambia de lugar entre las dos cajas."""
    for eje in range(3):
        otros = [i for i in range(3) if i != eje]
        if (abs(math.log((alumno[otros[0]] + 0.01) / (modelo[otros[1]] + 0.01))) < 0.4
                and abs(math.log((alumno[otros[1]] + 0.01) / (modelo[otros[0]] + 0.01))) < 0.4):
            return eje
    return 0


def _revisar_pieza(indice: int, pieza: Dict[str, Any], m: _Caja, a: Optional[_Caja], nivel: int, nombre: str,
                   modo: str, apoyada: bool) -> PiezaRevisada:
    tol_tamano = math.log(TAMANO_POR_NIVEL[nivel])
    tol_lugar = LUGAR_POR_NIVEL[nivel]
    base = {
        "indice": indice, "nombre": nombre, "primitiva": pieza.get("primitive", ""),
        "centro": tuple(pieza.get("location") or (0.0, 0.0, 0.0)),
        "medidas": tuple(pieza.get("size") or (1.0, 1.0, 1.0)),
        "giro": tuple(pieza.get("rotation") or (0.0, 0.0, 0.0)),
    }
    prim = pieza.get("primitive", "")
    if a is None:
        return PiezaRevisada(
            **base, estado=VACIA, motivo=FALTA,
            mensaje=f"Aquí va «{nombre}» ({UN.get(prim, 'una pieza')})." if modo == "molde" else f"Falta «{nombre}» ({UN.get(prim, 'una pieza')}).",
            teclas=("Shift+A", "Malla", MALLA.get(prim, "")) if prim in MALLA else ("Shift+A",),
            habilidad=HABILIDAD_DE_MOTIVO[FALTA],
        )
    if not _misma_forma(a, m, nivel <= 2):
        return PiezaRevisada(
            **base, estado=EQUIVOCADA, motivo=FORMA, objeto=a.nombre,
            mensaje=f"«{nombre}» es {UN.get(m.familia, 'otra forma')}; aquí hay {UN.get(a.familia, 'otra forma')}.",
            teclas=("X", "Shift+A", MALLA.get(prim, "")) if prim in MALLA else ("X", "Shift+A"),
            habilidad=HABILIDAD_DE_MOTIVO[FORMA],
        )
    error, eje, signo = _error_tamano(a.medidas, m.medidas, m.largo)
    sin_giro = _error_tamano_sin_giro(a.medidas, m.medidas, m.largo)
    simetrica = m.familia in ("sphere",)  # una esfera no tiene «de pie»
    if error > tol_tamano and sin_giro <= tol_tamano and not simetrica and _girada(a.medidas, m.medidas):
        giro_eje = _eje_del_giro(a.medidas, m.medidas)
        return PiezaRevisada(
            **base, estado=CASI, motivo=GIRO, objeto=a.nombre, eje=giro_eje,
            mensaje=_frase_giro(nombre, a.medidas, m.medidas),
            teclas=("R", EJES[giro_eje], "90"), habilidad=HABILIDAD_DE_MOTIVO[GIRO],
        )
    if error > tol_tamano:
        verbo = "le sobra" if signo > 0 else "le falta"
        return PiezaRevisada(
            **base, estado=CASI, motivo=TAMANO, objeto=a.nombre, eje=eje,
            mensaje=f"A «{nombre}» {verbo} {MEDIDA_EJE[eje]}.",
            teclas=("S", EJES[eje]), habilidad=HABILIDAD_DE_MOTIVO[TAMANO],
        )
    if apoyada and a.base > max(0.06, 0.15 * m.medidas[2]) * (2.0 if nivel <= 2 else 1.0):
        return PiezaRevisada(
            **base, estado=CASI, motivo=FLOTA, objeto=a.nombre, eje=2,
            mensaje=f"«{nombre}» flota: tiene que tocar el suelo.",
            teclas=("G", "Z"), habilidad=HABILIDAD_DE_MOTIVO[FLOTA],
        )
    lugar = _error_lugar(a, m)
    if lugar > tol_lugar:
        delta = [m.centro[i] - a.centro[i] for i in range(3)]
        eje = max(range(3), key=lambda i: abs(delta[i]))
        hacia = HACIA[(eje, 1 if delta[eje] > 0 else -1)]
        poco = "un poco " if lugar < 2 * tol_lugar else ""
        return PiezaRevisada(
            **base, estado=CASI, motivo=LUGAR, objeto=a.nombre, eje=eje,
            mensaje=f"«{nombre}» va {poco}{hacia}.",
            teclas=("G", EJES[eje]), habilidad=HABILIDAD_DE_MOTIVO[LUGAR],
        )
    return PiezaRevisada(**base, estado=LLENA, objeto=a.nombre, mensaje=f"«{nombre}» lista.")


def _mallas(scene: SceneState, ignorar: Sequence[str]) -> List[SceneObject]:
    return [o for o in scene.objects if o.object_type == "MESH" and o.name not in ignorar
            and not any(t == "amatista_ayuda" for t in o.tags)]


def revisar_molde(piezas: Sequence[Dict[str, Any]], scene: SceneState, modo: str = "molde", nivel: int = 1,
                  etiquetas: Optional[Dict[str, str]] = None, ignorar: Sequence[str] = ()) -> RevisionMolde:
    """Revisa la escena contra las piezas del modelo (las que se comparan: compare != false)."""
    nivel = max(1, min(5, int(nivel or 1)))
    etiquetas = etiquetas or {}
    lista = [p for p in piezas if p.get("compare", True) is not False]
    modelo = [_caja_modelo(p) for p in lista]
    alumno = [_caja_alumno(o) for o in _mallas(scene, ignorar)]
    tol_lugar = LUGAR_POR_NIVEL[nivel]
    tol_tamano = math.log(TAMANO_POR_NIVEL[nivel])
    giro_z, escala = 0, 1.0
    if modo == "libre" and alumno and modelo:
        mejor = None
        for giros in range(4):
            acomodadas, s = _acomodar(alumno, modelo, giros, escala_libre=nivel <= 3)
            asignadas, costo = _emparejar(acomodadas, modelo, tol_lugar, tol_tamano, nivel <= 2)
            costo += 8.0 * (len(modelo) - len(asignadas))
            if mejor is None or costo < mejor[0] - 1e-9:
                mejor = (costo, giros, acomodadas, s, asignadas)
        _, giros, alumno, escala, asignadas = mejor
        giro_z = 90 * giros
    else:
        asignadas, _ = _emparejar(alumno, modelo, tol_lugar, tol_tamano, nivel <= 2)
    piso = min((c.base for c in modelo), default=0.0)
    revisadas = []
    for j, (pieza, m) in enumerate(zip(lista, modelo)):
        a = alumno[asignadas[j]] if j in asignadas else None
        apoyada = m.base - piso <= SUELO
        revisadas.append(_revisar_pieza(j, pieza, m, a, nivel, _nombre(pieza, j, etiquetas), modo, apoyada))
    trabajando = next((p.indice for p in revisadas if p.estado in (CASI, EQUIVOCADA)), None)
    actual = trabajando if trabajando is not None else next((p.indice for p in revisadas if p.estado == VACIA), None)
    adornos = max(0, len(alumno) - len(asignadas))
    revuelto = modo == "molde" and adornos > max(SOBRAN_MAXIMO, 2 * len(modelo))
    return RevisionMolde(tuple(revisadas), modo, nivel, actual, adornos, giro_z, escala, revuelto=revuelto)


__all__ = [
    "CASI", "EQUIVOCADA", "ESTADOS", "FALTA", "FLOTA", "FORMA", "GIRO", "HABILIDAD_DE_MOTIVO", "LLENA", "LUGAR",
    "PiezaRevisada", "RevisionMolde", "TAMANO", "VACIA", "revisar_molde",
]
