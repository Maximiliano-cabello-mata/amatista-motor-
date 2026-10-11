"""«Conoce Amatista Motor»: las tres prácticas del add-on, sus paradas y lo que viaja a la plataforma.

Sin bpy (se prueba con pytest en addon/tests/test_recorrido.py). recorrido.py
es la parte que vive en Blender: comprueba cada parada en la escena, dibuja la
tarjeta y avisa a la plataforma.

Add-on 5.2 (11 de octubre): el recorrido de diez paradas del 5.1 se volvió tres
prácticas cortas que, juntas, explican todas las herramientas del add-on. No son
un curso: viven en la página Blender de la plataforma (#/blender, «Conoce
Amatista Motor») y en la pestaña Amatista.

1. «Tu pestaña Amatista»: la barra N, la cuenta, la plataforma, la lección
   actual, los ajustes y cómo viaja tu avance.
2. «Muévete y usa tus herramientas»: la vista 3D (orbitar, acercar, elegir,
   mover, girar, escalar), «Tus herramientas», «¿Cómo se usa?» y el modo
   enfocado.
3. «Así te enseña el taller»: el ciclo de cada habilidad, la tarjeta, «Mira»,
   el molde, «Comprobar», las pistas con freno, pausa y saltar, Mi isla, los
   repasos y la lección en vivo.

Cada parada enseña una sola cosa y, cuando se puede, se comprueba sola: el
alumno hace lo que se pide y la parada se marca sin que tenga que pulsar nada.
Las que solo explican se pasan con «Siguiente». Las de tipo «uso:…» se marcan al
pulsar el botón del add-on del que hablan (recorrido.anotar).

La plataforma ve lo mismo en vivo (detalle.recorrido del latido) y puede empezar
una práctica y avanzarla (orden «recorrido» con accion empezar · siguiente ·
anterior · salir y el id de la práctica en `recorrido`).
"""

