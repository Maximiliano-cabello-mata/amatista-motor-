"""Entrenadores de los validadores del motor v3 (plan de estudios de Blender).

Igual que coach.py: convierten el resultado de un validador en una guía con
teclas, resaltados y un «Hazlo conmigo». Se suman a ENTRENADORES al final de
coach.py. Los textos están escritos para alguien que nunca abrió Blender:
una acción por línea, la tecla primero.
"""
from __future__ import annotations

from typing import Dict, Optional

from ..validators.base import primitiva, selector
from .coach import (
    TONO_ANIMO,
    TONO_CERCA,
    TONO_LOGRADO,
    Contexto,
    Parcial,
    Paso,
    _bien,
    _num,
    _seleccionar,
)
from .models import RESALTE_CORREGIR, TONO_OJO, GuideAction, Highlight, VisualCue

NOMBRE_PRIMITIVA = {
    "cube": "Cubo", "cylinder": "Cilindro", "sphere": "Esfera UV", "icosphere": "Icoesfera", "cone": "Cono",
    "torus": "Toroide", "plane": "Plano", "circle": "Círculo", "suzanne": "Mono",
}
NOMBRE_MODIFICADOR = {"MIRROR": "Espejo (Mirror)", "SUBSURF": "Superficie de subdivisión", "BEVEL": "Biselar",
                      "ARRAY": "Matriz (Array)", "SOLIDIFY": "Solidificar"}


def _fallidos(ctx: Contexto):
    d = ctx.result.details
    nombres = [f.get("object") for f in d.get("failed") or [] if f.get("object")]
    for clave in ("object", "missing"):
        valor = d.get(clave)
        if isinstance(valor, str) and valor not in nombres:
            nombres.append(valor)
    return nombres


def _corregir(nombres, texto):
    return tuple(Highlight(n, RESALTE_CORREGIR, texto) for n in nombres[:4])


def _ok(ctx: Contexto) -> Optional[Parcial]:
    if ctx.result.passed:
        sel = selector(ctx.target)
        from ..validators.base import select

        return Parcial(ctx.result.message, TONO_LOGRADO, highlights=_bien(select(ctx.scene, sel)[:6], ctx.que()) if sel else ())
    return None


# --- Objetos y forma (módulo 1) ---------------------------------------------------------


