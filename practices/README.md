# Prácticas, habilidades y ramas del motor

Contenido declarativo que leen **Amatista Engine**, el **add-on de Blender**, el **backend** y la **PWA**.

| Carpeta / archivo | Qué hay |
|---|---|
| `blender/cursos.json` | El mapa de la ruta de Blender (`amatista.curriculum/1`): cursos, requisitos, módulos y el taller de cada módulo. |
| `blender/habilidades.json` | Catálogo de **Amatista Taller** (`amatista.skill/1`): 33 habilidades con 62 variaciones cortas y 9 talleres (uno por módulo de Blender). El backend lo sincroniza al arrancar en la tabla `HABILIDADES`. |
| `blender/fichas.json` | Fuente única de las **26 fichas de herramientas** y **9 zonas de la ventana de Blender** (para qué sirve, a qué se parece, dónde está, cómo se usa y error típico). La usan la teoría de la PWA, el motor y el add-on. |
| `blender/palabras.json` | Diccionario bilingüe de menús y términos de Blender («Agregar (Add) › Malla (Mesh)»). |
| `blender/temas.json` | El mundo de cada módulo: colores, escenario, personaje y jefe final. |
| `blender/referencias.json` | Índice de las imágenes y planos de referencia (generado con `engine/herramientas/referencias.py`). |
| `blender/<curso>/m<n>-<nombre>/` | Las **9 prácticas de proyecto** que cierran cada módulo (`practica.json` en formato `amatista.practice/2` con `reference` y `example`, `pruebas.json`, `referencia.jpg` y `plano.svg`). |
| `ramas/` | Ramas del **Corazón Amatista 1.0** (`blender-principiante.json`, `blender-reto.json`, `aframe-web.json`): configuran perfil, andamio y extensiones con herencia ([ramas/README.md](ramas/README.md)). |
| `archivo/blender/` | Las 9 prácticas cortas de exploración anteriores al Motor 5 (reemplazadas por las actividades de `habilidades.json`). |
| `archivo/v2/` | Prácticas históricas anteriores al motor v3 (`mesa.json`, `podio.json`, `table.json`). |

## Prácticas de proyecto activas (9 módulos de Blender, 58 casos de prueba)

| Id | Carpeta | Curso › Módulo | Lección de proyecto |
|---|---|---|---|
| `blender.bp.m1.tren` | `blender/principiante/m1-tren/` | Principiante › Módulo 1 | `bp1_practica` |
| `blender.bp.m2.espada` | `blender/principiante/m2-espada/` | Principiante › Módulo 2 | `bp2_practica` |
| `blender.bp.m3.nave` | `blender/principiante/m3-nave/` | Principiante › Módulo 3 | `bp3_practica` |
| `blender.bpi.m1.pinta-nave` | `blender/principiante-intermedio/m1-pinta-nave/` | Principiante-Intermedio › Módulo 1 | `bpi1_practica` |
| `blender.bpi.m2.tres-puntos` | `blender/principiante-intermedio/m2-tres-puntos/` | Principiante-Intermedio › Módulo 2 | `bpi2_practica` |
| `blender.bpi.m3.pelota` | `blender/principiante-intermedio/m3-pelota/` | Principiante-Intermedio › Módulo 3 | `bpi3_practica` |
| `blender.bi.m1.puente` | `blender/intermedio/m1-puente/` | Intermedio › Módulo 1 | `bi1_practica` |
| `blender.bi.m2.aldea` | `blender/intermedio/m2-aldea/` | Intermedio › Módulo 2 | `bi2_practica` |
| `blender.bi.m3.diorama` | `blender/intermedio/m3-diorama/` | Intermedio › Módulo 3 | `bi3_practica` |

## Comprobación desde la terminal

```bash
python engine/herramientas/practicas.py revisar
python engine/herramientas/practicas.py probar
python engine/herramientas/corazon.py ramas
```