# comprobar: ninguna · barra · cuenta · orbitar · acercar · elegir · mover · girar · escalar · uso:<clave>.
# Ver recorrido.py › COMPROBACIONES y anotar(). «opcional»: se puede seguir sin hacerla.
RECORRIDOS = {
    "pestana": {
        "nombre": "Tu pestaña Amatista",
        "resumen": "Dónde está todo: tu cuenta, la plataforma, tu lección y cómo viaja tu avance.",
        "pasos": (
            {
                "id": "hola",
                "titulo": "Hola, soy Amatista",
                "texto": "La plataforma te explica la idea y Blender es donde la haces. Yo vivo en los dos y los "
                         "mantengo conectados: lo que haces aquí aparece allá, en vivo.",
                "hacer": "Pulsa «Siguiente» para empezar.",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "barra",
                "titulo": "Tu pestaña Amatista",
                "texto": "La barra lateral de la vista 3D se abre y se cierra con N. En su pestaña Amatista está "
                         "todo: tu cuenta, tu taller, tus herramientas y Mi isla.",
                "hacer": "Con el ratón sobre la vista 3D, pulsa N hasta ver la pestaña Amatista.",
                "teclas": ("N",),
                "comprobar": "barra",
            },
            {
                "id": "cuenta",
                "titulo": "Conecta tu cuenta",
                "texto": "Vincular une este Blender con tu cuenta: tu avance se guarda y la lección te ve en vivo. "
                         "Se hace una sola vez y nunca escribes tu contraseña en Blender.",
                "hacer": "Pulsa «Vincular» y escribe en la plataforma (Blender › Vincular) el código que aparece.",
                "teclas": (),
                "comprobar": "cuenta",
                "opcional": True,  # sin cuenta todavía: se puede seguir y vincular después
            },
            {
                "id": "plataforma",
                "titulo": "La plataforma, a un clic",
                "texto": "«Abrir la plataforma» abre Amatista en tu navegador. Allá están la teoría, tus cursos y "
                         "Mi panel; desde la lección puedes darle órdenes a este Blender.",
                "hacer": "Pulsa «Abrir la plataforma» en esta tarjeta del panel.",
                "teclas": (),
                "comprobar": "uso:plataforma",
                "opcional": True,
            },
            {
                "id": "leccion",
                "titulo": "Tu lección, sin buscarla",
                "texto": "«Abrir mi lección actual» abre aquí el taller o la práctica de la lección que tienes "
                         "abierta en la plataforma. También puedes pulsar «Abrir en Blender» desde la lección.",
                "hacer": "Recuerda: lección abierta en la plataforma › «Abrir mi lección actual» aquí.",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "ajustes",
                "titulo": "Amatista, a tu gusto",
                "texto": "En los niveles 1 y 2 Blender se enfoca: solo ves lo que usa la práctica. Eso y cuánto te "
                         "acompaño (tarjeta, avisos, diálogos) se cambia en la plataforma: Blender › Tu Blender.",
                "hacer": "Pulsa «Siguiente». Puedes cambiarlo cuando quieras desde la plataforma.",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "guardar",
                "titulo": "Tu avance viaja solo",
                "texto": "Cada intento se guarda en tu computadora y se envía a tu cuenta. Sin Internet se guarda "
                         "igual y se envía después. «Guardar mi avance» lo envía ahora mismo.",
                "hacer": "Pulsa «Guardar mi avance» en esta tarjeta del panel.",
                "teclas": (),
                "comprobar": "uso:guardar",
                "opcional": True,
            },
            {
                "id": "listo",
                "titulo": "¡Ya conoces tu pestaña!",
                "texto": "Sigue con «Muévete y usa tus herramientas»: la vista 3D, tus herramientas y el modo "
                         "enfocado.",
                "hacer": "Pulsa «Terminar».",
                "teclas": (),
                "comprobar": "ninguna",
            },
        ),
    },
    "vista": {
        "nombre": "Muévete y usa tus herramientas",
        "resumen": "La vista 3D, mover, girar y escalar, «Tus herramientas», «¿Cómo se usa?» y el modo enfocado.",
        "pasos": (
            {
                "id": "orbitar",
                "titulo": "Mira alrededor",
                "texto": "Orbitar es girar la vista alrededor de lo que miras. El cubo no se mueve: te mueves tú.",
                "hacer": "Arrastra con el botón central del ratón (la rueda). Con trackpad: dos dedos.",
                "teclas": ("Botón central",),
                "comprobar": "orbitar",
            },
            {
                "id": "acercar",
                "titulo": "Acércate y aléjate",
                "texto": "La rueda del ratón acerca y aleja la vista. Si te pierdes, la tecla Inicio encuadra "
                         "toda la escena.",
                "hacer": "Gira la rueda del ratón sobre la vista 3D. Con trackpad: pellizca.",
                "teclas": ("Rueda",),
                "comprobar": "acercar",
            },
            {
                "id": "elegir",
                "titulo": "Elige el cubo",
                "texto": "Antes de cambiar algo, lo eliges. El objeto elegido se ve con un borde naranja.",
                "hacer": "Haz clic sobre el cubo.",
                "teclas": ("Clic",),
                "comprobar": "elegir",
            },
            {
                "id": "mover",
                "titulo": "Muévelo",
                "texto": "G mueve. Después de la tecla mueves el ratón y haces clic para dejarlo. Clic derecho o "
                         "Esc cancelan.",
                "hacer": "Con el cubo elegido, pulsa G, mueve el ratón y haz clic.",
                "teclas": ("G", "Clic"),
                "comprobar": "mover",
            },
            {
                "id": "girar",
                "titulo": "Gíralo",
                "texto": "R gira. Si después pulsas X, Y o Z, gira solo en ese eje.",
                "hacer": "Pulsa R, mueve el ratón y haz clic.",
                "teclas": ("R", "Clic"),
                "comprobar": "girar",
            },
            {
                "id": "escalar",
                "titulo": "Cámbiale el tamaño",
                "texto": "S escala: lo agranda o lo achica. Con S y luego Z lo estiras solo hacia arriba.",
                "hacer": "Pulsa S, mueve el ratón y haz clic.",
                "teclas": ("S", "Clic"),
                "comprobar": "escalar",
            },
            {
                "id": "herramientas",
                "titulo": "Tus herramientas",
                "texto": "La caja «Tus herramientas» muestra solo las que usa la práctica, con su tecla. «Usar» "
                         "la arranca como si pulsaras la tecla; la que toca ahora se enciende.",
                "hacer": "Pulsa «Usar» en una de las herramientas de esta tarjeta.",
                "teclas": (),
                "comprobar": "uso:herramienta",
            },
            {
                "id": "ayuda",
                "titulo": "¿Cómo se usa?",
                "texto": "Cada herramienta se explica paso a paso, con sus teclas y el error típico. Es la ayuda "
                         "que buscas antes de pedir una pista.",
                "hacer": "Pulsa «¿Cómo se usa?» en una herramienta de esta tarjeta.",
                "teclas": (),
                "comprobar": "uso:ayuda",
            },
            {
                "id": "enfoque",
                "titulo": "Blender enfocado o completo",
                "texto": "En los niveles 1 y 2 Blender esconde lo que no usas para que no te pierdas. «Ver todo "
                         "Blender» muestra todos los menús y «Enfocar» vuelve a lo esencial.",
                "hacer": "Prueba «Ver todo Blender» y luego «Enfocar» en esta tarjeta.",
                "teclas": (),
                "comprobar": "uso:enfoque",
                "opcional": True,
            },
            {
                "id": "listo",
                "titulo": "¡Ya te mueves por Blender!",
                "texto": "Sigue con «Así te enseña el taller»: la tarjeta, el molde, las pistas y Mi isla.",
                "hacer": "Pulsa «Terminar».",
                "teclas": (),
                "comprobar": "ninguna",
            },
        ),
    },
    "taller": {
        "nombre": "Así te enseña el taller",
        "resumen": "El ciclo de cada habilidad, la tarjeta, «Mira», el molde, las pistas, Mi isla y la lección en vivo.",
        "pasos": (
            {
                "id": "ciclo",
                "titulo": "Aprendes habilidad por habilidad",
                "texto": "Cada módulo tiene un taller. Cada habilidad pasa por Mira, Hazlo conmigo, Hazlo tú, "
                         "Úsalo y Recuérdalo. Si ya la dominas, Amatista se salta lo que no necesitas.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "tarjeta",
                "titulo": "La tarjeta de la vista 3D",
                "texto": "Abajo a la izquierda, como esta, está siempre lo que toca: la actividad, sus teclas y "
                         "sus botones. Los botones se pueden tocar con el ratón.",
                "hacer": "Mira la tarjeta y pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "mira",
                "titulo": "Mira",
                "texto": "Amatista hace la habilidad frente a ti, con las teclas en pantalla, y la deshace. Nada "
                         "de lo tuyo cambia. Al terminar pulsas «Ahora tú».",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "molde",
                "titulo": "El molde",
                "texto": "Una figura translúcida te muestra dónde va cada pieza: azul la vacía, ámbar la que "
                         "toca, verde la que ya está y coral la que no cuadra.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "comprobar",
                "titulo": "Amatista revisa sola",
                "texto": "Cada vez que cambias algo, Amatista revisa la escena y te avisa cuando lo lograste. "
                         "Las medidas son amables al empezar y exactas en los niveles altos.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "pistas",
                "titulo": "Pistas con freno",
                "texto": "La primera pista dice qué falta, la segunda con qué herramienta, la tercera cómo, y la "
                         "última es «Mírame». Primero inténtalo: el botón espera un poco antes de dar teclas.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "pausa",
                "titulo": "Pausa, Saltar y Demuéstralo",
                "texto": "«Pausa» deja tu trabajo como está. «Saltar» pasa a la siguiente actividad. «¿Ya sabes "
                         "esto? Demuéstralo» te deja probar sin ver la demostración.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "isla",
                "titulo": "Mi isla y los repasos",
                "texto": "Cada proyecto del módulo deja su pieza en tu isla. Días después Amatista te pide un repaso "
                         "corto para que no olvides lo que aprendiste.",
                "hacer": "Pulsa «Siguiente».",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "enlace",
                "titulo": "En vivo con la plataforma",
                "texto": "La lección muestra esta misma tarjeta y tiene los mismos botones: pista, Mírame, pausa. "
                         "Al terminar, tu avance aparece en Mi panel y en tu curso.",
                "hacer": "Abre la plataforma y mira: dice lo mismo que esta tarjeta.",
                "teclas": (),
                "comprobar": "ninguna",
            },
            {
                "id": "listo",
                "titulo": "¡Listo para tu primer taller!",
                "texto": "Ya conoces todo Amatista Motor. Tu primer taller está en el Módulo 1 de Blender "
                         "Principiante: armas un tren de juguete.",
                "hacer": "Pulsa «Terminar» o «Abrir mi primer taller».",
                "teclas": (),
                "comprobar": "ninguna",
            },
        ),
    },
}
ORDEN = ("pestana", "vista", "taller")
PRIMERO = ORDEN[0]
ACCIONES = ("empezar", "siguiente", "anterior", "salir", "terminar")

