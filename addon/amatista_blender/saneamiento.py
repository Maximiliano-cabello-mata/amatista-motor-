"""Autosanación (motor 6): una sola Amatista encendida, sin restos de copias viejas.

Lo que encontró el creador: «ya tengo instaladas varias versiones… se cruzan
entre ellas, hacen cosas raras, las tarjetas se enciman». Pasaba así:

- El add-on clásico (``amatista_blender`` en scripts/addons, de antes del 4.2
  o instalado a mano) y la extensión (``bl_ext.user_default.amatista``)
  pueden estar encendidos a la vez. Cada copia registra sus manejadores de
  dibujo, su menú y su temporizador: dos tarjetas, dos menús Amatista, dos
  revisiones por cada cambio.
- Al desactivar una copia vieja que falló a medias, sus manejadores siguen
  dibujando.

Qué hace al encenderse:

1. **Una sola copia.** Busca las otras Amatista (por su módulo y su nombre)
   y apaga las de versión menor o igual (a igual versión gana la extensión).
   Si apagó alguna, se vuelve a encender ella misma para quedarse con sus
   menús y paneles (la otra pudo haber pisado los nombres al registrarse).
2. **Sin manejadores huérfanos.** Los manejadores de dibujo de Amatista se
   anotan en ``bpy.app.driver_namespace`` (sobrevive a recargar el add-on):
   al encender, quita los que dejó una carga anterior. Las funciones de
   ``bpy.app.handlers`` de módulos Amatista que ya no están encendidos
   también se quitan.
3. **Dueña del dibujo.** Anota qué copia manda (``duena``): las tarjetas de
   una copia que no es la dueña no se dibujan (interfaz/turno.py), así que
   aunque algo falle, nunca hay dos tarjetas.

Nada de esto borra archivos: las copias viejas quedan instaladas y apagadas,
y Preferencias › Amatista dice cuáles se apagaron.
"""
import sys

import bpy

CLAVE_DUENA = "amatista.duena"
CLAVE_DIBUJOS = "amatista.dibujos"
NOMBRES = ("Amatista Motor", "Amatista para Blender", "Amatista")
LISTAS = ("depsgraph_update_post", "depsgraph_update_pre", "load_post", "load_pre", "save_pre", "save_post",
          "undo_post", "redo_post", "frame_change_post")

ESTADO = {"apagadas": [], "revisado": False}


def paquete():
    """El módulo raíz de esta copia: «amatista_blender» o «bl_ext.user_default.amatista»."""
    return __package__ or __name__.rpartition(".")[0]


def version_propia():
    from . import ajustes

    return tuple(int(x) for x in ajustes.VERSION_ADDON.split(".")[:3])


def es_amatista(nombre, info=None):
    """¿Este módulo de add-on es una copia de Amatista? (por el nombre del módulo o el de su bl_info)."""
    nombre = str(nombre or "")
    if nombre == "amatista_blender" or nombre.startswith("amatista_blender_") or nombre.endswith(".amatista"):
        return True
    titulo = str((info or {}).get("name") or "")
    return titulo in NOMBRES and "amatista" in nombre.lower()


def _version_de(info):
    try:
        return tuple(int(x) for x in tuple((info or {}).get("version") or (0, 0, 0))[:3])
    except (TypeError, ValueError):
        return (0, 0, 0)


def gana(propia, otra, propio_nombre, otro_nombre):
    """¿Esta copia se queda encendida frente a la otra? La de versión mayor; a igual versión, la extensión."""
    if propia != otra:
        return propia > otra
    return propio_nombre.startswith("bl_ext.") and not otro_nombre.startswith("bl_ext.")


def otras_copias():
    """[(módulo, versión, encendida)] de las otras Amatista que conoce Blender."""
    import addon_utils

    propio = paquete()
    salida = []
    for mod in addon_utils.modules(refresh=False):
        nombre = getattr(mod, "__name__", "")
        if nombre == propio:
            continue
        info = addon_utils.module_bl_info(mod)
        if not es_amatista(nombre, info):
            continue
        encendida, _cargada = addon_utils.check(nombre)
        salida.append((nombre, _version_de(info), bool(encendida)))
    return salida


def apagar_otras():
    """Apaga las otras copias que pierden contra esta. Devuelve las que apagó."""
    import addon_utils

    propio, propia = paquete(), version_propia()
    apagadas = []
    for nombre, version, encendida in otras_copias():
        if not encendida or not gana(propia, version, propio, nombre):
            continue
        try:
            addon_utils.disable(nombre, default_set=True)
            apagadas.append(f"{nombre} {'.'.join(str(n) for n in version)}")
        except Exception as error:  # noqa: BLE001 - una copia rota igual se marca como apagada
            print(f"[Amatista] No se pudo apagar la otra copia {nombre}: {error}")
        quitar_funciones_de(nombre)
    return apagadas


def quitar_funciones_de(modulo):
    """Quita de bpy.app.handlers las funciones que vienen del módulo `modulo` (copias apagadas o rotas)."""
    quitadas = 0
    for nombre_lista in LISTAS:
        lista = getattr(bpy.app.handlers, nombre_lista, None)
        if lista is None:
            continue
        for funcion in list(lista):
            origen = getattr(funcion, "__module__", "") or ""
            if origen == modulo or origen.startswith(modulo + "."):
                lista.remove(funcion)
                quitadas += 1
    return quitadas


