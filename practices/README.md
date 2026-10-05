# Prácticas del motor

Las prácticas guiadas de Blender del plan de estudios, en formato [`amatista.practice/2`](../docs/motor/referencia/08_practicas_v3_y_herramientas.md), cada una con sus casos de prueba.

| Carpeta | Qué hay |
|---|---|
| `blender/cursos.json` | El mapa de la ruta de Blender (`amatista.curriculum/1`): cursos, requisitos y módulos. Lo usa el add-on para «Mi curso». |
| `blender/<curso>/m<n>-<nombre>/` | `practica.json` (la práctica, con su modelo de referencia en `reference`), `pruebas.json` (sus casos), `referencia.jpg` y `plano.svg` (cómo se debe ver, generados con `engine/herramientas/referencias.py`) e imágenes de sus píldoras. Van dentro del add-on (sin `pruebas.json`). El servidor las registra y publica solo al arrancar; también con `python herramientas/contenido.py practicas` (desde `backend/`) o Admin › Prácticas de Blender. |
| `blender/temas.json` | El mundo de cada módulo: colores, escenario, personaje (consejos, charla, datos y reacciones) y jefe. Lo comparten la plataforma y el add-on. |
| `blender/referencias.json` | Índice de las imágenes de referencia (lo escribe `referencias.py`). |
| `archivo/v2/` | Las prácticas anteriores al motor v3 (mesa, podio y el ejemplo `table.json`). No se empaquetan ni se registran; el add-on las muestra solo en modo Desarrollador. |

Prácticas actuales (18: en cada módulo, una exploración corta y una práctica de cierre, intercaladas con la teoría):

| Id | Carpeta | Curso › módulo | Lección |
|---|---|---|---|
| `blender.bp.m1.explora` | `blender/principiante/m1-explora/` | Principiante › 1 · exploración | `bp1_blender` |
| `blender.bp.m1.tren` | `blender/principiante/m1-tren/` | Principiante › 1 · cierre | `bp1_practica` |
| `blender.bp.m2.explora` | `blender/principiante/m2-explora/` | Principiante › 2 · exploración | `bp2_blender` |
| `blender.bp.m2.espada` | `blender/principiante/m2-espada/` | Principiante › 2 · cierre | `bp2_practica` |
| `blender.bp.m3.explora` | `blender/principiante/m3-explora/` | Principiante › 3 · exploración | `bp3_blender` |
| `blender.bp.m3.nave` | `blender/principiante/m3-nave/` | Principiante › 3 · cierre | `bp3_practica` |
| `blender.bpi.m1.explora` | `blender/principiante-intermedio/m1-explora/` | Principiante-Intermedio › 1 · exploración | `bpi1_blender` |
| `blender.bpi.m1.pinta-nave` | `blender/principiante-intermedio/m1-pinta-nave/` | Principiante-Intermedio › 1 · cierre | `bpi1_practica` |
| `blender.bpi.m2.explora` | `blender/principiante-intermedio/m2-explora/` | Principiante-Intermedio › 2 · exploración | `bpi2_blender` |
| `blender.bpi.m2.tres-puntos` | `blender/principiante-intermedio/m2-tres-puntos/` | Principiante-Intermedio › 2 · cierre | `bpi2_practica` |
| `blender.bpi.m3.explora` | `blender/principiante-intermedio/m3-explora/` | Principiante-Intermedio › 3 · exploración | `bpi3_blender` |
| `blender.bpi.m3.pelota` | `blender/principiante-intermedio/m3-pelota/` | Principiante-Intermedio › 3 · cierre | `bpi3_practica` |
| `blender.bi.m1.explora` | `blender/intermedio/m1-explora/` | Intermedio › 1 · exploración | `bi1_blender` |
| `blender.bi.m1.puente` | `blender/intermedio/m1-puente/` | Intermedio › 1 · cierre | `bi1_practica` |
| `blender.bi.m2.explora` | `blender/intermedio/m2-explora/` | Intermedio › 2 · exploración | `bi2_blender` |
| `blender.bi.m2.aldea` | `blender/intermedio/m2-aldea/` | Intermedio › 2 · cierre | `bi2_practica` |
| `blender.bi.m3.explora` | `blender/intermedio/m3-explora/` | Intermedio › 3 · exploración | `bi3_blender` |
| `blender.bi.m3.diorama` | `blender/intermedio/m3-diorama/` | Intermedio › 3 · cierre | `bi3_practica` |

El curso Avanzado está bloqueado y todavía no tiene prácticas ([ruta de aprendizaje](../docs/cursos/03_ruta_de_aprendizaje_blender.md)).

Una práctica nueva:

```bash
python engine/herramientas/practicas.py nueva blender.bp.m4.casa --plantilla modelado --curso blender_principiante --modulo 4
python engine/herramientas/practicas.py revisar
python engine/herramientas/practicas.py probar
```

Guía completa: [prácticas v3 y herramientas de autor](../docs/motor/referencia/08_practicas_v3_y_herramientas.md). Cambiar una práctica publicada = subir `version` y volver a registrar: el admin publica la nueva.
