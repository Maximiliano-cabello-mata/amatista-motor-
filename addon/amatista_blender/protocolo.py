"""«Abrir en Blender» con Blender cerrado: el enlace amatista:// (add-on 5.4).

Hasta el 5.3, «Abrir en Blender» solo funcionaba si Blender ya estaba abierto
(la orden espera en el servidor y el latido la recoge). Con Blender cerrado
la lección decía «Tu Blender no respondió» y no pasaba nada. Ahora el
instalador (y el add-on al arrancar) registra en el sistema el enlace
amatista://: la plataforma lo abre, el sistema arranca Blender así

    blender -- --amatista "amatista://taller/blender.bp.m1?actividad=..."

y el add-on lee esa dirección al arrancar y abre la actividad (lanzador.py).

Direcciones (las arma frontend/src/services/lanzador.js):

    amatista://abrir                          solo abre Blender
    amatista://practica/<id>                  abrir_practica
    amatista://taller/<id>?actividad=<id>     taller_abrir
        &etapa=exploracion&habilidades=a,b&leccion=<id>   (motor 6: la etapa de la lección)
    amatista://isla                           isla
    amatista://recorrido/<pestana|vista|taller>   «Conoce Amatista Motor»

Cualquier página web puede pedir un amatista://, así que la dirección solo
elige qué actividad abrir: nunca una ruta de archivo ni código. Un id que no
cumple ID_VALIDO se descarta.

Motor 6: el enlace arranca **Blender Amatista** (``--app-template amatista``,
la plantilla que instala el add-on) y ``crear_lanzador`` deja un acceso
directo «Blender Amatista» en el menú del sistema.

Este archivo no importa bpy (se prueba sin Blender): recibe la ruta de
Blender y escribe el registro de Windows, el .desktop de Linux o la pequeña
app de macOS que reciben el enlace.
"""
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ESQUEMA = "amatista"
ARGUMENTO = "--amatista"
VERSION = 2  # súbela si cambia cómo se registra: el add-on lo vuelve a registrar al arrancar
ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
RECORRIDOS = ("pestana", "vista", "taller")
NOMBRE_APP_MAC = "Amatista para Blender.app"
ID_APP_MAC = "tech.amatista-3d.lanzador"
DESKTOP_LINUX = "amatista-blender.desktop"
PLANTILLA = "amatista"  # la plantilla de aplicación «Blender Amatista» (plantilla_amatista/)
ARGS_PLANTILLA = ("--app-template", PLANTILLA)
NOMBRE_LANZADOR = "Blender Amatista"
DESKTOP_LANZADOR = "blender-amatista.desktop"
ETAPAS = ("exploracion", "practica")


def _id(texto):
    texto = unquote(str(texto or "")).strip().strip("/")
    return texto if ID_VALIDO.match(texto) else ""


def orden_de_url(url):
    """La orden del enlace en vivo que pide una dirección amatista:// ({tipo, datos}) o None."""
    try:
        partes = urlsplit(str(url or "").strip())
    except ValueError:
        return None
    if partes.scheme.lower() != ESQUEMA:
        return None
    que = (partes.netloc or "").lower()
    camino = [p for p in partes.path.split("/") if p]
    consulta = parse_qs(partes.query)
    if not que and camino:  # «amatista:taller/x» sin barras
        que, camino = camino[0].lower(), camino[1:]
    if que in ("", "abrir"):
        return {"tipo": "abrir", "datos": {}}
    if que == "practica" and camino and _id(camino[0]):
        return {"tipo": "abrir_practica", "datos": {"practica_id": _id(camino[0])}}
    if que == "taller" and camino and _id(camino[0]):
        datos = {"taller": _id(camino[0])}
        actividad = _id((consulta.get("actividad") or [""])[0])
        if actividad:
            datos["actividad"] = actividad
        etapa = (consulta.get("etapa") or [""])[0]
        if etapa in ETAPAS:
            datos["etapa"] = etapa
            habilidades = [_id(h) for h in ",".join(consulta.get("habilidades") or []).split(",")]
            datos["habilidades"] = [h for h in habilidades if h][:4]
        leccion = _id((consulta.get("leccion") or [""])[0])
        if leccion:
            datos["leccion"] = leccion
        return {"tipo": "taller_abrir", "datos": datos}
    if que == "isla":
        return {"tipo": "isla", "datos": {}}
    if que == "recorrido":
        cual = camino[0].lower() if camino else ""
        return {"tipo": "recorrido", "datos": {"accion": "empezar", **({"recorrido": cual} if cual in RECORRIDOS else {})}}
    return None


