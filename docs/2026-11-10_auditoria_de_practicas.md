# Auditoría de prácticas y del motor (10 de noviembre de 2026)

Qué se encontró al armar cada práctica como lo haría un alumno, sin Blender, qué se corrigió y qué sigue pendiente. Todo se reproduce con:

```bash
python engine/herramientas/auditar.py
```

## Lo que reportó quien prueba el tren

| Queja | Reproducido | Causa | Estado |
|---|---|---|---|
| «Le puse las 8 ruedas y me regresó un paso» | Sí. Con 7 ruedas bien puestas, agregar la octava recién aplanada bajaba el progreso de 66,7 % a 54,2 % y desmarcaba «ruedas en el suelo» y «ruedas pegadas» | Los pasos posteriores se daban por hechos antes que su requisito: con una sola rueda, «ruedas de pie» se cumple en vacío | Corregido |
| «No avanza» mientras se ponen las ruedas | Sí. El progreso saltaba de 29 % a 67 % con la primera rueda y se quedaba quieto hasta la octava | Un objetivo de conteo valía todo o nada | Corregido: suma en proporción (4 de 8 ruedas, la mitad de su peso) |
| «Es muy exigente con las ruedas, se confunde» | Sí. Ocho ruedas un poco gruesas (0,7 × 0,7 × 0,45) se tomaban todas por chimeneas: «Tienes 0 ruedas» | El reconocimiento comparaba proporciones sin distinguir un disco de una barra | Corregido |
| «No te muestra las medidas» | Sí. «Todavía no es delgado en X o Y: su lado más delgado es Y» para una rueda de pie pero gruesa | Un solo mensaje para dos fallas distintas, sin cifras | Corregido: «está acostado… gíralo con R» o «todavía es grueso: mide 0.45 m de grosor y 0.7 m de ancho. Adelgázalo hasta 0.35 m o menos» |
| «Las figuras no tienen sentido» | Sí. Siguiendo las pistas al pie de la letra (cubo en el origen, `S X 1.6`), los vagones quedan medio hundidos y el motor culpaba a una rueda: «Cylinder.004 debería tocar el suelo» | El piso se toma de la pieza más baja; si esa pieza es un vagón, todas las ruedas «flotan» | Corregido el mensaje: «Cube (Vagón) quedó más abajo que las piezas Rueda: súbela con G y luego Z» |

Lo que **no** resultó ser un problema del motor: un tren al doble de tamaño, con ruedas 40 % más chicas o 50 % más grandes, con vagones 80 % más largos, con las ruedas a 20 cm del vagón o levantadas 20 cm del suelo, se da por bueno. La exigencia de medidas ya era amplia; lo que frustraba eran los cuatro puntos de arriba.

## Las nueve prácticas

`auditar.py` agrega las piezas del modelo una a una, en el orden del modelo y en tres órdenes al azar, y revisa que nada retroceda. También revisa que cada pieza se reconozca sin poner roles, a la mitad y al doble de tamaño, y hecha a mano (±15 %, cinco variaciones).

| Práctica | Piezas | Resultado |
|---|---|---|
| `blender.bp.m1.tren` | 11 | Sin hallazgos después de las correcciones |
| `blender.bp.m2.espada` | 5 | **Un retroceso pendiente** (abajo) |
| `blender.bp.m3.nave` | 6 | Sin hallazgos |
| `blender.bpi.m1.pinta-nave` | 6 | Sin hallazgos |
| `blender.bpi.m2.tres-puntos` | 6 | Sin hallazgos |
| `blender.bpi.m3.pelota` | 1 | Sin hallazgos (una sola pieza: casi nada que auditar) |
| `blender.bi.m1.puente` | 3 | Sin hallazgos |
| `blender.bi.m2.aldea` | 6 | Sin hallazgos (no reconoce piezas por forma, por diseño) |
| `blender.bi.m3.diorama` | 1 | Sin hallazgos (una sola pieza) |

**Pendiente en la espada.** Es una sola malla. Si el alumno saca la guarda (ancha) antes que la hoja, la malla deja de ser «más larga que ancha», el paso «alargar» se desmarca y el progreso baja de 35 % a 5 %. Es del diseño de la práctica: hay que decidir si «alargar» se mide de otra forma o si se quita como paso. Queda declarado en `engine/tests/test_no_retrocede.py` (`CONOCIDOS`) para que no se olvide.

**Límite de esta auditoría.** Solo arma figuras por su caja. No prueba materiales, luces, animación, modificadores ni el modo edición, que es donde trabajan las prácticas de nivel intermedio. Tampoco prueba nada dentro de Blender ni la interfaz del complemento.

## Módulos que se quedaron atrás

Fecha del último cambio de cada módulo en la historia del repositorio:

| Módulo | Último cambio | Líneas | Nota |
|---|---|---|---|
| `engine/…/pedagogy/` (progreso y orden de pasos) | 4 oct | 458 | Aquí estaban el retroceso y el progreso quieto. Un mes sin tocarse mientras las prácticas cambiaban |
| `engine/…/figures/` (reconocer piezas y silueta) | 9 oct | 994 | Aquí estaban las ruedas tomadas por chimeneas y el mensaje del suelo |
| `engine/…/guide/` (`coach.py`, `coach_v3.py`) | 10 oct | 1.563 | Dos generaciones de guía en la misma carpeta |
| `engine/…/ruta/` | 10 oct | 548 | |
| `engine/…/ejemplo/` | 10 oct | 951 | |
| `engine/…/taller/` | 31 oct | 2.897 | Motor 5 |
| `engine/…/guion/` | 31 oct | 589 | Motor 7 |
| `engine/…/corazon/` | 5 nov | 1.582 | El más reciente |

