"""Auditoría de las prácticas: arma cada figura como lo haría un alumno y busca tropiezos.

    python engine/herramientas/auditar.py                 # todas las prácticas
    python engine/herramientas/auditar.py practices/blender/principiante/m1-tren
    python engine/herramientas/auditar.py --json          # para una máquina

No usa Blender. Por cada práctica con modelo de referencia comprueba:

  retroceso   Al agregar una a una las piezas correctas, el progreso nunca baja
              y ningún paso marcado como hecho se desmarca.
  rol         Sin poner roles, el motor reconoce cada pieza como lo que es, en
              cada momento de la construcción.
  tamaño      La figura completa se sigue reconociendo a la mitad y al doble de
              tamaño, y hecha a mano (medidas ±15 %, cinco manos distintas).
  orden       Lo mismo si las piezas se agregan en otro orden.

Sale con 1 si encuentra algo. Cada hallazgo dice la práctica, la comprobación,
el momento y el dato que no cuadra.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import amatista_engine  # noqa: E402
from amatista_engine.practice import parse_practice  # noqa: E402
from amatista_engine.testing import Escena  # noqa: E402

MANOS = (1, 2, 3, 4, 5)  # semillas de la variación «hecha a mano»
ORDENES = (1, 2, 3)  # semillas de los órdenes alternativos


def _piezas(practica) -> List[Any]:
    referencia = getattr(practica, "reference", None)
    return list(getattr(referencia, "compared", ()) or ()) if referencia else []


def _grupo(pieza) -> str:
    return getattr(pieza, "role", "") or ""


def _evaluar(motor, practica, piezas: Sequence[Any], roles: bool, **opciones):
    escena = Escena().referencia(piezas, roles=roles, **opciones).construir()
    return escena, motor.evaluate(practica, escena)


def _hechos(reporte) -> set:
    return {p.target_id for p in reporte.steps if p.status == "completado"}


def _construccion(motor, practica, piezas: Sequence[Any], etiqueta: str) -> List[Dict[str, Any]]:
    """Agrega las piezas una a una: ni el progreso ni los pasos hechos deben retroceder."""
    hallazgos = []
    progreso, hechos = 0.0, set()
    unidas = any(getattr(p, "join", "") for p in piezas)
    for k in range(1, len(piezas) + 1):
        _, reporte = _evaluar(motor, practica, piezas[:k], roles=True)
        nombre = getattr(piezas[k - 1], "name", "") or _grupo(piezas[k - 1]) or getattr(piezas[k - 1], "primitive", "")
        if reporte.progress < progreso - 0.01:
            hallazgos.append({"comprobacion": "retroceso", "cuando": f"{etiqueta}: al agregar la pieza {k} ({nombre})",
                              "dato": f"el progreso baja de {progreso:g} % a {reporte.progress:g} %"})
        perdidos = hechos - _hechos(reporte)
        if perdidos and not unidas:
            hallazgos.append({"comprobacion": "retroceso", "cuando": f"{etiqueta}: al agregar la pieza {k} ({nombre})",
                              "dato": "se desmarcan pasos ya hechos: " + ", ".join(sorted(perdidos))})
        progreso, hechos = max(progreso, reporte.progress), _hechos(reporte) | (hechos if unidas else set())
    return hallazgos


def _roles(motor, practica, piezas: Sequence[Any], cuando: str, **opciones) -> List[Dict[str, Any]]:
    """Sin roles puestos, cada pieza debe reconocerse como su grupo (o quedar sin rol, nunca como otro)."""
    if not getattr(practica, "infers_roles", True):
        return []  # la práctica no pide reconocer piezas por su forma
    if any(getattr(p, "join", "") for p in piezas):
        return []  # las piezas unidas se revisan por silueta, no por pieza
    escena, reporte = _evaluar(motor, practica, piezas, roles=False, **opciones)
    deducidos = dict(reporte.inferred_roles)
    hallazgos = []
    con_rol = [p for p in piezas if _grupo(p)]
    objetos = [o for o in escena.objects if o.object_type == "MESH"]
    if len(objetos) != len(piezas):
        return []
    for pieza, obj in zip(piezas, objetos):
        esperado, visto = _grupo(pieza), deducidos.get(obj.name, "")
        if esperado and visto and visto != esperado:
            hallazgos.append({"comprobacion": "rol", "cuando": cuando,
                              "dato": f"«{getattr(pieza, 'name', '') or esperado}» se toma por «{visto}» y es «{esperado}»"})
        elif esperado and not visto and len(con_rol) == len(piezas) and len(piezas) >= 3:
            hallazgos.append({"comprobacion": "rol", "cuando": cuando,
                              "dato": f"«{getattr(pieza, 'name', '') or esperado}» ({esperado}) no se reconoce"})
    return hallazgos


def auditar(ruta: Path, motor=None) -> Dict[str, Any]:
    motor = motor or amatista_engine.create_default_engine()
    practica = parse_practice(json.loads((ruta / "practica.json").read_text(encoding="utf-8")))
    piezas = _piezas(practica)
    informe: Dict[str, Any] = {"practica": practica.id, "carpeta": str(ruta), "piezas": len(piezas), "hallazgos": []}
    if not piezas:
        informe["nota"] = "sin modelo de referencia: no hay figura que armar"
        return informe
    hallazgos = informe["hallazgos"]
    hallazgos += _construccion(motor, practica, piezas, "orden del modelo")
    for semilla in ORDENES:
        otro = list(piezas)
        random.Random(semilla).shuffle(otro)
        hallazgos += _construccion(motor, practica, otro, f"orden alternativo {semilla}")
    for k in range(1, len(piezas) + 1):
        hallazgos += _roles(motor, practica, piezas[:k], f"con {k} de {len(piezas)} piezas")
    for escala in (0.5, 2.0):
        hallazgos += _roles(motor, practica, piezas, f"figura completa a escala {escala:g}", escala=escala)
    for mano in MANOS:
        hallazgos += _roles(motor, practica, piezas, f"hecha a mano (±15 %, mano {mano})", variacion=0.15, semilla=mano)
    # Un mismo tropiezo se repite en varios momentos: se deja el primero de cada uno.
    vistos, unicos = set(), []
    for h in hallazgos:
        clave = (h["comprobacion"], h["dato"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(h)
    informe["hallazgos"] = unicos
    return informe


def carpetas(argumentos: Sequence[str]) -> List[Path]:
    if argumentos:
        return [Path(a) for a in argumentos]
    return sorted(p.parent for p in (RAIZ / "practices" / "blender").rglob("practica.json"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument("practicas", nargs="*", help="carpetas de práctica (por defecto, todas)")
    analizador.add_argument("--json", action="store_true", help="salida para una máquina")
    opciones = analizador.parse_args(argv)
    motor = amatista_engine.create_default_engine()
    informes = [auditar(ruta, motor) for ruta in carpetas(opciones.practicas)]
    total = sum(len(i["hallazgos"]) for i in informes)
    if opciones.json:
        print(json.dumps({"hallazgos": total, "practicas": informes}, ensure_ascii=False, indent=2))
        return 1 if total else 0
    for informe in informes:
        marca = "✓" if not informe["hallazgos"] else "✗"
        print(f"{marca} {informe['practica']}  ({informe['piezas']} piezas)" + (f"  {informe['nota']}" if informe.get("nota") else ""))
        for h in informe["hallazgos"]:
            print(f"    [{h['comprobacion']}] {h['cuando']}: {h['dato']}")
    print(f"\n{total} hallazgo(s) en {len(informes)} práctica(s).")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
