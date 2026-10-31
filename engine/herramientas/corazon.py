"""Herramientas del Corazón Amatista para quien desarrolla el motor (sin Blender).

    python engine/herramientas/corazon.py ramas                 revisa practices/ramas/
    python engine/herramientas/corazon.py perfiles              programas y herramientas que ubican
    python engine/herramientas/corazon.py extensiones           las extensiones incluidas
    python engine/herramientas/corazon.py turno <practica.json> [--rama blender-principiante]
                                                                el primer turno con la escena vacía, en JSON
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "engine"))

from amatista_engine import create_default_engine  # noqa: E402
from amatista_engine.corazon import extensiones, perfiles, ramas  # noqa: E402
from amatista_engine.corazon.simulado import AdaptadorSimulado  # noqa: E402
from amatista_engine.practice import load_practice  # noqa: E402

RAMAS = RAIZ / "practices" / "ramas"


def _ramas(_args):
    todas = ramas.cargar_ramas(RAMAS)
    for r in todas.values():
        f = ramas.resolver(r, todas)
        print(f"{r.id:24} {f.software:8} extensiones: {', '.join(f.extensiones) or '—'}")
    problemas = ramas.revisar(todas)
    for p in problemas:
        print("  ✗", p)
    return 1 if problemas else 0


def _perfiles(_args):
    for p in perfiles.todos().values():
        faltan = p.faltan()
        print(f"{p.software:8} {p.estado:9} {len(p.lugares):3} lugares" + (f"  faltan: {', '.join(faltan)}" if faltan else ""))
    return 0


def _extensiones(_args):
    for ext_id in extensiones.disponibles():
        e = extensiones.crear(ext_id)
        print(f"{e.id:24} {e.version:6} {', '.join(sorted(e.aporta))}: {e.descripcion}")
    return 0


def _turno(args):
    todas = ramas.cargar_ramas(RAMAS)
    rama = todas[args.rama]
    practica = load_practice(args.practica)
    final = ramas.resolver(rama, todas)
    programa = AdaptadorSimulado(perfiles.perfil(final.software))
    d = ramas.crear_director(practica, rama, adaptador=programa, todas=todas)
    t = d.ciclo(programa, create_default_engine().evaluate(practica, programa.capturar()), 0)
    print(json.dumps(t.como_dict(), ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("ramas").set_defaults(f=_ramas)
    sub.add_parser("perfiles").set_defaults(f=_perfiles)
    sub.add_parser("extensiones").set_defaults(f=_extensiones)
    t = sub.add_parser("turno")
    t.add_argument("practica")
    t.add_argument("--rama", default="blender-principiante")
    t.set_defaults(f=_turno)
    args = parser.parse_args(argv)
    return args.f(args)


if __name__ == "__main__":
    sys.exit(main())
