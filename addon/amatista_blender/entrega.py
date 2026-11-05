"""Entregar la práctica al profesor (panel del profesor evaluador, sql/014).

Cuando un profesor deja una práctica a su grupo, el alumno la entrega desde
Blender (menú Amatista › «Entregar a mi profesor») o desde Mi panel en la
plataforma (orden «entregar» del enlace en vivo). Se manda:

- el modelo ligero de la escena de la práctica (modelo_ligero.py): mallas en
  triángulos, con modificadores aplicados, en unos pocos KB. El .blend nunca
  sale de esta computadora.
- nada más: el progreso lo pone el servidor, con lo que ya midió el motor.

Antes de entregar se sincroniza el intento, así el profesor ve el progreso
de este momento. Sin conexión, la entrega queda en la cola (red.encolar) y
se envía sola al volver la red.
"""
import bpy

from . import ajustes, modelo_ligero, red

RUTA_ASIGNACIONES = "/api/evaluacion/mis-asignaciones"
RUTA_ENTREGAS = "/api/evaluacion/entregas"
TIPOS = {"MESH": "MESH", "CURVE": "CURVE", "SURFACE": "CURVE", "META": "CURVE", "FONT": "CURVE",
         "LIGHT": "LIGHT", "CAMERA": "CAMERA", "EMPTY": "EMPTY"}
ESTADO = {"enviando": False, "mensaje": "", "asignaciones": None}


def _color(material):
    """El color base del material: el del Principled BSDF si lo hay, si no el de la vista."""
    if material is None:
        return (0.8, 0.8, 0.8)
    if material.use_nodes and material.node_tree:
        for nodo in material.node_tree.nodes:
            if nodo.type == "BSDF_PRINCIPLED":
                entrada = nodo.inputs.get("Base Color")
                if entrada is not None:
                    return tuple(entrada.default_value[:3])
    return tuple(material.diffuse_color[:3])


def extraer(escena, depsgraph=None):
    """Los objetos visibles de la escena como pide modelo_ligero.armar (en el espacio del mundo)."""
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    materiales, indices, objetos = [], {}, []
    for obj in escena.objects:
        if not obj.visible_get(view_layer=depsgraph.view_layer) or obj.get("amatista_ayuda"):
            continue
        tipo = TIPOS.get(obj.type, "OTRO")
        uno = {
            "nombre": obj.name,
            "tipo": "MESH" if tipo == "CURVE" else tipo,
            "p": tuple(obj.matrix_world.translation),
            "r": tuple(obj.rotation_euler),
            "s": tuple(obj.scale),
            "mods": [m.type for m in getattr(obj, "modifiers", ())],
        }
        if tipo in ("MESH", "CURVE"):
            evaluado = obj.evaluated_get(depsgraph)
            try:
                malla = evaluado.to_mesh()
            except RuntimeError:
                malla = None
            if malla is not None:
                malla.calc_loop_triangles()
                mundo = obj.matrix_world
                uno["vertices"] = [tuple(mundo @ v.co) for v in malla.vertices]
                uno["triangulos"] = [tuple(t.vertices) for t in malla.loop_triangles]
                material = obj.active_material
                if material is not None:
                    if material.name not in indices:
                        indices[material.name] = len(materiales)
                        materiales.append({"nombre": material.name, "color": _color(material)})
                    uno["material"] = indices[material.name]
                evaluado.to_mesh_clear()
            if not uno.get("vertices"):
                uno.pop("vertices", None)
                uno.pop("triangulos", None)
                uno["tipo"] = "EMPTY"
        objetos.append(uno)
    return modelo_ligero.armar(objetos, materiales, bpy.app.version_string)


def asignacion_para(asignaciones, practica_id):
    """La tarea abierta de esa práctica que todavía se puede entregar (la más reciente), o None."""
    for a in asignaciones or ():
        entrega = a.get("entrega") or {}
        if a.get("practica_id") == practica_id and a.get("estado") == "abierta" and entrega.get("estado") != "evaluada":
            return a
    return None


def _avisar(texto, tono="animo"):
    from . import guia, practicas

    ESTADO["mensaje"] = texto
    try:
        guia.avisar("Entrega a tu profesor", texto, tono)
    except Exception:  # noqa: BLE001 - sin guía, el mensaje queda en el panel
        pass
    practicas.redibujar()


def entregar(context=None, al_terminar=None):
    """Busca la tarea de la práctica abierta y la entrega. Devuelve un texto para mostrar."""
    from . import practicas

    context = context or bpy.context
    practica = practicas.practica_activa(context)
    if practica is None:
        return "Abre la práctica que te dejó tu profesor para entregarla."
    p = ajustes.prefs()
    if not (p and p.token):
        return "Conecta tu cuenta de Amatista para entregar (menú Amatista › Conectar mi cuenta)."
    if ESTADO["enviando"]:
        return "Ya se está entregando…"
    escena = practicas.escena(context)
    try:
        paquete = modelo_ligero.empaquetar(extraer(escena))
    except Exception as error:  # noqa: BLE001 - sin modelo se entrega el progreso
        print(f"[Amatista] No se pudo leer el modelo: {error}")
        paquete = None
    # El intento primero: el profesor ve el progreso de este momento.
    try:
        practicas.sincronizar(context, forzar=True)
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Sincronizar antes de entregar: {error}")
    ESTADO["enviando"] = True

    def con_asignaciones(respuesta, error, estado):
        if error is None:
            ESTADO["asignaciones"] = respuesta.get("asignaciones") or []
        elif ESTADO["asignaciones"] is None:
            # Sin red y sin una lista anterior no sabemos a qué tarea va: mejor no adivinar.
            ESTADO["enviando"] = False
            _avisar("No pudimos ver tus tareas: revisa tu conexión y vuelve a intentarlo.", "ojo")
            return
        asignacion = asignacion_para(ESTADO["asignaciones"], practica.id)
        if asignacion is None:
            ESTADO["enviando"] = False
            _avisar("Tu profesor no te dejó esta práctica (o ya la evaluó). Tus avances se guardan igual.", "animo")
            return
        datos = {"asignacion_id": asignacion["id"], "modelo": paquete, "version_addon": ajustes.VERSION_ADDON}

        def entregada(respuesta, error, estado):
            ESTADO["enviando"] = False
            if error is None:
                kb = max(1, round((respuesta.get("modelo_bytes") or 0) / 1024))
                _avisar(f"¡Entregado a tu profesor! Tu modelo viajó en {kb} KB.", "logrado")
            elif red.es_reintentable(estado) or estado is None:
                red.encolar(RUTA_ENTREGAS, datos)
                _avisar("Sin conexión: tu entrega se enviará sola cuando vuelva el internet.", "animo")
            else:
                _avisar(error, "ojo")
            if al_terminar:
                al_terminar(respuesta, error)

        red.pedir("POST", RUTA_ENTREGAS, entregada, datos, segundos=30)

    red.pedir("GET", RUTA_ASIGNACIONES, con_asignaciones)
    return "Entregando a tu profesor…"


class AMATISTA_OT_entregar_profesor(bpy.types.Operator):
    """Entrega esta práctica al profesor: tu avance y tu modelo en pocos KB (el .blend no sale de tu computadora)"""

    bl_idname = "amatista.entregar_profesor"
    bl_label = "Entregar a mi profesor"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        from . import practicas

        return practicas.practica_activa(context) is not None and not ESTADO["enviando"]

    def execute(self, context):
        self.report({"INFO"}, entregar(context))
        return {"FINISHED"}


CLASES = (AMATISTA_OT_entregar_profesor,)
