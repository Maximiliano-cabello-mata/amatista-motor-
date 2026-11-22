# Motor de Amatista y add-on para Blender · instrucciones para agentes

**Leer primero la [base oficial del proyecto](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md)** (versión 1, congelada el 22 de noviembre de 2026). Define las piezas, el flujo de trabajo y las prioridades, y manda sobre cualquier otro plan.

> **Amatista** enseña y mide; **G7B** extrae y guarda; **Amatista IA** audita; **Geoda** adapta; **Amatista Machine Learning** crea.

## Lugar de este repositorio en la base

| Pieza | Papel en la base |
|---|---|
| **Motor de Amatista** (`engine/`, `amatista_engine`) | Evalúa lo que el alumno hace en Blender: prácticas, pistas y progreso. Incluye el Corazón Amatista. **No es el motor adaptativo** |
| **Add-on Amatista para Blender** (`addon/`) | Lo descarga el alumno desde Amatista. Lleva el motor a Blender, es **sonda de Blender** (mide el equipo, con permiso) y es donde **corre Geoda**, el kernel adaptativo de G7B |
| **Prácticas** (`practices/`) | Lo que leen el motor, la API y la web |

- **El add-on solo habla con la API de Amatista.** Los datos personales no salen de ahí; hacia G7B solo van mediciones agregadas y con permiso.
- **Geoda llega al add-on en la prioridad 3 de la base** (Geoda mínimo en la vista 3D sobre los perfiles N1–N2). Hasta entonces no se agregan funciones de adaptación al add-on.

## Reglas

- No agregar piezas, servicios, bases de datos ni proveedores de IA. Una idea nueva va al estacionamiento de la base.
- Un solo cambio activo a la vez, y solo dentro de la prioridad vigente de la base.
- La sonda del add-on mide solo con permiso del alumno y nunca envía datos personales.
- Antes de entregar: `python -m pytest -q engine/tests addon/tests`.
- No afirmar que algo está desplegado o probado sin evidencia.
