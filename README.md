# Amatista · Motor

El motor que evalúa lo que el alumno hace en Blender, el complemento que lo lleva dentro de Blender (con el Corazón Amatista) y las prácticas que ambos leen.

Es uno de los repositorios de [Amatista](https://amatista-3dt.tech). Se separó del monorepo el 10 de noviembre de 2026.

| Carpeta | Qué es |
|---|---|
| [`engine/`](engine/) | `amatista_engine`: Python puro, sin dependencias ni `bpy`. Lee una práctica, evalúa una foto de la escena y decide progreso, pistas y guía |
| [`addon/`](addon/) | El complemento de Blender (`amatista_blender`), sus instaladores y sus pruebas. Incluye una copia del motor dentro del `.zip` |
| [`practices/`](practices/) | Las prácticas, habilidades, fichas y ramas, descritas en JSON |

## Responsabilidad

Este repositorio decide **qué es una práctica y cuándo está bien hecha**. No guarda cuentas ni progreso: eso es de la API. No muestra lecciones: eso es de la web.

| Repositorio | Responsabilidad | Relación con el motor |
|---|---|---|
| `amatista-motor-` (este) | Motor, complemento y prácticas | — |
| [`amatista-api-`](https://github.com/Maximiliano-cabello-mata/amatista-api-) | Cuentas, progreso, contenido, clases y base de datos | Importa `amatista_engine` y lee `practices/` para volver a evaluar cada intento |
| Web (hoy en el monorepo) | Lo que ven el alumno, el profesor y el administrador | Sus lecciones enlazan prácticas de `practices/` |
| [`amatista-g7b-etl`](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl) | Datos de rendimiento para Geoda | Ninguna |

## Probar

Con Python 3.11 o posterior y `pytest`:

```bash
python -m pytest -q engine/tests addon/tests
```

Dentro de Blender, con el módulo `bpy` de PyPI:

```bash
pip install bpy==5.0.1
python addon/tests/en_blender.py
```

### Pruebas de contrato

Algunas pruebas comparan el motor con los otros repositorios: el modelo ligero de una entrega (API) y las lecciones que enlazan prácticas (web). Buscan al vecino en una carpeta hermana (`../amatista-api-`) o en `AMATISTA_API_DIR` y `AMATISTA_WEB_DIR`. Si no está, se saltan y dicen qué falta. La regla está en [`vecinos.py`](vecinos.py).

## Historia

La historia de este repositorio sale de filtrar `engine/`, `addon/` y `practices/` del monorepo (del 3 de octubre al 5 de noviembre de 2026). Los identificadores de commit son nuevos; los originales están en la rama `historia/vm-main` del monorepo.

## Licencia

El complemento es GPL ([`addon/amatista_blender/LICENSE`](addon/amatista_blender/LICENSE)). Maximiliano Cabello Mata dirige el proyecto.
