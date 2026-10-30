"""El modelo ligero de una entrega (formato amatista.modelo/1), sin bpy.

Para que el profesor vea el modelo de cada alumno no viaja el .blend: viaja
una descripción de pocos KB que su navegador vuelve a armar. Cada malla va
en triángulos, con los vértices en el espacio del mundo cuantizados a
enteros de 16 bits alrededor de un centro común; todo el JSON se comprime
con zlib y se manda en base64. El servidor lo revisa con
backend/contenido/modelo_ligero.py y la plataforma lo lee con
frontend/src/profesor/modelo.js: los tres hablan el mismo formato.

entrega.py junta los datos de la escena (necesita Blender); aquí solo se
arma el paquete, así se prueba sin Blender (addon/tests/test_modelo_ligero.py).
"""
import base64
import json
import zlib

FORMATO = "amatista.modelo/1"
COORDENADA = 32767
# Por encima de esto el resto de las mallas viaja como su caja: la entrega
# sigue siendo de pocos KB aunque alguien suba una escultura.
MAX_TRIANGULOS = 60000
MAX_OBJETOS = 300
MAX_MATERIALES = 64


def _caja(vertices):
    xs, ys, zs = zip(*vertices)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _como_caja(vertices):
    (x0, y0, z0), (x1, y1, z1) = _caja(vertices)
    puntos = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    caras = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return puntos, caras


def _redondo(valores, decimales=4):
    return [round(float(v), decimales) for v in valores]


def armar(objetos, materiales=(), blender=""):
    """Arma el diccionario del formato.

    objetos: [{"nombre", "tipo", "material": índice o -1, "vertices": [(x, y, z)…] en el mundo,
               "triangulos": [(a, b, c)…], "p", "r", "s", "mods": [...]}]; las luces, cámaras y
               vacíos van sin vértices.
    materiales: [{"nombre", "color": (r, g, b)}].
    """
    objetos = list(objetos)[:MAX_OBJETOS]
    materiales = list(materiales)[:MAX_MATERIALES]
    resumido = False
    usados = 0
    mallas = []
    for objeto in objetos:
        vertices, triangulos = objeto.get("vertices") or [], objeto.get("triangulos") or []
        if vertices and triangulos and usados + len(triangulos) > MAX_TRIANGULOS:
            vertices, triangulos = _como_caja(vertices)
            resumido = True
        if vertices and triangulos:
            usados += len(triangulos)
        mallas.append((objeto, vertices, triangulos))

    todos = [v for _, vertices, _ in mallas for v in vertices]
    for objeto, _, _ in mallas:
        if objeto.get("p"):
            todos.append(tuple(objeto["p"]))
    if todos:
        (x0, y0, z0), (x1, y1, z1) = _caja(todos)
    else:
        x0 = y0 = z0 = x1 = y1 = z1 = 0.0
    centro = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    escala = max(x1 - x0, y1 - y0, z1 - z0) / 2 or 1.0

    def cuantizar(punto):
        return [max(-COORDENADA, min(COORDENADA, round((punto[i] - centro[i]) / escala * COORDENADA))) for i in range(3)]

    salida = []
    for objeto, vertices, triangulos in mallas:
        material = objeto.get("material", -1)
        uno = {
            "nombre": str(objeto.get("nombre", "Objeto"))[:80],
            "tipo": objeto.get("tipo", "MESH"),
            "material": material if isinstance(material, int) and -1 <= material < len(materiales) else -1,
        }
        if vertices and triangulos:
            uno["v"] = [c for punto in vertices for c in cuantizar(punto)]
            uno["t"] = [int(i) for tri in triangulos for i in tri]
        for clave in ("p", "r", "s"):
            if objeto.get(clave) is not None:
                uno[clave] = _redondo(objeto[clave])
        if objeto.get("mods"):
            uno["mods"] = [str(m)[:30] for m in objeto["mods"]][:12]
        salida.append(uno)

    return {
        "formato": FORMATO,
        "blender": str(blender)[:20],
        "centro": _redondo(centro, 5),
        "escala": round(escala, 6),
        "materiales": [
            {"nombre": str(m.get("nombre", ""))[:60], "color": _redondo(m.get("color", (0.8, 0.8, 0.8)), 3)}
            for m in materiales
        ],
        "objetos": salida,
        "resumido": resumido,
    }


def empaquetar(datos):
    """JSON compacto → zlib → base64 (lo que viaja en POST /api/evaluacion/entregas)."""
    texto = json.dumps(datos, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(zlib.compress(texto, 9)).decode("ascii")


def desempaquetar(paquete):
    return json.loads(zlib.decompress(base64.b64decode(paquete)).decode("utf-8"))
