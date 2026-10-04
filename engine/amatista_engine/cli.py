"""Herramientas de autor en la terminal (motor v3).

    python engine/herramientas/practicas.py nueva blender.bp.m4.mi-practica --plantilla materiales \\
           --titulo "Mi práctica" --curso blender_principiante --modulo 4
    python engine/herramientas/practicas.py revisar            # compila y revisa la pedagogía de todas
    python engine/herramientas/practicas.py probar             # corre los casos de pruebas.json
    python engine/herramientas/practicas.py simular practices/blender/principiante/m1-tren
    python engine/herramientas/practicas.py validadores --md docs/motor/referencia/09_validadores.md
    python engine/herramientas/practicas.py plan               # mapa del plan de estudios

Una práctica vive en una carpeta: practica.json (la práctica) y
pruebas.json (escenas de prueba y lo que debe pasar con cada una). Así un
cambio en la práctica se comprueba en segundos, sin abrir Blender, y CI lo
repite en cada push. Sale con código 1 si algo falla.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__, create_default_engine
from .curriculum import load_curriculum, unlock_state
from .errors import InvalidPracticeError
from .guide import build_guidance
from .practice import compile_practice, parse_practice
from .practice.templates import PLANTILLAS, nueva_practica, nuevas_pruebas
from .testing import escena_de_caso

RAIZ = Path(__file__).resolve().parents[2]
PRACTICAS = RAIZ / "practices" / "blender"
ARCHIVO = "practica.json"
PRUEBAS = "pruebas.json"
CURSOS = PRACTICAS / "cursos.json"

VERDE, ROJO, AMARILLO, GRIS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"


def _color(texto: str, color: str) -> str:
    return f"{color}{texto}{FIN}" if sys.stdout.isatty() else texto


def _carpetas(rutas: Sequence[str]) -> List[Path]:
    """Carpetas de práctica a partir de rutas (carpeta o practica.json) o todas las del repositorio."""
    if not rutas:
        return sorted(p.parent for p in PRACTICAS.rglob(ARCHIVO))
    salida = []
    for ruta in rutas:
        p = Path(ruta)
        salida.append(p.parent if p.is_file() else p)
    return salida


def _leer(ruta: Path) -> Any:
    return json.loads(ruta.read_text(encoding="utf-8"))


# --- revisar ------------------------------------------------------------------------------


def revisar(rutas: Sequence[str]) -> int:
    motor = create_default_engine()
    errores_totales = 0
    for carpeta in _carpetas(rutas):
        archivo = carpeta / ARCHIVO
        try:
            datos = _leer(archivo)
        except (OSError, ValueError) as error:
            print(_color(f"✗ {archivo}: {error}", ROJO))
            errores_totales += 1
            continue
        resultado = compile_practice(datos, motor.registry, motor.tools)
        nombre = datos.get("id", carpeta.name) if isinstance(datos, dict) else carpeta.name
        if resultado.ok:
            p = resultado.practice
            print(_color(f"✓ {nombre}", VERDE) + _color(
                f"  {len(p.targets)} objetivos · {len(p.guards)} vigilantes · {len(p.pills)} píldoras", GRIS))
        else:
            print(_color(f"✗ {nombre}", ROJO))
        for error in resultado.errors:
            print(_color(f"    error: {error}", ROJO))
        for aviso in resultado.warnings:
            print(_color(f"    aviso: {aviso}", AMARILLO))
        for pildora in (datos.get("pills") or []) if isinstance(datos, dict) else []:
            visual = str(pildora.get("visual") or "")
            if visual.startswith("image:") and not (carpeta / visual[6:]).exists():
                print(_color(f"    error: la píldora {pildora.get('id')} usa {visual[6:]}, que no está en la carpeta", ROJO))
                errores_totales += 1
        if not (carpeta / PRUEBAS).exists():
            print(_color(f"    aviso: no hay {PRUEBAS}: crea al menos la escena vacía y la solución", AMARILLO))
        errores_totales += len(resultado.errors)
    return 1 if errores_totales else 0


# --- probar -------------------------------------------------------------------------------


def comprobar_caso(motor, practica, caso: Dict[str, Any]) -> List[str]:
    """Fallas de un caso de pruebas.json (lista vacía si cumple lo esperado)."""
    escena = escena_de_caso(caso)
    reporte = motor.evaluate(practica, escena)
    guia = build_guidance(practica, escena, reporte)
    espera = caso.get("espera") or {}
    fallas = []
    if "completada" in espera and reporte.completed != espera["completada"]:
        fallas.append(f"completada = {reporte.completed} (se esperaba {espera['completada']})")
    if "progreso_min" in espera and reporte.progress < espera["progreso_min"]:
        fallas.append(f"progreso = {reporte.progress:.0f} (se esperaba al menos {espera['progreso_min']})")
    if "progreso_max" in espera and reporte.progress > espera["progreso_max"]:
        fallas.append(f"progreso = {reporte.progress:.0f} (se esperaba como máximo {espera['progreso_max']})")
    if "actual" in espera and reporte.current_target_id != espera["actual"]:
        fallas.append(f"paso actual = {reporte.current_target_id} (se esperaba {espera['actual']})")
    if "pausa" in espera and reporte.paused_by != espera["pausa"]:
        fallas.append(f"pausa = {reporte.paused_by} (se esperaba {espera['pausa']})")
    if "accion" in espera:
        accion = guia.action.kind if guia.action else None
        if accion != espera["accion"]:
            fallas.append(f"«Hazlo conmigo» = {accion} (se esperaba {espera['accion']})")
    if "pildoras" in espera:
        ids = [p.id for p in motor.pills(practica, escena, reporte)]
        faltan = [p for p in espera["pildoras"] if p not in ids]
        if faltan:
            fallas.append(f"no aparecen las píldoras {faltan} (aparecen {ids})")
    if "mensaje_contiene" in espera and espera["mensaje_contiene"].lower() not in guia.feedback.lower():
        fallas.append(f"el mensaje «{guia.feedback}» no dice «{espera['mensaje_contiene']}»")
    for r in reporte.results + reporte.guards:
        if r.passed is None:
            fallas.append(f"«{r.target_id}» no se pudo evaluar: {r.message}")
    return fallas


def probar(rutas: Sequence[str], detalle: bool = False) -> int:
    motor = create_default_engine()
    total = fallidos = 0
    for carpeta in _carpetas(rutas):
        try:
            practica = parse_practice(_leer(carpeta / ARCHIVO))
        except (OSError, ValueError, InvalidPracticeError) as error:
            print(_color(f"✗ {carpeta}: {error}", ROJO))
            fallidos += 1
            continue
        archivo = carpeta / PRUEBAS
        if not archivo.exists():
            print(_color(f"· {practica.id}: sin {PRUEBAS}", AMARILLO))
            continue
        pruebas = _leer(archivo)
        if pruebas.get("practica") != practica.id:
            print(_color(f"✗ {archivo}: «practica» debe ser {practica.id}", ROJO))
            fallidos += 1
            continue
        print(practica.id)
        for caso in pruebas.get("casos") or []:
            total += 1
            try:
                fallas = comprobar_caso(motor, practica, caso)
            except (ValueError, KeyError, TypeError, InvalidPracticeError) as error:
                fallas = [f"la escena de prueba no es válida: {error}"]
            if fallas:
                fallidos += 1
                print(_color(f"  ✗ {caso.get('nombre')}", ROJO))
                for falla in fallas:
                    print(_color(f"      {falla}", ROJO))
            else:
                print(_color(f"  ✓ {caso.get('nombre')}", VERDE))
            if detalle:
                _tabla(motor, practica, escena_de_caso(caso))
    print(f"{total - fallidos} de {total} casos correctos")
    return 1 if fallidos else 0


# --- simular ------------------------------------------------------------------------------


def _tabla(motor, practica, escena) -> None:
    reporte = motor.evaluate(practica, escena)
    guia = build_guidance(practica, escena, reporte)
    print(_color(f"    progreso {reporte.progress:.0f} % · completada {reporte.completed}"
                 + (f" · EN PAUSA por {reporte.paused_by}" if reporte.paused else ""), GRIS))
    for paso in reporte.steps:
        r = reporte.result(paso.target_id)
        marca = {"completado": "✓", "actual": "▶", "bloqueado": "🔒"}.get(paso.status, "·")
        print(f"    {marca} {paso.title:<34} {r.message}")
    for g in reporte.guards:
        print(f"    {'✓' if g.passed else '⚠'} vigilante {g.target_id:<22} {g.message}")
    print(_color(f"    guía: {guia.title} — {guia.feedback}", GRIS))
    for i in guia.instructions:
        print(_color(f"      [{' '.join(i.keys)}] {i.text}", GRIS))
    if guia.action:
        print(_color(f"      Hazlo conmigo: {guia.action.kind} «{guia.action.label}»", GRIS))
    pildoras = motor.pills(practica, escena, reporte)
    if pildoras:
        print(_color(f"    píldoras ahora: {', '.join(p.id for p in pildoras)}", GRIS))


def simular(ruta: str, escena: Optional[str]) -> int:
    motor = create_default_engine()
    carpeta = _carpetas([ruta])[0]
    practica = parse_practice(_leer(carpeta / ARCHIVO))
    if escena:
        datos = _leer(Path(escena))
        casos = [{"nombre": Path(escena).name, **({"escena": datos} if "objetos" in datos else datos)}]
    else:
        casos = (_leer(carpeta / PRUEBAS).get("casos") or []) if (carpeta / PRUEBAS).exists() else []
    for caso in casos:
        print(caso.get("nombre"))
        _tabla(motor, practica, escena_de_caso(caso))
    return 0


# --- nueva --------------------------------------------------------------------------------


def nueva(practica_id: str, plantilla: str, titulo: str, curso: str, modulo: int, carpeta: Optional[str]) -> int:
    destino = Path(carpeta) if carpeta else PRACTICAS / (curso.replace("blender_", "").replace("_", "-") or "otras") / (
        practica_id.split(".")[-1]
    )
    if (destino / ARCHIVO).exists():
        print(_color(f"Ya existe {destino / ARCHIVO}: no se sobrescribe.", ROJO))
        return 1
    datos = nueva_practica(practica_id, plantilla, titulo, curso, modulo)
    resultado = compile_practice(datos)
    if not resultado.ok:
        print(_color("La plantilla no compila (avisa al equipo del motor):", ROJO))
        for error in resultado.errors:
            print(f"  {error}")
        return 1
    destino.mkdir(parents=True, exist_ok=True)
    (destino / ARCHIVO).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / PRUEBAS).write_text(
        json.dumps(nuevas_pruebas(practica_id, plantilla), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(_color(f"✓ Creada {destino / ARCHIVO} (plantilla {plantilla}) y {destino / PRUEBAS}", VERDE))
    print("  Siguiente: edita los textos, agrega el caso «Solución» a pruebas.json y corre «probar».")
    return 0


# --- validadores y plan -------------------------------------------------------------------


def validadores(md: Optional[str]) -> int:
    motor = create_default_engine()
    specs = motor.registry.specs()
    if not md:
        categoria = None
        for spec in sorted(specs, key=lambda s: (s.category, s.id)):
            if spec.category != categoria:
                categoria = spec.category
                print(_color(f"\n{categoria.upper()}", GRIS))
            params = ", ".join(p.name + ("*" if p.required else "") for p in spec.params)
            print(f"  {spec.id:<24} {spec.label} — {spec.description}")
            if params:
                print(_color(f"  {'':<24} params: {params}", GRIS))
        return 0
    lineas = [
        "# Catálogo de validadores",
        "",
        f"Generado con `python engine/herramientas/practicas.py validadores --md` (Amatista Engine {__version__}). "
        "No se edita a mano: cambia la descripción en `engine/amatista_engine/validators/builtin.py` y vuelve a generarlo.",
        "",
        "Los validadores que aceptan **selector** (`role`, `name`, `name_prefix`, `type`, `tag`, `collection`, "
        "`primitive`) se aplican a los objetos que cumplen todos los criterios; sin selector, a todos.",
        "",
    ]
    categoria = None
    for spec in sorted(specs, key=lambda s: (s.category, s.id)):
        if spec.category != categoria:
            categoria = spec.category
            lineas += [f"## {categoria.capitalize()}", ""]
        lineas += [f"### `{spec.id}` — {spec.label}", "", spec.description, ""]
        if spec.params:
            lineas += ["| Parámetro | Tipo | Qué es | Obligatorio | Por defecto |", "|---|---|---|---|---|"]
            for p in spec.params:
                defecto = "" if p.default is None else f"`{p.default}`"
                lineas.append(f"| `{p.name}` | {p.kind} | {p.label} | {'sí' if p.required else ''} | {defecto} |")
            lineas.append("")
        lineas += [f"Se vuelve a revisar con: {', '.join(spec.watch)}.", ""]
    Path(md).write_text("\n".join(lineas), encoding="utf-8")
    print(_color(f"✓ Escrito {md} ({len(specs)} validadores)", VERDE))
    return 0


def plan(completadas: Sequence[str]) -> int:
    curriculo = load_curriculum(_leer(CURSOS))
    estado = unlock_state(curriculo, completadas)
    print(curriculo.title)
    for curso in curriculo.courses:
        print(f"  {curso.title} [{curso.difficulty}, {curso.status}]")
        for m in curso.modules:
            marca = {"completado": "✓", "disponible": "▶", "bloqueado": "🔒", "proximamente": "…"}.get(
                estado.get(m.practice, ""), "·")
            print(f"    {marca} Módulo {m.number}: {m.title}" + (f"  ({m.practice})" if m.practice else ""))
    problemas = revisar_plan(curriculo)
    for problema in problemas:
        print(_color(f"  error: {problema}", ROJO))
    return 1 if problemas else 0


def revisar_plan(curriculo) -> List[str]:
    """Cada módulo del plan apunta a una práctica que existe y que dice estar en ese curso y módulo."""
    practicas: Dict[str, Dict[str, Any]] = {}
    for archivo in sorted(PRACTICAS.rglob(ARCHIVO)):
        datos = _leer(archivo)
        if isinstance(datos, dict) and "id" in datos:
            practicas[datos["id"]] = datos
    problemas = []
    for curso in curriculo.courses:
        for m in curso.modules:
            if not m.practice:
                continue
            datos = practicas.get(m.practice)
            if datos is None:
                problemas.append(f"{curso.id} módulo {m.number}: no existe la práctica {m.practice}")
                continue
            lugar = datos.get("course") or {}
            if lugar.get("id") != curso.id or lugar.get("module") != m.number:
                problemas.append(f"{m.practice}: su «course» dice {lugar.get('id')} módulo {lugar.get('module')}, "
                                 f"pero cursos.json la pone en {curso.id} módulo {m.number}")
    return problemas


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="practicas", description="Herramientas de autor de Amatista Engine")
    sub = parser.add_subparsers(dest="comando", required=True)
    n = sub.add_parser("nueva", help="crea una práctica desde una plantilla")
    n.add_argument("id")
    n.add_argument("--plantilla", choices=sorted(PLANTILLAS), default="vacia")
    n.add_argument("--titulo", default="Nueva práctica")
    n.add_argument("--curso", default="blender_principiante")
    n.add_argument("--modulo", type=int, default=1)
    n.add_argument("--carpeta")
    r = sub.add_parser("revisar", help="compila y revisa la pedagogía")
    r.add_argument("rutas", nargs="*")
    p = sub.add_parser("probar", help="corre los casos de pruebas.json")
    p.add_argument("rutas", nargs="*")
    p.add_argument("--detalle", action="store_true")
    s = sub.add_parser("simular", help="muestra paso a paso qué ve el alumno")
    s.add_argument("ruta")
    s.add_argument("--escena", help="foto exportada desde el add-on o archivo con «construir»")
    v = sub.add_parser("validadores", help="catálogo de validadores")
    v.add_argument("--md", help="escribe el catálogo en Markdown")
    pl = sub.add_parser("plan", help="mapa del plan de estudios")
    pl.add_argument("--completadas", nargs="*", default=[])
    a = parser.parse_args(argv)
    if a.comando == "nueva":
        return nueva(a.id, a.plantilla, a.titulo, a.curso, a.modulo, a.carpeta)
    if a.comando == "revisar":
        return revisar(a.rutas)
    if a.comando == "probar":
        return probar(a.rutas, a.detalle)
    if a.comando == "simular":
        return simular(a.ruta, a.escena)
    if a.comando == "validadores":
        return validadores(a.md)
    return plan(a.completadas)


if __name__ == "__main__":
    sys.exit(main())
