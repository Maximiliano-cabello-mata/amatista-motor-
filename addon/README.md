# Amatista para Blender (add-on)

Extensión de Blender 4.2+ (**Amatista Motor 4.0**, versión 4.0.0) que convierte Blender en un aula de Amatista. **Motor 4**: la práctica es una ruta de misiones, una a la vez, con una sola tarjeta en la vista 3D que se anima al empezar y al cumplir cada misión, teclas que se encienden al usarlas, herramientas iluminadas (la de ahora, las usadas y las que vienen; en los niveles 1 y 2 queda elegida en la barra T) y medidas amables según el nivel ([la experiencia del alumno](../docs/motor/referencia/15_experiencia_del_alumno.md)). Pestañas pestañas **Aprender** (píldoras de teoría y repaso), **Practicar** (la práctica con guía paso a paso, «Hazlo conmigo» y pausa cuando algo se rompe) y **Mi curso** (el mapa de cursos y módulos). Cada práctica abre en su propia escena de Blender: abrir otra no arrastra lo de la anterior y «Empezar de nuevo» parte de una escena limpia. Prepara la escena de inicio de cada práctica y registra el progreso en la plataforma. Cada práctica muestra «Así se debe ver» (imagen y plano del modelo de referencia), la temática de su módulo con su personaje y «El ejemplo resuelto»: **Ver el ejemplo** lo arma en su propia escena, sin tocar la del alumno, y la lista «Comparado con el ejemplo» dice qué falta ([el ejemplo y la revisión](../docs/motor/referencia/14_ejemplo_y_revision.md)). En los niveles 1 y 2 Blender abre en **modo enfocado**: solo las herramientas de la práctica, en el panel «Tus herramientas» con «Usar» y «¿Cómo se usa?», y «Ver todo Blender» para volver al Blender completo. Con el **enlace en vivo** (`enlace.py`) Blender late cada 5 s y la lección de la plataforma puede abrir la práctica, comprobar, pedir una pista, «Hazlo conmigo», guardar, empezar de nuevo o mostrar el ejemplo. Cada paquete lleva `integridad.json` y, si se descargó con cuenta, una marca de agua firmada ([protección del código](../docs/seguridad/02_proteccion_del_codigo.md)). Probada en Blender 4.2 y 5.0. Modos **Alumno** y **Desarrollador** (Amatista Author).

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
└─ en_blender.py         dentro de Blender: python addon/tests/en_blender.py (con bpy)
```

```bash
python addon/herramientas/construir.py                         # dist/amatista-4.0.0.zip
python addon/herramientas/construir.py --sistema macos \
       --servidor https://api.ejemplo --plataforma https://app.ejemplo   # paquete con instalador
```

Los alumnos no usan estos comandos: la plataforma arma el paquete al descargarlo (`/api/addon/v1/descargas/{sistema}`). Licencia de esta carpeta: GPL-3.0-or-later (usa `bpy`).

Documentación: [docs/motor/referencia/03_addon.md](../docs/motor/referencia/03_addon.md), [guía y acompañamiento](../docs/motor/referencia/07_guia_y_acompanamiento.md), [instalación](../docs/motor/referencia/04_instalacion_alumno.md), [la plataforma maneja Blender](../docs/motor/referencia/12_plataforma_y_blender.md), [instructor y silueta](../docs/motor/referencia/13_instructor_y_silueta.md) y [modo desarrollador](../docs/motor/referencia/06_modo_desarrollador.md).