def quitar_huerfanas():
    """Funciones de bpy.app.handlers de módulos Amatista que ya no están cargados (o no son esta copia)."""
    propio = paquete()
    quitadas = 0
    for nombre_lista in LISTAS:
        lista = getattr(bpy.app.handlers, nombre_lista, None)
        if lista is None:
            continue
        for funcion in list(lista):
            origen = getattr(funcion, "__module__", "") or ""
            raiz = origen.split(".amatista.")[0] + ".amatista" if ".amatista." in origen else origen.split(".")[0]
            if not es_amatista(raiz) or raiz == propio:
                continue
            if raiz not in sys.modules or not _encendida(raiz):
                lista.remove(funcion)
                quitadas += 1
    return quitadas


def _encendida(nombre):
    try:
        import addon_utils

        return bool(addon_utils.check(nombre)[0])
    except Exception:  # noqa: BLE001
        return False


# --- Manejadores de dibujo anotados ---------------------------------------------------------------


def _dibujos():
    return bpy.app.driver_namespace.setdefault(CLAVE_DIBUJOS, [])


def agregar_dibujo(espacio, funcion, argumentos, region, tipo):
    """draw_handler_add que queda anotado: una carga posterior lo puede quitar aunque esta falle."""
    manejador = espacio.draw_handler_add(funcion, argumentos, region, tipo)
    _dibujos().append((paquete(), espacio, manejador, region))
    return manejador


def quitar_dibujo(espacio, manejador, region):
    try:
        espacio.draw_handler_remove(manejador, region)
    except (ValueError, RuntimeError):
        pass
    lista = _dibujos()
    lista[:] = [d for d in lista if d[2] is not manejador]


def quitar_dibujos_anteriores():
    """Quita los manejadores anotados por cargas anteriores (de esta copia o de otra Amatista)."""
    lista = _dibujos()
    quitados = 0
    for _dueno, espacio, manejador, region in list(lista):
        try:
            espacio.draw_handler_remove(manejador, region)
            quitados += 1
        except (ValueError, RuntimeError):
            pass
    lista.clear()
    return quitados


# --- Dueña del dibujo ----------------------------------------------------------------------------


def tomar():
    bpy.app.driver_namespace[CLAVE_DUENA] = paquete()


def soltar():
    if bpy.app.driver_namespace.get(CLAVE_DUENA) == paquete():
        del bpy.app.driver_namespace[CLAVE_DUENA]


def soy_duena():
    duena = bpy.app.driver_namespace.get(CLAVE_DUENA)
    return duena is None or duena == paquete()


# --- Al encender ---------------------------------------------------------------------------------


def antes_de_registrar():
    """Lo primero de register(): limpia lo que dejaron cargas anteriores y toma el dibujo."""
    quitados = quitar_dibujos_anteriores()
    huerfanas = quitar_huerfanas()
    if quitados or huerfanas:
        print(f"[Amatista] Autosanación: quité {quitados} dibujos y {huerfanas} funciones de cargas anteriores.")
    tomar()


def _revisar_copias():
    """Temporizador corto después de encender: apagar las otras no se hace dentro de register()."""
    ESTADO["revisado"] = True
    try:
        apagadas = apagar_otras()
    except Exception as error:  # noqa: BLE001 - autosanar nunca rompe Blender
        print(f"[Amatista] Autosanación: {error}")
        return None
    if not apagadas:
        return None
    ESTADO["apagadas"] = apagadas
    print(f"[Amatista] Autosanación: apagué otras copias de Amatista ({', '.join(apagadas)}).")
    try:
        import addon_utils

        # La otra pudo pisar nuestros menús y paneles al registrarse: encender de nuevo los deja bien.
        propio = paquete()
        addon_utils.disable(propio, default_set=False)
        addon_utils.enable(propio, default_set=True)
        ESTADO["apagadas"] = apagadas
        from . import ajustes

        ajustes.guardar_preferencias()
    except Exception as error:  # noqa: BLE001
        print(f"[Amatista] Autosanación (volver a encender): {error}")
    return None


def despues_de_registrar():
    if not bpy.app.timers.is_registered(_revisar_copias):
        bpy.app.timers.register(_revisar_copias, first_interval=0.2)


def al_desregistrar():
    if bpy.app.timers.is_registered(_revisar_copias):
        bpy.app.timers.unregister(_revisar_copias)
    soltar()


def resumen():
    """Lo que Preferencias › Amatista dice de las otras copias."""
    try:
        otras = otras_copias()
    except Exception:  # noqa: BLE001
        otras = []
    encendidas = [f"{n} {'.'.join(str(x) for x in v)}" for n, v, e in otras if e]
    return {"apagadas": list(ESTADO["apagadas"]), "encendidas": encendidas, "instaladas": len(otras)}


__all__ = ["agregar_dibujo", "antes_de_registrar", "apagar_otras", "despues_de_registrar", "es_amatista", "gana",
           "otras_copias", "quitar_dibujo", "resumen", "soy_duena"]