Dos observaciones:

- **Cinco capas deciden «qué sigue»**: `pedagogy`, `guide`, `ruta`, `taller`/`guion` y `corazon`. Cada versión del motor agregó la suya sin retirar la anterior. Las fallas del tren estaban en las dos más viejas, que siguen siendo las que calculan el progreso y reconocen las piezas.
- **El número de versión no dice la verdad**: `amatista_engine.__version__` vale `5.0.0`, el complemento es `7.1.0` y el código habla de «motor 6.1» y «motor 6.2». No se cambió aquí porque la API publica ese número y hay que revisar quién lo compara.

## Sobre usar otros lenguajes

Ninguna de las fallas encontradas viene de un límite de Python: son reglas de enseñanza mal encadenadas. Reescribirlas en C++ las habría dejado igual de mal, más rápido.

C++ o Rust dentro de un complemento de Blender tiene un costo concreto: hay que compilar un binario por sistema operativo, por arquitectura y por versión de Python de cada Blender (4.2, 4.5, 5.0…). Eso va en contra del objetivo de no quedarse atrás con las versiones. Hoy el motor no depende de nada y corre igual en todos lados.

Lo que sí ayudaría a que el código crezca sano:

| Necesidad | Propuesta | Por qué |
|---|---|---|
| Que una regla vieja no se quede atrás en silencio | La auditoría de este documento, corriendo en cada cambio | Ya está: encontró lo que las pruebas que ya existían no veían |
| Errores de forma en las prácticas (JSON) | Un esquema JSON de `amatista.practice/2` validado en CI | Lo valida cualquier lenguaje y cualquier editor |
| Errores de tipos entre módulos | Revisión estática de tipos (`mypy` o `pyright`) en el motor | El motor ya está anotado; falta exigirlo |
| Geometría pesada (silueta de mallas grandes) | Medir primero. Si de verdad es lenta, `numpy`, que Blender ya trae | Sin binarios propios |
| Compartir el contrato entre motor, API y web | Generar tipos de TypeScript desde el esquema | Hoy el modelo ligero se escribe tres veces a mano |

Si más adelante una medición muestra un cuello de botella real, Rust es mejor opción que C++ para un núcleo pequeño. No antes de medir.

## Lo que este cambio no hace

- No toca la interfaz del complemento: tarjetas, diálogos y cuánta información se muestra de golpe.
- No amplía el Corazón ni unifica las cinco capas.
- No envía los errores del complemento al servidor cuando hay conexión.
- No divide los archivos grandes del complemento (`practicas.py`, 989 líneas; `interfaz/`, 3.775).
- No corrige las pistas del tren, que siguen sin decir que hay que subir los vagones ni achicar las ruedas. Ahora el mensaje de error sí lo dice.

## Corazón 1.1: el juicio (agregado el mismo día)

`engine/amatista_engine/corazon/juicio/` compara la escena del alumno con el ejemplo, pieza por pieza, y decide **una** indicación. Son tres módulos sin estado:

| Módulo | Tarea |
|---|---|
| `plano.py` | Lo que se espera: las piezas del ejemplo con sus medidas |
| `diferencia.py` | Lo que hay contra lo que se espera. Cada pieza queda como bien, falta, tamaño o girada |
| `decision.py` | Una sola indicación, por reglas en orden fijo: girar, corregir tamaño, agregar lo que falta y, con todo bien, lo que diga el motor |

Las medidas se piden **en la escala del alumno**: si su tren es el doble de grande, la rueda «debería medir» el doble. Ejemplo real, con una rueda de pie pero gruesa en un tren al doble:

> «Cylinder» (Rueda) mide 0.9 m en Y; en tu figura debería medir cerca de 0.4 m. Redúcela con S y luego Y.

Límites:

- Cubre las prácticas de piezas sueltas (tren, puente, aldea, diorama y pelota). Las cuatro que se modelan en una sola malla (espada, nave, pinta-nave y tres-puntos) no: ahí no hay piezas que separar y sigue mandando la silueta.
- **Conectado al complemento el mismo día.** El `Director` juzga la escena en cada revisión y el turno trae `revision`, `revision_objeto` y `piezas`. En la banda y en el panel, la corrección de una pieza ocupa la línea que antes mostraba el motivo general del paso: no se agrega texto. Solo se muestran correcciones de piezas que ya existen; qué agregar lo sigue diciendo el paso. Probado dentro de Blender 5.0.1 sin ventana (`addon/tests/en_blender.py`); falta verlo con un alumno.
- Una pieza tan deformada que ya no se reconoce (una rueda al triple de grosor) no se reporta como faltante: si sobra un objeto de la misma primitiva, se toma como esa pieza y se dice qué medida corregir.
- Juzga tamaño y giro por la caja de cada pieza. La posición la sigue juzgando el motor.
- El orden en que pide las piezas es el del modelo de referencia, no el de los pasos de la práctica.
