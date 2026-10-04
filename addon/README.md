# Amatista para Blender (add-on)

Extensión de Blender 4.2+ que lleva las prácticas de Amatista dentro de Blender: revisa la escena mientras el alumno trabaja, da pistas y registra el progreso en la plataforma. Modos **Alumno** y **Desarrollador** (Amatista Author).

```
amatista_blender/        la extensión (blender_manifest.toml, paneles, red, motor)
herramientas/
├─ construir.py          arma la extensión .zip y el paquete con instalador por sistema
├─ generar_iconos.py     iconos PNG de la interfaz
└─ instalador/           .bat, .command, .sh, instalar_en_blender.py y LEEME
tests/
├─ test_construir.py     python -m pytest addon/tests
└─ en_blender.py         dentro de Blender: python addon/tests/en_blender.py (con bpy)
```

```bash
python addon/herramientas/construir.py                         # dist/amatista-<versión>.zip
python addon/herramientas/construir.py --sistema macos \
       --servidor https://api.ejemplo --plataforma https://app.ejemplo   # paquete con instalador
```

Los alumnos no usan estos comandos: la plataforma arma el paquete al descargarlo (`/api/addon/v1/descargas/{sistema}`). Licencia de esta carpeta: GPL-3.0-or-later (usa `bpy`).

Documentación: [docs/motor/referencia/03_addon.md](../docs/motor/referencia/03_addon.md), [instalación](../docs/motor/referencia/04_instalacion_alumno.md) y [modo desarrollador](../docs/motor/referencia/06_modo_desarrollador.md).
