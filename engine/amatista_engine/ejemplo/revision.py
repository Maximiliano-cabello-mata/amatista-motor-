"""La revisión autónoma: la escena del alumno contra el ejemplo resuelto (motor 3.5).

El autor ya no escribe a mano cada cosa que se revisa: el motor mira qué
tiene el ejemplo (ejemplo/pasos.py) y lo busca en la escena del alumno,
aspecto por aspecto. Cada aspecto aparece solo si el ejemplo lo tiene:

    figura         piezas, proporciones y relaciones (figures/reconocer.py) o la
                   silueta de una figura hecha en una sola malla (figures/silueta.py)
    malla          trabajo en Modo Edición: más vértices que la primitiva, solo una mitad
    modificadores  los mismos tipos (Espejo en el mismo eje, Subdivisión con sus niveles)
    materiales     metálico, pulido o rugoso, vidrio y, en los niveles 4 y 5, el color
    colecciones    los objetos agrupados como en el ejemplo
    luces          las luces del ejemplo por tipo
    camara         una cámara activa que mira al modelo
    animacion      las mismas propiedades animadas, con sus claves y su recorrido
    render         el motor de render y el render (F12)
    archivo        guardado con el nombre del ejemplo

Como un instructor, no como un examen: el nombre de los objetos, el lugar,
el tamaño y los colores son libres en los niveles 1 a 3; lo que da sentido
a la práctica no. Cada punto que falta trae cómo hacerlo, con sus teclas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..figures.reconocer import Perfil, reconocer
from ..figures.silueta import PERDON, partes_del_modelo
from ..figures.silueta import lista_de_revision as lista_silueta
from ..models import MaterialInfo, SceneObject, SceneState
from ..testing import GEOMETRIA
from .pasos import LUCES, MODIFICADORES, MOTORES

ASPECTOS = {
    "figura": "La figura",
    "malla": "La malla",
    "modificadores": "Modificadores",
    "materiales": "Materiales",
    "colecciones": "Colecciones",
    "luces": "Luces",
    "camara": "Cámara",
    "animacion": "Animación",
    "render": "Render",
    "archivo": "Archivo",
}
COLECCIONES_BASE = {"collection", "scene collection", ""}
GRIS = (0.8, 0.8, 0.8)
EJE = "XYZ"
PROPIEDAD = {"location": "Ubicación", "rotation_euler": "Rotación", "scale": "Escala"}


@dataclass
class Aspecto:
    id: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    ok: Optional[bool] = None  # None: lo decide la lista (todos bien)

    @property
    def nombre(self) -> str:
        return ASPECTOS.get(self.id, self.id)

    @property
    def aprobado(self) -> bool:
        return self.ok if self.ok is not None else all(i["ok"] for i in self.items)

    def punto(self, texto: str, ok: bool, consejo: str = "", estado: str = "") -> None:
        self.items.append({"texto": texto, "ok": bool(ok), "estado": estado or ("Bien" if ok else "Falta"),
                           "consejo": "" if ok and estado != "Detalle" else consejo, "aspecto": self.nombre})


@dataclass
class RevisionEjemplo:
    aspectos: List[Aspecto]

    @property
    def aprobada(self) -> bool:
        return all(a.aprobado for a in self.aspectos)

    @property
    def lista(self) -> List[Dict[str, Any]]:
        return [i for a in self.aspectos for i in a.items]

    @property
    def puntaje(self) -> float:
        items = self.lista
        return sum(1 for i in items if i["ok"]) / len(items) if items else 1.0

    @property
    def pendientes(self) -> List[Dict[str, Any]]:
        return [i for a in self.aspectos if not a.aprobado for i in a.items if not i["ok"]] or [
            {"texto": a.nombre, "ok": False, "estado": "Revisar", "consejo": "", "aspecto": a.nombre}
            for a in self.aspectos if not a.aprobado]


# --- Ayudantes ----------------------------------------------------------------------------


def _mallas(scene: SceneState) -> List[SceneObject]:
    return [o for o in scene.objects if o.object_type == "MESH"]


def _pareja(objeto: SceneObject, candidatos: Sequence[SceneObject]) -> Optional[SceneObject]:
    """El objeto del alumno que hace de «objeto» del ejemplo: mismo nombre, misma primitiva o el más grande."""
    if not candidatos:
        return None
    base = objeto.name.split(".")[0].lower()
    por_nombre = [c for c in candidatos if c.name.split(".")[0].lower() == base]
    if por_nombre:
        return por_nombre[0]
    por_primitiva = [c for c in candidatos if c.primitive and c.primitive == objeto.primitive]
    lista = por_primitiva or list(candidatos)
    return max(lista, key=lambda c: max(c.dimensions or (0.0,)))


def _nombre_obj(objeto: SceneObject) -> str:
    return objeto.name.split(".")[0]


# --- La figura ----------------------------------------------------------------------------


def _partes_de(esperada: SceneState) -> List[Dict[str, Any]]:
    """Las mallas del ejemplo como piezas de un modelo de referencia (cuando el ejemplo no usa «reference»)."""
    partes = []
    for o in _mallas(esperada):
        partes.append({"primitive": o.primitive or "cube", "size": list(o.dimensions), "location": list(o.location),
                       "rotation": [math.degrees(a) for a in o.rotation], "role": o.role or "",
                       "name": _nombre_obj(o), "join": None})
    return partes


def _figura(esperada: SceneState, alumno: SceneState, perfil: Perfil, partes: Sequence[Dict[str, Any]],
            flexibles: Sequence[str], etiquetas: Dict[str, str], titulo: str) -> Aspecto:
    from ..validators.recognize import lista_de_revision as lista_figura

    a = Aspecto("figura")
    unida = any(o.silhouette is not None for o in _mallas(esperada)) and any(p.get("join") for p in partes)
    mallas = _mallas(alumno)
    if unida:  # una figura modelada en una sola malla: la silueta
        modelo, tramos = partes_del_modelo([p for p in partes if p.get("compare", True) is not False])
        con_silueta = [o for o in mallas if o.silhouette is not None]
        if not mallas:
            a.punto(titulo or "Tu malla", False, "Agrega un cubo (Shift + A › Malla › Cubo): de ahí sale la figura.")
            return a
        if not con_silueta or modelo is None:
            a.punto(titulo or "La silueta", True, "Actualiza el add-on Amatista Motor para que revise la silueta.",
                    "Detalle")
            return a
        from ..validators.silhouette import mejor_malla

        _, r = mejor_malla(con_silueta, modelo, tramos, perfil.id)
        for item in lista_silueta(r):
            a.punto(item["texto"], item["ok"], item.get("consejo", ""), item.get("estado", ""))
        a.ok = not r.criticas and len(r.fuera) <= PERDON.get(perfil.id, 0)
        if a.ok:
            for item in a.items:
                if not item["ok"]:
                    item.update(ok=True, estado="Detalle")
        return a
    piezas = list(partes) or _partes_de(esperada)
    if not piezas:
        return a
    r = reconocer(alumno, piezas, perfil, flexibles)
    for item in lista_figura(r, piezas, alumno, etiquetas, flexibles, perfil):
        a.punto(item["texto"], item["ok"], item.get("consejo", ""), item.get("estado", ""))
    vacia = r.peor is not None and r.peor.get("tipo") == "vacia"
    a.ok = (not vacia and r.puntaje >= perfil.min_score and r.forma >= perfil.min_forma
            and r.relaciones >= perfil.relaciones and not r.criticas
            and not any(i["estado"] == "Falta" and not i["ok"] for i in a.items))
    if a.ok:  # lo que este nivel perdona queda como sugerencia del instructor
        for item in a.items:
            if not item["ok"]:
                item.update(ok=True, estado="Detalle")
    if perfil.escala_real and r.escala and not 1 / perfil.escala_real <= r.escala <= perfil.escala_real:
        a.ok = False
        a.punto("Tamaño", False, f"En este nivel las medidas cuentan: tu figura es {r.escala:.1f} veces la del "
                                 f"ejemplo, {'redúcela' if r.escala > 1 else 'agrándala'} con S.", "Revisar")
    if not a.ok and all(i["ok"] for i in a.items):
        a.punto("Proporciones", False, "Compara tu figura con la del ejemplo: las piezas no tienen todavía sus "
                                       "proporciones ni su lugar.", "Revisar")
    return a


# --- La malla ----------------------------------------------------------------------------


def _malla(esperada: SceneState, alumno: SceneState) -> Aspecto:
    a = Aspecto("malla")
    mallas = _mallas(alumno)
    for o in _mallas(esperada):
        base = GEOMETRIA.get(o.primitive, (None, None))[0]
        if base is not None and o.vertices is not None and o.vertices > base and o.silhouette is None:
            hecho = any(m.vertices is not None and m.vertices > GEOMETRIA.get(m.primitive, (8, 6))[0] for m in mallas)
            a.punto(f"«{_nombre_obj(o)}» modelado en Modo Edición", hecho,
                    "Selecciona la malla, entra a Modo Edición (Tab) y dale forma: extruye con E y corta con Ctrl + R.")
        lados = o.side_counts or ()
        for eje, (menos, mas) in enumerate(lados):
            if (menos == 0) != (mas == 0):
                hecho = any(len(m.side_counts or ()) > eje
                            and (m.side_counts[eje][0] == 0) != (m.side_counts[eje][1] == 0) for m in mallas)
                a.punto(f"Solo una mitad de «{_nombre_obj(o)}» (en {EJE[eje]})", hecho,
                        f"En Modo Edición borra la mitad de un lado del eje {EJE[eje]} (selecciona y X › Vértices): "
                        "el Espejo dibuja la otra.")
    return a


# --- Modificadores ------------------------------------------------------------------------


def _modificadores(esperada: SceneState, alumno: SceneState, nivel: int) -> Aspecto:
    a = Aspecto("modificadores")
    pedidos: Dict[str, List[Tuple[SceneObject, Any]]] = {}
    for o in _mallas(esperada):
        for m in o.modifier_details:
            pedidos.setdefault(m.type, []).append((o, m))
    mallas = _mallas(alumno)
    for tipo, lista in pedidos.items():
        nombre = MODIFICADORES.get(tipo, tipo.capitalize())
        necesarios = len(lista) if nivel >= 4 else 1
        objeto, mod = lista[0]

        def cumple(m) -> bool:
            if m.type != tipo or not m.enabled:
                return False
            if tipo == "MIRROR" and not all(t or not e for e, t in zip(mod.axes, m.axes)):
                return False
            if tipo == "SUBSURF" and (mod.levels or 1) > 1 and (m.levels or 1) < (mod.levels or 1):
                return False
            return True

        tienen = [o for o in mallas if any(cumple(m) for m in o.modifier_details)]
        extra = ""
        if tipo == "MIRROR":
            extra = f" en {' y '.join(e for e, act in zip(EJE, mod.axes) if act) or 'X'}"
        elif tipo == "SUBSURF" and (mod.levels or 1) > 1:
            extra = f" con {mod.levels} niveles"
        texto = f"{nombre}{extra}" + (f" en {len(lista)} objetos" if necesarios > 1 else "")
        consejo = (f"Selecciona «{_nombre_obj(objeto)}» (o la tuya), pestaña Modificadores (la llave) › Agregar "
                   f"modificador › {nombre}{extra}.")
        tipo_suelto = [o for o in mallas if any(m.type == tipo for m in o.modifier_details)]
        if not tienen and tipo_suelto:
            consejo = f"Ya tienes {nombre}: revisa sus ajustes{extra} y que esté encendido (el ojo)."
        a.punto(texto, len(tienen) >= necesarios, consejo)
    return a


# --- Materiales ---------------------------------------------------------------------------


def _rasgos(m: MaterialInfo) -> List[str]:
    rasgos = []
    if m.metallic >= 0.5:
        rasgos.append("metálico")
    if m.transmission >= 0.5 or m.alpha < 0.6:
        rasgos.append("vidrio")
    if m.roughness <= 0.3:
        rasgos.append("pulido")
    elif m.roughness >= 0.6 and (m.metallic >= 0.5 or m.transmission >= 0.5):
        rasgos.append("rugoso")
    return rasgos


def _distancia(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])))


def _material_cumple(esperado: MaterialInfo, m: MaterialInfo, nivel: int) -> bool:
    if (esperado.metallic >= 0.5) != (m.metallic >= 0.5):
        return False
    vidrio = lambda x: x.transmission >= 0.5 or x.alpha < 0.6  # noqa: E731
    if vidrio(esperado) and not vidrio(m):
        return False
    if esperado.roughness <= 0.3 and m.roughness > 0.4:
        return False
    if esperado.roughness >= 0.6 and (esperado.metallic >= 0.5 or vidrio(esperado)) and m.roughness < 0.5:
        return False
    if nivel >= 4:
        if abs(esperado.metallic - m.metallic) > 0.25 or abs(esperado.roughness - m.roughness) > 0.25:
            return False
        if _distancia(esperado.base_color, GRIS) > 0.1 and _distancia(esperado.base_color, m.base_color) > 0.35:
            return False
    return True


def _consejo_material(m: MaterialInfo, objeto: str, nivel: int) -> str:
    pasos = []
    if m.metallic >= 0.5:
        pasos.append("sube Metálico a 1")
    if m.transmission >= 0.5:
        pasos.append("sube Transmisión a 1 (vidrio)")
    if m.roughness <= 0.3:
        pasos.append(f"baja Rugosidad a {m.roughness:.1f}")
    elif m.roughness >= 0.6 and (m.metallic >= 0.5 or m.transmission >= 0.5):
        pasos.append(f"sube Rugosidad a {m.roughness:.1f}")
    if _distancia(m.base_color, GRIS) > 0.1:
        pasos.append("usa el color del ejemplo" if nivel >= 4 else "elige su Color base")
    detalle = f" y {', '.join(pasos)}" if pasos else ""
    return f"Selecciona «{objeto}» (o la tuya), pestaña Material (la esfera roja) › Nuevo{detalle}."


def _materiales(esperada: SceneState, alumno: SceneState, nivel: int) -> Aspecto:
    a = Aspecto("materiales")
    pedidos: List[Tuple[SceneObject, MaterialInfo]] = []
    vistos = set()
    for o in esperada.objects:
        for m in o.material_details:
            if m.name not in vistos:
                vistos.add(m.name)
                pedidos.append((o, m))
    if not pedidos:
        return a
    disponibles = [m for o in alumno.objects for m in o.material_details]
    usados: set = set()
    # Primero los más específicos (metal pulido) para que no se los lleve uno cualquiera.
    for o, m in sorted(pedidos, key=lambda par: -len(_rasgos(par[1]))):
        rasgos = _rasgos(m)
        if not rasgos and _distancia(m.base_color, GRIS) > 0.1:
            rasgos = ["con su color"]
        texto = f"«{m.name}»" + (f": {', '.join(rasgos)}" if rasgos else "")
        encontrado = next((i for i, d in enumerate(disponibles) if i not in usados and _material_cumple(m, d, nivel)),
                          None)
        if encontrado is not None:
            usados.add(encontrado)
        a.punto(texto, encontrado is not None, _consejo_material(m, _nombre_obj(o), nivel))
    distintos = _aspectos_distintos([m for _, m in pedidos])
    if distintos >= 2:
        propios = _aspectos_distintos(disponibles)
        a.punto(f"{distintos} materiales que se distinguen", propios >= distintos,
                f"Haz que cada material se vea distinto (otro Color base, metálico o vidrio): el ejemplo tiene "
                f"{distintos} y tú {propios}. Los colores los eliges tú.")
    return a


def _aspectos_distintos(materiales: Sequence[MaterialInfo]) -> int:
    """Cuántos materiales se ven distintos: otro color o, con el mismo color, metal o vidrio."""
    vistos: List[Tuple[Sequence[float], Tuple[str, ...]]] = []
    for m in materiales:
        rasgos = tuple(r for r in _rasgos(m) if r in ("metálico", "vidrio"))
        if all(_distancia(m.base_color, c) > 0.15 or rasgos != r for c, r in vistos):
            vistos.append((m.base_color, rasgos))
    return len(vistos)


# --- Colecciones --------------------------------------------------------------------------


def _colecciones(esperada: SceneState, alumno: SceneState, nivel: int) -> Aspecto:
    a = Aspecto("colecciones")
    pedidas: Dict[str, int] = {}
    for o in esperada.objects:
        for c in o.collections:
            if c.lower() not in COLECCIONES_BASE:
                pedidas[c] = pedidas.get(c, 0) + 1
    if not pedidas:
        return a
    propias: Dict[str, int] = {}
    for o in alumno.objects:
        for c in o.collections:
            if c.lower() not in COLECCIONES_BASE:
                propias[c] = propias.get(c, 0) + 1
    usadas: set = set()
    for nombre, cuantos in pedidas.items():
        candidatas = [c for c, n in propias.items() if c not in usadas and n >= cuantos]
        igual = [c for c in candidatas if c.lower() == nombre.lower()]
        elegida = (igual or ([] if nivel >= 4 else candidatas) or [None])[0]
        if elegida:
            usadas.add(elegida)
        a.punto(f"Colección «{nombre}» con {cuantos} objetos", elegida is not None,
                f"Selecciona esos {cuantos} objetos y pulsa M › Nueva colección; llámala «{nombre}».")
    return a


# --- Luces y cámara ------------------------------------------------------------------------


def _luces(esperada: SceneState, alumno: SceneState, nivel: int) -> Aspecto:
    a = Aspecto("luces")
    pedidas: Dict[str, int] = {}
    for o in esperada.objects:
        if o.object_type == "LIGHT":
            pedidas[o.light_type or "POINT"] = pedidas.get(o.light_type or "POINT", 0) + 1
    if not pedidas:
        return a
    tiene: Dict[str, int] = {}
    for o in alumno.objects:
        if o.object_type == "LIGHT":
            tiene[o.light_type or "POINT"] = tiene.get(o.light_type or "POINT", 0) + 1
    total_ok = sum(tiene.values()) >= sum(pedidas.values())
    for tipo, cuantas in pedidas.items():
        nombre, articulo = LUCES.get(tipo, (tipo, tipo))
        texto = f"{cuantas} {'luces' if cuantas > 1 else 'luz'} {nombre}" if tipo != "SUN" else f"{cuantas} Sol"
        consejo = (f"Agrega {articulo} (Shift + A › Luz › {nombre})" +
                   (f": el ejemplo usa {cuantas}." if cuantas > 1 else "."))
        if tiene.get(tipo, 0) >= cuantas:
            a.punto(texto, True)
        elif nivel <= 2 and total_ok:  # el tipo es una sugerencia en los primeros niveles
            a.punto(texto, True, f"Un detalle: el ejemplo usa {articulo}; prueba cambiar la tuya en la pestaña de "
                                 "la luz (el foco verde).", "Detalle")
        else:
            a.punto(texto, False, consejo)
    return a


def _camara(esperada: SceneState, alumno: SceneState) -> Aspecto:
    from ..validators.lighting import forward_from_euler

    a = Aspecto("camara")
    if not esperada.active_camera:
        return a
    cam = alumno.object_by_name(alumno.active_camera) if alumno.active_camera else None
    cam = cam or next((o for o in alumno.objects if o.object_type == "CAMERA"), None)
    a.punto("Una cámara", cam is not None, "Agrega una cámara (Shift + A › Cámara) y hazla la activa (Ctrl + 0).")
    mallas = _mallas(alumno)
    if cam is not None and mallas:
        minimos = [o.caja()[0] for o in mallas]
        maximos = [o.caja()[1] for o in mallas]
        centro = tuple((min(m[i] for m in minimos) + max(m[i] for m in maximos)) / 2 for i in range(3))
        hacia = cam.forward or forward_from_euler(cam.rotation)
        d = tuple(centro[i] - cam.location[i] for i in range(3))
        largo = math.sqrt(sum(x * x for x in d)) or 1e-6
        angulo = math.degrees(math.acos(max(-1.0, min(1.0, sum(d[i] * hacia[i] for i in range(3)) / largo))))
        limite = math.degrees((cam.camera_angle or 0.6911) / 2.0) * 1.2
        a.punto("La cámara mira a tu modelo", angulo <= limite,
                f"Se desvía {angulo:.0f}°: pulsa 0 del teclado numérico para ver por la cámara y muévela con G y R.")
    return a


# --- Animación -----------------------------------------------------------------------------


def _animacion(esperada: SceneState, alumno: SceneState, nivel: int) -> Aspecto:
    a = Aspecto("animacion")
    for o in esperada.objects:
        for canal in o.animation:
            prop = f"{PROPIEDAD.get(canal.path, canal.path)} {EJE[canal.index]}"
            texto = f"{prop} de «{_nombre_obj(o)}» animada ({len(canal.keys)} claves)"
            recorrido = max(canal.values) - min(canal.values) if canal.values else 0.0
            minimo_claves = len(canal.keys) if nivel >= 3 else min(2, len(canal.keys))
            minimo_recorrido = recorrido * (0.35 if nivel <= 2 else 0.5)
            candidatos = [obj for obj in alumno.objects if obj.channel(canal.path, canal.index) is not None]
            mejor = _pareja(o, candidatos) if candidatos else None
            if mejor is None:
                a.punto(texto, False, f"Selecciona «{_nombre_obj(o)}» (o el tuyo), ve al fotograma "
                                      f"{int(canal.keys[0][0])} y pulsa I › {PROPIEDAD.get(canal.path, canal.path)}; luego cambia de "
                                      "fotograma, muévelo y pulsa I otra vez.")
                continue
            suyo = mejor.channel(canal.path, canal.index)
            valores = suyo.values
            ok_claves = len(suyo.keys) >= minimo_claves
            ok_recorrido = (max(valores) - min(valores) if valores else 0.0) >= minimo_recorrido - 1e-6
            consejo = ""
            if not ok_claves:
                consejo = f"Te faltan claves: el ejemplo usa {len(canal.keys)} (fotogramas " + ", ".join(
                    str(int(f)) for f, _ in canal.keys) + ")."
            elif not ok_recorrido:
                consejo = (f"Se mueve muy poco: en el ejemplo {prop.lower()} recorre {recorrido:.2f}; separa más los "
                           "valores de tus claves.")
            a.punto(texto, ok_claves and ok_recorrido, consejo)
    return a


# --- Render y archivo ----------------------------------------------------------------------


def _render(esperada: SceneState, alumno: SceneState, pide: Dict[str, Any]) -> Aspecto:
    a = Aspecto("render")
    motor = pide.get("motor")
    if motor:
        nombre = MOTORES.get(motor, motor)
        a.punto(f"Motor {nombre}", (alumno.render_engine or "").upper() == motor or (
            "EEVEE" in motor and "EEVEE" in (alumno.render_engine or "").upper()),
            f"Pestaña Render (la cámara de atrás) › Motor de render › {nombre}.")
    if esperada.renders:
        a.punto("Un render (F12)", alumno.renders > 0, "Pulsa F12 y espera a que termine la imagen.")
    return a


def _archivo(alumno: SceneState, pide: Dict[str, Any]) -> Aspecto:
    a = Aspecto("archivo")
    archivo = pide.get("archivo")
    if not archivo:
        return a
    # Como file.named: basta que el nombre lleve la palabra del ejemplo («mi_pelota» → «pelota»).
    palabra = archivo.lower().rsplit(".", 1)[0]
    palabra = palabra[3:] if palabra.startswith("mi_") else palabra
    igual = alumno.file_saved and palabra in alumno.file_name.lower()
    consejo = f"Archivo › Guardar como (Ctrl + Shift + S) y llámalo «{archivo}»."
    if alumno.file_saved and not igual:
        consejo = (f"Lo guardaste como «{alumno.file_name}»: el nombre debe llevar «{palabra}», como «{archivo}» "
                   "(Ctrl + Shift + S).")
    a.punto(f"Guardado como «{archivo}»", igual, consejo)
    return a


# --- Todo junto ---------------------------------------------------------------------------


def aspectos_del_ejemplo(esperada: SceneState, pide: Dict[str, Any]) -> List[str]:
    """Los aspectos que tiene el ejemplo (los que se pueden revisar)."""
    mallas = _mallas(esperada)
    tiene = {
        "figura": bool(mallas),
        "malla": any((o.vertices or 0) > GEOMETRIA.get(o.primitive, (10 ** 9,))[0] and o.silhouette is None
                     or any((m == 0) != (p == 0) for m, p in (o.side_counts or ())) for o in mallas),
        "modificadores": any(o.modifier_details for o in mallas),
        "materiales": any(o.material_details for o in esperada.objects),
        "colecciones": any(c.lower() not in COLECCIONES_BASE for o in esperada.objects for c in o.collections),
        "luces": any(o.object_type == "LIGHT" for o in esperada.objects),
        "camara": bool(esperada.active_camera),
        "animacion": any(o.animation for o in esperada.objects),
        "render": bool(esperada.renders or pide.get("motor")),
        "archivo": bool(pide.get("archivo")),
    }
    return [a for a in ASPECTOS if tiene[a]]


def revisar_ejemplo(esperada: SceneState, alumno: SceneState, perfil: Perfil, nivel: int,
                    pide: Optional[Dict[str, Any]] = None, aspectos: Optional[Sequence[str]] = None,
                    partes: Sequence[Dict[str, Any]] = (), flexibles: Sequence[str] = (),
                    etiquetas: Optional[Dict[str, str]] = None, titulo: str = "") -> RevisionEjemplo:
    pide = pide or {}
    elegidos = [a for a in (aspectos or aspectos_del_ejemplo(esperada, pide)) if a in ASPECTOS]
    salida = []
    for aspecto in elegidos:
        if aspecto == "figura":
            r = _figura(esperada, alumno, perfil, partes, flexibles, etiquetas or {}, titulo)
        elif aspecto == "malla":
            r = _malla(esperada, alumno)
        elif aspecto == "modificadores":
            r = _modificadores(esperada, alumno, nivel)
        elif aspecto == "materiales":
            r = _materiales(esperada, alumno, nivel)
        elif aspecto == "colecciones":
            r = _colecciones(esperada, alumno, nivel)
        elif aspecto == "luces":
            r = _luces(esperada, alumno, nivel)
        elif aspecto == "camara":
            r = _camara(esperada, alumno)
        elif aspecto == "animacion":
            r = _animacion(esperada, alumno, nivel)
        elif aspecto == "render":
            r = _render(esperada, alumno, pide)
        else:
            r = _archivo(alumno, pide)
        if r.items or r.ok is not None:
            salida.append(r)
    return RevisionEjemplo(salida)
