"""¿Esta copia del add-on es la que entregó Amatista? (sin red).

El servidor mete en cada paquete integridad.json con el SHA-256 de cada
archivo y una huella del conjunto. Aquí se recalculan y se comparan:

- «oficial»: todos los archivos coinciden.
- «modificada»: alguien cambió, agregó o quitó código. El panel lo avisa y
  la plataforma marca los intentos como «sin verificar».
- «desarrollo»: no hay integridad.json (se corre desde el repositorio).

Límite honesto: quien modifique el add-on también puede modificar esta
revisión. No impide copiar ni cambiar el código (eso no es posible con un
programa que corre en la computadora del alumno); sirve para que una
copia alterada por descuido o a propósito no pase como oficial y para que
el servidor, que es quien califica, lo sepa. Ver
docs/seguridad/02_proteccion_del_codigo.md.
"""
import hashlib
import json
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
ARCHIVO = "integridad.json"
# Archivos que el servidor escribe por descarga (o Blender crea): no cuentan.
VARIABLES = {"config.json", "licencia.json", ARCHIVO}
IGNORAR = {"__pycache__"}

_resultado = None


def _archivos_actuales():
    for ruta in sorted(CARPETA.rglob("*")):
        if not ruta.is_file() or IGNORAR & set(ruta.relative_to(CARPETA).parts) or ruta.suffix == ".pyc":
            continue
        nombre = ruta.relative_to(CARPETA).as_posix()
        if nombre not in VARIABLES:
            yield nombre, ruta


def revisar(forzar=False):
    """{"estado": oficial|modificada|desarrollo, "huella": str, "cambios": [archivos]}."""
    global _resultado
    if _resultado is not None and not forzar:
        return _resultado
    try:
        esperado = json.loads((CARPETA / ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _resultado = {"estado": "desarrollo", "huella": "", "cambios": []}
        return _resultado
    archivos = esperado.get("archivos") or {}
    actuales = {}
    for nombre, ruta in _archivos_actuales():
        try:
            actuales[nombre] = hashlib.sha256(ruta.read_bytes()).hexdigest()
        except OSError:
            actuales[nombre] = ""
    cambios = sorted(n for n in set(archivos) | set(actuales) if archivos.get(n) != actuales.get(n))
    texto = "\n".join(f"{n}:{v}" for n, v in sorted(actuales.items()))
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    estado = "oficial" if not cambios and huella == esperado.get("huella") else "modificada"
    _resultado = {"estado": estado, "huella": huella, "cambios": cambios[:20]}
    return _resultado


def licencia():
    """La marca de agua de la descarga (cuenta y fecha), o {} si no trae."""
    try:
        return json.loads((CARPETA / "licencia.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
