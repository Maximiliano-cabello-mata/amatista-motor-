"""La lección de la plataforma, vista desde Blender (motor 6.1).

Pedido del creador: «el motor funciona como una extensión de la plataforma, no
una cosa separada; una no puede vivir sin la otra». Hasta el 6.0 Blender solo
sabía de la plataforma cuando le mandaba abrir un taller, y al cumplir la etapa
«Volver a la plataforma» abría otra pestaña del navegador.

Ahora la lección abierta en la plataforma se lo dice a Blender con la orden
«leccion» (al abrirse y cada poco mientras está a la vista): curso, lección,
título, qué clase de lección es (teoría, Blender, examen) y su lugar en el
módulo. Con eso Blender:

- muestra en la barra de estado y en la barra de Blender Amatista dónde va el
  alumno en la plataforma («Lección 2 de 5 · Extruir, cortar y limpiar»);
- al cumplir la etapa no abre otra pestaña si la plataforma está abierta: la
  lección ya avanzó sola y Blender lo dice («La plataforma ya pasó a…»);
- si la plataforma no está abierta, «Ir a la plataforma» la abre en la lección.

Sin bpy: lo prueban las pruebas del add-on sin Blender.
"""
import time

VIVA = 240.0  # s: la plataforma repite la orden cada 90 s mientras la lección está a la vista
CLASES = ("teoria", "blender", "examen", "proyecto")
NOMBRE_CLASE = {"teoria": "teoría", "blender": "en Blender", "examen": "examen", "proyecto": "proyecto"}

LECCION = {}


def _vacia():
    return {"curso": "", "leccion": "", "titulo": "", "clase": "", "numero": 0, "total": 0, "modulo": "", "en": 0.0}


LECCION.update(_vacia())


def reiniciar():
    LECCION.update(_vacia())


def _texto(valor, largo):
    return str(valor or "").strip()[:largo]


def _entero(valor):
    try:
        return max(0, min(99, int(valor)))
    except (TypeError, ValueError):
        return 0


def recibir(datos, ahora=None):
    """La orden «leccion» de la plataforma. Devuelve True si la lección cambió."""
    datos = datos if isinstance(datos, dict) else {}
    leccion = _texto(datos.get("leccion"), 120)
    if not leccion:
        return False
    antes = LECCION["leccion"]
    clase = _texto(datos.get("clase"), 12)
    LECCION.update(curso=_texto(datos.get("curso"), 60), leccion=leccion, titulo=_texto(datos.get("titulo"), 120),
                   clase=clase if clase in CLASES else "teoria", numero=_entero(datos.get("numero")),
                   total=_entero(datos.get("total")), modulo=_texto(datos.get("modulo"), 80),
                   en=time.time() if ahora is None else float(ahora))
    return leccion != antes


def viva(ahora=None):
    """¿La plataforma está abierta en una lección (avisó hace poco)?"""
    ahora = time.time() if ahora is None else ahora
    return bool(LECCION["leccion"]) and ahora - LECCION["en"] <= VIVA


def actual(ahora=None):
    return dict(LECCION) if viva(ahora) else None


def ruta():
    """La dirección de la lección en la plataforma, o "" si no se sabe."""
    if not LECCION["leccion"] or not LECCION["curso"]:
        return ""
    return f"#/curso/{LECCION['curso']}/leccion/{LECCION['leccion']}"


def texto_corto(ahora=None):
    """«Lección 2 de 5 · Extruir, cortar y limpiar (teoría)» o "" si la plataforma no está abierta."""
    leccion = actual(ahora)
    if leccion is None:
        return ""
    lugar = f"Lección {leccion['numero']} de {leccion['total']} · " if leccion["numero"] and leccion["total"] else ""
    clase = NOMBRE_CLASE.get(leccion["clase"], "")
    return f"{lugar}{leccion['titulo'] or 'tu lección'}{f' ({clase})' if clase else ''}"


def frase_al_volver(leccion_de_la_etapa="", ahora=None):
    """Lo que dice Blender al cumplir la etapa, según dónde esté la plataforma ("" si no está abierta)."""
    leccion = actual(ahora)
    if leccion is None:
        return ""
    if leccion_de_la_etapa and leccion["leccion"] == leccion_de_la_etapa:
        return "¡Listo! Tu lección en el navegador ya lo sabe y sigue sola en un momento."
    titulo = f"«{leccion['titulo']}»" if leccion["titulo"] else "la siguiente lección"
    if leccion["clase"] == "teoria":
        return f"¡Listo! La plataforma ya pasó a {titulo}: es la teoría de lo que acabas de hacer."
    if leccion["clase"] == "examen":
        return f"¡Listo! La plataforma ya pasó a {titulo}. Blender te espera para lo que sigue."
    return f"¡Listo! La plataforma ya pasó a {titulo}."


__all__ = ["CLASES", "LECCION", "VIVA", "actual", "frase_al_volver", "recibir", "reiniciar", "ruta", "texto_corto",
           "viva"]
