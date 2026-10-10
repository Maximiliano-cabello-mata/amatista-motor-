# Amatista Engine (motor)

Python puro (3.11+, sin dependencias ni `bpy`): lee una práctica `amatista.practice/1` o `/2`, evalúa una foto de la escena y decide progreso, paso actual, pistas y autonomía; desde la etapa 2 también arma la guía del paso (qué hacer, teclas, qué resaltar) y decide cuándo acompañar; desde la etapa 3 (motor v3) elige las píldoras de teoría, pausa el progreso con vigilantes, lleva el repaso espaciado y lee el plan de estudios. Desde el motor 3.4 reconoce la figura por la forma de sus piezas y, desde el 3.5, su silueta cuando está hecha en una sola malla. En el motor 3.5 **el ejemplo manda**: cada práctica trae su ejemplo resuelto en código (`example.steps`) y el motor revisa la escena del alumno contra él, aspecto por aspecto, con el validador `example.matches` (42 validadores en total). Lo usan el add-on de Blender (copia dentro del `.zip`) y el backend (que vuelve a evaluar cada intento).

```
amatista_engine/
├─ engine.py, bootstrap.py    AmatistaEngine y create_default_engine()
├─ models.py, snapshot.py     SceneState / SceneObject y su (de)serialización segura
├─ practice/                  loader (validación con errores en español; agrega el objetivo del ejemplo), compiler, schema, templates (plantillas), plano (SVG)
├─ validators/                los 42 validadores y su registro (builtin.py), incluido example.matches
├─ ejemplo/                   el ejemplo resuelto: la escena esperada (pasos.py) y la revisión contra ella (revision.py)
├─ figures/                   reconocer la figura (reconocer.py) y su silueta (silueta.py)
├─ pedagogy/                  pistas por niveles, progreso, autonomía, grafo de habilidades, píldoras (pills) y repaso (spaced)
├─ curriculum.py              plan de estudios (amatista.curriculum/1) y desbloqueo
├─ testing.py, cli.py         escenas de prueba (Escena) y la terminal de autor
├─ guide/                     etapa 2: guía paso a paso (coach) y acompañante (companion)
├─ tools/                     catálogo de herramientas de Blender y avisos de nivel
└─ blender/                   único lugar con bpy: capturar la escena y roles (tagger)
herramientas/practicas.py      nueva · revisar · probar (también que el ejemplo complete su práctica) · simular · validadores · plan (sin Blender)
herramientas/referencias.py    imagen y plano del modelo de referencia (con bpy)
herramientas/run_in_blender.py  prueba manual desde Scripting
demo.py                         python engine/demo.py (sin Blender)
tests/                          python -m pytest engine/tests
```

## Escribir el ejemplo de una práctica

Cada `practica.json` lleva un bloque `example` con la solución en pasos, en el mismo idioma que los casos de `pruebas.json`:

```json
"example": {
  "title": "Pelota que rebota",
  "description": "La pelota cae, toca el piso en el fotograma 12, se aplasta y vuelve a subir en el 24.",
  "steps": [
    {"esfera": {"nombre": "Pelota", "loc": [0, 0, 4]}},
    {"plano": {"nombre": "Piso"}},
    {"animar": {"objeto": "Pelota", "propiedad": "location", "eje": "z", "claves": [[1, 4], [12, 0.85], [24, 4]]}},
    {"guardado": {"archivo": "mi_pelota.blend"}}
  ]
}
```

1. Arma la solución como un caso de `pruebas.json` que aprueba.
2. Copia esos pasos a `example.steps` y escribe `title` y `description`. Usa `{"referencia": {}}` para armar la figura del modelo de referencia y `check` si solo quieres revisar algunos aspectos.
3. Corre `python engine/herramientas/practicas.py probar <carpeta>`: además de los casos, comprueba que el ejemplo complete la práctica.
4. En Blender, «Ver el ejemplo» lo arma en su propia escena.

Campos, pasos admitidos y cómo revisa cada aspecto: [el ejemplo y la revisión](../docs/motor/referencia/14_ejemplo_y_revision.md).

Documentación: [docs/motor/](../docs/motor/README.md), sobre todo [arquitectura](../docs/motor/referencia/01_arquitectura.md), [formato de práctica](../docs/motor/referencia/02_formato_de_practica.md), [guía y acompañamiento](../docs/motor/referencia/07_guia_y_acompanamiento.md), [prácticas v3 y herramientas de autor](../docs/motor/referencia/08_practicas_v3_y_herramientas.md), [validadores](../docs/motor/referencia/09_validadores.md) y [el ejemplo y la revisión](../docs/motor/referencia/14_ejemplo_y_revision.md). Historia: [etapas](../docs/motor/etapas/etapa-1.md).
