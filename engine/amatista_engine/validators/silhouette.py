"""figure.silhouette: Amatista reconoce la silueta de una malla (motor 3.5).

Para figuras modeladas en UNA malla (la espada del módulo 2): compara la
silueta del alumno, rebanada por rebanada, con la del modelo de referencia,
y dice parte por parte (Pomo, Mango, Guarda, Hoja, Punta) qué está bien y
qué falta, con la tecla que lo arregla. El detalle está en
amatista_engine/figures/silueta.py.

Como un instructor: lo que hace que la figura no tenga sentido (no hay
guarda, la punta no se afila) no pasa en ningún nivel; una parte un poco
fuera de medida se perdona en los niveles 1 a 3 y se sugiere como detalle.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from ..figures.reconocer import perfil_para
from ..figures.silueta import PERDON, comparar_siluetas, lista_de_revision, partes_del_modelo
from ..models import SceneState, TargetDefinition, ValidationResult
from .base import number, result, select, selector, text


@lru_cache(maxsize=32)
def _modelo(clave: str):
    return partes_del_modelo(json.loads(clave))


def modelo_de(partes: List[Dict[str, Any]]):
    return _modelo(json.dumps(partes, sort_keys=True))


def mejor_malla(mallas, modelo, tramos, exigencia: str, candidatas: int = 3):
    """(objeto, revisión) de la malla que más se parece al modelo entre las más largas; revisión None sin silueta."""
    con_silueta = sorted((o for o in mallas if o.silhouette is not None), key=lambda o: -o.silhouette.largo)
    if not con_silueta:
        return max(mallas, key=lambda o: max(o.dimensions or (0.0,))), None
    revisadas = [(o, comparar_siluetas(o.silhouette, modelo, tramos, exigencia)) for o in con_silueta[:candidatas]]
    return max(revisadas, key=lambda par: (not par[1].criticas, -len(par[1].fuera), par[1].puntaje))


def silhouette(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    partes = target.params.get("parts")
    if not isinstance(partes, list) or not partes:
        raise ValueError("figure.silhouette necesita las piezas del modelo («reference» en la práctica)")
    nivel = int(number(target, "level", 1))
    perfil = perfil_para(nivel, text(target, "strictness") or "")
    titulo = text(target, "title") or "el modelo"
    modelo, tramos = modelo_de(partes)
    if modelo is None or not tramos:
        raise ValueError("figure.silhouette: el modelo de referencia no tiene forma")
    sel = selector(target)
    mallas = [o for o in (select(scene, sel) if sel else scene.objects) if o.object_type == "MESH"]
    detalles: Dict[str, Any] = {"level": nivel, "strictness": perfil.id, "strictness_label": perfil.nombre,
                                "parts_expected": [t.nombre for t in tramos]}
    lista_vacia = [{"texto": t.nombre, "ok": False, "estado": "Falta", "consejo": ""} for t in tramos]
    if not mallas:
        detalles["checklist"] = lista_vacia
        return result(target, False, "Todavía no hay una malla: agrega un cubo (Shift + A › Malla › Cubo); "
                                     f"de ahí sale {titulo}.", detalles)
    # La malla principal: de las más largas, la que más se parece (un piso plano también es largo).
    obj, revision = mejor_malla(mallas, modelo, tramos, perfil.id)
    detalles["object"] = obj.name
    if revision is None:
        # Sin evidencia no se aprueba: una captura antigua o demasiado grande debe repetirse.
        detalles["no_silhouette"] = True
        return result(target, False, "Pendiente de verificación: Amatista no pudo medir la silueta de tu malla (actualiza el add-on "
                                    "Amatista Motor; si persiste, simplifica la malla y vuelve a comprobar).", detalles)

    lista = lista_de_revision(revision)
    porcentaje = round(revision.puntaje * 100)
    detalles.update({
        "score": round(revision.puntaje, 3), "checklist": lista, "inverted": revision.invertida,
        "axes": revision.ejes, "critical": len(revision.criticas), "out_of_range": len(revision.fuera),
        "parts": [{k: v for k, v in p.items() if k in ("parte", "ancho", "grueso", "largo", "ok")}
                  for p in revision.partes],
    })
    otras = len(mallas) - 1
    nota = ""
    if otras:
        nota = (f" Amatista mira tu malla «{obj.name}»; en esta práctica la figura es un solo objeto "
                f"(júntalos con Ctrl + J).")

    if perfil.escala_real and revision.largo_modelo:
        escala = revision.largo / revision.largo_modelo
        detalles["scale"] = round(escala, 2)
        if not 1 / perfil.escala_real <= escala <= perfil.escala_real:
            return result(target, False, (
                f"Tu malla mide cerca de {revision.largo:.2f} m de largo y el modelo {revision.largo_modelo:.2f} m: "
                f"en este nivel las medidas cuentan, {'redúcela' if escala > 1 else 'agrándala'} con S."), detalles)

    pendientes = [i for i in lista if not i["ok"]]
    sugerencias = [i for i in lista if i["consejo"]]
    aprueba = not revision.criticas and len(revision.fuera) <= PERDON.get(perfil.id, 0)
    if aprueba:
        bien = ", ".join(i["texto"] for i in lista if i["estado"] == "Bien")
        mensaje = f"Amatista reconoce tu figura: {titulo} ({porcentaje} %)."
        if bien:
            mensaje += f" Bien: {bien}."
        if sugerencias:  # perdonado en este nivel: el instructor lo sugiere como detalle
            mensaje += f" Un detalle para que se parezca más: {sugerencias[0]['consejo']}"
        return result(target, True, mensaje, detalles)
    return result(target, False, f"{pendientes[0]['consejo']}{nota}" if pendientes else
                  f"Tu figura todavía no tiene la forma de {titulo}.{nota}", detalles)
