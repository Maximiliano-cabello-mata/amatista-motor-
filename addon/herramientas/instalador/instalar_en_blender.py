"""Instala Amatista en el Blender que lo ejecuta.

Lo lanza «Instalar Amatista» (.bat, .command o .sh) así:

    blender --background --python-exit-code 9 --python instalar_en_blender.py -- amatista-X.Y.Z.zip

1. Comprueba que Blender sea compatible (4.2 o más nuevo: extensiones).
2. Instala la extensión en el repositorio del usuario y la activa
   (si ya estaba, la reemplaza por esta versión).
3. Permite el acceso a internet de Blender, que Amatista necesita para
   guardar el progreso en la plataforma (se puede apagar en Preferencias ›
   Sistema › Red; el add-on sigue funcionando sin conexión y avisa).
4. Guarda las preferencias: al abrir Blender, Amatista ya está ahí.
5. Add-on 5.4: registra el enlace amatista:// para este Blender (protocolo.py),
   así «Abrir en Blender» de la plataforma abre Blender aunque esté cerrado.
   Si no se puede, sigue: el add-on lo vuelve a intentar al arrancar.

Códigos de salida: 0 instalado, 3 Blender no compatible, 4 no se pudo
instalar. La última línea siempre es «AMATISTA_RESULTADO=...».
"""
import importlib.util
import sys
from pathlib import Path

import bpy

MINIMA = (4, 2, 0)
OK, INCOMPATIBLE, ERROR = 0, 3, 4


def terminar(codigo, resultado, mensaje):
    print()
    print(mensaje)
    print(f"AMATISTA_RESULTADO={resultado}")
    sys.stdout.flush()
    sys.exit(codigo)


def buscar_zip():
    argumentos = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argumentos:
        return Path(argumentos[0]).expanduser().resolve()
    candidatos = sorted(Path(__file__).resolve().parent.glob("amatista-*.zip"))
    return candidatos[-1] if candidatos else None


def registrar_enlace():
    """El enlace amatista:// con el protocolo.py de la extensión recién instalada (nunca detiene el instalador)."""
    try:
        carpeta = Path(bpy.utils.user_resource("EXTENSIONS", path="user_default")) / "amatista"
        spec = importlib.util.spec_from_file_location("amatista_protocolo", carpeta / "protocolo.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        ok, texto = modulo.registrar(bpy.app.binary_path)
    except Exception as error:  # noqa: BLE001
        ok, texto = False, f"no se pudo registrar el enlace amatista:// ({error})"
    print(("Enlace con la plataforma: " if ok else "Aviso: ") + texto)
    return ok


def main():
    version = bpy.app.version
    texto_version = ".".join(str(n) for n in version)
    print(f"Blender encontrado: {texto_version} (Python {sys.version.split()[0]})")
    if tuple(version) < MINIMA:
        terminar(
            INCOMPATIBLE, "incompatible",
            f"Tu Blender {texto_version} es anterior a 4.2 y no puede instalar Amatista.\n"
            "Descarga una versión nueva en https://www.blender.org/download/ y vuelve a ejecutar el instalador.",
        )

    archivo = buscar_zip()
    if archivo is None or not archivo.is_file():
        terminar(ERROR, "error", "No encontré el archivo amatista-*.zip junto al instalador.")

    print(f"Instalando {archivo.name}…")
    try:
        resultado = bpy.ops.extensions.package_install_files(
            filepath=str(archivo), repo="user_default", enable_on_install=True, overwrite=True,
        )
    except Exception as error:  # noqa: BLE001
        terminar(ERROR, "error", f"Blender no pudo instalar la extensión: {error}")
    if "FINISHED" not in resultado:
        terminar(ERROR, "error", "Blender no pudo instalar la extensión (revisa los mensajes de arriba).")

    enlace = registrar_enlace()

    preferencias = bpy.context.preferences
    if hasattr(preferencias.system, "use_online_access"):
        preferencias.system.use_online_access = True
    preferencias.use_preferences_save = True
    bpy.ops.wm.save_userpref()
    siguiente = ("Ya puedes pulsar «Abrir en Blender» en la plataforma." if enlace
                 else "Abre Blender: busca el menú Amatista arriba, junto a Ayuda.")
    terminar(OK, "ok", f"Amatista quedó instalado en Blender {texto_version}. {siguiente}")


if __name__ == "__main__":
    main()
