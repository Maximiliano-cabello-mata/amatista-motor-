"""Corazón Amatista: el motor que decide qué ve el alumno, en cualquier programa 3D.

Contrato estable ``amatista.corazon/1`` (ver ``contrato.py``). Las piezas:

- ``contrato``     señales, eventos, lugares y el turno (lo único que ve el alumno)
- ``adaptador``    el perfil de un programa (datos) y la interfaz del adaptador
- ``perfiles/``    Blender (estable), A-Frame (estable), Maya y 3ds Max (borrador)
- ``andamiaje``    cuánta ayuda dar por herramienta (mostrar › señalar › recordar › reto)
- ``senales``      qué señal pedir y su ciclo de vida (nunca caduca por reloj)
- ``director``     junta todo: observa el reporte, decide el turno, pide y comprueba la señal
- ``extensiones``  los puntos donde entra un comportamiento nuevo sin tocar el corazón
- ``ramas``        variantes del motor en JSON (``amatista.rama/1``), con herencia
- ``conformidad``  revisa que un adaptador nuevo cumpla el contrato
- ``simulado``     un programa de mentira para probar

Python puro, sin ``bpy``: corre en Blender, en el servidor y en pytest.
Referencia: docs/motor/referencia/23_corazon.md.
"""
from .adaptador import Adaptador, AdaptadorBase, Capacidades, Perfil
from .contrato import CONTRATO, EstadoSenal, Evento, Lugar, ResultadoSenal, Senal, Turno
from .director import Director
from .extensiones import Extension, Extensiones
from .ramas import Rama, crear_director, leer_rama

VERSION = "1.0.0"

__all__ = ["Adaptador", "AdaptadorBase", "CONTRATO", "Capacidades", "Director", "EstadoSenal", "Evento", "Extension",
           "Extensiones", "Lugar", "Perfil", "Rama", "ResultadoSenal", "Senal", "Turno", "VERSION", "crear_director",
           "leer_rama"]
