"""Herramientas de autor del motor v3: plantillas, CLI, constructor de escenas y foto de escena."""
import json

import pytest

from amatista_engine import create_default_engine
from amatista_engine.cli import main
from amatista_engine.practice import compile_practice
from amatista_engine.practice.templates import PLANTILLAS, nueva_practica, nuevas_pruebas
from amatista_engine.snapshot import scene_from_dict, scene_to_dict
from amatista_engine.testing import Escena, escena_desde_pasos


@pytest.mark.parametrize("plantilla", sorted(PLANTILLAS))
def test_cada_plantilla_compila(plantilla):
    motor = create_default_engine()
    datos = nueva_practica(f"prueba.{plantilla}", plantilla, "Prueba", "blender_principiante", 1)
    resultado = compile_practice(datos, motor.registry, motor.tools)
    assert resultado.ok, resultado.errors
    assert nuevas_pruebas(datos["id"], plantilla)["casos"]


def test_cli_nueva_revisar_y_probar(tmp_path, capsys):
    carpeta = tmp_path / "mi-practica"
    assert main(["nueva", "prueba.cli", "--plantilla", "modelado", "--carpeta", str(carpeta)]) == 0
    assert (carpeta / "practica.json").exists() and (carpeta / "pruebas.json").exists()
    assert main(["revisar", str(carpeta)]) == 0
    assert main(["probar", str(carpeta)]) == 0
    assert "casos correctos" in capsys.readouterr().out


def test_cli_probar_detecta_un_caso_falso(tmp_path):
    carpeta = tmp_path / "p"
    main(["nueva", "prueba.falla", "--plantilla", "vacia", "--carpeta", str(carpeta)])
    pruebas = json.loads((carpeta / "pruebas.json").read_text(encoding="utf-8"))
    pruebas["casos"].append({"nombre": "mentira", "construir": [], "espera": {"completada": True}})
    (carpeta / "pruebas.json").write_text(json.dumps(pruebas), encoding="utf-8")
    assert main(["probar", str(carpeta)]) == 1


def test_cli_validadores_markdown(tmp_path):
    destino = tmp_path / "v.md"
    assert main(["validadores", "--md", str(destino)]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "light.three_point" in texto and "logic.any" in texto


def test_pasos_desconocidos_avisan():
    with pytest.raises(ValueError, match="paso desconocido"):
        escena_desde_pasos([{"cubito": {}}])


def test_foto_v3_ida_y_vuelta():
    escena = (
        Escena().cubo("Nave", rol="nave", mitad="x-", encimados=2)
        .modificador("Nave", "MIRROR").modificador("Nave", "SUBSURF", niveles=2)
        .material("Nave", "Metal", metal=1.0, rugosidad=0.2)
        .esfera("Pelota", loc=(3, 0, 4)).animar("Pelota", "location", "z", [(1, 4), (12, 1), (24, 4)])
        .luz("Key", "AREA", (-4, -5, 4), 500).camara(loc=(0, -10, 4))
        .seleccionar("Nave").motor("BLENDER_EEVEE").renders(2).guardado("mi_nave.blend")
        .construir()
    )
    vuelta = scene_from_dict(json.loads(json.dumps(scene_to_dict(escena))))
    nave = vuelta.objects[0]
    assert nave.modifier("SUBSURF").levels == 2 and nave.modifier("MIRROR").axes == (True, False, False)
    assert nave.material_details[0].metallic == 1.0 and nave.duplicate_vertices == 2
    assert vuelta.objects[1].channel("location", 2).values == (4.0, 1.0, 4.0)
    assert vuelta.objects[2].light_type == "AREA"
    assert (vuelta.active_camera, vuelta.renders, vuelta.render_engine) == ("Camera", 2, "BLENDER_EEVEE")
    assert vuelta.active_object == "Nave" and vuelta.selected == ("Nave",)
