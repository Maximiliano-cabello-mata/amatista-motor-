"""figure.recognize: el motor reconoce la figura del alumno (motor 3.4).

A diferencia de figure.resembles (motor 3.3), no necesita roles, revisa
las relaciones que hacen reconocible la figura (encima de, tocando, en el
suelo, a los dos lados, nada flotando), exige según el nivel de la
práctica y dice qué figura parece cuando no es la de la práctica. El
detalle del algoritmo está en amatista_engine/figures/reconocer.py.
"""
from __future__ import annotations

from typing import Any, Dict

from ..figures.reconocer import ENCIMA, FLOTA, LADOS, SUELO, TOCA, biblioteca, identificar, perfil_para, reconocer
from ..models import SceneState, TargetDefinition, ValidationResult
from .base import number, result, text
from .figure import EJES_TEXTO, _nombre_grupo, mensaje_de

EJE_LADO = {0: "a lo largo", 1: "a lo ancho"}


def _pieza(nombre: str, grupo: str, etiquetas: Dict[str, str]) -> str:
    rol = _nombre_grupo(grupo, etiquetas)
    if not nombre or nombre.split(".")[0].lower() == rol.lower():
        return f"«{nombre or rol}»"
    return f"«{nombre}» ({rol})"


def mensaje_relacion(relacion, detalle: Dict[str, Any], etiquetas: Dict[str, str]) -> str:
    objeto = detalle.get("objeto", "")
    if relacion.tipo == SUELO:
        return f"{_pieza(objeto, relacion.grupo, etiquetas)} debería tocar el suelo, como en el modelo."
    if relacion.tipo == ENCIMA:
        return (f"{_pieza(objeto, relacion.grupo, etiquetas)} debería ir apoyada encima de "
                f"{_pieza(detalle.get('otro', ''), relacion.otro, etiquetas)}.")
    if relacion.tipo == TOCA:
        return (f"{_pieza(objeto, relacion.grupo, etiquetas)} debería tocar a "
                f"{_pieza(detalle.get('otro', ''), relacion.otro, etiquetas)}: júntalas con G.")
    if relacion.tipo == LADOS:
        return (f"Las piezas «{_nombre_grupo(relacion.grupo, etiquetas)}» deberían repartirse a los dos lados "
                f"de la figura ({EJE_LADO.get(relacion.eje, 'a lo largo')}), no todas de un lado.")
    if relacion.tipo == FLOTA:
        return f"«{objeto}» está flotando: apóyala en el suelo o en otra pieza."
    return "Tu figura todavía no tiene la forma del modelo."


PRIMITIVA_TEXTO = {"cube": "Cubo", "cylinder": "Cilindro", "sphere": "Esfera UV", "uv_sphere": "Esfera UV",
                   "icosphere": "Icoesfera", "cone": "Cono", "torus": "Toroide", "plane": "Plano"}


def lista_de_revision(r, partes, scene: SceneState, etiquetas: Dict[str, str], flexibles, perfil) -> list:
    """La lista del instructor (motor 3.5): cada pieza del modelo y cada relación que da sentido a la figura."""
    esperadas: Dict[str, set] = {}
    primitivas: Dict[str, str] = {}
    for i, pieza in enumerate(partes):
        grupo = pieza.get("role") or pieza.get("primitive", "")
        esperadas.setdefault(grupo, set()).add(pieza.get("join") or f"#{i}")
        primitivas.setdefault(grupo, pieza.get("primitive", "cube"))
    tienes: Dict[str, int] = {}
    for obj in scene.objects:
        grupo = r.deducidos.get(obj.name) or (obj.roles[0] if obj.roles else None)
        if grupo:
            tienes[grupo] = tienes.get(grupo, 0) + 1
    lista = []
    for grupo, juntas in esperadas.items():
        nombre = _nombre_grupo(grupo, etiquetas)
        falta = 0 if grupo in flexibles and tienes.get(grupo) else len(juntas) - tienes.get(grupo, 0)
        consejo = ""
        if falta > 0:
            consejo = (f"Te {'falta' if falta == 1 else 'faltan'} {falta} «{nombre}»: Shift + A › Malla › "
                       f"{PRIMITIVA_TEXTO.get(primitivas[grupo], 'Cubo')}.")
        lista.append({"texto": nombre, "ok": falta <= 0, "estado": "Bien" if falta <= 0 else "Falta",
                      "consejo": consejo})
    for _, relacion, detalle in r.fallas[:4]:
        lista.append({"texto": "Que tenga sentido", "ok": False, "estado": "Revisar",
                      "consejo": mensaje_relacion(relacion, detalle, etiquetas)})
    if r.forma < perfil.min_forma and r.peor and r.peor.get("tipo") not in ("vacia", "falta", "cantidad", "sin_roles"):
        lista.append({"texto": "Proporciones", "ok": False, "estado": "Revisar", "consejo": mensaje_de(r.peor, etiquetas)})
    return lista


