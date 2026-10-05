"""Construye el add-on de Amatista: la extensión .zip y el paquete con instalador.

Uso desde la terminal (en la raíz del repositorio):

    python addon/herramientas/construir.py                      # dist/amatista-3.3.0.zip
    python addon/herramientas/construir.py --sistema windows \\
        --servidor https://api.ejemplo.cl --plataforma https://ejemplo.cl

El backend importa este módulo para armar las descargas al vuelo
(GET /api/addon/v1/descargas/...), así que no hay binarios en el repositorio.

Qué hace:
1. Copia addon/amatista_blender/ (sin pruebas ni cachés).
2. Mete Amatista Engine dentro (amatista_blender/amatista_engine/) para que la
   extensión no dependa de nada instalado aparte.
3. Copia las prácticas de practices/blender/ (cursos.json, practica.json e imágenes) a
   practicas/ (funcionan sin red).
4. Escribe config.json con las direcciones del servidor y de la plataforma y,
   si se pide, un vínculo de un solo uso para conectar la cuenta sin pasos.
5. Comprime con fechas fijas: el mismo código produce el mismo .zip (y el
   mismo hash, que Blender verifica en su repositorio de extensiones).

El paquete con instalador agrega instalar_en_blender.py (comprueba la versión
de Blender e instala la extensión), el lanzador del sistema y un LEEME.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import zipfile
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ADDON = RAIZ / "addon" / "amatista_blender"
MOTOR = RAIZ / "engine" / "amatista_engine"
PRACTICAS = RAIZ / "practices" / "blender"
INSTALADOR = Path(__file__).resolve().parent / "instalador"

FECHA_FIJA = (2026, 1, 1, 0, 0, 0)
# Protección del código en el equipo del alumno (docs/seguridad/02_proteccion_del_codigo.md).
ARCHIVO_INTEGRIDAD = "integridad.json"
ARCHIVO_LICENCIA = "licencia.json"
IGNORAR = {"__pycache__", "tests", ".DS_Store"}
SISTEMAS = ("windows", "macos", "linux")
LANZADORES = {
    "windows": ("Instalar Amatista.bat", 0o644),
    "macos": ("Instalar Amatista.command", 0o755),
    "linux": ("instalar-amatista.sh", 0o755),
}


def leer_manifiesto() -> dict:
    """Campos simples de blender_manifest.toml (sin depender de tomllib en 3.10)."""
    texto = (ADDON / "blender_manifest.toml").read_text(encoding="utf-8")
    datos = {}
    for clave in ("id", "version", "name", "tagline", "maintainer", "type", "website", "blender_version_min"):
        coincidencia = re.search(rf'^{clave}\s*=\s*"([^"]*)"', texto, re.MULTILINE)
        if coincidencia:
            datos[clave] = coincidencia.group(1)
    datos["license"] = re.findall(r'"(SPDX:[^"]+)"', texto)
    datos["tags"] = json.loads(re.search(r"^tags\s*=\s*(\[.*\])", texto, re.MULTILINE).group(1))
    permisos = re.search(r"\[permissions\]\n((?:\w+\s*=.*\n)+)", texto)
    datos["permissions"] = dict(re.findall(r'^(\w+)\s*=\s*"([^"]*)"', permisos.group(1), re.MULTILINE)) if permisos else {}
    return datos


VERSION = leer_manifiesto()["version"]
# Nombre del producto que ve el alumno: «Amatista Motor 3.3» (mayor.menor).
NOMBRE = leer_manifiesto()["name"]
VERSION_CORTA = ".".join(VERSION.split(".")[:2])
NOMBRE_COMPLETO = f"{NOMBRE} {VERSION_CORTA}"
CARPETA_PAQUETE = NOMBRE_COMPLETO


def nombre_extension(version: str = VERSION) -> str:
    return f"amatista-{version}.zip"


def _archivos(carpeta: Path):
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta)
        if ruta.is_file() and not (IGNORAR & set(relativa.parts)) and ruta.suffix != ".pyc":
            yield ruta, relativa.as_posix()


def _agregar(zf: zipfile.ZipFile, nombre: str, contenido: bytes, permisos: int = 0o644, comprimir: bool = True) -> None:
    info = zipfile.ZipInfo(nombre, date_time=FECHA_FIJA)
    info.compress_type = zipfile.ZIP_DEFLATED if comprimir else zipfile.ZIP_STORED
    info.external_attr = (0o100000 | permisos) << 16
    info.create_system = 3  # Unix: conserva los permisos del lanzador en macOS y Linux
    zf.writestr(info, contenido)


def configuracion(servidor: str, plataforma: str, canal: str = "estable", vinculo: dict | None = None) -> dict:
    config = {"servidor": servidor.rstrip("/"), "plataforma": plataforma.rstrip("/"), "canal": canal}
    if vinculo:
        config["vinculo"] = {"id": vinculo["id"], "secreto": vinculo["secreto"]}
    return config


def _huella_fuentes() -> tuple:
    """Cambia cuando cambia algún archivo que entra al paquete (fecha y tamaño)."""
    datos = []
    for carpeta in (ADDON, MOTOR, PRACTICAS):
        for ruta, nombre in _archivos(carpeta):
            info = ruta.stat()
            datos.append((nombre, info.st_mtime_ns, info.st_size))
    return tuple(datos)


_HUELLA = {"momento": -1e9, "valor": ()}


def _huella_reciente(segundos: float = 10.0) -> tuple:
    """_huella_fuentes() recorre ~200 archivos (unos 4 ms): se revisa cada 10 s como mucho."""
    momento = time.monotonic()
    if momento - _HUELLA["momento"] > segundos:
        _HUELLA.update(momento=momento, valor=_huella_fuentes())
    return _HUELLA["valor"]


@lru_cache(maxsize=2)
def _base_extension(_huella: tuple) -> bytes:
    """La extensión sin config.json, ya comprimida.

    Comprimir ~200 archivos es lo caro de cada descarga (informe de
    rendimiento del 5 de octubre: ~55 ms por descarga con cuenta y ~900 ms con
    diez a la vez). Se hace una vez; cada descarga solo agrega su config.json.
    """
    salida = io.BytesIO()
    hashes = {}
    with zipfile.ZipFile(salida, "w") as zf:

        def poner(nombre: str, contenido: bytes) -> None:
            hashes[nombre] = hashlib.sha256(contenido).hexdigest()
            _agregar(zf, nombre, contenido)

        for ruta, nombre in _archivos(ADDON):
            if nombre in ("config.json", ARCHIVO_INTEGRIDAD, ARCHIVO_LICENCIA):
                continue
            poner(nombre, ruta.read_bytes())
        for ruta, nombre in _archivos(MOTOR):
            poner(f"amatista_engine/{nombre}", ruta.read_bytes())
        for ruta, nombre in _archivos(PRACTICAS):
            # Prácticas, mapa de cursos e imágenes de referencia; los casos de prueba se quedan en el repo.
            if ruta.suffix in (".json", ".svg", ".png", ".jpg") and ruta.name != "pruebas.json":
                poner(f"practicas/{nombre}", ruta.read_bytes())
        _agregar(zf, ARCHIVO_INTEGRIDAD, integridad(hashes))
    return salida.getvalue()


def huella_de(hashes: dict) -> str:
    """Huella del paquete: SHA-256 de la lista ordenada «archivo:sha256»."""
    texto = "\n".join(f"{nombre}:{valor}" for nombre, valor in sorted(hashes.items()))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def integridad(hashes: dict) -> bytes:
    """integridad.json: el add-on la compara con sus archivos al arrancar (sin red)."""
    datos = {"version": VERSION, "huella": huella_de(hashes), "archivos": dict(sorted(hashes.items()))}
    return (json.dumps(datos, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def huella_oficial() -> str:
    """La huella del add-on que entrega este servidor (el backend la compara con la que manda el add-on)."""
    with zipfile.ZipFile(io.BytesIO(_base_extension(_huella_reciente()))) as zf:
        return json.loads(zf.read(ARCHIVO_INTEGRIDAD))["huella"]


def construir_extension(servidor: str = "http://localhost:8000", plataforma: str = "http://localhost:5173",
                        canal: str = "estable", vinculo: dict | None = None, licencia: dict | None = None) -> bytes:
    """La extensión lista para Blender (manifiesto en la raíz del .zip).

    licencia: marca de agua firmada por el servidor (api/addon.py) con la
    cuenta que descargó; si una copia circula, dice de quién salió.
    """
    salida = io.BytesIO(_base_extension(_huella_reciente()))
    with zipfile.ZipFile(salida, "a") as zf:
        config = configuracion(servidor, plataforma, canal, vinculo)
        _agregar(zf, "config.json", (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        if licencia:
            _agregar(zf, ARCHIVO_LICENCIA, (json.dumps(licencia, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return salida.getvalue()


def leeme(sistema: str) -> str:
    texto = (INSTALADOR / "LEEME.txt").read_text(encoding="utf-8")
    return texto.replace("{{NOMBRE}}", NOMBRE_COMPLETO.upper()).replace("{{VERSION}}", VERSION).replace("{{LANZADOR}}", LANZADORES[sistema][0])


def construir_paquete(sistema: str, **opciones) -> bytes:
    """Carpeta «Amatista Motor X.Y» con la extensión, el instalador y las instrucciones."""
    if sistema not in SISTEMAS:
        raise ValueError(f"Sistema desconocido: {sistema}. Usa uno de {', '.join(SISTEMAS)}.")
    extension = construir_extension(**opciones)
    lanzador, permisos = LANZADORES[sistema]
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        script = (INSTALADOR / lanzador).read_bytes()
        if lanzador.endswith(".bat"):  # cmd.exe necesita CRLF
            script = script.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        _agregar(zf, f"{CARPETA_PAQUETE}/{lanzador}", script, permisos)
        _agregar(zf, f"{CARPETA_PAQUETE}/instalar_en_blender.py", (INSTALADOR / "instalar_en_blender.py").read_bytes())
        # La extensión ya viene comprimida: se guarda tal cual (comprimirla otra vez solo gasta CPU).
        _agregar(zf, f"{CARPETA_PAQUETE}/{nombre_extension()}", extension, comprimir=False)
        texto = leeme(sistema)
        if sistema == "windows":
            texto = texto.replace("\n", "\r\n")
        _agregar(zf, f"{CARPETA_PAQUETE}/LEEME.txt", texto.encode("utf-8"))
    return salida.getvalue()


def nombre_descarga(sistema: str) -> str:
    """Nombre del archivo que baja la plataforma: Amatista-Motor-3.2-windows.zip."""
    return f"{NOMBRE_COMPLETO.replace(' ', '-')}-{sistema}.zip"


def indice_repositorio(extension: bytes, url_archivo: str) -> dict:
    """index.json de un repositorio remoto de extensiones de Blender (schema 1.0.0).

    Con esto, Preferencias › Get Extensions › Repositories › + › Add Remote
    Repository muestra Amatista y Blender avisa cuando hay versión nueva.
    """
    m = leer_manifiesto()
    return {
        "version": "v1",
        "blocklist": [],
        "data": [{
            "schema_version": "1.0.0",
            "id": m["id"],
            "name": m["name"],
            "tagline": m["tagline"],
            "version": m["version"],
            "type": m["type"],
            "maintainer": m["maintainer"],
            "license": m["license"],
            "blender_version_min": m["blender_version_min"],
            "website": m.get("website", ""),
            "permissions": m["permissions"],
            "tags": m["tags"],
            "archive_url": url_archivo,
            "archive_size": len(extension),
            "archive_hash": "sha256:" + hashlib.sha256(extension).hexdigest(),
        }],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sistema", choices=SISTEMAS, help="Arma el paquete con instalador para ese sistema")
    parser.add_argument("--servidor", default="http://localhost:8000", help="URL de la API de Amatista")
    parser.add_argument("--plataforma", default="http://localhost:5173", help="URL de la PWA")
    parser.add_argument("--canal", default="estable")
    parser.add_argument("--salida", type=Path, default=RAIZ / "dist")
    args = parser.parse_args(argv)
    opciones = {"servidor": args.servidor, "plataforma": args.plataforma, "canal": args.canal}
    args.salida.mkdir(parents=True, exist_ok=True)
    if args.sistema:
        destino = args.salida / f"amatista-{VERSION}-{args.sistema}.zip"
        destino.write_bytes(construir_paquete(args.sistema, **opciones))
    else:
        destino = args.salida / nombre_extension()
        destino.write_bytes(construir_extension(**opciones))
    print(f"Listo: {destino} ({destino.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
