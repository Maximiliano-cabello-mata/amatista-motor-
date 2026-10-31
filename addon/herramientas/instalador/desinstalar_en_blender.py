"""Quita Amatista del Blender que lo ejecuta (lo llama el desinstalador de Windows y Linux).

    blender --background --python-exit-code 9 --python desinstalar_en_blender.py

1. Apaga la extensión y la borra del repositorio del usuario.
2. Borra la plantilla «Blender Amatista» (bl_app_templates_user/amatista).
3. Guarda las preferencias.

Tu avance y tus archivos .blend no se tocan: el avance vive en la plataforma
y en la carpeta de Amatista de tu usuario. Salida 0 siempre que Blender
arranque (si ya no estaba instalada, no hay nada que quitar).
"""
import shutil
import sys
from pathlib import Path

import bpy

MODULO = "bl_ext.user_default.amatista"


def main():
    import addon_utils

    try:
        addon_utils.disable(MODULO, default_set=True)
    except Exception as error:  # noqa: BLE001
        print(f"Aviso: no se pudo apagar Amatista ({error})")
    for tipo, ruta in (("EXTENSIONS", "user_default/amatista"), ("SCRIPTS", "startup/bl_app_templates_user/amatista")):
        try:
            carpeta = Path(bpy.utils.user_resource(tipo, path=ruta))
        except Exception:  # noqa: BLE001
            continue
        if carpeta.is_dir():
            shutil.rmtree(carpeta, ignore_errors=True)
            print(f"Borré {carpeta}")
    bpy.context.preferences.use_preferences_save = True
    bpy.ops.wm.save_userpref()
    print("Amatista quedó desinstalado de este Blender.")
    print("AMATISTA_RESULTADO=ok")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
