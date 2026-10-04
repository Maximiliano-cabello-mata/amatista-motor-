# Amatista Engine (motor)

Python puro (3.11+, sin dependencias ni `bpy`): lee una práctica `amatista.practice/1` o `/2`, evalúa una foto de la escena y decide progreso, paso actual, pistas y autonomía; desde la etapa 2 también arma la guía del paso (qué hacer, teclas, qué resaltar) y decide cuándo acompañar; desde la etapa 3 (motor v3) elige las píldoras de teoría, pausa el progreso con vigilantes, lleva el repaso espaciado y lee el plan de estudios. Lo usan el add-on de Blender (copia dentro del `.zip`) y el backend (que vuelve a evaluar cada intento).

```
amatista_engine/
├─ engine.py, bootstrap.py    AmatistaEngine y create_default_engine()
├─ models.py, snapshot.py     SceneState / SceneObject y su (de)serialización segura
├─ practice/                  loader (validación con errores en español), compiler, schema, templates (plantillas)
├─ validators/                validadores incluidos y su registro (builtin.py)
├─ pedagogy/                  pistas por niveles, progreso, autonomía, grafo de habilidades, píldoras (pills) y repaso (spaced)
├─ curriculum.py              plan de estudios (amatista.curriculum/1) y desbloqueo
├─ testing.py, cli.py         escenas de prueba (Escena) y la terminal de autor
├─ guide/                     etapa 2: guía paso a paso (coach) y acompañante (companion)
├─ tools/                     catálogo de herramientas de Blender y avisos de nivel
└─ blender/                   único lugar con bpy: capturar la escena y roles (tagger)
herramientas/practicas.py      nueva · revisar · probar · simular · validadores · plan (sin Blender)
herramientas/run_in_blender.py  prueba manual desde Scripting
demo.py                         python engine/demo.py (sin Blender)
tests/                          python -m pytest engine/tests
```

Documentación: [docs/motor/](../docs/motor/README.md), sobre todo [arquitectura](../docs/motor/referencia/01_arquitectura.md), [formato de práctica](../docs/motor/referencia/02_formato_de_practica.md) [guía y acompañamiento](../docs/motor/referencia/07_guia_y_acompanamiento.md) y [prácticas v3 y herramientas de autor](../docs/motor/referencia/08_practicas_v3_y_herramientas.md). Historia: [etapas](../docs/motor/etapas/etapa-1.md).
