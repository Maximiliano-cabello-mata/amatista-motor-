# Prácticas del motor

Prácticas en formato [`amatista.practice/1`](../docs/motor/referencia/02_formato_de_practica.md).

| Carpeta | Qué hay |
|---|---|
| `blender/level_<n>/` | Prácticas oficiales del curso de Blender, por nivel. Van dentro del add-on y se registran en Oracle con `python herramientas/contenido.py practicas` (desde `backend/`) o con Admin › Prácticas de Blender › Registrar las del repositorio. |
| `sandbox/` | El ejemplo del prototipo v0.1 (`table.json`), para probar compatibilidad. No se registra. |

Prácticas actuales:

| Id | Archivo | Lección |
|---|---|---|
| `blender.n1.mesa` (versión 2, con `guide` en cada paso) | `blender/level_1/mesa.json` | Módulo 2 › «Práctica: construye una mesa» (`les_103`), la última lección antes del examen |

Una práctica nueva: créala con el modo Desarrollador del add-on ([guía](../docs/motor/referencia/06_modo_desarrollador.md)), expórtala aquí y agrega un bloque `blender_practice` en la **última lección del módulo** (solo el examen puede ir después; [docs/plataforma/02](../docs/plataforma/02_modulos_y_practica.md)). Opcional: `guide.why` y `guide.steps` en cada objetivo para escribir tú la explicación del paso. Cambiar una práctica publicada = subir `version` y volver a registrar: el admin publica la nueva.