# Compatibilidad con el add-on 5.1 (un solo recorrido): PASOS es el de la primera práctica.
PASOS = RECORRIDOS[PRIMERO]["pasos"]


def valido(rid):
    """El id de una práctica conocida (o la primera si llega cualquier otra cosa)."""
    return rid if rid in RECORRIDOS else PRIMERO


def pasos_de(rid):
    return RECORRIDOS[valido(rid)]["pasos"]


def total(rid):
    return len(pasos_de(rid))


def ultimo(rid):
    return total(rid) - 1


def siguiente_de(rid):
    """La práctica que sigue a esta (None al final)."""
    indice = ORDEN.index(valido(rid))
    return ORDEN[indice + 1] if indice + 1 < len(ORDEN) else None


def mover(rid, indice, paso):
    """El índice de la parada siguiente o anterior, sin salirse."""
    return max(0, min(ultimo(rid), int(indice) + int(paso)))


def puede_seguir(rid, indice, hechas):
    """Una parada que se comprueba sola necesita estar hecha (salvo las opcionales); las demás se pasan con
    «Siguiente»."""
    lista = pasos_de(rid)
    paso = lista[max(0, min(len(lista) - 1, int(indice)))]
    return paso["comprobar"] == "ninguna" or bool(paso.get("opcional")) or paso["id"] in hechas


