"""Kit de pruebas para autores de prácticas (motor v3).

Escribir una práctica ya no exige abrir Blender para cada cambio: se
describe una escena de prueba en pocas líneas (o se exporta una real desde
el modo Desarrollador del add-on) y el motor dice qué pasaría.

    from amatista_engine.testing import Escena

    escena = (
        Escena()
        .cubo("Vagon", dims=(2, 1, 1), loc=(0, 0, 0.9), rol="vagon")
        .cilindro("Rueda", dims=(0.6, 0.2, 0.6), loc=(0.6, 0.55, 0.3), rol="rueda")
        .camara("Camara", loc=(0, -8, 2), mira_a=(0, 0, 0.5))
        .construir()
    )

En pruebas.json (junto a cada práctica) la misma escena se escribe como
lista de pasos: [{"cubo": {"nombre": "Vagon", "dims": [2, 1, 1], ...}}].
Lo ejecuta `python engine/herramientas/practicas.py probar`.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .models import AnimationChannel, MaterialInfo, ModifierInfo, SceneObject, SceneState
from .snapshot import scene_from_dict, scene_to_dict

# Vértices y caras de cada primitiva recién agregada (Blender 4.2, valores por defecto).
GEOMETRIA = {
    "cube": (8, 6),
    "cylinder": (64, 34),
    "sphere": (482, 512),
    "icosphere": (42, 80),
    "cone": (33, 33),
    "plane": (4, 1),
    "torus": (576, 576),
    "suzanne": (507, 500),
}
DATOS = {
    "cube": "Cube", "cylinder": "Cylinder", "sphere": "Sphere", "icosphere": "Icosphere", "cone": "Cone",
    "plane": "Plane", "torus": "Torus", "suzanne": "Suzanne",
}


def _v(valor, defecto=(0.0, 0.0, 0.0)) -> Tuple[float, float, float]:
    if valor is None:
        return defecto
    return tuple(float(x) for x in valor)


def _rotar(punto, rot_rad):
    """Rota un punto con Euler XYZ (como Blender)."""
    a, b, c = rot_rad
    x, y, z = punto
    y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
    x, z = x * math.cos(b) + z * math.sin(b), -x * math.sin(b) + z * math.cos(b)
    x, y = x * math.cos(c) - y * math.sin(c), x * math.sin(c) + y * math.cos(c)
    return x, y, z


def caja_rotada(loc, dims, rot_rad):
    """Caja envolvente en el mundo de una caja centrada en loc con medidas locales dims."""
    esquinas = [
        _rotar((sx * dims[0] / 2, sy * dims[1] / 2, sz * dims[2] / 2), rot_rad)
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    ]
    minimo = tuple(round(loc[i] + min(e[i] for e in esquinas), 6) for i in range(3))
    maximo = tuple(round(loc[i] + max(e[i] for e in esquinas), 6) for i in range(3))
    return minimo, maximo


def _normal(v):
    largo = math.sqrt(sum(x * x for x in v)) or 1.0
    return tuple(x / largo for x in v)


class Escena:
    """Constructor fluido de SceneState para pruebas (sin Blender)."""

    def __init__(self, blender: str = "4.2.0") -> None:
        self._objetos: List[SceneObject] = []
        self._datos: Dict[str, Any] = {
            "blender_version": blender, "file_path": "", "file_saved": False, "mode": "OBJECT",
            "active_object": None, "selected": (), "active_camera": None, "render_engine": "BLENDER_EEVEE_NEXT",
            "renders": 0, "frame_range": (1, 250),
        }
        self._usados: Dict[str, int] = {}

    # --- Objetos ---------------------------------------------------------------------

    def _nombre(self, base: str) -> str:
        n = self._usados.get(base, 0)
        self._usados[base] = n + 1
        return base if n == 0 else f"{base}.{n:03d}"

    def malla(self, primitiva: str, nombre: str = "", dims=None, loc=None, rot=None, escala=None, rol: str = "",
              etiquetas: Sequence[str] = (), vertices: Optional[int] = None, caras: Optional[int] = None,
              mitad: str = "", encimados: int = 0, coleccion: str = "Collection") -> "Escena":
        """Una malla salida de una primitiva. rot en GRADOS. mitad: «x-», «x+»… (solo un lado del eje)."""
        datos = DATOS.get(primitiva, primitiva.capitalize())
        verts, faces = GEOMETRIA.get(primitiva, (8, 6))
        dims = _v(dims, (2.0, 2.0, 2.0))
        loc = _v(loc)
        lados = [(verts // 2, verts // 2)] * 3
        if mitad:
            eje = "xyz".index(mitad[0])
            lados[eje] = (verts, 0) if mitad[1:] == "-" else (0, verts)
        rot_rad = tuple(math.radians(a) for a in _v(rot))
        caja_min, caja_max = caja_rotada(loc, dims, rot_rad)
        obj = SceneObject(
            name=nombre or self._nombre(datos),
            object_type="MESH",
            roles=(rol,) if rol else (),
            location=loc,
            rotation=rot_rad,
            scale=_v(escala, (1.0, 1.0, 1.0)),
            dimensions=dims,
            tags=tuple(etiquetas),
            collections=(coleccion,),
            vertices=vertices if vertices is not None else verts,
            faces=caras if caras is not None else faces,
            bbox_min=caja_min,
            bbox_max=caja_max,
            data_name=self._nombre("__d_" + datos).replace("__d_", ""),
            duplicate_vertices=encimados,
            side_counts=tuple(lados),
            materials_used=(),
        )
        self._objetos.append(obj)
        return self

    def cubo(self, nombre: str = "", **kw) -> "Escena":
        return self.malla("cube", nombre, **kw)

    def cilindro(self, nombre: str = "", **kw) -> "Escena":
        return self.malla("cylinder", nombre, **kw)

    def esfera(self, nombre: str = "", **kw) -> "Escena":
        return self.malla("sphere", nombre, **kw)

    def plano(self, nombre: str = "", **kw) -> "Escena":
        kw.setdefault("dims", (10.0, 10.0, 0.0))
        return self.malla("plane", nombre, **kw)

    def cono(self, nombre: str = "", **kw) -> "Escena":
        return self.malla("cone", nombre, **kw)

    def luz(self, nombre: str = "Light", tipo: str = "POINT", loc=None, energia: float = 1000.0,
            mira_a=None) -> "Escena":
        loc = _v(loc, (4.0, 1.0, 6.0))
        hacia = _normal(tuple(m - l for m, l in zip(_v(mira_a), loc))) if mira_a is not None else (0.0, 0.0, -1.0)
        self._objetos.append(SceneObject(
            name=nombre, object_type="LIGHT", location=loc, dimensions=(0.0, 0.0, 0.0), collections=("Collection",),
            data_name=nombre, light_type=tipo.upper(), light_energy=float(energia), forward=hacia,
        ))
        return self

    def camara(self, nombre: str = "Camera", loc=None, mira_a=(0.0, 0.0, 0.0), angulo: float = 0.6911,
               activa: bool = True) -> "Escena":
        loc = _v(loc, (7.0, -7.0, 5.0))
        hacia = _normal(tuple(m - l for m, l in zip(_v(mira_a), loc)))
        self._objetos.append(SceneObject(
            name=nombre, object_type="CAMERA", location=loc, dimensions=(0.0, 0.0, 0.0), collections=("Collection",),
            data_name=nombre, camera_angle=angulo, forward=hacia,
        ))
        if activa:
            self._datos["active_camera"] = nombre
        return self

    def inicial(self) -> "Escena":
        """La escena de inicio de Blender: cubo, luz y cámara."""
        return self.cubo("Cube", dims=(2, 2, 2)).luz("Light", "POINT", (4.08, 1.0, 5.9)).camara(
            "Camera", (7.36, -6.93, 4.96), (0, 0, 0))

    # --- Datos de objetos que ya existen ----------------------------------------------------

    def _cambiar(self, nombre: str, **cambios) -> "Escena":
        for i, o in enumerate(self._objetos):
            if o.name == nombre:
                self._objetos[i] = replace(o, **cambios)
                return self
        raise KeyError(f"No hay un objeto «{nombre}» en la escena de prueba")

    def _obj(self, nombre: str) -> SceneObject:
        return next(o for o in self._objetos if o.name == nombre)

    def modificador(self, objeto: str, tipo: str, ejes: Sequence[bool] = (True, False, False),
                    niveles: Optional[int] = None, encendido: bool = True) -> "Escena":
        o = self._obj(objeto)
        tipo = tipo.upper()
        m = ModifierInfo(tipo, tipo.capitalize(), tuple(bool(e) for e in ejes) if tipo == "MIRROR" else (False,) * 3,
                         niveles if niveles is not None else (1 if tipo == "SUBSURF" else None), encendido)
        return self._cambiar(objeto, modifiers=o.modifiers + (tipo,), modifier_details=o.modifier_details + (m,))

    def material(self, objeto: str, nombre: str, color=(0.8, 0.8, 0.8, 1.0), metal: float = 0.0,
                 rugosidad: float = 0.5, transmision: float = 0.0, alfa: float = 1.0, usado: bool = True) -> "Escena":
        o = self._obj(objeto)
        info = MaterialInfo(nombre, tuple(color) + ((1.0,) if len(color) == 3 else ()), metal, rugosidad,
                            transmision, alfa)
        usados = tuple(o.materials_used or ()) + ((nombre,) if usado else ())
        return self._cambiar(objeto, materials=o.materials + (nombre,), material_details=o.material_details + (info,),
                             materials_used=usados)

    def animar(self, objeto: str, propiedad: str, eje: str, claves: Iterable[Sequence[float]]) -> "Escena":
        o = self._obj(objeto)
        canal = AnimationChannel(propiedad, "xyz".index(eje.lower()), tuple((float(f), float(v)) for f, v in claves))
        return self._cambiar(objeto, animation=o.animation + (canal,))

    def rol(self, objeto: str, rol: str) -> "Escena":
        return self._cambiar(objeto, roles=(rol,))

    def mover(self, objeto: str, loc) -> "Escena":
        o = self._obj(objeto)
        loc = _v(loc)
        caja_min, caja_max = caja_rotada(loc, o.dimensions, o.rotation)
        return self._cambiar(objeto, location=loc, bbox_min=caja_min, bbox_max=caja_max)

    def quitar(self, objeto: str) -> "Escena":
        self._objetos = [o for o in self._objetos if o.name != objeto]
        return self

    # --- Escena ------------------------------------------------------------------------

    def modo(self, modo: str) -> "Escena":
        self._datos["mode"] = modo
        return self

    def seleccionar(self, *nombres: str) -> "Escena":
        self._datos["selected"] = tuple(nombres)
        self._datos["active_object"] = nombres[0] if nombres else None
        return self

    def motor(self, motor: str) -> "Escena":
        self._datos["render_engine"] = motor
        return self

    def renders(self, n: int = 1) -> "Escena":
        self._datos["renders"] = n
        return self

    def guardado(self, archivo: str = "practica.blend", guardado: bool = True) -> "Escena":
        self._datos["file_path"] = archivo
        self._datos["file_saved"] = guardado
        return self

    def construir(self) -> SceneState:
        return SceneState(objects=tuple(self._objetos), **self._datos)

    def a_dict(self) -> Dict[str, Any]:
        return scene_to_dict(self.construir())


# Pasos de pruebas.json → métodos del constructor.
PASOS = {
    "inicial": "inicial", "cubo": "cubo", "cilindro": "cilindro", "esfera": "esfera", "plano": "plano",
    "cono": "cono", "malla": "malla", "luz": "luz", "camara": "camara", "modificador": "modificador",
    "material": "material", "animar": "animar", "rol": "rol", "mover": "mover", "quitar": "quitar",
    "modo": "modo", "seleccionar": "seleccionar", "motor": "motor", "renders": "renders", "guardado": "guardado",
}


def escena_desde_pasos(pasos: List[Dict[str, Any]]) -> SceneState:
    """[{"cubo": {"nombre": "Vagon", "dims": [2,1,1]}}, {"renders": 1}] → SceneState."""
    e = Escena()
    for i, paso in enumerate(pasos):
        if not isinstance(paso, dict) or len(paso) != 1:
            raise ValueError(f"construir[{i}] debe ser un objeto con una sola clave (cubo, luz, material…)")
        clave, args = next(iter(paso.items()))
        if clave not in PASOS:
            raise ValueError(f"construir[{i}]: paso desconocido «{clave}» (usa: {', '.join(sorted(PASOS))})")
        metodo = getattr(e, PASOS[clave])
        if isinstance(args, dict):
            metodo(**args)
        elif isinstance(args, list):
            metodo(*args)
        elif args is None or args is True:
            metodo()
        else:
            metodo(args)
    return e.construir()


def escena_de_caso(caso: Dict[str, Any]) -> SceneState:
    """Un caso de pruebas.json: «construir» (pasos) o «escena» (foto exportada del add-on)."""
    if "escena" in caso:
        return scene_from_dict(caso["escena"])
    return escena_desde_pasos(caso.get("construir") or [])
