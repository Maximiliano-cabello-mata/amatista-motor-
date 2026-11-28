"""Dónde vive el token de la cuenta: cifrado, fuera de userpref.blend (sin bpy, se prueba fuera de Blender).

Antes el token era una StringProperty normal de las preferencias: subtype PASSWORD solo lo ocultaba en
la interfaz, pero quedaba en claro dentro de userpref.blend (un archivo que se copia, se respalda o se
comparte con facilidad). Ahora la propiedad «token» de las preferencias usa get/set (ajustes.py) y su
valor nunca se escribe en userpref.blend: se guarda aquí, en <config de Blender>/amatista/sesion.dat.

- Windows: cifrado con DPAPI (CryptProtectData), atado a la cuenta de Windows del alumno. Otro usuario
  de la misma PC, o quien copie el archivo a otra máquina, no puede descifrarlo.
- macOS/Linux: archivo con permisos 0600 (solo el dueño lo lee). No es cifrado; queda fuera del .blend
  de preferencias y de lo que otros usuarios del equipo pueden leer.
"""
import ctypes
import os
import sys
from pathlib import Path

ARCHIVO = "sesion.dat"
CABECERA_DPAPI = b"AMT1D"  # contenido cifrado con DPAPI (Windows)
CABECERA_PLANO = b"AMT1P"  # contenido sin cifrar con permisos 0600 (otros sistemas)
# Entropía adicional de DPAPI: otro programa de la misma cuenta necesita conocerla para descifrar.
ENTROPIA = b"amatista-blender-token-v1"
_SIN_INTERFAZ = 0x1  # CRYPTPROTECT_UI_FORBIDDEN: nunca mostrar diálogos


def metodo():
    """'dpapi' en Windows (cifrado real); 'archivo' en otros sistemas (permisos 0600)."""
    return "dpapi" if sys.platform == "win32" else "archivo"


class _BLOB(ctypes.Structure):
    """DATA_BLOB de Win32: puntero y longitud de un bloque de bytes."""
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(datos):
    """DATA_BLOB que apunta a una copia de datos; devuelve (blob, buffer) para que el buffer siga vivo."""
    buffer = ctypes.create_string_buffer(datos, len(datos))
    return _BLOB(len(datos), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _dpapi(datos, proteger):
    """Cifra (proteger=True) o descifra datos con DPAPI de la cuenta actual de Windows. OSError si falla."""
    from ctypes import wintypes

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    funcion = crypt32.CryptProtectData if proteger else crypt32.CryptUnprotectData
    funcion.restype = wintypes.BOOL

    entrada, _buf_entrada = _blob(datos)
    entropia, _buf_entropia = _blob(ENTROPIA)
    salida = _BLOB()
    ok = funcion(ctypes.byref(entrada), None, ctypes.byref(entropia), None, None, _SIN_INTERFAZ, ctypes.byref(salida))
    if not ok:
        raise OSError(f"DPAPI falló (error {ctypes.GetLastError()})")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(salida.pbData, ctypes.c_void_p))


def _ruta(carpeta):
    """Ruta de sesion.dat dentro de la carpeta de configuración del add-on."""
    return Path(carpeta) / ARCHIVO


def guardar(carpeta, token):
    """Guarda el token (cifrado en Windows); con token vacío borra la sesión guardada.

    Escribe primero un archivo temporal y lo renombra, para no dejar nunca una sesión a medias.
    """
    if not token:
        borrar(carpeta)
        return
    datos = token.encode("utf-8")
    contenido = CABECERA_DPAPI + _dpapi(datos, True) if metodo() == "dpapi" else CABECERA_PLANO + datos
    ruta = _ruta(carpeta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    # O_CREAT con 0o600: en macOS/Linux el archivo nace legible solo por su dueño.
    descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as archivo:
        archivo.write(contenido)
    os.replace(temporal, ruta)
    if metodo() != "dpapi":
        os.chmod(ruta, 0o600)


def leer(carpeta):
    """Token guardado, o '' si no hay sesión o el archivo no se puede descifrar (otra cuenta, dañado)."""
    try:
        contenido = _ruta(carpeta).read_bytes()
    except OSError:
        return ""
    try:
        if contenido.startswith(CABECERA_DPAPI) and metodo() == "dpapi":
            return _dpapi(contenido[len(CABECERA_DPAPI):], False).decode("utf-8")
        if contenido.startswith(CABECERA_PLANO):
            return contenido[len(CABECERA_PLANO):].decode("utf-8")
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def borrar(carpeta):
    """Borra la sesión guardada (al desvincular la cuenta). No falla si no existe."""
    try:
        _ruta(carpeta).unlink()
    except FileNotFoundError:
        pass