def leer_hechos(texto):
    """Las prácticas terminadas guardadas en las preferencias («pestana,vista»), en su orden."""
    partes = {p.strip() for p in str(texto or "").split(",")}
    return [rid for rid in ORDEN if rid in partes]


def escribir_hechos(hechos):
    return ",".join(rid for rid in ORDEN if rid in set(hechos))


def estado_publico(rid, indice, hechas, activo, hechos):
    """detalle.recorrido del latido (backend/api/enlace.py › RecorridoVivo).

    `rid` es la práctica de ahora (o la última abierta); `hechos`, las prácticas terminadas.
    """
    rid = valido(rid)
    lista = pasos_de(rid)
    hecho = rid in set(hechos) and not activo
    indice = ultimo(rid) if hecho and not activo else max(0, min(ultimo(rid), int(indice)))
    paso = lista[indice]
    return {
        "id": rid,
        "nombre": RECORRIDOS[rid]["nombre"][:60],
        "activo": bool(activo),
        "hecho": bool(hecho),
        "hechos": [h for h in ORDEN if h in set(hechos)],
        "paso": indice,
        "total": len(lista),
        "titulo": paso["titulo"][:80],
        "texto": paso["texto"][:300],
        "hacer": paso["hacer"][:160],
        "teclas": [t[:16] for t in paso["teclas"][:6]],
        "pasos": [
            {"titulo": p["titulo"][:60], "ok": bool(hecho) or p["id"] in hechas
             or (i < indice and p["comprobar"] == "ninguna")}
            for i, p in enumerate(lista)
        ],
    }
