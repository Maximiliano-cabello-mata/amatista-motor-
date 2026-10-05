"""La figura tiene sentido: se compara con el modelo de referencia (motor 3.3).

Antes, una práctica pedía medidas exactas pieza por pieza («la rueda en
Z = 0 ± 0.1») y aun así aceptaba figuras sin sentido. Ahora la práctica
describe la figura terminada en «reference» (piezas con su forma, medida y
lugar) y figure.resembles revisa que la del alumno SE PAREZCA:

- mismas piezas (por rol o, sin roles, por primitiva): si falta un tipo de pieza
  no pasa, y cada pieza de más o de menos resta;
- cada pieza con un tamaño parecido RESPECTO DE LA FIGURA (±tolerance);
- cada pieza en un lugar parecido dentro de la figura;
- la figura completa con proporciones parecidas (alta, larga, ancha).

Todo se mide relativo al tamaño de la figura: un tren el doble de grande
pero bien armado pasa; uno con las ruedas flotando sobre el techo, no. La
figura puede estar girada en el suelo (90°, 180°) o en espejo: se prueba
cada orientación y se usa la que más se parece.

dimension.approx revisa UNA medida «cerca de» un valor (±tolerance) en
lugar de un rango estrecho: «la esfera mide cerca de 2 m de ancho».
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..models import SceneObject, SceneState, TargetDefinition, ValidationResult
from .base import describe, number, primitiva, result, select, selector, text

EPSILON = 0.03  # medida mínima relativa: un plano (alto 0) no dispara el error de proporción
NOMBRE_PRIMITIVA = {"cube": "cubo", "cylinder": "cilindro", "sphere": "esfera", "icosphere": "icoesfera",
                    "cone": "cono", "torus": "dona", "plane": "plano"}


# --- Geometría -----------------------------------------------------------------------


def _rotar(punto, rot_rad):
    a, b, c = rot_rad
    x, y, z = punto
    y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
    x, z = x * math.cos(b) + z * math.sin(b), -x * math.sin(b) + z * math.cos(b)
    x, y = x * math.cos(c) - y * math.sin(c), x * math.sin(c) + y * math.cos(c)
    return x, y, z


def caja_de_pieza(pieza: Dict[str, Any]) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    """Caja en el mundo de una pieza de referencia (size local, rotation en grados)."""
    medidas = pieza["size"]
    rot = tuple(math.radians(a) for a in pieza.get("rotation") or (0, 0, 0))
    loc = pieza.get("location") or (0, 0, 0)
    esquinas = [_rotar((sx * medidas[0] / 2, sy * medidas[1] / 2, sz * medidas[2] / 2), rot)
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    return (tuple(loc[i] + min(e[i] for e in esquinas) for i in range(3)),
            tuple(loc[i] + max(e[i] for e in esquinas) for i in range(3)))


class _Caja:
    __slots__ = ("centro", "medidas", "nombre")

    def __init__(self, minimo, maximo, nombre=""):
        self.centro = tuple((a + b) / 2 for a, b in zip(minimo, maximo))
        self.medidas = tuple(max(0.0, b - a) for a, b in zip(minimo, maximo))
        self.nombre = nombre

    @property
    def volumen(self) -> float:
        return (self.medidas[0] + EPSILON) * (self.medidas[1] + EPSILON) * (self.medidas[2] + EPSILON)


def _union(cajas: Sequence[_Caja]) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    minimo = tuple(min(c.centro[i] - c.medidas[i] / 2 for c in cajas) for i in range(3))
    maximo = tuple(max(c.centro[i] + c.medidas[i] / 2 for c in cajas) for i in range(3))
    return minimo, maximo


# Orientaciones probadas: giro en el suelo (0, 90, 180, 270) y espejo en X.
ORIENTACIONES = [(giro, espejo) for giro in range(4) for espejo in (False, True)]


def _orientar(caja: _Caja, giro: int, espejo: bool) -> _Caja:
    x, y, z = caja.centro
    dx, dy, dz = caja.medidas
    if espejo:
        x = -x
    for _ in range(giro):
        x, y = -y, x
        dx, dy = dy, dx
    nueva = _Caja((0, 0, 0), (0, 0, 0), caja.nombre)
    nueva.centro, nueva.medidas = (x, y, z), (dx, dy, dz)
    return nueva


# --- Puntajes -------------------------------------------------------------------------


def _puntaje(error: float, tolerancia: float, caida: float) -> float:
    """1 dentro de la tolerancia; baja en línea recta hasta 0 en tolerancia + caida."""
    if error <= tolerancia:
        return 1.0
    return max(0.0, 1.0 - (error - tolerancia) / caida)


def _error_medidas(a: Sequence[float], b: Sequence[float]) -> Tuple[float, int, float]:
    """(peor |ln(a/b)|, eje, razón a/b en ese eje) con medidas ya relativas a la figura."""
    peor, eje, razon = 0.0, 0, 1.0
    for i in range(3):
        r = (a[i] + EPSILON) / (b[i] + EPSILON)
        if abs(math.log(r)) > peor:
            peor, eje, razon = abs(math.log(r)), i, r
    return peor, eje, razon


def _emparejar(alumno: List[_Caja], modelo: List[_Caja], tol_pos: float, tol_med: float):
    """Empareja piezas del alumno con las del modelo, la mejor pareja primero."""
    candidatos = []
    for i, a in enumerate(alumno):
        for j, m in enumerate(modelo):
            distancia = math.dist(a.centro, m.centro)
            error, _, _ = _error_medidas(a.medidas, m.medidas)
            candidatos.append((distancia / tol_pos + error / tol_med, i, j))
    candidatos.sort()
    usados_a, usados_m, parejas = set(), set(), []
    for _, i, j in candidatos:
        if i not in usados_a and j not in usados_m:
            usados_a.add(i)
            usados_m.add(j)
            parejas.append((alumno[i], modelo[j]))
    return parejas


def comparar(grupos_alumno: Dict[str, List[_Caja]], grupos_modelo: Dict[str, List[_Caja]], tolerancia: float,
             flexibles: Sequence[str] = ()):
    """Puntaje 0..1 de la figura del alumno contra el modelo, con el detalle del peor problema.

    En los grupos flexibles la cantidad es libre: solo cuentan las piezas emparejadas.
    """
    todas_m = [c for cajas in grupos_modelo.values() for c in cajas]
    todas_a = [c for cajas in grupos_alumno.values() for c in cajas]
    if not todas_a:
        return 0.0, {"tipo": "vacia"}, None
    min_m, max_m = _union(todas_m)
    largo_m = max(b - a for a, b in zip(min_m, max_m)) or 1.0
    centro_m = tuple((a + b) / 2 for a, b in zip(min_m, max_m))
    tol_med = math.log(1.0 + tolerancia)
    tol_pos = tolerancia * 0.25  # 0.35 → cada pieza puede correrse ~9 % del largo de la figura sin perder puntos

    def relativa(caja: _Caja, centro, largo) -> _Caja:
        nueva = _Caja((0, 0, 0), (0, 0, 0), caja.nombre)
        nueva.centro = tuple((caja.centro[i] - centro[i]) / largo for i in range(3))
        nueva.medidas = tuple(m / largo for m in caja.medidas)
        return nueva

    modelo_rel = {g: [relativa(c, centro_m, largo_m) for c in cajas] for g, cajas in grupos_modelo.items()}
    prop_m = tuple((b - a) / largo_m for a, b in zip(min_m, max_m))
    total_modelo = sum(len(c) for g, c in grupos_modelo.items() if g not in flexibles)

    mejor = None
    for giro, espejo in ORIENTACIONES:
        orientadas = {g: [_orientar(c, giro, espejo) for c in cajas] for g, cajas in grupos_alumno.items()}
        todas = [c for cajas in orientadas.values() for c in cajas]
        min_a, max_a = _union(todas)
        largo_a = max(b - a for a, b in zip(min_a, max_a)) or 1.0
        centro_a = tuple((a + b) / 2 for a, b in zip(min_a, max_a))
        prop_a = tuple((b - a) / largo_a for a, b in zip(min_a, max_a))
        error_prop, eje_prop, razon_prop = _error_medidas(prop_a, prop_m)
        puntaje_prop = _puntaje(error_prop, tol_med, tol_med)
        problemas = []
        if puntaje_prop < 1:
            problemas.append((1 - puntaje_prop, {"tipo": "proporcion", "eje": eje_prop, "razon": razon_prop}))
        suma, sobran, falta, por_grupo, total_flexibles = 0.0, 0, False, [], 0
        for grupo, piezas_m in modelo_rel.items():
            piezas_a = [relativa(c, centro_a, largo_a) for c in orientadas.get(grupo, [])]
            if not piezas_a:
                falta = True
                problemas.append((2.0, {"tipo": "falta", "grupo": grupo, "modelo": len(piezas_m), "alumno": 0}))
                continue
            libre = grupo in flexibles
            if libre:
                total_grupo = min(len(piezas_a), len(piezas_m))
            elif len(piezas_a) != len(piezas_m):
                sobran += max(0, len(piezas_a) - len(piezas_m))
                diferencia = abs(len(piezas_a) - len(piezas_m)) / max(len(piezas_a), len(piezas_m))
                problemas.append((0.5 + diferencia, {"tipo": "cantidad", "grupo": grupo, "modelo": len(piezas_m),
                                                     "alumno": len(piezas_a)}))
            suma_grupo = 0.0
            for a, m in _emparejar(piezas_a, piezas_m, tol_pos, tol_med):
                error_m, eje_m, razon_m = _error_medidas(a.medidas, m.medidas)
                p_med = _puntaje(error_m, tol_med, tol_med)
                distancia = math.dist(a.centro, m.centro)
                p_pos = _puntaje(distancia, tol_pos, tol_pos * 2)
                suma_grupo += p_med * p_pos  # una pieza bien hecha pero en otro lugar no cuenta
                if p_med < 1:
                    girada = _error_medidas(sorted(a.medidas), sorted(m.medidas))[0] <= tol_med
                    problemas.append((1 - p_med, {"tipo": "girada" if girada else "medida", "grupo": grupo,
                                                  "objeto": a.nombre, "eje": eje_m, "razon": razon_m}))
                if p_pos < 1:
                    dz = a.centro[2] - m.centro[2]
                    problemas.append((1 - p_pos, {"tipo": "lugar", "grupo": grupo, "objeto": a.nombre,
                                                  "vertical": abs(dz) >= 0.6 * distancia, "dz": dz}))
            suma += suma_grupo
            if libre:
                total_flexibles += total_grupo
            por_grupo.append(suma_grupo / (total_grupo if libre else max(len(piezas_a), len(piezas_m))))
        # Mitad: cada pieza vale lo mismo (8 ruedas pesan más que 1 chimenea; las de sobra restan).
        # Mitad: el tipo de pieza peor hecho (dos vagones apilados no son un tren aunque las ruedas estén bien).
        piezas = suma / max(1, total_modelo + sobran + total_flexibles)
        total = 0.0 if falta else 0.85 * (0.5 * piezas + 0.5 * min(por_grupo)) + 0.15 * puntaje_prop
        peor = max(problemas, key=lambda p: p[0])[1] if problemas else None
        candidato = (total, peor, {"giro": giro * 90, "espejo": espejo, "largo": largo_a})
        if mejor is None or candidato[0] > mejor[0]:
            mejor = candidato
    return mejor[0], mejor[1], {**mejor[2], "largo_modelo": largo_m}


# --- Mensajes ---------------------------------------------------------------------------

EJES_TEXTO = {0: ("más larga", "más corta"), 1: ("más ancha", "más angosta"), 2: ("más alta", "más baja")}


def _nombre_grupo(grupo: str, etiquetas: Dict[str, str]) -> str:
    return etiquetas.get(grupo) or NOMBRE_PRIMITIVA.get(grupo, grupo)


def _quien(peor: Dict[str, Any], nombre: str) -> str:
    objeto = peor.get("objeto") or ""
    if not objeto or objeto.split(".")[0].lower() == nombre.lower():
        return f"Una pieza «{nombre}»" if objeto else f"«{nombre}»"
    return f"«{objeto}» ({nombre})"


def mensaje_de(peor: Optional[Dict[str, Any]], etiquetas: Dict[str, str]) -> str:
    if not peor:
        return "Tu figura se parece al modelo de referencia."
    tipo = peor["tipo"]
    if tipo == "vacia":
        return "Todavía no hay piezas para comparar con el modelo de referencia."
    if tipo == "sin_roles":
        nombres = ", ".join(f"«{_nombre_grupo(r, etiquetas)}»" for r in peor["roles"])
        return f"Asigna los roles ({nombres}) a tus piezas en la pestaña Amatista para compararlas con el modelo."
    nombre = _nombre_grupo(peor.get("grupo", ""), etiquetas)
    if tipo == "falta":
        if peor.get("rol"):
            return (f"Falta «{nombre}»: el modelo de referencia tiene {peor['modelo']}. Si ya la hiciste, "
                    f"asígnale el rol «{nombre}» en la pestaña Amatista.")
        return f"Falta «{nombre}»: el modelo de referencia tiene {peor['modelo']}."
    if tipo == "cantidad":
        return f"El modelo tiene {peor['modelo']} de «{nombre}» y tu figura {peor['alumno']}."
    if tipo == "proporcion":
        mas, menos = EJES_TEXTO[peor["eje"]]
        return f"Tu figura completa es {mas if peor['razon'] > 1 else menos} que el modelo: compárala con la imagen."
    if tipo == "medida":
        grande = peor["razon"] > 1
        if peor["eje"] == 2:
            como = "demasiado alta" if grande else "demasiado baja"
        else:
            como = "demasiado larga o ancha" if grande else "demasiado corta o angosta"
        quien = _quien(peor, nombre)
        return f"{quien} se ve {como} comparada con el resto de la figura."
    if tipo == "girada":
        return f"{_quien(peor, nombre)} tiene la medida correcta pero está girada: ponla como en la imagen con R."
    if tipo == "lugar":
        quien = _quien(peor, nombre)
        if peor.get("vertical"):
            return f"{quien} debería ir {'más abajo' if peor['dz'] > 0 else 'más arriba'} dentro de la figura."
        return f"{quien} no está donde va en la figura: compárala con la imagen de referencia."
    return "Tu figura todavía no se parece al modelo de referencia."


# --- Validadores -------------------------------------------------------------------------


def _grupo(pieza: Dict[str, Any]) -> str:
    return str(pieza.get("group") or pieza.get("role") or primitiva(pieza.get("primitive", "")))


def _cajas_modelo(partes: List[Dict[str, Any]]) -> Dict[str, List[_Caja]]:
    grupos: Dict[str, List[_Caja]] = {}
    unidas: Dict[Tuple[str, str], List[_Caja]] = {}
    for pieza in partes:
        minimo, maximo = caja_de_pieza(pieza)
        caja = _Caja(minimo, maximo)
        if pieza.get("join"):
            unidas.setdefault((_grupo(pieza), pieza["join"]), []).append(caja)
        else:
            grupos.setdefault(_grupo(pieza), []).append(caja)
    for (grupo, _), cajas in unidas.items():  # varias piezas unidas = un objeto del alumno
        minimo, maximo = _union(cajas)
        grupos.setdefault(grupo, []).append(_Caja(minimo, maximo))
    return grupos


def _cajas_alumno(scene: SceneState, grupos: Sequence[str], roles_modelo: set) -> Dict[str, List[_Caja]]:
    salida: Dict[str, List[_Caja]] = {}
    for grupo in grupos:
        if grupo in roles_modelo:
            objetos = [o for o in scene.objects if grupo in o.roles]
        else:
            objetos = [o for o in scene.objects if o.object_type == "MESH" and o.primitive == primitiva(grupo)]
        salida[grupo] = [_Caja(*o.caja(), nombre=o.name) for o in objetos]
    return salida


def resembles(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """La figura del alumno se parece al modelo de referencia (params.parts, que pone «reference»)."""
    partes = target.params.get("parts")
    if not isinstance(partes, list) or not partes:
        raise ValueError("figure.resembles necesita las piezas del modelo («reference» en la práctica)")
    tolerancia = number(target, "tolerance", 0.35)
    minimo = number(target, "min_score", 0.7)
    escala = number(target, "scale_range", 2.5)
    etiquetas = dict(target.params.get("labels") or {})
    modelo = _cajas_modelo(partes)
    # Pieza con rol: se compara con los objetos de ese rol; sin rol, con los de su primitiva.
    roles = {_grupo(p) for p in partes if p.get("role")}
    alumno = _cajas_alumno(scene, list(modelo), roles)
    flexibles = [str(g) for g in target.params.get("flexible") or []]
    puntaje, peor, orientacion = comparar(alumno, modelo, tolerancia, flexibles)
    if peor and peor.get("tipo") == "falta" and peor.get("grupo") in roles:
        peor = {**peor, "rol": True}
    if peor and peor.get("tipo") == "vacia" and roles and any(o.object_type == "MESH" for o in scene.objects):
        peor = {"tipo": "sin_roles", "roles": sorted(roles)}
    detalles: Dict[str, Any] = {"score": round(puntaje, 3), "min_score": minimo, "tolerance": tolerancia,
                                "worst": peor, "orientation": orientacion}
    if orientacion and escala > 1:
        razon = orientacion["largo"] / (orientacion["largo_modelo"] or 1.0)
        detalles["scale"] = round(razon, 2)
        if not 1 / escala <= razon <= escala:
            mensaje = (f"Tu figura mide cerca de {orientacion['largo']:.1f} m de largo y el modelo "
                       f"{orientacion['largo_modelo']:.1f} m: {'redúcela' if razon > 1 else 'agrándala'} con S.")
            return result(target, False, mensaje, detalles)
    porcentaje = round(puntaje * 100)
    if puntaje >= minimo:
        return result(target, True, f"Tu figura se parece al modelo de referencia ({porcentaje} %).", detalles)
    return result(target, False, f"{mensaje_de(peor, etiquetas)} Parecido: {porcentaje} %.", detalles)


EJES_APROX = {"x": 0, "y": 1, "z": 2}


def approx_dimension(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    """Una medida «cerca de» value (±tolerance). axis x|y|z, o largest/smallest (sin importar el giro)."""
    sel = selector(target)
    if not sel:
        raise ValueError("dimension.approx requiere un selector (role, primitive, name…)")
    eje = (text(target, "axis") or "largest").lower()
    if eje not in ("x", "y", "z", "largest", "smallest"):
        raise ValueError("dimension.approx requiere axis x, y, z, largest o smallest")
    valor = number(target, "value", 0.0)
    if valor <= 0:
        raise ValueError("dimension.approx requiere value > 0")
    tolerancia = number(target, "tolerance", 0.35)
    objetos: Tuple[SceneObject, ...] = select(scene, sel)
    que = describe(sel)
    bajo, alto = valor * (1 - tolerancia), valor * (1 + tolerancia)
    if not objetos:
        return result(target, False, f"No hay «{que}» para medir.", {"selector": sel})
    fallan = []
    for obj in objetos:
        caja = obj.caja()
        medidas = [caja[1][i] - caja[0][i] for i in range(3)]
        medida = max(medidas) if eje == "largest" else min(medidas) if eje == "smallest" else medidas[EJES_APROX[eje]]
        if not bajo <= medida <= alto:
            fallan.append({"object": obj.name, "value": round(medida, 2)})
    donde = {"largest": "en su lado más largo", "smallest": "en su lado más corto"}.get(eje, f"en {eje.upper()}")
    if not fallan:
        mensaje = f"«{que}» mide cerca de {valor:g} m {donde}."
    else:
        f = fallan[0]
        mensaje = (f"«{f['object']}» mide {f['value']:g} m {donde}; se busca cerca de {valor:g} m "
                   f"(entre {bajo:.1f} y {alto:.1f}).")
    return result(target, not fallan, mensaje, {"selector": sel, "axis": eje, "value": valor,
                                                 "tolerance": tolerancia, "failed": fallan})
