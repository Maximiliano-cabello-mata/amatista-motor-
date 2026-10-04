# Prácticas del motor

Las prácticas guiadas de Blender del plan de estudios, en formato [`amatista.practice/2`](../docs/motor/referencia/08_practicas_v3_y_herramientas.md), cada una con sus casos de prueba.

| Carpeta | Qué hay |
|---|---|
| `blender/cursos.json` | El mapa de la ruta de Blender (`amatista.curriculum/1`): cursos, requisitos y módulos. Lo usa el add-on para «Mi curso». |
| `blender/<curso>/m<n>-<nombre>/` | `practica.json` (la práctica), `pruebas.json` (sus casos) e imágenes de sus píldoras. Van dentro del add-on (sin `pruebas.json`) y se registran en Oracle con `python herramientas/contenido.py practicas` (desde `backend/`) o con Admin › Prácticas de Blender › Registrar las del repositorio. |
| `archivo/v2/` | Las prácticas anteriores al motor v3 (mesa, podio y el ejemplo `table.json`). No se empaquetan ni se registran; el add-on las muestra solo en modo Desarrollador. |

Prácticas actuales:

| Id | Carpeta | Curso › módulo | Lección |
|---|---|---|---|
| `blender.bp.m1.tren` | `blender/principiante/m1-tren/` | Principiante › 1 | `bp1_practica` |
| `blender.bp.m2.espada` | `blender/principiante/m2-espada/` | Principiante › 2 | `bp2_practica` |
| `blender.bp.m3.nave` | `blender/principiante/m3-nave/` | Principiante › 3 | `bp3_practica` |
| `blender.bpi.m1.pinta-nave` | `blender/principiante-intermedio/m1-pinta-nave/` | Principiante-Intermedio › 1 | `bpi1_practica` |
| `blender.bpi.m2.tres-puntos` | `blender/principiante-intermedio/m2-tres-puntos/` | Principiante-Intermedio › 2 | `bpi2_practica` |
| `blender.bpi.m3.pelota` | `blender/principiante-intermedio/m3-pelota/` | Principiante-Intermedio › 3 | `bpi3_practica` |

Una práctica nueva:

```bash
python engine/herramientas/practicas.py nueva blender.bp.m4.casa --plantilla modelado --curso blender_principiante --modulo 4
python engine/herramientas/practicas.py revisar
python engine/herramientas/practicas.py probar
```

Guía completa: [prácticas v3 y herramientas de autor](../docs/motor/referencia/08_practicas_v3_y_herramientas.md). Cambiar una práctica publicada = subir `version` y volver a registrar: el admin publica la nueva.
