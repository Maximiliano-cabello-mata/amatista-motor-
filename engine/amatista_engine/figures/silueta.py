"""Silueta de una malla (motor 3.5).

``figure.recognize`` reconoce figuras hechas con varias piezas. Una espada
modelada en Modo Edición es UNA malla: su caja envolvente solo dice que es
larga, no si tiene guarda, mango o punta. Para saberlo, Amatista la corta
en rebanadas a lo largo de su eje más largo y mide qué tan ancha y qué tan
gruesa es cada rebanada: la silueta. Así se ve, como lo vería una persona,
que la guarda sobresale a los lados, que la hoja es larga y delgada o que la
punta se afila.

Luego ``comparar_siluetas`` reparte las rebanadas del alumno entre las
partes del modelo (Pomo, Mango, Guarda, Hoja, Punta) sin exigir que cada
una empiece en el mismo lugar: una hoja más corta sigue siendo la hoja. Por
cada parte dice si está, si su largo, su ancho y su grosor se parecen a los
del modelo (con la holgura del nivel) y qué hacer si no. Las relaciones que
dan sentido a la figura (la guarda mucho más ancha que el mango y que la
hoja, la punta que se afila) se exigen en todos los niveles.

Todo es Python puro: el add-on mide la malla en Blender
(``silueta_de_malla``) y el servidor repite la comparación con la foto.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..models import Silhouette

REBANADAS = 32
FINAS = 4  # el modelo se mide con 4 veces más rebanadas (sus partes chicas no se pierden)
MAX_ARISTAS = 60000  # mallas más grandes no se miden en cada cambio (sería lento)
EPS = 0.006  # ancho relativo mínimo: evita dividir entre cero en rebanadas vacías
PESO_LARGO = 2.0  # cuánto cuesta repartir las rebanadas con largos distintos a los del modelo
EJES = "XYZ"

# Holgura por exigencia (figures/reconocer.py › PERFILES): veces más o menos permitido.
HOLGURA = {"forma": 2.5, "proporcion": 2.0, "cercana": 1.6, "medidas": 1.3, "exacta": 1.15}
# Partes fuera de su holgura que se perdonan (la figura sigue reconocible).
PERDON = {"forma": 1, "proporcion": 1, "cercana": 1, "medidas": 0, "exacta": 0}
CONTRASTE = 1.6  # una parte «mucho más ancha» que su vecina en el modelo
DETALLE = 1.35  # una parte que sobresale «un poco» (el pomo): si no se nota, se sugiere
AFILADA = 0.5  # una parte cuyo extremo mide menos de la mitad que su base se afila

Silueta = Silhouette  # el mismo dato que viaja en la foto de la escena (models.py)


def transversales(eje: int) -> Tuple[int, int]:
    return tuple(i for i in range(3) if i != eje)  # type: ignore[return-value]


# --- Medir ------------------------------------------------------------------------------


def silueta_de_malla(vertices: Sequence[Sequence[float]], aristas: Iterable[Sequence[int]],
                     rebanadas: int = REBANADAS) -> Optional[Silueta]:
    """Corta la malla (vértices en el MUNDO) en rebanadas por su eje más largo.

    Cada rebanada es el plano que pasa por su centro: las aristas que lo
    cruzan dan los puntos del contorno y su extensión es el ancho y el grueso.
    """
    if len(vertices) < 2:
        return None
    minimos = [min(v[i] for v in vertices) for i in range(3)]
    maximos = [max(v[i] for v in vertices) for i in range(3)]
    medidas = [maximos[i] - minimos[i] for i in range(3)]
    eje = max(range(3), key=lambda i: medidas[i])
    largo = medidas[eje]
    if largo <= 1e-6:
        return None
    a, b = transversales(eje)
    inicio = minimos[eje]
    paso = largo / rebanadas
    rangos = [[math.inf, -math.inf, math.inf, -math.inf] for _ in range(rebanadas)]
    for n, arista in enumerate(aristas):
        if n >= MAX_ARISTAS:
            break
        p, q = vertices[arista[0]], vertices[arista[1]]
        if p[eje] > q[eje]:
            p, q = q, p
        k0 = max(0, math.ceil((p[eje] - inicio) / paso - 0.5))
        k1 = min(rebanadas - 1, math.floor((q[eje] - inicio) / paso - 0.5))
        tramo = q[eje] - p[eje]
        for k in range(k0, k1 + 1):
            centro = inicio + (k + 0.5) * paso
            t = (centro - p[eje]) / tramo if tramo > 1e-12 else 0.0
            x = p[a] + (q[a] - p[a]) * t
            y = p[b] + (q[b] - p[b]) * t
            r = rangos[k]
            r[0], r[1], r[2], r[3] = min(r[0], x), max(r[1], x), min(r[2], y), max(r[3], y)
    anchos = tuple((max(0.0, r[1] - r[0]) if r[1] >= r[0] else 0.0, max(0.0, r[3] - r[2]) if r[3] >= r[2] else 0.0)
                   for r in rangos)
    return Silueta(eje, largo, anchos)


def _girar(punto, grados):
    x, y, z = punto
    rx, ry, rz = (math.radians(g) for g in grados)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return x, y, z


def malla_de_pieza(primitiva: str, medidas, ubicacion=(0.0, 0.0, 0.0), giro=(0.0, 0.0, 0.0), segmentos: int = 0):
    """Vértices y aristas sencillos de una primitiva (para medir la silueta del modelo)."""
    sx, sy, sz = (float(m) / 2 for m in medidas)
    n = int(segmentos or 16)
    puntos: List[Tuple[float, float, float]] = []
    aristas: List[Tuple[int, int]] = []

    def anillo(z, rx, ry):
        base = len(puntos)
        for i in range(n):
            ang = 2 * math.pi * i / n
            puntos.append((rx * math.cos(ang), ry * math.sin(ang), z))
            aristas.append((base + i, base + (i + 1) % n))
        return base

    if primitiva in ("cylinder", "circle"):
        abajo, arriba = anillo(-sz, sx, sy), anillo(sz, sx, sy)
        aristas.extend((abajo + i, arriba + i) for i in range(n))
    elif primitiva == "cone":
        abajo = anillo(-sz, sx, sy)
        puntos.append((0.0, 0.0, sz))
        aristas.extend((abajo + i, len(puntos) - 1) for i in range(n))
    elif primitiva in ("sphere", "uv_sphere", "icosphere"):
        anillos = 9
        bases = []
        for j in range(1, anillos):
            theta = math.pi * j / anillos
            bases.append(anillo(-sz * math.cos(theta), sx * math.sin(theta), sy * math.sin(theta)))
        puntos.extend([(0.0, 0.0, -sz), (0.0, 0.0, sz)])
        polo_abajo, polo_arriba = len(puntos) - 2, len(puntos) - 1
        for i in range(n):
            aristas.append((polo_abajo, bases[0] + i))
            aristas.extend((bases[j] + i, bases[j + 1] + i) for j in range(len(bases) - 1))
            aristas.append((bases[-1] + i, polo_arriba))
    else:  # cubo, plano y lo demás: su caja
        puntos = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        aristas = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count("1") == 1]
    mundo = [tuple(c + o for c, o in zip(_girar(p, giro), ubicacion)) for p in puntos]
    return mundo, aristas


def _campo(pieza, clave, defecto=None):
    return pieza.get(clave, defecto) if isinstance(pieza, dict) else getattr(pieza, clave, defecto)


def silueta_de_piezas(piezas: Sequence[Any], rebanadas: int = REBANADAS) -> Optional[Silueta]:
    """La silueta del modelo: sus piezas unidas como si fueran una sola malla."""
    vertices: List[Tuple[float, float, float]] = []
    aristas: List[Tuple[int, int]] = []
    for pieza in piezas:
        puntos, lineas = malla_de_pieza(str(_campo(pieza, "primitive", "cube")), _campo(pieza, "size", (1, 1, 1)),
                                        _campo(pieza, "location", (0, 0, 0)) or (0, 0, 0),
                                        _campo(pieza, "rotation", (0, 0, 0)) or (0, 0, 0),
                                        int(_campo(pieza, "segments", 0) or 0))
        base = len(vertices)
        vertices.extend(puntos)
        aristas.extend((base + i, base + j) for i, j in lineas)
    return silueta_de_malla(vertices, aristas, rebanadas)


# --- Las partes del modelo ------------------------------------------------------------------


@dataclass(frozen=True)
class Parte:
    nombre: str
    desde: float  # fracción del largo (0 a 1)
    hasta: float
    primitiva: str = ""


def partes_del_modelo(piezas: Sequence[Any]) -> Tuple[Optional[Silueta], List[Parte]]:
    """Cada pieza del modelo es un tramo de la silueta, en orden a lo largo del eje."""
    silueta = silueta_de_piezas(piezas, REBANADAS * FINAS)
    if silueta is None:
        return None, []
    eje = silueta.eje
    tramos = []
    for pieza in piezas:
        puntos, _ = malla_de_pieza(str(_campo(pieza, "primitive", "cube")), _campo(pieza, "size", (1, 1, 1)),
                                   _campo(pieza, "location", (0, 0, 0)) or (0, 0, 0),
                                   _campo(pieza, "rotation", (0, 0, 0)) or (0, 0, 0), 8)
        tramos.append([min(p[eje] for p in puntos), max(p[eje] for p in puntos),
                       str(_campo(pieza, "name", "") or _campo(pieza, "primitive", "pieza")).strip(),
                       str(_campo(pieza, "primitive", ""))])
    tramos.sort(key=lambda t: (t[0] + t[1]) / 2)
    # Dos piezas que ocupan casi el mismo tramo (una al lado de la otra) son una sola parte.
    unidos: List[list] = []
    for t in tramos:
        if unidos:
            u = unidos[-1]
            comun = min(u[1], t[1]) - max(u[0], t[0])
            if comun > 0.5 * min(u[1] - u[0], t[1] - t[0]):
                u[0], u[1], u[2] = min(u[0], t[0]), max(u[1], t[1]), f"{u[2]} y {t[2]}"
                continue
        unidos.append(t)
    inicio = min(t[0] for t in unidos)
    fin = max(t[1] for t in unidos)
    largo = fin - inicio or 1.0
    cortes = [inicio] + [(unidos[i][1] + unidos[i + 1][0]) / 2 for i in range(len(unidos) - 1)] + [fin]
    partes = [Parte(t[2], (cortes[i] - inicio) / largo, (cortes[i + 1] - inicio) / largo, t[3])
              for i, t in enumerate(unidos)]
    return silueta, [p for p in partes if p.hasta - p.desde > 1e-4]


# --- Comparar --------------------------------------------------------------------------------


def _orientada(silueta: Silueta) -> Tuple[List[float], List[float], Tuple[int, int]]:
    """Anchos relativos al largo, con el eje «ancho» primero (el que más mide en promedio)."""
    a = [w[0] / silueta.largo for w in silueta.anchos]
    b = [w[1] / silueta.largo for w in silueta.anchos]
    ejes = silueta.transversales
    if sum(b) > sum(a):
        return b, a, (ejes[1], ejes[0])
    return a, b, ejes


def _log(x: float, y: float) -> float:
    return math.log((x + EPS) / (y + EPS))


def _muestra(valores: Sequence[float], desde: float, hasta: float, u: float) -> float:
    """Valor del modelo en la posición u (0 a 1) dentro de la parte [desde, hasta)."""
    n = len(valores)
    pos = (desde + (hasta - desde) * u) * n - 0.5
    i = max(0, min(n - 1, int(math.floor(pos))))
    j = min(n - 1, i + 1)
    f = min(1.0, max(0.0, pos - i))
    return valores[i] * (1 - f) + valores[j] * f


def _muestras(m_ancho, m_grueso, partes: Sequence[Parte], n: int):
    """log del modelo para cada parte y cada largo posible (en rebanadas del alumno)."""
    tabla = []
    for p in partes:
        por_largo = [None]
        for largo in range(1, n + 1):
            us = [(j + 0.5) / largo for j in range(largo)]
            por_largo.append(([math.log(_muestra(m_ancho, p.desde, p.hasta, u) + EPS) for u in us],
                              [math.log(_muestra(m_grueso, p.desde, p.hasta, u) + EPS) for u in us]))
        tabla.append(por_largo)
    return tabla


def _repartir(ancho, grueso, muestras, partes: Sequence[Parte], escala: float = 1.0):
    """Programación dinámica: qué rebanadas del alumno son cada parte del modelo (en orden).

    escala: cuánto más grande se ve la malla del alumno que el modelo cuando se mide en fracciones de su
    largo (una hoja corta hace que todo lo demás parezca más ancho y más largo): se descuenta.
    """
    n, k = len(ancho), len(partes)
    if n < k:
        return math.inf, []
    la = [math.log(a + EPS) for a in ancho]
    lg = [math.log(g + EPS) for g in grueso]

    def costo(i: int, s: int, e: int) -> float:
        largo = e - s
        m_a, m_g = muestras[i][largo]
        total = 0.0
        for j in range(largo):
            da = la[s + j] - m_a[j]
            dg = lg[s + j] - m_g[j]
            total += da * da + 0.5 * dg * dg
        return total + PESO_LARGO * math.log((largo / n) / ((partes[i].hasta - partes[i].desde) * escala)) ** 2

    inf = math.inf
    tabla = [[inf] * (n + 1) for _ in range(k + 1)]
    desde = [[0] * (n + 1) for _ in range(k + 1)]
    tabla[0][0] = 0.0
    for i in range(1, k + 1):
        for e in range(i, n - (k - i) + 1):
            mejor, origen = inf, 0
            for s in range(i - 1, e):
                if tabla[i - 1][s] == inf:
                    continue
                c = tabla[i - 1][s] + costo(i - 1, s, e)
                if c < mejor:
                    mejor, origen = c, s
            tabla[i][e], desde[i][e] = mejor, origen
    cortes = [n]
    e = n
    for i in range(k, 0, -1):
        e = desde[i][e]
        cortes.append(e)
    cortes.reverse()
    return tabla[k][n], [(cortes[i], cortes[i + 1]) for i in range(k)]


def _media_log(valores: Sequence[float], modelo: Sequence[float], p: Parte, s: int, e: int) -> float:
    if e <= s:
        return 0.0
    return sum(_log(valores[j], _muestra(modelo, p.desde, p.hasta, (j - s + 0.5) / (e - s))) for j in range(s, e)) / (e - s)


def _media(valores: Sequence[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def _afilado(valores: Sequence[float]) -> float:
    """Extremo final / base (menos de 1: se afila hacia el final)."""
    if len(valores) < 2:
        return 1.0
    mitad = max(1, len(valores) // 3)
    base, punta = _media(valores[:mitad]), _media(valores[-mitad:])
    return (punta + EPS) / (base + EPS)


@dataclass
class Revision:
    puntaje: float
    partes: List[Dict[str, Any]]
    criticas: List[Dict[str, Any]]
    fuera: List[Dict[str, Any]]
    detalles: List[Dict[str, Any]]
    invertida: bool
    ejes: Dict[str, str]
    largo: float
    largo_modelo: float


def _leer_partes(ancho, grueso, m_ancho, m_grueso, muestras, partes: Sequence[Parte], escala: float):
    """Reparte las rebanadas entre las partes y mide cada una contra el modelo."""
    # La espada puede estar con la punta hacia arriba o hacia abajo: gana la lectura que mejor encaja.
    directo = _repartir(ancho, grueso, muestras, partes, escala)
    al_reves = _repartir(ancho[::-1], grueso[::-1], muestras, partes, escala)
    invertida = al_reves[0] < directo[0]
    if invertida:
        ancho, grueso = ancho[::-1], grueso[::-1]
    tramos = (al_reves if invertida else directo)[1]
    n = len(ancho)
    resultado: List[Dict[str, Any]] = []
    for p, (s, e) in zip(partes, tramos):
        muestras_parte = [_muestra(m_ancho, p.desde, p.hasta, (i + 0.5) / 8) for i in range(8)]
        resultado.append({
            "parte": p.nombre, "desde": s, "hasta": e,
            "ancho": round(math.exp(_media_log(ancho, m_ancho, p, s, e)), 3),
            "grueso": round(math.exp(_media_log(grueso, m_grueso, p, s, e)), 3),
            "largo": round(((e - s) / n) / ((p.hasta - p.desde) * escala), 3),
            "ancho_alumno": _media(ancho[s:e]), "ancho_modelo": _media(muestras_parte),
            "pico_alumno": max(ancho[s:e] or [0.0]), "pico_modelo": max(muestras_parte),
            "afilado": round(_afilado(ancho[s:e]), 3), "afilado_modelo": round(_afilado(muestras_parte), 3),
        })
    return resultado, invertida, ancho, grueso


def comparar_siluetas(alumno: Silueta, modelo: Silueta, partes: Sequence[Parte], exigencia: str = "proporcion"
                      ) -> Revision:
    holgura = HOLGURA.get(exigencia, 2.0)
    m_ancho, m_grueso, _ = _orientada(modelo)
    ancho, grueso, ejes = _orientada(alumno)
    muestras = _muestras(m_ancho, m_grueso, partes, len(ancho))
    resultado, invertida, ancho, grueso = _leer_partes(ancho, grueso, m_ancho, m_grueso, muestras, partes, 1.0)
    # Si una parte es mucho más corta o más larga (la hoja), todo lo demás se ve más ancho o más angosto
    # medido en fracciones del largo: se calcula la escala real con los anchos y se vuelve a leer.
    logs = sorted(math.log(r["ancho"]) for r in resultado)
    escala = math.exp(logs[len(logs) // 2]) if logs else 1.0
    if abs(math.log(escala)) > 0.08:
        base_a, base_g = (ancho, grueso) if not invertida else (ancho[::-1], grueso[::-1])
        resultado, invertida, ancho, grueso = _leer_partes([a / escala for a in base_a], [g / escala for g in base_g],
                                                           m_ancho, m_grueso, muestras, partes, escala)

    criticas: List[Dict[str, Any]] = []
    # Lo que da sentido a la figura: una parte mucho más ancha (o angosta) que su vecina, y lo que se afila.
    for i in range(len(resultado) - 1):
        a, b = resultado[i], resultado[i + 1]
        if min(a["afilado_modelo"], b["afilado_modelo"]) < AFILADA:
            continue  # una parte que se afila (la punta) se revisa aparte
        razon_modelo = (b["ancho_modelo"] + EPS) / (a["ancho_modelo"] + EPS)
        razon = (b["ancho_alumno"] + EPS) / (a["ancho_alumno"] + EPS)
        if razon_modelo >= CONTRASTE and razon < max(1.2, razon_modelo ** 0.35):
            criticas.append({"tipo": "contraste", "parte": b["parte"], "vecina": a["parte"], "mas": "ancha",
                             "modelo": round(razon_modelo, 2), "tuya": round(razon, 2)})
        elif razon_modelo <= 1 / CONTRASTE and razon > min(1 / 1.2, razon_modelo ** 0.35):
            criticas.append({"tipo": "contraste", "parte": a["parte"], "vecina": b["parte"], "mas": "ancha",
                             "modelo": round(1 / razon_modelo, 2), "tuya": round(1 / razon, 2)})
    # Detalles: una parte que en el modelo sobresale un poco (el pomo) y en la malla no se nota.
    detalles: List[Dict[str, Any]] = []
    ya = {c["parte"] for c in criticas}
    for i in range(len(resultado) - 1):
        for a, b in ((resultado[i], resultado[i + 1]), (resultado[i + 1], resultado[i])):
            if b["parte"] in ya or min(a["afilado_modelo"], b["afilado_modelo"]) < AFILADA:
                continue
            modelo_pico = (b["pico_modelo"] + EPS) / (a["ancho_modelo"] + EPS)
            tuyo_pico = (b["pico_alumno"] + EPS) / (a["ancho_alumno"] + EPS)
            if DETALLE <= modelo_pico < CONTRASTE * 1.2 and tuyo_pico < 1.12:
                detalles.append({"tipo": "detalle", "parte": b["parte"], "vecina": a["parte"]})
                ya.add(b["parte"])
    for r in resultado:
        if r["afilado_modelo"] < AFILADA and r["afilado"] > 0.75:
            criticas.append({"tipo": "afilar", "parte": r["parte"], "modelo": r["afilado_modelo"], "tuya": r["afilado"]})

    fuera: List[Dict[str, Any]] = []
    puntos = []
    pesos = []
    for p, r in zip(partes, resultado):
        problemas = []
        for clave, limite in (("largo", holgura), ("ancho", holgura), ("grueso", holgura * 1.5)):
            if not 1 / limite <= r[clave] <= limite:
                problemas.append((abs(math.log(r[clave])) - math.log(limite), clave))
        r["ok"] = not problemas
        if problemas:
            peor = max(problemas)[1]
            r["problema"] = peor
            fuera.append(r)
        error = abs(math.log(r["ancho"])) + abs(math.log(r["largo"])) + 0.5 * abs(math.log(r["grueso"]))
        puntos.append(math.exp(-error))
        pesos.append(p.hasta - p.desde)
    criticas_por_parte = {c["parte"] for c in criticas}
    for r in resultado:
        if r["parte"] in criticas_por_parte:
            r["ok"] = False
    puntaje = sum(x * w for x, w in zip(puntos, pesos)) / (sum(pesos) or 1.0)
    if criticas:
        puntaje *= 0.6
    nombres = {"largo": EJES[alumno.eje], "ancho": EJES[ejes[0]], "grueso": EJES[ejes[1]]}
    return Revision(puntaje, resultado, criticas, fuera, detalles, invertida, nombres, alumno.largo, modelo.largo)


# --- Lo que dice el instructor ----------------------------------------------------------------


def _parte(nombre: str, inicio: bool = False) -> str:
    return f"{'La' if inicio else 'la'} parte «{nombre}»"


def consejo_critico(c: Dict[str, Any], ejes: Dict[str, str]) -> Tuple[str, str]:
    """(estado corto, consejo) de una relación rota: lo que hace que la figura no tenga sentido."""
    if c["tipo"] == "afilar":
        return "No se afila", (
            f"{_parte(c['parte'], True)} no se afila: selecciona las caras o vértices del extremo y "
            f"escálalos casi a cero (S, 0) o júntalos al centro (M › En el centro).")
    return "Falta", (
        f"Falta {_parte(c['parte'])}: en el modelo es mucho más ancha que «{c['vecina']}» y en tu malla miden casi "
        f"lo mismo. Con Ctrl + R haz un corte donde va y escala ese anillo hacia los lados (S, {ejes['ancho']}).")


def consejo_de_parte(r: Dict[str, Any], ejes: Dict[str, str]) -> Tuple[str, str]:
    """(estado corto, consejo) de una parte fuera de su holgura."""
    nombre = _parte(r["parte"], True)
    problema = r.get("problema")
    if problema == "largo":
        if r["largo"] < 1:
            return "Muy corta", (f"{nombre} es más corta que en el modelo: alárgala extruyendo su cara "
                                 f"(E, {ejes['largo']}) o moviendo sus caras (G, {ejes['largo']}).")
        return "Muy larga", (f"{nombre} es más larga que en el modelo: acórtala moviendo sus caras "
                             f"(G, {ejes['largo']}).")
    if problema == "ancho":
        if r["ancho"] < 1:
            return "Muy angosta", (f"{nombre} es más angosta que en el modelo: selecciona sus caras y "
                                   f"escálalas hacia los lados (S, {ejes['ancho']}).")
        return "Muy ancha", (f"{nombre} es más ancha que en el modelo: escálala hacia adentro "
                             f"(S, {ejes['ancho']}).")
    if problema == "grueso":
        if r["grueso"] > 1:
            return "Muy gruesa", f"{nombre} es más gruesa que en el modelo: aplánala (S, {ejes['grueso']})."
        return "Muy delgada", f"{nombre} es más delgada que en el modelo: engrósala (S, {ejes['grueso']})."
    return "Bien", ""


def consejo_detalle(d: Dict[str, Any], ejes: Dict[str, str]) -> Tuple[str, str]:
    return "Detalle", (
        f"En el modelo {_parte(d['parte'])} sobresale un poco de «{d['vecina']}» y en tu malla no se nota: haz un "
        f"corte con Ctrl + R donde va y escala ese anillo un poco hacia afuera (S).")


def lista_de_revision(revision: Revision) -> List[Dict[str, Any]]:
    """La lista del instructor: cada parte del modelo, si está bien y qué hacer si no.

    ok=True con estado «Detalle»: la parte se acepta en este nivel, pero el
    instructor sugiere cómo acercarla al modelo.
    """
    criticas = {}
    for c in revision.criticas:
        criticas.setdefault(c["parte"], c)
    detalles = {d["parte"]: d for d in revision.detalles}
    lista = []
    for r in revision.partes:
        if r["parte"] in criticas:
            estado, consejo = consejo_critico(criticas[r["parte"]], revision.ejes)
        elif not r["ok"]:
            estado, consejo = consejo_de_parte(r, revision.ejes)
        elif r["parte"] in detalles:
            estado, consejo = consejo_detalle(detalles[r["parte"]], revision.ejes)
        else:
            estado, consejo = "Bien", ""
        lista.append({"texto": r["parte"], "ok": estado in ("Bien", "Detalle"), "estado": estado, "consejo": consejo})
    return lista