def url_de_argumentos(argv=None):
    """La dirección que trae Blender después de «--» (… -- --amatista amatista://…) o ""."""
    argv = list(sys.argv if argv is None else argv)
    if "--" not in argv:
        return ""
    resto = argv[argv.index("--") + 1:]
    for i, valor in enumerate(resto):
        if valor == ARGUMENTO and i + 1 < len(resto):
            return resto[i + 1]
        if valor.startswith(ARGUMENTO + "="):
            return valor.split("=", 1)[1]
        if valor.lower().startswith(ESQUEMA + ":"):  # algunos sistemas pasan solo la dirección
            return valor
    return ""


# --- Registrar el enlace en el sistema ----------------------------------------------------


def lanzador_de(binario):
    """El ejecutable que debe abrir el enlace. En Windows, blender-launcher.exe (no abre la consola)."""
    binario = Path(binario)
    if sys.platform.startswith("win"):
        launcher = binario.with_name("blender-launcher.exe")
        if launcher.is_file():
            return launcher
    if sys.platform == "darwin":
        return binario  # …/Blender.app/Contents/MacOS/Blender
    return binario


def comando_linux(binario, entorno=None):
    """La línea Exec= del .desktop: Flatpak y Snap ven otra ruta dentro de su caja."""
    entorno = os.environ if entorno is None else entorno
    if entorno.get("FLATPAK_ID"):
        inicio = f"flatpak run {entorno['FLATPAK_ID']}"
    elif entorno.get("SNAP"):
        inicio = "/snap/bin/blender"
    else:
        inicio = shlex.quote(str(binario))
    return f"{inicio} {' '.join(ARGS_PLANTILLA)} -- {ARGUMENTO} %u"


def texto_desktop(binario, entorno=None):
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Amatista para Blender",
        "Comment=Abre tus prácticas de Amatista en Blender",
        f"Exec={comando_linux(binario, entorno)}",
        "MimeType=x-scheme-handler/amatista;",
        "NoDisplay=true",
        "Terminal=false",
        "",
    ])


def guion_mac(binario):
    """El AppleScript de la app que recibe amatista:// en macOS (osacompile)."""
    ruta = str(binario).replace("\\", "\\\\").replace('"', '\\"')
    return (
        "on open location direccion\n"
        f'\tdo shell script quoted form of "{ruta}" & " {" ".join(ARGS_PLANTILLA)} -- {ARGUMENTO} " & quoted form of direccion'
        ' & " > /dev/null 2>&1 &"\n'
        "end open location\n"
        "on run\n"
        f'\tdo shell script quoted form of "{ruta}" & " {" ".join(ARGS_PLANTILLA)} > /dev/null 2>&1 &"\n'
        "end run\n"
    )


def _registrar_windows(binario):
    import winreg  # solo existe en Windows

    comando = f'"{lanzador_de(binario)}" {" ".join(ARGS_PLANTILLA)} -- {ARGUMENTO} "%1"'
    base = rf"Software\Classes\{ESQUEMA}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as clave:
        winreg.SetValueEx(clave, "", 0, winreg.REG_SZ, "URL:Amatista para Blender")
        winreg.SetValueEx(clave, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\DefaultIcon") as clave:
        winreg.SetValueEx(clave, "", 0, winreg.REG_SZ, f'"{binario}",0')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as clave:
        winreg.SetValueEx(clave, "", 0, winreg.REG_SZ, comando)
    return f"Windows: HKCU\\{base}"


def _registrar_linux(binario, casa=None):
    casa = Path(casa or Path.home())
    carpeta = Path(os.environ.get("XDG_DATA_HOME") or casa / ".local" / "share") / "applications"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / DESKTOP_LINUX
    archivo.write_text(texto_desktop(binario), encoding="utf-8")
    for comando in (["xdg-mime", "default", DESKTOP_LINUX, f"x-scheme-handler/{ESQUEMA}"],
                    ["update-desktop-database", str(carpeta)]):
        try:
            subprocess.run(comando, check=False, timeout=10, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            pass  # sin xdg-utils el .desktop sigue sirviendo en la mayoría de escritorios
    return f"Linux: {archivo}"


def _registrar_mac(binario, casa=None):
    casa = Path(casa or Path.home())
    app = casa / "Applications" / NOMBRE_APP_MAC
    app.parent.mkdir(parents=True, exist_ok=True)
    guion = app.parent / ".amatista-lanzador.applescript"
    guion.write_text(guion_mac(binario), encoding="utf-8")
    subprocess.run(["osacompile", "-o", str(app), str(guion)], check=True, timeout=60, capture_output=True)
    guion.unlink(missing_ok=True)
    plist = app / "Contents" / "Info.plist"
    buddy = "/usr/libexec/PlistBuddy"
    for orden in (f"Set :CFBundleIdentifier {ID_APP_MAC}",
                  "Delete :CFBundleURLTypes",
                  "Add :CFBundleURLTypes array",
                  "Add :CFBundleURLTypes:0 dict",
                  "Add :CFBundleURLTypes:0:CFBundleURLName string Amatista",
                  "Add :CFBundleURLTypes:0:CFBundleURLSchemes array",
                  f"Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string {ESQUEMA}",
                  "Add :LSUIElement bool true"):
        subprocess.run([buddy, "-c", orden, str(plist)], check=False, timeout=10, capture_output=True)
    lsregister = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
                  "LaunchServices.framework/Support/lsregister")
    subprocess.run([lsregister, "-f", str(app)], check=False, timeout=30, capture_output=True)
    return f"macOS: {app}"


# --- El acceso directo «Blender Amatista» (motor 6) -----------------------------------------------


def texto_desktop_lanzador(binario, icono="", entorno=None):
    entorno = os.environ if entorno is None else entorno
    if entorno.get("FLATPAK_ID"):
        inicio = f"flatpak run {entorno['FLATPAK_ID']}"
    elif entorno.get("SNAP"):
        inicio = "/snap/bin/blender"
    else:
        inicio = shlex.quote(str(binario))
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={NOMBRE_LANZADOR}",
        "GenericName=Aprende 3D con Amatista",
        "Comment=Blender con Amatista: tu taller y la plataforma de la mano",
        f"Exec={inicio} {' '.join(ARGS_PLANTILLA)} %f",
        f"Icon={icono or 'blender'}",
        "Categories=Graphics;3DGraphics;Education;",
        "Terminal=false",
        "",
    ])


