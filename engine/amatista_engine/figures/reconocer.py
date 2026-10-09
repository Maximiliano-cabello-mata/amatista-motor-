"""Reconocimiento de figuras (motor 3.4).

El motor ya no necesita que el alumno le diga qué es cada pieza: la
reconoce por su forma y por su lugar, como lo hace una persona. La idea
viene de la teoría de reconocimiento por componentes (Biederman, 1987):
un objeto se identifica por sus partes simples (cajas, cilindros, esferas)
Y por cómo se relacionan (encima de, a los dos lados, tocando el suelo).
Una taza y una cubeta tienen las mismas partes; cambia la relación.

Tres preguntas, en este orden:

1. ¿Qué es cada pieza? (``inferir_roles``) Cada malla sin rol toma el rol
   del modelo cuya forma se le parece más (primitiva y proporciones, sin
   importar el tamaño). Los roles que puso el alumno se respetan.
2. ¿La figura tiene sentido? (``relaciones_del_modelo`` y ``revisar``) Del
   modelo se deducen solas las relaciones que importan: qué toca el suelo,
   qué va apoyado encima de qué, qué piezas se tocan, qué grupos van a los
   dos lados. La figura del alumno debe cumplirlas aunque sus medidas sean
   otras. Además nada debe flotar.
3. ¿Qué figura es? (``identificar``) Se compara con la biblioteca de
   figuras conocidas: si se parece más a una mesa que a un tren, se dice.

La exigencia depende del nivel (``PERFILES``): al nivel 1 le basta una
forma identificable; en el 5 se piden las medidas del modelo en metros.
Las piezas de decoración que no se parecen a ninguna del modelo no restan:
el alumno tiene libertad creativa mientras la figura siga reconocible.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..models import SceneObject, SceneState
from ..validators.base import primitiva
from ..validators.figure import (
    EPSILON,
    ORIENTACIONES,
    _Caja,
    _cajas_modelo,
    _emparejar,
    _grupo,
    _orientar,
    _union,
    caja_de_pieza,
    comparar,
)

BIBLIOTECA = Path(__file__).with_name("biblioteca.json")


# --- Exigencia por nivel ---------------------------------------------------------------


@dataclass(frozen=True)
class Perfil:
    """Cuánto se exige: medidas, parecido mínimo, relaciones y escala real."""

    id: str
    nombre: str
    tolerancia: float  # holgura de medidas relativas (0.6 = ±60 %)
    min_score: float  # parecido total para aprobar
    relaciones: float  # parte de las relaciones que deben cumplirse
    peso_relaciones: float  # cuánto pesan las relaciones en el parecido total
    holgura: float  # multiplica la holgura de contacto y de suelo
    min_forma: float  # parecido mínimo de piezas y proporciones (sin las relaciones)
    escala_real: Optional[float] = None  # None: tamaño libre; 1.25: ±25 % del tamaño del modelo


PERFILES: Dict[str, Perfil] = {
    p.id: p
    for p in (
        Perfil("forma", "Forma identificable", 0.60, 0.55, 0.75, 0.50, 2.0, 0.40),
        Perfil("proporcion", "Forma y proporción", 0.45, 0.65, 0.80, 0.40, 1.5, 0.50),
        Perfil("cercana", "Proporción cercana", 0.35, 0.70, 0.85, 0.30, 1.0, 0.60),
        Perfil("medidas", "Medidas cercanas", 0.20, 0.80, 1.00, 0.20, 0.75, 0.75, 1.25),
        Perfil("exacta", "Medidas exactas", 0.10, 0.88, 1.00, 0.20, 0.5, 0.85, 1.10),
    )
}
PERFIL_POR_NIVEL = {1: "forma", 2: "proporcion", 3: "cercana", 4: "medidas", 5: "exacta"}


def perfil_para(nivel: int, exigencia: str = "") -> Perfil:
    """El perfil que fija la práctica («strictness») o el de su nivel."""
    if exigencia in PERFILES:
        return PERFILES[exigencia]
    return PERFILES[PERFIL_POR_NIVEL.get(max(1, min(5, int(nivel or 1))), "forma")]


# --- 1. ¿Qué es cada pieza? -------------------------------------------------------------

# Primitivas que se pueden confundir sin castigo (una esfera UV o una icoesfera).
PARECIDAS = {"icosphere": "sphere"}
# Primitivas de Blender: una de estas que el modelo no usa es adorno (un faro esférico en el tren).
CONOCIDAS = {"cube", "cylinder", "sphere", "cone", "torus", "plane", "circle", "suzanne"}


def _familia(nombre: str) -> str:
    base = primitiva(nombre)
    return PARECIDAS.get(base, base)


def _forma(medidas: Sequence[float]) -> Tuple[float, float, float]:
    """Proporciones ordenadas (de la más chica a 1): no dependen del tamaño ni del giro."""
    grande = max(medidas) or 1.0
    return tuple(sorted((m + EPSILON * grande) / grande for m in medidas))


def _error_forma(a: Sequence[float], b: Sequence[float]) -> float:
    return max(abs(math.log(x / y)) for x, y in zip(_forma(a), _forma(b)))


@dataclass(frozen=True)
class _Prototipo:
    grupo: str
    familia: str
    medidas: Tuple[float, float, float]
    relativa: float  # lado más largo de la pieza / lado más largo de la figura


def _prototipos(partes: Sequence[Dict[str, Any]]) -> List[_Prototipo]:
    """Una forma por pieza (o por grupo de piezas unidas) del modelo."""
    cajas: Dict[Tuple[str, str], List[Tuple[Tuple[float, ...], Tuple[float, ...]]]] = {}
    familias: Dict[Tuple[str, str], str] = {}
    for i, pieza in enumerate(partes):
        clave = (_grupo(pieza), pieza.get("join") or f"#{i}")
        cajas.setdefault(clave, []).append(caja_de_pieza(pieza))
        familias.setdefault(clave, _familia(pieza.get("primitive", "")))
    todas = [c for lista in cajas.values() for c in lista]
    largo = max(max(c[1][i] for c in todas) - min(c[0][i] for c in todas) for i in range(3)) or 1.0
    salida = []
    for clave, lista in cajas.items():
        minimo = tuple(min(c[0][i] for c in lista) for i in range(3))
        maximo = tuple(max(c[1][i] for c in lista) for i in range(3))
        medidas = tuple(b - a for a, b in zip(minimo, maximo))
        salida.append(_Prototipo(clave[0], familias[clave], medidas, max(medidas) / largo))
    return salida


def _medidas(obj: SceneObject) -> Tuple[float, float, float]:
    minimo, maximo = obj.caja()
    return tuple(max(0.0, maximo[i] - minimo[i]) for i in range(3))


def _mallas(scene: SceneState) -> List[SceneObject]:
    return [o for o in scene.objects if o.object_type == "MESH"]


def inferir_roles(partes: Sequence[Dict[str, Any]], objetos: Sequence[SceneObject],
                  usar_roles: bool = True) -> Dict[str, str]:
    """{nombre del objeto: rol} para las mallas sin rol que se parecen a una pieza con rol.

    Primero la primitiva (un cilindro solo puede ser rueda o chimenea), luego
    la forma sin importar el tamaño (la rueda es plana, la chimenea alargada)
    y, si la figura ya tiene varias piezas, el tamaño respecto de la figura:
    un cubito de adorno no es un vagón. Lo que no se parece a nada queda sin
    rol: es decoración y no cuenta para la figura.
    """
    protos = [p for p in _prototipos(partes) if any(_grupo(x) == p.grupo and x.get("role") for x in partes)]
    if not protos:
        return {}
    pendientes = [o for o in objetos if o.object_type == "MESH" and not (usar_roles and o.roles)]
    if not pendientes:
        return {}
    propuestas: Dict[str, Tuple[str, _Prototipo]] = {}
    for obj in pendientes:
        familia = _familia(obj.primitive)
        candidatos = [p for p in protos if p.familia == familia]
        if not candidatos and familia not in CONOCIDAS:
            # Malla sin primitiva reconocible (unida o renombrada): puede ser cualquier pieza.
            candidatos = list(protos)
        if not candidatos:
            continue
        medidas = _medidas(obj)
        mejor = min(candidatos, key=lambda p: (_error_forma(medidas, p.medidas), p.grupo))
        propuestas[obj.name] = (mejor.grupo, mejor)
    # Segunda vuelta: con la figura armada, lo que es demasiado chico o grande es adorno.
    con_rol = [o for o in objetos if o.object_type == "MESH" and ((usar_roles and o.roles) or o.name in propuestas)]
    if len(con_rol) >= 3:
        cajas = [o.caja() for o in con_rol]
        largo = max(max(c[1][i] for c in cajas) - min(c[0][i] for c in cajas) for i in range(3)) or 1.0
        for obj in pendientes:
            if obj.name not in propuestas:
                continue
            proto = propuestas[obj.name][1]
            relativa = max(_medidas(obj)) / largo
            if proto.relativa > 0 and abs(math.log((relativa + 0.02) / (proto.relativa + 0.02))) > math.log(4.0):
                del propuestas[obj.name]
    return {nombre: grupo for nombre, (grupo, _) in propuestas.items()}


def con_roles(scene: SceneState, roles: Dict[str, str]) -> SceneState:
    """La misma escena con los roles deducidos puestos en sus objetos."""
    if not roles:
        return scene
    from dataclasses import replace

    objetos = tuple(replace(o, roles=(roles[o.name],)) if o.name in roles and not o.roles else o for o in scene.objects)
    return replace(scene, objects=objetos)


# --- 2. ¿La figura tiene sentido? --------------------------------------------------------

SUELO, ENCIMA, TOCA, LADOS, FLOTA = "suelo", "encima", "toca", "lados", "flota"
PESOS = {SUELO: 1.0, ENCIMA: 1.5, TOCA: 1.0, LADOS: 1.5, FLOTA: 1.5}
# Sin estas la figura no tiene sentido en NINGÚN nivel: ruedas en el aire, una
# chimenea flotando, todas las ruedas de un lado. Las demás cuentan para el porcentaje.
CRITICAS = (SUELO, ENCIMA, LADOS, FLOTA)


@dataclass(frozen=True)
class Relacion:
    tipo: str
    grupo: str
    indice: int = -1  # pieza del modelo dentro de su grupo
    otro: str = ""
    otro_indice: int = -1
    eje: int = -1


def _min(c: _Caja, i: int) -> float:
    return c.centro[i] - c.medidas[i] / 2


def _max(c: _Caja, i: int) -> float:
    return c.centro[i] + c.medidas[i] / 2


def _hueco(a: _Caja, b: _Caja) -> float:
    """Distancia entre dos cajas (0 si se tocan o se cruzan)."""
    return math.sqrt(sum(max(0.0, _min(a, i) - _max(b, i), _min(b, i) - _max(a, i)) ** 2 for i in range(3)))


def _sobre(a: _Caja, b: _Caja, holgura: float) -> bool:
    """a descansa encima de b: su base a la altura de la tapa de b y su centro sobre la huella de b."""
    if abs(_min(a, 2) - _max(b, 2)) > holgura:
        return False
    return all(_min(b, i) - holgura <= a.centro[i] <= _max(b, i) + holgura for i in (0, 1))


def _relativas(grupos: Dict[str, List[_Caja]]):
    """Cajas relativas a la figura (centro en 0, lado más largo = 1) y el largo real."""
    todas = [c for cajas in grupos.values() for c in cajas]
    minimo, maximo = _union(todas)
    largo = max(b - a for a, b in zip(minimo, maximo)) or 1.0
    centro = tuple((a + b) / 2 for a, b in zip(minimo, maximo))
    salida = {}
    for g, cajas in grupos.items():
        lista = []
        for c in cajas:
            nueva = _Caja((0, 0, 0), (0, 0, 0), c.nombre)
            nueva.centro = tuple((c.centro[i] - centro[i]) / largo for i in range(3))
            nueva.medidas = tuple(m / largo for m in c.medidas)
            lista.append(nueva)
        salida[g] = lista
    return salida, largo


def relaciones_del_modelo(modelo: Dict[str, List[_Caja]]) -> List[Relacion]:
    """Las relaciones que hacen reconocible la figura, deducidas del modelo."""
    rel, _ = _relativas(modelo)
    piezas = [(g, i, c) for g, cajas in rel.items() for i, c in enumerate(cajas)]
    if len(piezas) < 2:
        return []
    piso = min(_min(c, 2) for _, _, c in piezas)
    salida: List[Relacion] = []
    for g, i, c in piezas:
        if _min(c, 2) - piso <= 0.03:
            salida.append(Relacion(SUELO, g, i))
    for ga, ia, a in piezas:
        for gb, ib, b in piezas:
            if (ga, ia) == (gb, ib):
                continue
            if _sobre(a, b, 0.03) and a.medidas[2] > 0:
                salida.append(Relacion(ENCIMA, ga, ia, gb, ib))
            elif ga < gb or (ga == gb and ia < ib):
                if ga != gb and _hueco(a, b) <= 0.02:
                    salida.append(Relacion(TOCA, ga, ia, gb, ib))
    for g, cajas in rel.items():
        if len(cajas) < 2:
            continue
        for eje in (0, 1):
            if min(c.centro[eje] for c in cajas) < -0.08 and max(c.centro[eje] for c in cajas) > 0.08:
                salida.append(Relacion(LADOS, g, eje=eje))
    return salida


def _alinear(grupos_alumno: Dict[str, List[_Caja]], giro: int, espejo: bool):
    orientadas = {g: [_orientar(c, giro, espejo) for c in cajas] for g, cajas in grupos_alumno.items() if cajas}
    return _relativas(orientadas) if orientadas else ({}, 1.0)


def _parejas(alumno_rel, modelo_rel, tolerancia: float) -> Dict[Tuple[str, int], _Caja]:
    """(grupo, índice de la pieza del modelo) → caja del alumno que le corresponde."""
    tol_med = math.log(1.0 + tolerancia)
    tol_pos = tolerancia * 0.25
    salida = {}
    for g, piezas_m in modelo_rel.items():
        piezas_a = alumno_rel.get(g) or []
        if not piezas_a:
            continue
        for a, m in _emparejar(piezas_a, piezas_m, tol_pos, tol_med):
            salida[(g, piezas_m.index(m))] = a
    return salida


def _flotantes(cajas: Sequence[_Caja], holgura: float) -> List[_Caja]:
    """Piezas que no llegan al suelo por ninguna cadena de piezas que se tocan."""
    if not cajas:
        return []
    piso = min(_min(c, 2) for c in cajas)
    apoyadas = {i for i, c in enumerate(cajas) if _min(c, 2) - piso <= holgura}
    cambio = True
    while cambio:
        cambio = False
        for i, c in enumerate(cajas):
            if i not in apoyadas and any(_hueco(c, cajas[j]) <= holgura for j in apoyadas):
                apoyadas.add(i)
                cambio = True
    return [c for i, c in enumerate(cajas) if i not in apoyadas]


def revisar(relaciones: Sequence[Relacion], modelo: Dict[str, List[_Caja]], grupos_alumno: Dict[str, List[_Caja]],
            orientacion: Dict[str, Any], perfil: Perfil):
    """(parte cumplida 0..1, [(peso, relación, detalle)] de las que fallan)."""
    if not relaciones:
        return 1.0, []
    modelo_rel, _ = _relativas(modelo)
    alumno_rel, largo = _alinear(grupos_alumno, orientacion.get("giro", 0) // 90, orientacion.get("espejo", False))
    if not alumno_rel:
        return 0.0, []
    parejas = _parejas(alumno_rel, modelo_rel, perfil.tolerancia)
    holgura = 0.05 * perfil.holgura
    piso = min(_min(c, 2) for cajas in alumno_rel.values() for c in cajas)
    total = cumplido = 0.0
    fallas = []
    for r in relaciones:
        peso = PESOS[r.tipo]
        detalle: Dict[str, Any] = {}
        if r.tipo == LADOS:
            cajas = alumno_rel.get(r.grupo) or []
            ok = len(cajas) >= 2 and min(c.centro[r.eje] for c in cajas) < -0.02 < 0.02 < max(c.centro[r.eje] for c in cajas)
        else:
            a = parejas.get((r.grupo, r.indice))
            if a is None:
                continue  # la pieza falta: eso ya lo castiga la comparación de forma
            detalle["objeto"] = a.nombre
            if r.tipo == SUELO:
                ok = _min(a, 2) - piso <= holgura * 1.2
            else:
                b = parejas.get((r.otro, r.otro_indice))
                if b is None:
                    continue
                detalle["otro"] = b.nombre
                ok = _sobre(a, b, holgura * 1.6) if r.tipo == ENCIMA else _hueco(a, b) <= holgura
        total += peso
        if ok:
            cumplido += peso
        else:
            fallas.append((peso, r, detalle))
    # Nada flota: si el modelo está apoyado, la figura del alumno también.
    flotan_modelo = _flotantes([c for cajas in modelo_rel.values() for c in cajas], 0.03)
    if not flotan_modelo:
        piezas = [c for cajas in alumno_rel.values() for c in cajas]
        for c in _flotantes(piezas, holgura):
            total += PESOS[FLOTA]
            fallas.append((PESOS[FLOTA], Relacion(FLOTA, ""), {"objeto": c.nombre}))
    parte = cumplido / total if total else 1.0
    return parte, sorted(fallas, key=lambda f: -f[0])


# --- Comparación completa -------------------------------------------------------------------


def agrupar(scene: SceneState, partes: Sequence[Dict[str, Any]], usar_roles: bool = True):
    """(grupos del alumno como cajas, cajas de adorno, roles deducidos)."""
    modelo_grupos = {_grupo(p) for p in partes}
    roles_modelo = {_grupo(p) for p in partes if p.get("role")}
    mallas = _mallas(scene)
    deducidos = inferir_roles(partes, mallas, usar_roles=usar_roles)
    grupos: Dict[str, List[_Caja]] = {g: [] for g in modelo_grupos}
    extras: List[_Caja] = []
    for obj in mallas:
        caja = _Caja(*obj.caja(), nombre=obj.name)
        rol = next((r for r in obj.roles if r in roles_modelo), None) if usar_roles else None
        rol = rol or deducidos.get(obj.name)
        if rol:
            grupos[rol].append(caja)
        elif primitiva(obj.primitive) in modelo_grupos and primitiva(obj.primitive) not in roles_modelo:
            grupos[primitiva(obj.primitive)].append(caja)
        else:
            extras.append(caja)
    return grupos, extras, deducidos


@dataclass
class Reconocimiento:
    puntaje: float  # 0..1, ya con las relaciones
    forma: float  # parecido de piezas y proporciones
    relaciones: float  # parte de las relaciones cumplidas
    peor: Optional[Dict[str, Any]]  # el peor problema de forma (figure.mensaje_de)
    fallas: List[Tuple[float, Relacion, Dict[str, Any]]]
    orientacion: Dict[str, Any]
    deducidos: Dict[str, str]
    adornos: int
    escala: float  # largo del alumno / largo del modelo

    @property
    def criticas(self) -> List[Tuple[float, Relacion, Dict[str, Any]]]:
        return [f for f in self.fallas if f[1].tipo in CRITICAS]


def reconocer(scene: SceneState, partes: Sequence[Dict[str, Any]], perfil: Perfil, flexibles: Sequence[str] = (),
              usar_roles: bool = True, tolerancia: Optional[float] = None) -> Reconocimiento:
    modelo = _cajas_modelo(list(partes))
    grupos, extras, deducidos = agrupar(scene, partes, usar_roles)
    tol = perfil.tolerancia if tolerancia is None else tolerancia
    forma, peor, orientacion = comparar(grupos, modelo, tol, flexibles)
    if not any(grupos.values()):
        return Reconocimiento(0.0, 0.0, 0.0, peor, [], orientacion or {}, deducidos, len(extras), 0.0)
    parte, fallas = revisar(relaciones_del_modelo(modelo), modelo, grupos, orientacion or {}, perfil)
    faltan = peor is not None and peor.get("tipo") == "falta"
    puntaje = 0.0 if faltan else (1 - perfil.peso_relaciones) * forma + perfil.peso_relaciones * parte
    escala = (orientacion or {}).get("largo", 0.0) / ((orientacion or {}).get("largo_modelo") or 1.0)
    return Reconocimiento(puntaje, forma, parte, peor, fallas, orientacion or {}, deducidos, len(extras), escala)


# --- 3. ¿Qué figura es? ----------------------------------------------------------------------


@lru_cache(maxsize=1)
def biblioteca() -> Tuple[Dict[str, Any], ...]:
    """Figuras conocidas (mesa, silla, casa…): con qué se puede confundir la del alumno."""
    try:
        datos = json.loads(BIBLIOTECA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple(f for f in datos.get("figures", []) if f.get("id") and f.get("parts"))


def identificar(scene: SceneState, figuras: Iterable[Dict[str, Any]], perfil: Optional[Perfil] = None,
                limite: int = 3) -> List[Dict[str, Any]]:
    """[{id, title, score}] de las figuras que más se parecen, la mejor primero."""
    perfil = perfil or PERFILES["proporcion"]
    salida = []
    for figura in figuras:
        r = reconocer(scene, figura["parts"], perfil, figura.get("flexible") or (), usar_roles=False)
        salida.append({"id": figura["id"], "title": figura.get("title") or figura["id"], "score": round(r.puntaje, 3)})
    salida.sort(key=lambda f: -f["score"])
    return salida[:limite]
