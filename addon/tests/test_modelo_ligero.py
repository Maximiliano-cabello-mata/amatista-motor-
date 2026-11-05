"""El modelo ligero de una entrega (amatista_blender/modelo_ligero.py), sin Blender.

Lo arma el add-on, lo revisa el servidor (backend/contenido/modelo_ligero.py)
y lo vuelve a armar el navegador del profesor: los tres deben entenderse.
"""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


addon = cargar("addon_modelo_ligero", RAIZ / "addon" / "amatista_blender" / "modelo_ligero.py")
servidor = cargar("servidor_modelo_ligero", RAIZ / "backend" / "contenido" / "modelo_ligero.py")

CUBO = [(x, y, z) for x in (0, 2) for y in (0, 2) for z in (0, 2)]
CARAS = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
         (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]


def test_cuantiza_alrededor_del_centro_y_el_servidor_lo_acepta():
    datos = addon.armar(
        [{"nombre": "Caja", "tipo": "MESH", "material": 0, "vertices": CUBO, "triangulos": CARAS, "p": (1, 1, 1)},
         {"nombre": "Sol", "tipo": "LIGHT", "p": (0, 0, 5)}],
        [{"nombre": "Madera", "color": (0.6, 0.4, 0.2)}],
        "5.0.1",
    )
    assert datos["formato"] == servidor.FORMATO == addon.FORMATO
    caja = datos["objetos"][0]
    # El centro de la caja de todo (con la luz en z=5) y la escala del lado más largo.
    assert datos["centro"] == [1.0, 1.0, 2.5] and datos["escala"] == 2.5
    assert max(abs(c) for c in caja["v"]) <= addon.COORDENADA and len(caja["t"]) == 36
    assert "v" not in datos["objetos"][1]
    paquete = addon.empaquetar(datos)
    assert addon.desempaquetar(paquete) == datos
    assert servidor.resumen_de(paquete)["triangulos"] == 12


def test_una_malla_enorme_viaja_como_su_caja():
    enorme = [(i * 0.001, 0, 0) for i in range(3)] + CUBO
    tris = [(0, 1, 2)] * (addon.MAX_TRIANGULOS + 1)
    datos = addon.armar([{"nombre": "Escultura", "tipo": "MESH", "vertices": enorme, "triangulos": tris}])
    assert datos["resumido"] is True
    assert len(datos["objetos"][0]["t"]) == 36
    assert len(addon.empaquetar(datos)) < 2000


def test_material_desconocido_queda_sin_material():
    datos = addon.armar([{"nombre": "X", "tipo": "MESH", "material": 7, "vertices": CUBO, "triangulos": CARAS}])
    assert datos["objetos"][0]["material"] == -1
    servidor.resumen_de(addon.empaquetar(datos))
