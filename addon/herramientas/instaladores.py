"""Prepara los instaladores de verdad de Amatista (motor 6.2): .exe para Windows y .deb para Linux.

El creador lo pidió: «abandonemos el concepto de descargar el zip, que sea
una aplicación [...] un .exe, una aplicación segura, que Windows y Linux no la
detecten como maliciosa». El .zip con el .bat sigue en la plataforma como plan
B, pero lo principal es un instalador firmado que se abre con doble clic.

    python addon/herramientas/instaladores.py preparar   # dist/instaladores/comun/ (lo que lleva cada instalador)
    python addon/herramientas/instaladores.py deb        # dist/instaladores/amatista_X.Y.Z_all.deb (necesita dpkg-deb)
    python addon/herramientas/instaladores.py version    # imprime la versión (para el flujo de CI)

El .exe lo compila Inno Setup en Windows con instalador/windows/amatista.iss
sobre la carpeta que deja «preparar» (el flujo .github/workflows/instaladores.yml
lo hace solo y lo firma si están los secretos; ver docs/motor/referencia/21_motor_6_2.md).

Por qué así y no un .exe hecho a mano:

- **Un solo instalador para todos.** La firma de código sella el archivo:
  si se le metiera un vínculo de cuenta por alumno, la firma se rompería.
  Por eso el instalador firmado es igual para todos y la cuenta se conecta
  después, desde Blender («Conectar mi cuenta»), con el código de siempre.
- **Sin administrador.** Se instala en la carpeta del usuario
  (``%LOCALAPPDATA%\\Programs\\Amatista``): sin UAC y sin tocar el sistema.
- **Nada que se descargue y ejecute al vuelo.** Todo viene dentro y lo
  instala el Blender del alumno; los antivirus marcan justo lo contrario
  (descargadores, empaquetadores como UPX, scripts ocultos).
"""
from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir  # noqa: E402

RAIZ = construir.RAIZ
INSTALADOR = construir.INSTALADOR
SALIDA = RAIZ / "dist" / "instaladores"
SERVIDOR = "https://api.amatista-3d.tech"
PLATAFORMA = "https://amatista-3d.tech"
ICONOS = (RAIZ / "frontend" / "public" / "icons" / "pwa-192.png", construir.ADDON / "iconos" / "logo.png")
PAQUETE_DEB = "amatista"
COMUNES = ("instalar_en_blender.py", "desinstalar_en_blender.py")


def version() -> str:
    return construir.VERSION


def icono_ico(pngs) -> bytes:
    """Un .ico con imágenes PNG dentro (Windows Vista en adelante lo lee así): sin Pillow."""
    imagenes = []
    for ruta in pngs:
        datos = Path(ruta).read_bytes()
        ancho, alto = struct.unpack(">II", datos[16:24])
        imagenes.append((ancho, alto, datos))
    cabecera = struct.pack("<HHH", 0, 1, len(imagenes))
    directorio, cuerpo = b"", b""
    desplazamiento = 6 + 16 * len(imagenes)
    for ancho, alto, datos in imagenes:
        directorio += struct.pack("<BBBBHHII", ancho % 256, alto % 256, 0, 0, 1, 32, len(datos),
                                  desplazamiento + len(cuerpo))
        cuerpo += datos
    return cabecera + directorio + cuerpo


def preparar(destino: Path = SALIDA / "comun", servidor: str = SERVIDOR, plataforma: str = PLATAFORMA) -> Path:
    """La carpeta que llevan los dos instaladores: la extensión oficial, los scripts y el icono."""
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    extension = construir.construir_extension(servidor=servidor, plataforma=plataforma)
    (destino / construir.nombre_extension()).write_bytes(extension)
    for nombre in COMUNES:
        shutil.copyfile(INSTALADOR / nombre, destino / nombre)
    shutil.copyfile(construir.ADDON / "LICENSE", destino / "LICENSE.txt")
    (destino / "amatista.ico").write_bytes(icono_ico(p for p in ICONOS if p.is_file()))
    shutil.copyfile(ICONOS[0], destino / "amatista.png")
    (destino / "VERSION").write_text(version() + "\n", encoding="utf-8")
    return destino


