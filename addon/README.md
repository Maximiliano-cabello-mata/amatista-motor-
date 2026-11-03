# Amatista para Blender (add-on)

Extensión de Blender 4.2+ (**Amatista Motor 7.1**, versión `7.1.0`) que conecta Blender con la plataforma Amatista y convierte la vista 3D en un taller guiado.

- **Add-on 7.1 · Corazón Amatista 1.0 (`corazon/`)** ([referencia](../docs/motor/referencia/23_corazon.md)): quien decide qué ve el alumno es el corazón del motor (`amatista_engine.corazon`, contrato estable `amatista.corazon/1`), no estados sueltos del add-on. En `corazon/adaptador.py` solo vive el adaptador de Blender, que ejecuta las señales reales sobre la interfaz y las vuelve a comprobar cada 0,5 s; si dejan de ser verdad, la banda lo avisa y ofrece «Señálalo otra vez». Nada desaparece por reloj.
- **Motor 7 · Guion (`guion/`)** ([referencia](../docs/motor/referencia/22_motor_7.md)): la práctica avanza con lo que hay en la escena, un paso con verbo a la vez y en el orden que el alumno quiera, revisado a los 0,15 s de cada cambio, guardado o `Ctrl + Z`. Muestra una sola banda arriba de la vista 3D y el panel **N › Amatista › Paso a paso** con tres pistas verificadas (`¿Qué falta?`, `¿Dónde está?` y `¿Cómo se hace?`). Las cuentas de administrador practican sin guardar progreso.
- **Motor 6 a 6.2 (`saneamiento.py`, `blender_amatista.py`, `fichas.py`, `navegar.py`, `taller/acompanar.py`)**: autosanación de copias anteriores, plantilla de aplicación «Blender Amatista», fichas de herramientas (`practices/blender/fichas.json`), modo curioso, acompañamiento según el ánimo del alumno y botón «Volver a mi práctica».
- **Motor 5 · Amatista Taller (`taller/`)** ([referencia](../docs/motor/referencia/16_amatista_taller.md)): ciclo por habilidad (**Mira → Hazlo conmigo → Hazlo tú → Úsalo → Recuérdalo**), molde translúcido pieza por pieza e isla del alumno (**Mi isla**).

```text
amatista_blender/        la extensión 7.1.0 (blender_manifest.toml)
├─ corazon/              adaptador de Blender para el Corazón Amatista 1.0 (señales cada 0,5 s)
├─ guion/                banda superior, panel N › Paso a paso y señalización real de herramientas
├─ taller/               sesión por habilidad, molde, demostraciones «Mira», ánimo e isla
├─ interfaz/             paneles, HUD, turno de tarjetas, visor 3D e íconos
├─ plantilla_amatista/   plantilla de aplicación «Blender Amatista» y splash
├─ fichas.py             fichas de herramientas para novatos y modo curioso
├─ plataforma.py         seguimiento en vivo de la lección abierta en la plataforma
├─ protocolo.py          registro y manejo del enlace amatista://
├─ saneamiento.py        autosanación: una sola copia activa y limpieza de manejadores
└─ navegar.py            «Volver a mi práctica» desde cualquier escena
herramientas/
├─ construir.py          arma dist/amatista-7.1.0.zip y los paquetes por sistema
├─ instaladores.py       arma instaladores .exe (Inno Setup) y .deb (Linux)
├─ generar_iconos.py     iconos PNG de la interfaz
├─ generar_splash.py     splash de la plantilla Blender Amatista
└─ instalador/           .bat, .command, .sh, instalar_en_blender.py y LEEME
tests/
├─ test_construir.py     el .zip y los paquetes (python -m pytest addon/tests)
├─ test_integridad.py    integridad.json y marca de agua
├─ test_addon_motor6.py, test_addon_motor61.py, test_addon_motor62.py, test_addon_motor7.py
├─ simular_alumnos.py    100 alumnos simulados con el tren (99/100 terminan con el 7.0/7.1)
└─ en_blender.py         pruebas completas dentro de Blender sin ventana (con bpy)
```

```bash
python addon/herramientas/construir.py                         # dist/amatista-7.1.0.zip
python addon/herramientas/construir.py --sistema macos \
       --servidor https://api.amatista-3d.tech --plataforma https://amatista-3d.tech
```

Licencia de esta carpeta: `GPL-3.0-or-later` (usa `bpy`).