def guion_lanzador_mac(binario):
    ruta = str(binario).replace("\\", "\\\\").replace('"', '\\"')
    return f'do shell script quoted form of "{ruta}" & " {" ".join(ARGS_PLANTILLA)} > /dev/null 2>&1 &"\n'


def guion_lanzador_windows(binario, destino):
    """PowerShell que crea el acceso directo .lnk (WScript.Shell): sin dependencias."""
    objetivo = str(lanzador_de(binario)).replace("'", "''")
    destino = str(destino).replace("'", "''")
    return (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + destino + "'); "
        "$s.TargetPath = '" + objetivo + "'; "
        "$s.Arguments = '" + " ".join(ARGS_PLANTILLA) + "'; "
        "$s.Description = 'Blender con Amatista'; "
        "$s.IconLocation = '" + str(binario).replace("'", "''") + ",0'; "
        "$s.Save()"
    )


def crear_lanzador(binario, icono="", casa=None):
    """Deja el acceso directo «Blender Amatista» en el menú del sistema. Devuelve (ok, texto). Nunca lanza."""
    if not binario:
        return False, "No sé dónde está Blender."
    try:
        casa = Path(casa or Path.home())
        if sys.platform.startswith("win"):
            menu = Path(os.environ.get("APPDATA") or casa / "AppData" / "Roaming") / "Microsoft" / "Windows" / \
                "Start Menu" / "Programs" / f"{NOMBRE_LANZADOR}.lnk"
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            guion_lanzador_windows(binario, menu)], check=True, timeout=60, capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True, f"Windows: {menu}"
        if sys.platform == "darwin":
            app = casa / "Applications" / f"{NOMBRE_LANZADOR}.app"
            app.parent.mkdir(parents=True, exist_ok=True)
            guion = app.parent / ".blender-amatista.applescript"
            guion.write_text(guion_lanzador_mac(binario), encoding="utf-8")
            subprocess.run(["osacompile", "-o", str(app), str(guion)], check=True, timeout=60, capture_output=True)
            guion.unlink(missing_ok=True)
            return True, f"macOS: {app}"
        carpeta = Path(os.environ.get("XDG_DATA_HOME") or casa / ".local" / "share") / "applications"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / DESKTOP_LANZADOR
        archivo.write_text(texto_desktop_lanzador(binario, icono), encoding="utf-8")
        return True, f"Linux: {archivo}"
    except Exception as error:  # noqa: BLE001
        return False, f"No se pudo crear el acceso directo «{NOMBRE_LANZADOR}» ({error})."


def registrar(binario):
    """Registra amatista:// para este Blender. Devuelve (ok, texto). Nunca lanza."""
    if not binario:
        return False, "No sé dónde está Blender."
    try:
        if sys.platform.startswith("win"):
            return True, _registrar_windows(binario)
        if sys.platform == "darwin":
            return True, _registrar_mac(binario)
        return True, _registrar_linux(binario)
    except Exception as error:  # noqa: BLE001 - registrar el enlace nunca rompe Blender ni el instalador
        return False, f"No se pudo registrar el enlace amatista:// ({error})."
