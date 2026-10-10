"""El plan del taller: qué hace el alumno ahora, según lo que ya domina.

El ciclo de cada habilidad (§6.1 de la investigación) y quién decide:

    Mira → Hazlo conmigo → Hazlo tú → Úsalo → Recuérdalo
           └── el modelo del alumno (modelo.py) elige el paso ──┘

| P(L)        | Fase        | Qué ve                                      | Ayuda                         |
|-------------|-------------|---------------------------------------------|-------------------------------|
| < 0.3       | nueva       | Mira (una vez) y Hazlo conmigo con molde    | teclas a un clic              |
| 0.3 – 0.7   | acompañada  | Hazlo conmigo con molde                     | teclas a pedido, tras intentar |
| 0.7 – 0.95  | sola        | Hazlo tú: otra variación, sin molde          | qué falta y con qué           |
| ≥ 0.95      | dominada    | nada: pasa al repaso                        | —                             |

Se aprende una habilidad a la vez, en el orden del taller: queda lista
cuando se hace sola y al menos una vez salió sin ninguna ayuda. Cuando todas
se hacen solas llega el proyecto (Úsalo: la práctica de siempre, que queda
en la isla) y después el reto final sin molde. Lo que toca repasar se
ofrece aparte, nunca bloquea.

Cada actividad que se revisa se convierte en una práctica
``amatista.practice/2`` generada al vuelo (``practica_de_actividad``): el
add-on la abre y la evalúa con el mismo motor de siempre y el servidor la
puede volver a revisar con la foto de la escena.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .ayudas import CON_QUE, MIRAME, QUE
from .habilidades import Catalogo, Habilidad, Reto, Taller, Variacion
from .modelo import ACOMPANADA, DOMINADA, NUEVA, SOLA, Dominio, dominio, fase

MIRA, CONMIGO, TU, PROYECTO, RETO, REPASO, PRUEBA = "mira", "conmigo", "tu", "proyecto", "reto", "repaso", "prueba"
TIPOS = (MIRA, CONMIGO, TU, PROYECTO, RETO, REPASO, PRUEBA)
NOMBRE_TIPO = {MIRA: "Mira", CONMIGO: "Hazlo conmigo", TU: "Hazlo tú", PROYECTO: "Úsalo", RETO: "Reto",
               REPASO: "Recuérdalo", PRUEBA: "Demuéstralo"}

# Cómo se ofrecen las teclas (regla 1: el alumno recuerda antes de que le digamos).
A_UN_CLIC = "a_un_clic"  # habilidad nueva: el botón «¿Cómo?» las muestra enseguida
A_PEDIDO = "a_pedido"  # después de intentarlo 20 s o de un intento fallido
OCULTAS = "ocultas"  # Hazlo tú, retos y repasos

# Herramientas de base que toda actividad permite (mirar, agregar y acomodar).
BASE = ("view.navigate", "view.numpad", "object.add", "transform.move", "transform.rotate", "transform.scale",
        "object.duplicate", "object.delete")


@dataclass(frozen=True)
class Actividad:
    id: str  # «conmigo:bl-escalar-eje:tabla», «proyecto:blender.bp.m1», «reto:blender.bp.m1»
    tipo: str
    taller: str
    titulo: str  # la habilidad o el proyecto
    pide: str  # qué hacer, en una frase
    habilidad: str = ""
    variacion: str = ""
    practica_id: str = ""  # la práctica que se abre (generada o la del proyecto); vacío en «Mira»
    molde: Tuple[Dict[str, Any], ...] = ()  # piezas que se dibujan (vacío: no se dibuja nada)
    piezas: Tuple[Dict[str, Any], ...] = ()  # piezas que se revisan (con o sin molde)
    modo: str = "molde"  # molde (importa el lugar) | libre (la figura se acomoda sola)
    dibujo: str = ""  # molde (la pieza translúcida) | marca (solo la huella en el suelo) | "" (nada)
    inicio: Tuple[Dict[str, Any], ...] = ()  # piezas que ya están en la escena al empezar (arréglalas)
    teclas: str = A_PEDIDO
    techo: int = MIRAME
    freno: bool = True
    habilidades: Tuple[str, ...] = ()  # las que suben con este intento
    minutos: int = 2
    nivel: int = 1
    fase: str = NUEVA
    numero: int = 0  # qué variación es (1, 2, 3…) dentro de su habilidad
    de: int = 0  # de cuántas

    @property
    def nombre_tipo(self) -> str:
        return NOMBRE_TIPO[self.tipo]

    @property
    def revisa(self) -> bool:
        return self.tipo != MIRA

    def a_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "tipo": self.tipo, "nombre_tipo": self.nombre_tipo, "taller": self.taller,
            "titulo": self.titulo, "pide": self.pide, "habilidad": self.habilidad, "variacion": self.variacion,
            "practica_id": self.practica_id, "molde": bool(self.molde), "modo": self.modo, "dibujo": self.dibujo,
            "teclas": self.teclas,
            "techo": self.techo, "habilidades": list(self.habilidades), "minutos": self.minutos, "nivel": self.nivel,
            "fase": self.fase, "numero": self.numero, "de": self.de,
        }


@dataclass(frozen=True)
class EstadoHabilidad:
    id: str
    titulo: str
    p: float
    fase: str
    intentos: int = 0
    vio_demo: bool = False
    repaso_vencido: bool = False
    sin_ayuda: int = 0  # veces que le salió sin molde ni pistas

    @property
    def lista(self) -> bool:
        """Ya no necesita guía: dominada, o se hace sola y al menos una vez le salió sin ayuda."""
        return self.fase == DOMINADA or (self.fase == SOLA and self.sin_ayuda > 0)

    def a_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "titulo": self.titulo, "p": round(self.p, 3), "fase": self.fase,
                "intentos": self.intentos, "vio_demo": self.vio_demo, "repaso_vencido": self.repaso_vencido,
                "lista": self.lista}


@dataclass(frozen=True)
class Plan:
    taller: Taller
    actual: Optional[Actividad]
    habilidades: Tuple[EstadoHabilidad, ...]
    proyecto_hecho: bool = False
    reto_hecho: bool = False
    repasos: Tuple[str, ...] = ()  # habilidades con repaso vencido (las del taller y las que repasa)
    puede_probar: bool = False  # camino rápido: «¿Ya sabes esto? Demuéstralo»
    siguientes: Tuple[Actividad, ...] = field(default_factory=tuple)

    @property
    def listas(self) -> int:
        """Habilidades que ya se hacen solas (fase sola o dominada)."""
        return sum(1 for h in self.habilidades if h.fase in (SOLA, DOMINADA))

    @property
    def proyecto_abierto(self) -> bool:
        return all(h.fase in (SOLA, DOMINADA) for h in self.habilidades)

    @property
    def completo(self) -> bool:
        return self.proyecto_hecho and self.proyecto_abierto

    def a_dict(self) -> Dict[str, Any]:
        return {
            "taller": self.taller.id,
            "titulo": self.taller.titulo,
            "curso": self.taller.curso,
            "modulo": self.taller.modulo,
            "actual": self.actual.a_dict() if self.actual else None,
            "habilidades": [h.a_dict() for h in self.habilidades],
            "listas": self.listas,
            "total": len(self.habilidades),
            "proyecto": self.taller.proyecto,
            "proyecto_abierto": self.proyecto_abierto,
            "proyecto_hecho": self.proyecto_hecho,
            "reto_hecho": self.reto_hecho,
            "completo": self.completo,
            "repasos": list(self.repasos),
            "puede_probar": self.puede_probar,
            "isla": dict(self.taller.isla),
            "siguientes": [a.a_dict() for a in self.siguientes],
        }


# --- Actividades de una habilidad -------------------------------------------------------------


def _ayuda(fase_actual: str) -> Tuple[str, int, bool]:
    """(cómo se ofrecen las teclas, techo de la escalera, freno) según la fase."""
    if fase_actual == NUEVA:
        return A_UN_CLIC, MIRAME, False
    if fase_actual == ACOMPANADA:
        return A_PEDIDO, MIRAME, True
    if fase_actual == SOLA:
        return OCULTAS, CON_QUE, True
    return OCULTAS, QUE, True


def _practica_id(tipo: str, *partes: str) -> str:
    return ".".join(("taller",) + tuple(p for p in partes if p) + (tipo,))[:80]


def _variacion(h: Habilidad, indice: int) -> Tuple[Variacion, int]:
    i = indice % len(h.variaciones)
    return h.variaciones[i], i


def actividad_de_habilidad(taller: Taller, h: Habilidad, tipo: str, fase_actual: str, indice: int = 0) -> Actividad:
    """Mira, Hazlo conmigo o Hazlo tú de una habilidad (indice elige la variación)."""
    nivel = max(taller.nivel, 1)
    if tipo == MIRA:
        return Actividad(
            id=f"{MIRA}:{h.id}", tipo=MIRA, taller=taller.id, titulo=h.titulo, pide=h.que, habilidad=h.id,
            teclas=A_UN_CLIC, techo=0, freno=False, habilidades=(), minutos=1, nivel=nivel, fase=fase_actual,
        )
    v, i = _variacion(h, indice)
    teclas, techo, freno = _ayuda(fase_actual if tipo == CONMIGO else SOLA)
    if tipo == CONMIGO and teclas == OCULTAS:
        teclas, techo = A_PEDIDO, MIRAME  # quien vuelve a «conmigo» siempre puede pedir las teclas
    inicio = _piezas_de_inicio(v.inicio)
    if tipo == CONMIGO:
        # Con molde hasta el nivel 3 (en el 4 y el 5 solo la marca del lugar).
        modo, dibujo = "molde", ("molde" if nivel <= 3 else "marca")
    elif inicio:
        modo, dibujo = "molde", "marca"  # «arregla esta escena»: importa el lugar; se ve solo la huella
    else:
        modo, dibujo = "libre", ""  # sin molde: la figura se reconoce donde esté
    return Actividad(
        id=f"{tipo}:{h.id}:{v.id}", tipo=tipo, taller=taller.id, titulo=h.titulo, pide=v.pide, habilidad=h.id,
        variacion=v.id, practica_id=_practica_id(tipo, h.id, v.id), molde=v.molde if (dibujo and v.molde) else (),
        piezas=() if v.solo_dibujo else v.molde, modo=modo, dibujo=dibujo if v.molde else "", inicio=inicio, teclas=teclas, techo=techo,
        freno=freno, habilidades=(h.id,), minutos=v.minutos, nivel=nivel, fase=fase_actual, numero=i + 1,
        de=len(h.variaciones),
    )


def _piezas_de_inicio(inicio: Dict[str, Any]) -> Tuple[Dict[str, Any], ...]:
    objetos = (inicio or {}).get("objetos") or ()
    return tuple(dict(o) for o in objetos if isinstance(o, dict))


def _actividad_reto(taller: Taller, reto: Reto, tipo: str, titulo: str, habilidades: Sequence[str], h: str = "",
                    fase_actual: str = SOLA) -> Actividad:
    marca = not reto.libre and bool(reto.piezas)
    return Actividad(
        id=f"{tipo}:{h or taller.id}" + (f":{reto.id}" if tipo == REPASO else ""), tipo=tipo, taller=taller.id,
        titulo=titulo, pide=reto.pide, habilidad=h, variacion=reto.id,
        practica_id=_practica_id(tipo, h or taller.id.replace(".", "-")), molde=reto.piezas if marca else (),
        piezas=reto.piezas, modo="molde" if marca else "libre", dibujo="marca" if marca else "",
        inicio=_piezas_de_inicio(reto.inicio), teclas=OCULTAS, techo=QUE, freno=True,
        habilidades=tuple(habilidades), minutos=reto.minutos, nivel=max(taller.nivel, 1), fase=fase_actual,
    )


def _reto_de_habilidad(h: Habilidad) -> Reto:
    """El reto propio de la habilidad o, si no tiene, su última variación sin molde."""
    if h.reto is not None:
        return h.reto
    v = h.variaciones[-1]
    return Reto(id=f"{h.id}.{v.id}", pide=v.pide, piezas=v.molde, objetivos=v.objetivos, inicio=v.inicio,
                minutos=v.minutos)


def actividad_de_prueba(catalogo: Catalogo, taller_id: str, habilidad_id: str) -> Optional[Actividad]:
    """Camino rápido: el reto de la habilidad sin ayuda; dos bien hechos y se salta su guía."""
    taller, h = catalogo.taller(taller_id), catalogo.habilidad(habilidad_id)
    if taller is None or h is None:
        return None
    return _actividad_reto(taller, _reto_de_habilidad(h), PRUEBA, h.titulo, (h.id,), h.id)


def actividad_de_repaso(catalogo: Catalogo, taller_id: str, habilidad_id: str) -> Optional[Actividad]:
    """El reto de un minuto de «Recuérdalo» (el repaso propio de la habilidad o su reto)."""
    taller, h = catalogo.taller(taller_id), catalogo.habilidad(habilidad_id)
    if taller is None or h is None:
        return None
    reto = h.repaso or _reto_de_habilidad(h)
    return _actividad_reto(taller, reto, REPASO, h.titulo, (h.id,), h.id, DOMINADA)


def actividad_de_proyecto(taller: Taller, titulo: str = "") -> Actividad:
    return Actividad(
        id=f"{PROYECTO}:{taller.id}", tipo=PROYECTO, taller=taller.id, titulo=titulo or taller.titulo,
        pide=(taller.isla.get("texto") or "Arma el proyecto del módulo: queda en tu isla."), practica_id=taller.proyecto,
        teclas=OCULTAS, techo=CON_QUE, freno=True, habilidades=taller.habilidades, minutos=20,
        nivel=max(taller.nivel, 1), fase=SOLA,
    )


def actividad_de_reto_final(taller: Taller) -> Optional[Actividad]:
    if taller.reto is None:
        return None
    return _actividad_reto(taller, taller.reto, RETO, "Reto del módulo", taller.habilidades)


# --- El plan ----------------------------------------------------------------------------------


def _estado_habilidades(catalogo: Catalogo, ids: Iterable[str], estado: Dict[str, Dominio], ahora: float):
    salida = []
    for hid in catalogo.orden(ids):
        h = catalogo.habilidades[hid]
        d = estado.get(hid)
        p = dominio(d, h.bkt, ahora)
        vencido = bool(d and d.caja and d.proximo and d.proximo <= ahora)
        salida.append(EstadoHabilidad(hid, h.titulo, p, fase(p), d.intentos if d else 0, bool(d and d.vio_demo), vencido,
                                      d.sin_ayuda if d else 0))
    return salida


def _siguiente_de(taller: Taller, h: Habilidad, eh: EstadoHabilidad) -> Optional[Actividad]:
    if eh.fase == DOMINADA:
        return None
    if eh.fase == NUEVA and not eh.vio_demo and h.demo:
        return actividad_de_habilidad(taller, h, MIRA, eh.fase)
    if eh.fase in (NUEVA, ACOMPANADA):
        return actividad_de_habilidad(taller, h, CONMIGO, eh.fase, eh.intentos)
    return actividad_de_habilidad(taller, h, TU, eh.fase, eh.intentos + 1)


def planear(catalogo: Catalogo, taller_id: str, estado: Dict[str, Dominio], ahora: float,
            completadas: Iterable[str] = (), elegida: str = "") -> Optional[Plan]:
    """El plan del taller para este alumno ahora.

    completadas: ids de prácticas o actividades ya terminadas (el proyecto, el
    reto final). elegida: una habilidad que el alumno eligió practicar
    (autonomía); si ya la domina se sigue el orden del taller.
    """
    taller = catalogo.taller(taller_id)
    if taller is None:
        return None
    hechas = set(completadas)
    habilidades = _estado_habilidades(catalogo, taller.habilidades, estado, ahora)
    por_id = {e.id: e for e in habilidades}
    proyecto_hecho = bool(taller.proyecto) and (taller.proyecto in hechas or f"{PROYECTO}:{taller.id}" in hechas)
    reto = actividad_de_reto_final(taller)
    reto_hecho = reto is None or reto.id in hechas or reto.practica_id in hechas

    candidatas: List[Actividad] = []

    def sumar(a: Optional[Actividad]) -> None:
        if a is not None and all(a.id != c.id for c in candidatas):
            candidatas.append(a)

    if elegida in por_id:
        sumar(_siguiente_de(taller, catalogo.habilidades[elegida], por_id[elegida]))
    # Una habilidad a la vez, en el orden del taller: Mira, Hazlo conmigo hasta que sale sola y un
    # «Hazlo tú» sin ayuda. Después la siguiente. Lo que ya está listo no se vuelve a pedir (tedio).
    for eh in habilidades:
        if not eh.lista:
            sumar(_siguiente_de(taller, catalogo.habilidades[eh.id], eh))
    abierto = all(e.fase in (SOLA, DOMINADA) for e in habilidades)
    if taller.proyecto and not proyecto_hecho and abierto:
        sumar(actividad_de_proyecto(taller))
    if reto is not None and not reto_hecho and proyecto_hecho:
        sumar(reto)

    repasar = [h for h in list(taller.repasa) + list(taller.habilidades) if h in catalogo.habilidades]
    vencidos = tuple(h for h in repasar if (d := estado.get(h)) and d.caja and d.proximo and d.proximo <= ahora)
    sin_intentos = not any(estado.get(h) and estado[h].intentos for h in taller.habilidades)
    return Plan(
        taller=taller,
        actual=candidatas[0] if candidatas else None,
        habilidades=tuple(habilidades),
        proyecto_hecho=proyecto_hecho,
        reto_hecho=reto_hecho,
        repasos=tuple(dict.fromkeys(vencidos)),
        puede_probar=sin_intentos,
        siguientes=tuple(candidatas[1:4]),
    )


def actividad_por_id(catalogo: Catalogo, taller_id: str, actividad_id: str,
                     estado: Optional[Dict[str, Dominio]] = None, ahora: float = 0.0) -> Optional[Actividad]:
    """Vuelve a armar una actividad por su id (órdenes de la plataforma y revisión en el servidor)."""
    taller = catalogo.taller(taller_id)
    if taller is None or not isinstance(actividad_id, str):
        return None
    partes = actividad_id.split(":")
    tipo = partes[0]
    if tipo == PROYECTO:
        return actividad_de_proyecto(taller) if len(partes) == 2 and partes[1] == taller.id else None
    if tipo == RETO:
        return actividad_de_reto_final(taller) if len(partes) == 2 and partes[1] == taller.id else None
    if len(partes) < 2:
        return None
    h = catalogo.habilidad(partes[1])
    if h is None:
        return None
    if tipo == PRUEBA:
        return actividad_de_prueba(catalogo, taller_id, h.id)
    if tipo == REPASO:
        return actividad_de_repaso(catalogo, taller_id, h.id)
    p = dominio((estado or {}).get(h.id), h.bkt, ahora)
    if tipo == MIRA:
        return actividad_de_habilidad(taller, h, MIRA, fase(p))
    if tipo in (CONMIGO, TU) and len(partes) == 3:
        ids = [v.id for v in h.variaciones]
        if partes[2] not in ids:
            return None
        return actividad_de_habilidad(taller, h, tipo, fase(p) if tipo == CONMIGO else SOLA, ids.index(partes[2]))
    return None


# --- El proyecto con molde (Úsalo, niveles 1 y 2) -----------------------------------------------

NIVEL_MAXIMO_MOLDE = 2  # el molde solo en los niveles 1 y 2 (riesgo: volver a la copia mecánica)


def piezas_del_proyecto(practica) -> Tuple[Dict[str, Any], ...]:
    """Las piezas del modelo de referencia de una práctica (las que se comparan)."""
    from ..practice.loader import pieza_como_dict

    referencia = getattr(practica, "reference", None)
    if referencia is None:
        return ()
    return tuple(pieza_como_dict(p) for p in referencia.compared)


def molde_del_proyecto(practica) -> Tuple[Dict[str, Any], ...]:
    """Las piezas que se dibujan como molde en el proyecto (vacío desde el nivel 3)."""
    if getattr(practica, "level", 9) > NIVEL_MAXIMO_MOLDE:
        return ()
    piezas = piezas_del_proyecto(practica)
    # Una figura hecha en una sola malla (la espada) no se arma con piezas sueltas: no hay molde de piezas.
    return () if any(p.get("join") for p in piezas) else piezas


def revisar_proyecto(practica, scene, con_molde: bool = True):
    """El molde del proyecto revisado; si el alumno arma fuera del molde, la figura en modo libre.

    Devuelve None si la práctica no tiene modelo de piezas sueltas.
    """
    from .molde import revisar_molde

    piezas = piezas_del_proyecto(practica)
    if not piezas or any(p.get("join") for p in piezas):
        return None
    etiquetas = {r.id: r.label for r in getattr(practica, "roles", ())}
    nivel = getattr(practica, "level", 1)
    if not (con_molde and nivel <= NIVEL_MAXIMO_MOLDE):
        return revisar_molde(piezas, scene, "libre", nivel, etiquetas)
    r = revisar_molde(piezas, scene, "molde", nivel, etiquetas)
    if r.completa or not any(o.object_type == "MESH" for o in scene.objects):
        return r
    # Armó a su manera (en otro lugar, girado o más grande): se revisa la figura donde esté.
    libre = revisar_molde(piezas, scene, "libre", nivel, etiquetas)
    return libre if libre.llenas > r.llenas else r


# --- La práctica que se genera ------------------------------------------------------------------


def _objetivos_extra(objetivos: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    salida = []
    for o in objetivos:
        nuevo = dict(o)
        nuevo.setdefault("weight", 10)
        nuevo.setdefault("title", o.get("id"))
        salida.append(nuevo)
    return salida


def practica_de_actividad(catalogo: Catalogo, actividad: Actividad) -> Optional[Dict[str, Any]]:
    """La práctica amatista.practice/2 que revisa la actividad (None: «Mira» y el proyecto, que ya tiene la suya)."""
    if actividad.tipo in (MIRA, PROYECTO):
        return None
    taller = catalogo.taller(actividad.taller)
    if taller is None:
        return None
    h = catalogo.habilidad(actividad.habilidad) if actividad.habilidad else None
    if actividad.tipo in (CONMIGO, TU) and h is not None:
        v = next((x for x in h.variaciones if x.id == actividad.variacion), None)
        if v is None:
            return None
        objetivos, inicio = v.objetivos, v.inicio
    else:
        reto = (taller.reto if actividad.tipo == RETO else
                (h.repaso or _reto_de_habilidad(h)) if actividad.tipo == REPASO and h is not None else
                _reto_de_habilidad(h) if h is not None else None)
        if reto is None:
            return None
        objetivos, inicio = reto.objetivos, reto.inicio
    herramientas = list(dict.fromkeys(BASE + tuple(t for hid in actividad.habilidades
                                                    for t in (catalogo.habilidades[hid].herramientas
                                                              if hid in catalogo.habilidades else ()))))
    targets: List[Dict[str, Any]] = []
    if actividad.piezas:
        targets.append({
            "id": "figura",
            "title": actividad.pide,
            "validator": "taller.molde",
            "params": {"parts": [dict(p) for p in actividad.piezas], "mode": actividad.modo, "level": actividad.nivel},
            "weight": 60,
            "tip": actividad.pide,
        })
    targets.extend(_objetivos_extra(objetivos))
    return {
        "schema": "amatista.practice/2",
        "id": actividad.practica_id,
        "version": 1,
        "title": actividad.pide[:120],
        "level": actividad.nivel,
        "description": actividad.pide,
        "estimatedMinutes": actividad.minutos,
        "skills": list(actividad.habilidades),
        "tags": ["taller", actividad.tipo],
        "course": {"id": taller.curso, "module": taller.modulo, "lesson": taller.leccion},
        # Las piezas de inicio («arregla esta escena») las arma el add-on; la práctica empieza vacía.
        "starter": {k: v for k, v in (inicio or {}).items() if k != "objetos"} or {"scene": "empty"},
        "tools": {"allowed": herramientas},
        "targets": targets,
    }


__all__ = [
    "A_PEDIDO", "A_UN_CLIC", "BASE", "CONMIGO", "MIRA", "NOMBRE_TIPO", "OCULTAS", "PROYECTO", "PRUEBA", "REPASO",
    "RETO", "TIPOS", "TU", "Actividad", "EstadoHabilidad", "NIVEL_MAXIMO_MOLDE", "Plan", "actividad_de_habilidad",
    "actividad_de_proyecto", "actividad_de_prueba", "actividad_de_repaso", "actividad_de_reto_final", "actividad_por_id",
    "molde_del_proyecto", "piezas_del_proyecto", "planear", "practica_de_actividad", "revisar_proyecto",
]
