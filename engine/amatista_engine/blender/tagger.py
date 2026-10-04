"""Amatista Tagger (DEV-01 y DEV-02): roles y etiquetas educativas.

Toda la interfaz pasa por estas funciones; nadie toca las propiedades
directamente (regla 29 del Motor de Desarrollo). Así el formato de
almacenamiento puede cambiar sin rehacer la interfaz.

Almacenamiento actual (propiedades personalizadas del objeto, se guardan
dentro del .blend):
    obj["amatista_role"] = "pata"
    obj["amatista_tags"] = "estructura,mesa"
"""
PROP_ROL = "amatista_role"
PROP_ETIQUETAS = "amatista_tags"
PROP_IGNORAR = "amatista_ignore"


def _limpio(texto):
    return str(texto or "").strip().lower().replace(" ", "_")


def assign_role(obj, role):
    role = _limpio(role)
    if not role:
        remove_role(obj)
        return None
    obj[PROP_ROL] = role
    return role


def get_role(obj):
    valor = obj.get(PROP_ROL)
    return str(valor) if valor else None


def remove_role(obj):
    if PROP_ROL in obj.keys():
        del obj[PROP_ROL]


def get_tags(obj):
    crudo = obj.get(PROP_ETIQUETAS) or ""
    return tuple(t for t in (x.strip() for x in str(crudo).split(",")) if t)


def _guardar_etiquetas(obj, etiquetas):
    if etiquetas:
        obj[PROP_ETIQUETAS] = ",".join(etiquetas)
    elif PROP_ETIQUETAS in obj.keys():
        del obj[PROP_ETIQUETAS]


def add_tag(obj, tag):
    tag = _limpio(tag)
    etiquetas = list(get_tags(obj))
    if tag and tag not in etiquetas:
        etiquetas.append(tag)
        _guardar_etiquetas(obj, etiquetas)
    return tuple(etiquetas)


def remove_tag(obj, tag):
    etiquetas = [t for t in get_tags(obj) if t != _limpio(tag)]
    _guardar_etiquetas(obj, etiquetas)
    return tuple(etiquetas)


def is_ignored(obj):
    return bool(obj.get(PROP_IGNORAR))


def set_ignored(obj, ignored=True):
    if ignored:
        obj[PROP_IGNORAR] = 1
    elif PROP_IGNORAR in obj.keys():
        del obj[PROP_IGNORAR]


def inspect_object(obj):
    """Lo que Amatista entiende de un objeto (DEV-03, el Inspector)."""
    datos = getattr(obj, "data", None)
    return {
        "name": obj.name,
        "type": obj.type,
        "role": get_role(obj),
        "tags": get_tags(obj),
        "ignored": is_ignored(obj),
        "location": tuple(round(float(v), 3) for v in obj.location),
        "rotation": tuple(round(float(v), 4) for v in obj.rotation_euler),
        "scale": tuple(round(float(v), 3) for v in obj.scale),
        "dimensions": tuple(round(float(v), 3) for v in obj.dimensions),
        "modifiers": tuple(m.type for m in getattr(obj, "modifiers", ())),
        "materials": tuple(s.material.name for s in getattr(obj, "material_slots", ()) if s.material),
        "collections": tuple(c.name for c in obj.users_collection),
        "vertices": len(datos.vertices) if obj.type == "MESH" and datos is not None else None,
        "faces": len(datos.polygons) if obj.type == "MESH" and datos is not None else None,
    }
