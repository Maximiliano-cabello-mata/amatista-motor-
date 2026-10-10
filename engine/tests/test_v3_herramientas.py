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


# --- Auditoría del motor 3.5 (2026-10) ------------------------------------------------------------


@pytest.mark.parametrize("plantilla", sorted(PLANTILLAS))
def test_cada_plantilla_nace_con_ejemplo_y_caso_solucion(plantilla, tmp_path, capsys):
    carpeta = tmp_path / plantilla
    assert main(["nueva", f"prueba.{plantilla}", "--plantilla", plantilla, "--carpeta", str(carpeta)]) == 0
    datos = json.loads((carpeta / "practica.json").read_text(encoding="utf-8"))
    assert datos["example"]["steps"]
    casos = json.loads((carpeta / "pruebas.json").read_text(encoding="utf-8"))["casos"]
    assert any(c["espera"].get("completada") for c in casos)
    assert main(["revisar", str(carpeta)]) == 0
    assert main(["probar", str(carpeta)]) == 0


def test_cli_probar_reporta_una_escena_rota_sin_traceback(tmp_path, capsys):
    carpeta = tmp_path / "p"
    main(["nueva", "prueba.rota", "--plantilla", "vacia", "--carpeta", str(carpeta)])
    pruebas = json.loads((carpeta / "pruebas.json").read_text(encoding="utf-8"))
    pruebas["casos"] += [{"nombre": "dims rotas", "construir": [{"cubo": {"dims": [1, 2]}}], "espera": {}},
                         {"nombre": "luz rara", "construir": [{"luz": {"tipo": 3}}], "espera": {}}, "no-es-un-caso"]
    (carpeta / "pruebas.json").write_text(json.dumps(pruebas), encoding="utf-8")
    assert main(["probar", str(carpeta)]) == 1
    salida = capsys.readouterr().out
    assert "construir[0].cubo.dims" in salida and "construir[0].luz.tipo" in salida


def test_singular_y_mensajes_de_cantidad():
    from amatista_engine.validators.base import count_message, singular

    assert singular("luces") == "luz" and singular("luces de área") == "luz de área"
    assert singular("soles") == "sol" and singular("focos") == "foco" and singular("vértices") == "vértice"
    assert count_message(1, 2, None, "luces puntuales") == "Tienes 1 luz puntual; se necesitan al menos 2."
    assert count_message(1, 8, None, "«Rueda»") == "Tienes 1 de tipo «Rueda»; se necesitan al menos 8."
    assert count_message(3, 4, 4, "«Pata»") == "Tienes 3/4 «Pata». Falta 1."


def test_proporcion_por_encima_del_maximo():
    from amatista_engine.models import TargetDefinition
    from amatista_engine.validators.shape import proportion

    escena = Escena().cubo("Torre", dims=(1, 1, 10)).construir()
    r = proportion(TargetDefinition("t", "shape.proportion", {"name": "Torre", "min_ratio": 2, "max_ratio": 4}), escena)
    assert not r.passed and "como máximo 4" in r.message


def test_parametros_registrados_coinciden_con_lo_que_leen():
    motor = create_default_engine()
    below = {p.name: p for p in motor.registry.spec("spatial.below").params}
    assert not below["reference_role"].required and "reference" in below and "inside" in below
    assert "tolerance" in {p.name for p in motor.registry.spec("transform.scale_applied").params}
    assert "tolerance" in {p.name for p in motor.registry.spec("figure.recognize").params}
    datos = nueva_practica("prueba.below", "vacia", "Prueba", "blender_principiante", 1)
    datos["targets"].insert(0, {"id": "abajo", "title": "Abajo", "validator": "spatial.below",
                                "params": {"primitive": "cube", "reference": "Cube"}, "hints": ["x"]})
    assert compile_practice(datos).ok
    datos["targets"][0]["params"] = {"primitive": "cube"}
    assert any("reference_role" in e for e in compile_practice(datos).errors)


def test_parametros_con_tipo_incorrecto_no_compilan():
    datos = nueva_practica("prueba.tipos", "vacia", "Prueba", "blender_principiante", 1)
    datos["targets"][0]["params"] = {"type": "MESH", "min": [1]}
    assert any("«min» debe ser un número entero" in e for e in compile_practice(datos).errors)


def test_scene_mode():
    from amatista_engine.models import TargetDefinition
    from amatista_engine.validators.scene import scene_mode

    objetivo = TargetDefinition("m", "scene.mode", {"mode": "OBJECT"})
    assert scene_mode(objetivo, Escena().construir()).passed
    assert not scene_mode(objetivo, Escena().modo("EDIT_MESH").construir()).passed
    assert scene_mode(TargetDefinition("m", "scene.mode", {"mode": "EDIT"}), Escena().modo("EDIT_MESH").construir()).passed