def coach_object_count(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    sel = d.get("selector") or {}
    esperado = d.get("expected") or {}
    encontrados = d.get("found", 0)
    maximo = esperado.get("max")
    if maximo is not None and encontrados > maximo:
        sobran = (d.get("objects") or [])[maximo:]
        return Parcial(ctx.result.message, TONO_CERCA,
                       (_seleccionar(sobran[0]), Paso("Bórralo", ("X",))) if sobran else (),
                       _corregir(sobran, "Sobra"), action=GuideAction("focus", "Mostrarme cuál sobra", tuple(sobran[:1])))
    prim = primitiva(sel.get("primitive", "")) if sel.get("primitive") else "cube"
    nombre = NOMBRE_PRIMITIVA.get(prim, prim)
    rol = sel.get("role")
    pasos = [
        Paso("Con el ratón sobre la vista 3D, abre el menú Agregar", ("Shift", "A")),
        Paso(f"Elige Malla › {nombre}"),
    ]
    if rol:
        pasos.append(Paso(f"Dile a Amatista que es «{ctx.etiqueta(rol)}» (pestaña Amatista › Asignar rol)", ("N",)))
    existentes = d.get("objects") or []
    if existentes:
        pasos.append(Paso("¿Ya tienes uno igual? Duplícalo y muévelo", ("Shift", "D")))
    return Parcial(
        ctx.result.message,
        TONO_CERCA if (esperado.get("min") or 1) - encontrados == 1 else TONO_ANIMO,
        tuple(pasos),
        action=GuideAction("add_primitive", f"Agregar un {nombre.lower()} conmigo", role=rol, primitive=prim),
    )


def coach_thinnest(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    fallo = (d.get("failed") or [{}])[0]
    nombre = fallo.get("object")
    eje = d.get("axis", "horizontal")
    if not nombre:
        return Parcial(ctx.result.message, TONO_ANIMO)
    if eje == "horizontal" and fallo.get("thinnest") == "z":
        return Parcial(
            f"«{nombre}» está acostado como una moneda. Ponlo de pie girándolo 90°.",
            TONO_ANIMO,
            (_seleccionar(nombre), Paso("Rota sobre X", ("R", "X")), Paso("Escribe 90 y confirma", ("9", "0", "Enter"))),
            _corregir([nombre], "Ponlo de pie"),
            action=GuideAction("rotate", "Girarlo conmigo", (nombre,), "x", 90.0),
        )
    eje_escala = "z" if eje == "z" else ("y" if eje == "horizontal" else eje)
    return Parcial(
        f"«{nombre}» todavía es muy grueso. Hazlo más delgado escalando un solo eje.",
        TONO_ANIMO,
        (_seleccionar(nombre), Paso(f"Escala solo en {eje_escala.upper()}", ("S", eje_escala.upper())),
         Paso("Escribe 0.3 y confirma", ("0.3", "Enter"))),
        _corregir([nombre], "Más delgado"),
        action=GuideAction("scale", "Escalar conmigo", (nombre,), eje_escala, 0.3),
    )


def coach_proportion(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    fallo = (d.get("failed") or [{}])[0]
    nombre, eje = fallo.get("object"), d.get("axis", "z")
    if not nombre:
        return Parcial(ctx.result.message, TONO_ANIMO)
    return Parcial(
        ctx.result.message,
        TONO_ANIMO,
        (_seleccionar(nombre), Paso(f"Estíralo solo en {eje.upper()}", ("S", eje.upper())),
         Paso("Mueve el ratón hasta que se vea alargado y haz clic", ("Clic",))),
        _corregir([nombre], "Más largo"),
        action=GuideAction("scale", "Estirar conmigo", (nombre,), eje, 2.0),
    )


def coach_grounded(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    fallo = (d.get("failed") or [{}])[0]
    nombre = fallo.get("object")
    if not nombre:
        return Parcial(ctx.result.message, TONO_ANIMO)
    delta = round(d.get("height", 0.0) - fallo.get("value", 0.0), 3)
    return Parcial(
        ctx.result.message,
        TONO_CERCA,
        (_seleccionar(nombre), Paso("Muévelo solo en altura", ("G", "Z")),
         Paso(f"Escribe {_num(delta)} y confirma", (_num(delta), "Enter"))),
        _corregir([nombre], "Bájalo al suelo" if delta < 0 else "Súbelo al suelo"),
        (VisualCue("arrow", "Al suelo", {"object": nombre, "direction": "down" if delta < 0 else "up"}),),
        GuideAction("move", "Llevarlo al suelo conmigo", (nombre,), "z", delta),
    )


def coach_touching(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    nombres = _fallidos(ctx)
    if not nombres:
        return Parcial(ctx.result.message, TONO_ANIMO)
    return Parcial(
        ctx.result.message,
        TONO_ANIMO,
        (_seleccionar(nombres[0]), Paso("Muévelo hasta que toque la pieza", ("G",)),
         Paso("Mira desde el frente para comprobar", ("1",)), Paso("Haz clic para dejarlo", ("Clic",))),
        _corregir(nombres, "Acércalo"),
        (VisualCue("arrow", "Únelo", {"object": nombres[0], "direction": "in"}),),
        GuideAction("move", "Moverlo conmigo", (nombres[0],)),
    )


# --- Malla y modificadores (módulos 2 y 3) ----------------------------------------------


def coach_no_duplicates(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    nombres = _fallidos(ctx)
    return Parcial(
        ctx.result.message,
        TONO_OJO,
        (
            Paso("Entra a Edición si no estás ahí", ("Tab",)),
            Paso("Selecciona todo", ("A",)),
            Paso("Abre Fusionar y elige «Por distancia»", ("M",)),
        ),
        _corregir(nombres, "Vértices encimados"),
        action=GuideAction("merge_by_distance", "Fusionar por distancia conmigo", tuple(nombres[:1])),
    )


def coach_one_side(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    nombres = _fallidos(ctx)
    eje = (ctx.result.details.get("axis") or "x").upper()
    return Parcial(
        ctx.result.message,
        TONO_ANIMO,
        (
            Paso("Entra a Edición", ("Tab",)),
            Paso("Vista de frente para ver la mitad", ("1",)),
            Paso(f"Selecciona con caja los vértices del otro lado del eje {eje}", ("B",)),
            Paso("Bórralos: Vértices", ("X",)),
        ),
        _corregir(nombres, "Solo una mitad"),
        action=GuideAction("edit_mode", "Entrar a Edición conmigo", tuple(nombres[:1])),
    )


def coach_modifier_configured(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    tipo = str(ctx.target.params.get("modifier", "")).upper()
    nombre_mod = NOMBRE_MODIFICADOR.get(tipo, tipo)
    objeto = d.get("missing") or d.get("object") or (_fallidos(ctx) or [None])[0]
    motivo = d.get("reason")
    objetos = (objeto,) if objeto else ()
    if motivo == "missing":
        return Parcial(
            ctx.result.message,
            TONO_ANIMO,
            (_seleccionar(objeto), Paso("En Propiedades, abre la llave inglesa (Modificadores)"),
             Paso(f"Agregar modificador › Generar › {nombre_mod}")),
            _corregir([objeto], f"Falta {nombre_mod}"),
            action=GuideAction("add_modifier", f"Agregar {nombre_mod} conmigo", objetos, modifier=tipo, tab="MODIFIER"),
        )
    if motivo == "axis" or motivo == "extra_axis":
        eje = (d.get("axis") or "x").upper()
        texto = f"En el modificador Espejo deja encendido solo el eje {eje}" if motivo == "extra_axis" else \
            f"En el modificador Espejo enciende el eje {eje}"
        return Parcial(ctx.result.message, TONO_CERCA, (_seleccionar(objeto), Paso("Abre la llave inglesa (Modificadores)"),
                                                         Paso(texto)),
                       _corregir([objeto], f"Eje {eje}"),
                       action=GuideAction("open_tab", "Abrir Modificadores", objetos, tab="MODIFIER"))
    if motivo == "levels":
        return Parcial(ctx.result.message, TONO_CERCA,
                       (_seleccionar(objeto), Paso("Abre la llave inglesa (Modificadores)"),
                        Paso("Cambia «Niveles de vista» (Levels Viewport)"),
                        Paso("Atajo: Ctrl + un número pone esos niveles", ("Ctrl", "2"))),
                       _corregir([objeto], "Niveles"),
                       action=GuideAction("open_tab", "Abrir Modificadores", objetos, tab="MODIFIER"))
    return Parcial(ctx.result.message, TONO_CERCA,
                   (_seleccionar(objeto), Paso("Abre la llave inglesa y enciende el ojo del modificador")),
                   action=GuideAction("open_tab", "Abrir Modificadores", objetos, tab="MODIFIER"))


# --- Materiales (módulo 4) ---------------------------------------------------------------


def coach_material_distinct(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    faltan = max(0, (d.get("expected") or {}).get("min", 1) - d.get("found", 0))
    return Parcial(
        ctx.result.message,
        TONO_ANIMO if faltan > 1 else TONO_CERCA,
        (
            Paso("Selecciona la pieza que quieres pintar", ("Clic",)),
            Paso("Propiedades › Material (la esfera roja) › Nuevo"),
            Paso("Cambia Color base, Metálico y Rugosidad"),
            Paso("Repite con otra pieza: cada una con su propio material"),
        ),
        action=GuideAction("new_material", "Crear un material conmigo", tab="MATERIAL"),
    )


def coach_material_matches(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    pasos = [Paso("Selecciona la pieza", ("Clic",)), Paso("Propiedades › Material › Nuevo (o elige uno)")]
    for propiedad, comparacion, valor in d.get("conditions") or []:
        nombre = {"metallic": "Metálico", "roughness": "Rugosidad", "transmission": "Transmisión",
                  "alpha": "Alfa"}.get(propiedad, propiedad)
        pasos.append(Paso(f"Mueve {nombre} a {_num(valor)} {'o más' if comparacion == '>=' else 'o menos'}"))
    return Parcial(ctx.result.message, TONO_ANIMO, tuple(pasos[:6]),
                   action=GuideAction("open_tab", "Abrir Material", tab="MATERIAL"))


# --- Luces, cámara y render (módulo 5) --------------------------------------------------


def coach_three_point(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    motivo = d.get("reason")
    if motivo == "no_camera":
        return coach_camera_active(ctx)
    if motivo == "fill":
        return Parcial(ctx.result.message, TONO_CERCA,
                       (Paso("Selecciona la luz de relleno", ("Clic",)),
                        Paso("Propiedades › Datos de la luz (bombilla verde) › Potencia a la mitad")),
                       action=GuideAction("open_tab", "Abrir datos de la luz", tab="DATA"))
    pasos = [Paso("Agrega una luz de área", ("Shift", "A")), Paso("Elige Luz › Área")]
    if not d.get("back"):
        pasos.append(Paso("Llévala detrás del modelo, del lado contrario a la cámara", ("G",)))
    else:
        pasos.append(Paso("Llévala delante del modelo, al lado que todavía está oscuro", ("G",)))
    pasos.append(Paso("Gírala para que apunte al modelo", ("R",)))
    return Parcial(ctx.result.message, TONO_ANIMO, tuple(pasos),
                   action=GuideAction("add_light", "Agregar una luz de área conmigo", light_type="AREA"))


def coach_camera_active(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    hay = any(o.object_type == "CAMERA" for o in ctx.scene.objects)
    if hay:
        return Parcial(ctx.result.message, TONO_CERCA,
                       (Paso("Selecciona la cámara", ("Clic",)), Paso("Hazla la cámara activa", ("Ctrl", "0"))),
                       action=GuideAction("add_camera", "Activar la cámara conmigo"))
    return Parcial(ctx.result.message, TONO_ANIMO,
                   (Paso("Agrega una cámara", ("Shift", "A")), Paso("Elige Cámara")),
                   action=GuideAction("add_camera", "Agregar una cámara conmigo"))


def coach_camera_frames(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    if ctx.result.details.get("reason") == "no_camera":
        return coach_camera_active(ctx)
    return Parcial(
        ctx.result.message,
        TONO_CERCA,
        (Paso("Gira la vista hasta ver el modelo como quieres la foto"),
         Paso("Pon la cámara justo donde estás mirando", ("Ctrl", "Alt", "0")),
         Paso("Mira por la cámara para comprobar", ("0",))),
        action=GuideAction("align_camera", "Alinear la cámara conmigo"),
    )


def coach_render_engine(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    motor = str(ctx.target.params.get("engine") or "EEVEE").upper()
    return Parcial(ctx.result.message, TONO_CERCA,
                   (Paso("Propiedades › Render (la cámara de fotos de atrás)"), Paso(f"Motor de render: {motor.title()}")),
                   action=GuideAction("set_engine", f"Usar {motor.title()}", tab="RENDER", option=motor))


def coach_render_done(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    return Parcial(ctx.result.message, TONO_CERCA,
                   (Paso("Haz el render final", ("F12",)), Paso("Se abre una ventana con tu foto: Imagen › Guardar para conservarla")),
                   action=GuideAction("render", "Hacer el render (F12)"))


# --- Animación (módulo 6) ----------------------------------------------------------------


def coach_keyframes(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    nombres = _fallidos(ctx)
    eje = str(ctx.target.params.get("axis", "z")).lower()
    propiedad = str(ctx.target.params.get("property", "location")).lower()
    menu, tecla, verbo = {"scale": ("Escala", "S", "Escálala"), "rotation_euler": ("Rotación", "R", "Gírala")}.get(
        propiedad, ("Ubicación", "G", "Muévela"))
    return Parcial(
        ctx.result.message,
        TONO_ANIMO,
        (
            _seleccionar(nombres[0]) if nombres else Paso("Selecciona la pelota", ("Clic",)),
            Paso(f"En la línea de tiempo, ve al fotograma 1 y pulsa I › {menu}", ("I",)),
            Paso("Avanza 10 fotogramas", ("↑",)),
            Paso(f"{verbo} en {eje.upper()} y vuelve a insertar", (tecla, eje.upper())),
            Paso("Insertar fotograma clave", ("I",)),
        ),
        _corregir(nombres, "Animar"),
        action=GuideAction("insert_keyframe", "Insertar un fotograma clave conmigo", tuple(nombres[:1]), eje,
                           option=str(ctx.target.params.get("property", "location"))),
    )


def coach_varies(ctx: Contexto) -> Parcial:
    hecho = _ok(ctx)
    if hecho:
        return hecho
    d = ctx.result.details
    nombre = d.get("object")
    motivo = d.get("reason")
    if motivo == "keys":
        return coach_keyframes(ctx)
    textos = {
        "low": "En el fotograma del golpe, baja la pelota hasta el suelo y pulsa I",
        "high": "En el primer fotograma, sube la pelota y pulsa I",
        "bounce": "Después del golpe, avanza unos fotogramas, súbela de nuevo y pulsa I",
        "delta": "Haz que el cambio entre fotogramas clave sea más grande",
    }
    return Parcial(
        ctx.result.message,
        TONO_CERCA,
        (_seleccionar(nombre) if nombre else Paso("Selecciona la pelota", ("Clic",)),
         Paso(textos.get(motivo, "Revisa los fotogramas clave"), ("I",)),
         Paso("Reproduce para ver el resultado", ("Espacio",))),
        _corregir([nombre] if nombre else [], "Revisa la animación"),
        action=GuideAction("insert_keyframe", "Insertar un fotograma clave conmigo", (nombre,) if nombre else (),
                           str(ctx.target.params.get("axis", "z")).lower(),
                           option=str(ctx.target.params.get("property", "location"))),
    )


ENTRENADORES_V3: Dict[str, object] = {
    "object.count": coach_object_count,
    "shape.thinnest_axis": coach_thinnest,
    "shape.proportion": coach_proportion,
    "spatial.grounded": coach_grounded,
    "spatial.touching": coach_touching,
    "mesh.no_duplicates": coach_no_duplicates,
    "mesh.one_side": coach_one_side,
    "modifier.configured": coach_modifier_configured,
    "material.distinct": coach_material_distinct,
    "material.matches": coach_material_matches,
    "light.three_point": coach_three_point,
    "camera.active": coach_camera_active,
    "camera.frames": coach_camera_frames,
    "render.engine": coach_render_engine,
    "render.done": coach_render_done,
    "animation.keyframes": coach_keyframes,
    "animation.varies": coach_varies,
}
