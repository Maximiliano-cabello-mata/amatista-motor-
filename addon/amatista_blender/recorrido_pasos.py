"""Los primeros pasos dentro de Blender: las paradas y lo que viaja a la plataforma.

Sin bpy (se prueba con pytest en addon/tests/test_recorrido.py). recorrido.py
es la parte que vive en Blender: comprueba cada parada en la escena, dibuja la
tarjeta y avisa a la plataforma.

Cada parada enseña una sola cosa y, cuando se puede, se comprueba sola: el
alumno hace lo que se pide (abrir la barra con N, vincular su cuenta, orbitar,
elegir el cubo, moverlo con G) y la parada se marca sin que tenga que pulsar
nada. Las que solo explican se pasan con «Siguiente».

La plataforma ve lo mismo en vivo (detalle.recorrido del latido) y la lección
«Tus primeros pasos en Blender» del curso «Primeros pasos con Amatista» puede
empezarlo y avanzarlo (orden «recorrido» con accion empezar · siguiente ·
anterior · salir).
"""

# comprobar: ninguna · barra · cuenta · orbitar · elegir · mover. Ver recorrido.py › COMPROBACIONES.
PASOS = (
    {
        "id": "hola",
        "titulo": "Hola, soy Amatista",
        "texto": "La plataforma te explica la idea y Blender es donde la haces. Yo vivo en los dos y los mantengo "
                 "conectados: lo que haces aquí aparece allá.",
        "hacer": "Pulsa «Siguiente» para empezar.",
        "teclas": (),
        "comprobar": "ninguna",
    },
    {
        "id": "barra",
        "titulo": "Tu pestaña Amatista",
        "texto": "La barra lateral de la vista 3D se abre y se cierra con N. En su pestaña Amatista están tu cuenta, "
                 "tu taller y Mi isla.",
        "hacer": "Con el ratón sobre la vista 3D, pulsa N hasta ver la pestaña Amatista.",
        "teclas": ("N",),
        "comprobar": "barra",
    },
    {
        "id": "cuenta",
        "titulo": "Conecta tu cuenta",
        "texto": "Vincular une este Blender con tu cuenta: así tu avance se guarda y la lección te ve en vivo. "
                 "Se hace una sola vez.",
        "hacer": "Pulsa «Vincular» y escribe en la plataforma el código que aparece.",
        "teclas": (),
        "comprobar": "cuenta",
        "opcional": True,  # sin cuenta todavía: se puede seguir y vincular después
    },
    {
        "id": "orbitar",
        "titulo": "Mira alrededor",
        "texto": "Orbitar es girar la vista alrededor de lo que miras. El cubo no se mueve: te mueves tú.",
        "hacer": "Arrastra con el botón central del ratón (la rueda). Con trackpad: dos dedos.",
        "teclas": ("Botón central",),
        "comprobar": "orbitar",
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
        "texto": "G mueve, R gira y S escala. Después de la tecla mueves el ratón y haces clic para dejarlo.",
        "hacer": "Con el cubo elegido, pulsa G, mueve el ratón y haz clic.",
        "teclas": ("G", "Clic"),
        "comprobar": "mover",
    },
    {
        "id": "tarjeta",
        "titulo": "La tarjeta de la vista 3D",
        "texto": "En cada taller, lo que toca hacer aparece en una tarjeta como esta, abajo a la izquierda. "
                 "Un molde translúcido te muestra sobre el modelo la pieza que falta.",
        "hacer": "Mira la tarjeta y pulsa «Siguiente».",
        "teclas": (),
        "comprobar": "ninguna",
    },
    {
        "id": "ayuda",
        "titulo": "Si te atoras",
        "texto": "Primero lo intentas tú. Si no sale, pide una pista: la primera dice qué falta, la siguiente con "
                 "qué tecla, y «Mírame» lo hace frente a ti y lo deshace para que lo repitas.",
        "hacer": "Recuerda: la pista está en la pestaña Amatista y en la lección.",
        "teclas": (),
        "comprobar": "ninguna",
    },
    {
        "id": "enlace",
        "titulo": "Tu Blender y la plataforma, en vivo",
        "texto": "Cada pocos segundos Blender le cuenta a la plataforma qué haces. En la lección ves este mismo "
                 "paso, y desde la lección puedes abrir talleres, pedir pistas o avanzar aquí.",
        "hacer": "Abre la plataforma y mira la lección: dice lo mismo que esta tarjeta.",
        "teclas": (),
        "comprobar": "ninguna",
    },
    {
        "id": "listo",
        "titulo": "¡Listo para tu primer taller!",
        "texto": "Ya sabes dónde está todo. En el Módulo 1 armas un tren de juguete, habilidad por habilidad.",
        "hacer": "Pulsa «Terminar». Tu primer taller te espera en la plataforma.",
        "teclas": (),
        "comprobar": "ninguna",
    },
)
TOTAL = len(PASOS)
ULTIMO = TOTAL - 1
ACCIONES = ("empezar", "siguiente", "anterior", "salir", "terminar")


def mover(indice, paso):
    """El índice de la parada siguiente o anterior, sin salirse."""
    return max(0, min(ULTIMO, int(indice) + int(paso)))


def puede_seguir(indice, hechas):
    """Una parada que se comprueba sola necesita estar hecha (salvo la opcional, la cuenta); las demás
    se pasan con «Siguiente»."""
    paso = PASOS[max(0, min(ULTIMO, int(indice)))]
    return paso["comprobar"] == "ninguna" or bool(paso.get("opcional")) or paso["id"] in hechas


def estado_publico(indice, hechas, activo, hecho):
    """detalle.recorrido del latido (backend/api/enlace.py › RecorridoVivo)."""
    indice = max(0, min(ULTIMO, int(indice)))
    paso = PASOS[indice]
    return {
        "activo": bool(activo),
        "hecho": bool(hecho),
        "paso": indice,
        "total": TOTAL,
        "titulo": paso["titulo"][:80],
        "texto": paso["texto"][:300],
        "hacer": paso["hacer"][:160],
        "teclas": [t[:16] for t in paso["teclas"][:6]],
        "pasos": [
            {"titulo": p["titulo"][:60], "ok": bool(hecho) or p["id"] in hechas
             or (i < indice and p["comprobar"] == "ninguna")}
            for i, p in enumerate(PASOS)
        ],
    }
