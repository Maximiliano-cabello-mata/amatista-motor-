# Amatista Engine (motor)

Python puro (3.11+, sin dependencias ni `bpy`): lee una práctica `amatista.practice/1`, evalúa una foto de la escena y decide progreso, paso actual, pistas y autonomía; desde la etapa 2 también arma la guía del paso (qué hacer, teclas, qué resaltar) y decide cuándo acompañar. Lo usan el add-on de Blender (copia dentro del `.zip`) y el backend (que vuelve a evaluar cada intento).

```
amatista_engine/
├─ engine.py, bootstrap.py    AmatistaEngine y create_default_engine()
├─ models.py, snapshot.py     SceneState / SceneObject y su (de)serialización segura
├─ practice/                  loader (validación con errores en español), compiler, schema
├─ validators/                validadores incluidos y su registro (builtin.py)
├─ pedagogy/                  pistas por niveles, progreso, autonomía, grafo de habilidades
├─ guide/                     etapa 2: guía paso a paso (coach) y acompañante (companion)
├─ tools/                     catálogo de herramientas de Blender y avisos de nivel
└─ blender/                   único lugar con bpy: capturar la escena y roles (tagger)
herramientas/run_in_blender.py  prueba manual desde Scripting
demo.py                         python engine/demo.py (sin Blender)
tests/                          python -m pytest engine/tests
```

Documentación: [docs/motor/](../docs/motor/README.md), sobre todo [arquitectura](../docs/motor/referencia/01_arquitectura.md), [formato de práctica](../docs/motor/referencia/02_formato_de_practica.md) y [guía y acompañamiento](../docs/motor/referencia/07_guia_y_acompanamiento.md). Historia: [etapas](../docs/motor/etapas/etapa-1.md).