def recognize(target: TargetDefinition, scene: SceneState) -> ValidationResult:
    partes = target.params.get("parts")
    if not isinstance(partes, list) or not partes:
        raise ValueError("figure.recognize necesita las piezas del modelo («reference» en la práctica)")
    nivel = int(number(target, "level", 1))
    perfil = perfil_para(nivel, text(target, "strictness") or "")
    minimo = number(target, "min_score", perfil.min_score)
    etiquetas = dict(target.params.get("labels") or {})
    titulo = text(target, "title") or "el modelo"
    flexibles = [str(g) for g in target.params.get("flexible") or []]
    tolerancia = target.params.get("tolerance") if perfil.id == "cercana" else None
    r = reconocer(scene, partes, perfil, flexibles, tolerancia=tolerancia)
    detalles: Dict[str, Any] = {
        "score": round(r.puntaje, 3), "shape": round(r.forma, 3), "relations": round(r.relaciones, 3),
        "min_score": minimo, "strictness": perfil.id, "strictness_label": perfil.nombre, "level": nivel,
        "worst": r.peor, "orientation": r.orientacion, "inferred_roles": r.deducidos, "decorations": r.adornos,
        "failed_relations": [{"type": f[1].tipo, "group": f[1].grupo, **f[2]} for f in r.fallas[:5]],
        "critical": len(r.criticas),
        "checklist": lista_de_revision(r, partes, scene, etiquetas, flexibles, perfil),
    }
    porcentaje = round(r.puntaje * 100)

    if r.peor and r.peor.get("tipo") == "vacia":
        return result(target, False, mensaje_de(r.peor, etiquetas), detalles)

    # Niveles 4 y 5: además de la forma, el tamaño real del modelo.
    if perfil.escala_real and r.escala:
        detalles["scale"] = round(r.escala, 2)
        if not 1 / perfil.escala_real <= r.escala <= perfil.escala_real:
            largo = r.orientacion.get("largo", 0.0)
            modelo = r.orientacion.get("largo_modelo", 0.0)
            return result(target, False, (
                f"Tu figura mide cerca de {largo:.2f} m de largo y el modelo {modelo:.2f} m: en este nivel "
                f"las medidas cuentan, {'redúcela' if r.escala > 1 else 'agrándala'} con S."), detalles)
    elif r.escala and not 1 / 2.5 <= r.escala <= 2.5:
        detalles["scale"] = round(r.escala, 2)

    aprueba = (r.puntaje >= minimo and r.forma >= perfil.min_forma and r.relaciones >= perfil.relaciones
               and not r.criticas)
    if aprueba:
        extra = ""
        if r.adornos:
            extra = " Tu pieza de adorno no cuenta." if r.adornos == 1 else f" Tus {r.adornos} piezas de adorno no cuentan."
        return result(target, True, f"Amatista reconoce tu figura: {titulo} ({porcentaje} %).{extra}", detalles)

    # ¿Se parece más a otra figura conocida?
    if r.forma < 0.6 and len([o for o in scene.objects if o.object_type == "MESH"]) >= 3:
        otras = identificar(scene, [f for f in biblioteca() if f.get("title") != titulo])
        detalles["identified"] = otras
        if otras and otras[0]["score"] >= 0.6 and otras[0]["score"] > r.puntaje + 0.1:
            mensaje = (f"Tu figura se parece más a «{otras[0]['title']}» ({round(otras[0]['score'] * 100)} %) "
                       f"que a {titulo} ({porcentaje} %). Compárala con la imagen del modelo.")
            return result(target, False, mensaje, detalles)

    # Primero lo que falta o sobra, luego la relación rota más grave, luego la medida peor.
    grave = r.peor and r.peor.get("tipo") in ("falta", "cantidad", "sin_roles")
    fallas = r.criticas or r.fallas
    if not grave and fallas and (r.criticas or r.relaciones < perfil.relaciones or r.forma >= perfil.min_forma):
        mensaje = mensaje_relacion(fallas[0][1], fallas[0][2], etiquetas)
    else:
        mensaje = mensaje_de(r.peor, etiquetas)
        if r.peor and r.peor.get("tipo") == "proporcion" and nivel <= 1:
            mas, menos = EJES_TEXTO[r.peor["eje"]]
            mensaje = f"Tu figura es mucho {mas if r.peor['razon'] > 1 else menos} que el modelo: compárala con la imagen."
    return result(target, False, f"{mensaje} Parecido: {porcentaje} %.", detalles)