def control_deb(tam_kb: int) -> str:
    return "\n".join([
        f"Package: {PAQUETE_DEB}",
        f"Version: {version()}",
        "Section: education",
        "Priority: optional",
        "Architecture: all",
        "Depends: bash",
        "Recommends: blender (>= 4.2) | flatpak",
        f"Installed-Size: {tam_kb}",
        "Maintainer: Maximiliano Cabello Mata <noreply@amatista-3d.tech>",
        "Homepage: https://amatista-3d.tech",
        "Description: Amatista para Blender: aprende 3D habilidad por habilidad",
        " Instala Amatista Motor en tu Blender (4.2 o más nuevo) y lo abre como",
        " «Blender Amatista»: prácticas guiadas, la herramienta que toca iluminada",
        " y tu avance conectado con la plataforma amatista-3d.tech.",
        "",
    ])


def armar_arbol_deb(comun: Path, raiz: Path) -> Path:
    """El árbol del .deb: /usr/share/amatista (lo común), /usr/bin/amatista y su acceso directo."""
    if raiz.exists():
        shutil.rmtree(raiz)
    compartido = raiz / "usr" / "share" / PAQUETE_DEB
    compartido.mkdir(parents=True)
    for archivo in comun.iterdir():
        if archivo.suffix != ".ico":
            shutil.copyfile(archivo, compartido / archivo.name)
    linux = INSTALADOR / "linux"
    binario = raiz / "usr" / "bin" / PAQUETE_DEB
    binario.parent.mkdir(parents=True)
    shutil.copyfile(linux / "amatista", binario)
    binario.chmod(0o755)
    escritorio = raiz / "usr" / "share" / "applications" / "amatista.desktop"
    escritorio.parent.mkdir(parents=True)
    shutil.copyfile(linux / "amatista.desktop", escritorio)
    icono = raiz / "usr" / "share" / "icons" / "hicolor" / "192x192" / "apps" / "amatista.png"
    icono.parent.mkdir(parents=True)
    shutil.copyfile(comun / "amatista.png", icono)
    doc = raiz / "usr" / "share" / "doc" / PAQUETE_DEB / "copyright"
    doc.parent.mkdir(parents=True)
    shutil.copyfile(comun / "LICENSE.txt", doc)
    tam = sum(f.stat().st_size for f in raiz.rglob("*") if f.is_file()) // 1024 + 1
    control = raiz / "DEBIAN" / "control"
    control.parent.mkdir(parents=True)
    control.write_text(control_deb(tam), encoding="utf-8")
    for guion in ("postinst", "prerm"):
        destino = raiz / "DEBIAN" / guion
        shutil.copyfile(linux / guion, destino)
        destino.chmod(0o755)
    for carpeta in [raiz, *[p for p in raiz.rglob("*") if p.is_dir()]]:
        carpeta.chmod(0o755)
    return raiz


def deb(comun: Path = SALIDA / "comun") -> Path:
    if not comun.is_dir():
        preparar(comun)
    if shutil.which("dpkg-deb") is None:
        raise SystemExit("Falta dpkg-deb (Debian/Ubuntu: viene con dpkg).")
    raiz = armar_arbol_deb(comun, SALIDA / "deb")
    salida = SALIDA / f"{PAQUETE_DEB}_{version()}_all.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(raiz), str(salida)], check=True)
    return salida


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("accion", choices=("preparar", "deb", "version"))
    parser.add_argument("--servidor", default=SERVIDOR)
    parser.add_argument("--plataforma", default=PLATAFORMA)
    args = parser.parse_args(argv)
    if args.accion == "version":
        print(version())
        return 0
    if args.accion == "preparar":
        print(f"Listo: {preparar(servidor=args.servidor, plataforma=args.plataforma)}")
        return 0
    preparar(servidor=args.servidor, plataforma=args.plataforma)
    print(f"Listo: {deb()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
