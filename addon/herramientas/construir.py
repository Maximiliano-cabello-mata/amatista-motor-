"""Construye el add-on de Amatista: la extensión .zip y el paquete con instalador.

Uso desde la terminal (en la raíz del repositorio):

    python addon/herramientas/construir.py                      # dist/amatista-3.0.0.zip
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
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ADDON = RAIZ / "addon" / "amatista_blender"
MOTOR = RAIZ / "engine" / "amatista_engine"
PRACTICAS = RAIZ / "practices" / "blender"
INSTALADOR = Path(__file__).resolve().parent / "instalador"

FECHA_FIJA = (2026, 1, 1, 0, 0, 0)
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


def nombre_extension(version: str = VERSION) -> str:
    return f"amatista-{version}.zip"


def _archivos(carpeta: Path):
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta)
        if ruta.is_file() and not (IGNORAR & set(relativa.parts)) and ruta.suffix != ".pyc":
            yield ruta, relativa.as_posix()


def _agregar(zf: zipfile.ZipFile, nombre: str, contenido: bytes, permisos: int = 0o644) -> None:
    info = zipfile.ZipInfo(nombre, date_time=FECHA_FIJA)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100000 | permisos) << 16
    info.create_system = 3  # Unix: conserva los permisos del lanzador en macOS y Linux
    zf.writestr(info, contenido)


def configuracion(servidor: str, plataforma: str, canal: str = "estable", vinculo: dict | None = None) -> dict:
    config = {"servidor": servidor.rstrip("/"), "plataforma": plataforma.rstrip("/"), "canal": canal}
    if vinculo:
        config["vinculo"] = {"id": vinculo["id"], "secreto": vinculo["secreto"]}
    return config


def construir_extension(servidor: str = "http://localhost:8000", plataforma: str = "http://localhost:5173",
                        canal: str = "estable", vinculo: dict | None = None) -> bytes:
    """La extensión lista para Blender (manifiesto en la raíz del .zip)."""
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        for ruta, nombre in _archivos(ADDON):
            if nombre == "config.json":
                continue
            _agregar(zf, nombre, ruta.read_bytes())
        for ruta, nombre in _archivos(MOTOR):
            _agregar(zf, f"amatista_engine/{nombre}", ruta.read_bytes())
        for ruta, nombre in _archivos(PRACTICAS):
            # Prácticas, mapa de cursos e imágenes de las píldoras; los casos de prueba se quedan en el repo.
            if ruta.suffix in (".json", ".svg", ".png") and ruta.name != "pruebas.json":
                _agregar(zf, f"practicas/{nombre}", ruta.read_bytes())
        config = configuracion(servidor, plataforma, canal, vinculo)
        _agregar(zf, "config.json", (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return salida.getvalue()


def leeme(sistema: str) -> str:
    texto = (INSTALADOR / "LEEME.txt").read_text(encoding="utf-8")
    return texto.replace("{{VERSION}}", VERSION).replace("{{LANZADOR}}", LANZADORES[sistema][0])


def construir_paquete(sistema: str, **opciones) -> bytes:
    """Carpeta «Amatista» con la extensión, el instalador y las instrucciones."""
    if sistema not in SISTEMAS:
        raise ValueError(f"Sistema desconocido: {sistema}. Usa uno de {', '.join(SISTEMAS)}.")
    extension = construir_extension(**opciones)
    lanzador, permisos = LANZADORES[sistema]
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        script = (INSTALADOR / lanzador).read_bytes()
        if lanzador.endswith(".bat"):  # cmd.exe necesita CRLF
            script = script.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        _agregar(zf, f"Amatista/{lanzador}", script, permisos)
        _agregar(zf, "Amatista/instalar_en_blender.py", (INSTALADOR / "instalar_en_blender.py").read_bytes())
        _agregar(zf, f"Amatista/{nombre_extension()}", extension)
        texto = leeme(sistema)
        if sistema == "windows":
            texto = texto.replace("\n", "\r\n")
        _agregar(zf, "Amatista/LEEME.txt", texto.encode("utf-8"))
    return salida.getvalue()


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
