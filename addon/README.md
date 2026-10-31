# Amatista para Blender (add-on)

Extensión de Blender 4.2+ (**Amatista Motor 7.0**, versión 7.0.0) que convierte Blender en un taller de Amatista.

**Motor 7 · Guion** ([referencia](../docs/motor/referencia/22_motor_7.md)): la práctica avanza con lo que hay en la escena, un paso con verbo a la vez y en el orden que el alumno quiera, revisado al cambiar, guardar y deshacer. Una sola banda arriba al centro de la vista 3D y el panel **N › Amatista › Paso a paso** con tres pistas (¿Qué falta? · ¿Dónde está? · ¿Cómo se hace?) que señalan de verdad: la herramienta queda elegida en la barra, el menú se abre y las piezas que fallan se seleccionan. Paquete `guion/`. Las cuentas de administrador practican sin progreso. Lo de abajo (motor 5 y 6) sigue debajo del guion; la preferencia «Guion paso a paso» lo apaga.

Antes: **Motor 5 · Amatista Taller** ([referencia](../docs/motor/referencia/16_amatista_taller.md)): el alumno ya no recorre una práctica larga, aprende **habilidades**, cada una con el mismo ciclo: **Mira** (Amatista lo hace en la vista 3D con las teclas en pantalla), **Hazlo conmigo** (lo haces tú sobre un **molde** translúcido que se pinta pieza por pieza), **Hazlo tú** (otras piezas cortas, sin molde ni teclas), **Úsalo** (el proyecto del módulo, que queda en **Mi isla**) y **Recuérdalo** (un reto de un minuto días después). Una sola **tarjeta clicable** abajo al centro de la vista 3D dice qué hacer, con tres botones como máximo; las teclas no se dictan, se piden con la **escalera de pistas** (qué falta › con qué › cómo › Mírame), que tiene freno. Cada actividad empieza en una escena limpia y el proyecto en la suya. El avance se guarda sin conexión (`avance_taller_*.json`) y se envía a la plataforma, que también maneja el taller desde la lección por el enlace en vivo. Paquete `taller/` (sesión, escena, demostraciones, molde y tarjeta, panel, isla).

El proyecto de cada módulo sigue siendo una práctica, que ahora se abre dentro del taller como «Úsalo»; las pestañas de antes quedan para el modo desarrollador y la vista previa. Lo del motor 4 sigue debajo: la práctica es una ruta de misiones, una a la vez, con una sola tarjeta en la vista 3D que se anima al empezar y al cumplir cada misión, teclas que se encienden al usarlas, herramientas iluminadas (la de ahora, las usadas y las que vienen; en los niveles 1 y 2 queda elegida en la barra T) y medidas amables según el nivel ([la experiencia del alumno](../docs/motor/referencia/15_experiencia_del_alumno.md)). Pestañas **Aprender** (píldoras de teoría y repaso), **Practicar** (la práctica con guía paso a paso, «Hazlo conmigo» y pausa cuando algo se rompe) y **Mi curso** (el mapa de cursos y módulos). Cada práctica abre en su propia escena de Blender: abrir otra no arrastra lo de la anterior y «Empezar de nuevo» parte de una escena limpia. Prepara la escena de inicio de cada práctica y registra el progreso en la plataforma. Cada práctica muestra «Así se debe ver» (imagen y plano del modelo de referencia), la temática de su módulo con su personaje y «El ejemplo resuelto»: **Ver el ejemplo** lo arma en su propia escena, sin tocar la del alumno, y la lista «Comparado con el ejemplo» dice qué falta ([el ejemplo y la revisión](../docs/motor/referencia/14_ejemplo_y_revision.md)). En los niveles 1 y 2 Blender abre en **modo enfocado**: solo las herramientas de la práctica, en el panel «Tus herramientas» con «Usar» y «¿Cómo se usa?», y «Ver todo Blender» para volver al Blender completo. Con el **enlace en vivo** (`enlace.py`) Blender late cada 5 s y la lección de la plataforma puede abrir la práctica, comprobar, pedir una pista, «Hazlo conmigo», guardar, empezar de nuevo o mostrar el ejemplo. Cada paquete lleva `integridad.json` y, si se descargó con cuenta, una marca de agua firmada ([protección del código](../docs/seguridad/02_proteccion_del_codigo.md)). Probada en Blender 4.2 y 5.0. Modos **Alumno** y **Desarrollador** (Amatista Author).

```
amatista_blender/        la extensión (blender_manifest.toml, paneles, red, motor)
herramientas/
├─ construir.py          arma la extensión .zip y el paquete con instalador por sistema
├─ generar_iconos.py     iconos PNG de la interfaz
└─ instalador/           .bat, .command, .sh, instalar_en_blender.py y LEEME
tests/
├─ test_construir.py     el .zip y los paquetes (python -m pytest addon/tests)
├─ test_integridad.py    integridad.json: copia oficial, modificada o del repositorio
├─ test_temas.py         temáticas por módulo (temas.py, sin Blender)
├─ test_addon_motor7.py  lo que no debe volver (sin Blender)
├─ simular_alumnos.py    100 alumnos simulados con el tren: --motor 6|7 (con bpy)
└─ en_blender.py         dentro de Blender: python addon/tests/en_blender.py (con bpy)
```

```bash
python addon/herramientas/construir.py                         # dist/amatista-7.0.0.zip
python addon/herramientas/construir.py --sistema macos \
       --servidor https://api.ejemplo --plataforma https://app.ejemplo   # paquete con instalador
```

Los alumnos no usan estos comandos: la plataforma arma el paquete al descargarlo (`/api/addon/v1/descargas/{sistema}`). Licencia de esta carpeta: GPL-3.0-or-later (usa `bpy`).

Documentación: [Amatista Taller](../docs/motor/referencia/16_amatista_taller.md), [docs/motor/referencia/03_addon.md](../docs/motor/referencia/03_addon.md), [guía y acompañamiento](../docs/motor/referencia/07_guia_y_acompanamiento.md), [instalación](../docs/motor/referencia/04_instalacion_alumno.md), [la plataforma maneja Blender](../docs/motor/referencia/12_plataforma_y_blender.md), [instructor y silueta](../docs/motor/referencia/13_instructor_y_silueta.md) y [modo desarrollador](../docs/motor/referencia/06_modo_desarrollador.md).
