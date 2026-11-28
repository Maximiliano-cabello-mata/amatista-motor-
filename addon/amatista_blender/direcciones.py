"""Qué direcciones de servidor acepta el add-on para hablar con la API (sin bpy, se prueba fuera de Blender).

El token de la cuenta viaja en la cabecera Authorization: por http:// iría en claro y cualquiera en la
misma red (wifi del aula, cafetería) podría leerlo y entrar como el alumno. Por eso:

- https:// se acepta siempre;
- http:// solo hacia esta misma PC (localhost, 127.0.0.0/8, ::1 o *.localhost), donde el tráfico no sale
  del equipo: es el servidor de desarrollo por defecto (http://localhost:8000);
- cualquier otro esquema (file://, ftp://, …) se rechaza.
"""
import ipaddress
import urllib.parse

ERROR_ESQUEMA = "La dirección del servidor debe empezar con https://"
ERROR_HTTP = (
    "Por seguridad, el servidor debe usar https:// (http:// solo se permite con localhost). "
    "Revisa la dirección en Preferencias › Add-ons › Amatista."
)


def es_local(host):
    """True si host es esta misma PC: localhost, *.localhost o una IP de loopback (127.0.0.0/8, ::1)."""
    host = (host or "").strip().lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def revisar_servidor(url):
    """None si la URL es segura para enviar el token; si no, el mensaje de error para el alumno."""
    try:
        partes = urllib.parse.urlsplit((url or "").strip())
    except ValueError:
        return ERROR_ESQUEMA
    esquema = partes.scheme.lower()
    if esquema == "https" and partes.hostname:
        return None
    if esquema == "http" and partes.hostname:
        return None if es_local(partes.hostname) else ERROR_HTTP
    return ERROR_ESQUEMA
