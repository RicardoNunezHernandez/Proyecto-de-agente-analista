"""Parte F - Compara las respuestas del agente con las esperadas.

    python -m app.evaluar logs/corrida-A.jsonl [logs/corrida-B.jsonl ...]

Toma de las bitácoras el último evento fin REAL de cada pregunta (las corridas con
el modelo simulado se ignoran), lo compara con evaluacion/esperadas.json, imprime
una tabla y escribe evaluacion/resultados.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.agente import MARCA_SIMULADO
from app.guardia import numeros
from app.herramientas import normalizar

RUTA_ESPERADAS = "evaluacion/esperadas.json"
RUTA_RESULTADOS = "evaluacion/resultados.json"


def leer_esperadas(ruta: str = RUTA_ESPERADAS) -> dict[str, dict[str, Any]]:
    crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    lista = crudo.get("esperadas", crudo) if isinstance(crudo, dict) else crudo
    return {str(e["id"]): e for e in lista}


def leer_bitacoras(rutas: list[str]) -> tuple[dict[str, dict], dict[str, str], list[str]]:
    """Devuelve (último fin real por pregunta, pregunta por id, corridas leídas)."""
    finales: dict[str, dict] = {}
    preguntas: dict[str, str] = {}
    corridas: list[str] = []
    for ruta in rutas:
        for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if registro.get("modelo") == MARCA_SIMULADO:
                continue  # el simulado no cuenta como corrida real
            corrida = registro.get("corrida")
            if corrida and corrida not in corridas:
                corridas.append(corrida)
            identificador = str(registro.get("id", ""))
            if registro.get("evento") == "inicio":
                preguntas[identificador] = registro.get("pregunta", "")
            elif registro.get("evento") == "fin":
                finales[identificador] = registro
    return finales, preguntas, corridas


def evaluar_una(esperada: dict[str, Any], final: dict | None) -> dict[str, Any]:
    """Aplica el criterio automático, o deja constancia de la revisión manual."""
    revision = str(esperada.get("revision", "automatica"))
    salida: dict[str, Any] = {
        "id": str(esperada["id"]),
        "revision": revision,
        "turnos": final.get("turnos") if final else None,
        "herramientas": final.get("herramientas") if final else None,
        "cifras_sin_respaldo": final.get("cifras_sin_respaldo") if final else None,
        "respuesta": final.get("respuesta", "") if final else "",
    }

    if revision != "automatica":
        salida["criterio"] = esperada.get("criterio", "")

    if final is None:
        salida["resultado"] = "SIN CORRIDA"
        return salida

    if revision != "automatica":
        salida["resultado"] = "MANUAL"
        return salida

    respuesta = final.get("respuesta", "")
    cifras_respuesta = numeros(respuesta)
    faltan_cifras = [c for c in esperada.get("cifras_clave", []) if c not in cifras_respuesta]

    respuesta_norm = normalizar(respuesta)
    faltan_textos = [
        t for t in esperada.get("textos_clave", []) if normalizar(t) not in respuesta_norm
    ]

    salida["cifras_faltantes"] = faltan_cifras
    salida["textos_faltantes"] = faltan_textos
    salida["resultado"] = "PASA" if not faltan_cifras and not faltan_textos else "FALLA"
    return salida


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m app.evaluar", description="Evalúa las corridas reales del agente."
    )
    analizador.add_argument("bitacoras", nargs="+", help="uno o más logs/corrida-*.jsonl")
    argumentos = analizador.parse_args(argv)

    try:
        esperadas = leer_esperadas()
    except FileNotFoundError:
        print(
            f"Falta {RUTA_ESPERADAS}: corra primero python -m evaluacion.calcular_esperadas",
            file=sys.stderr,
        )
        return 1

    finales, preguntas, corridas = leer_bitacoras(argumentos.bitacoras)

    resultados = [
        evaluar_una(esperadas[identificador], finales.get(identificador))
        for identificador in sorted(esperadas)
    ]

    ancho = max([len(str(r["id"])) for r in resultados] + [2])
    print(f"{'ID'.ljust(ancho)}  RESULTADO   TURNOS  HERR  SIN RESPALDO  FALTANTES")
    for r in resultados:
        faltantes = ""
        if r["resultado"] == "FALLA":
            partes = []
            if r.get("cifras_faltantes"):
                partes.append(f"cifras {r['cifras_faltantes']}")
            if r.get("textos_faltantes"):
                partes.append(f"textos {r['textos_faltantes']}")
            faltantes = "; ".join(partes)
        print(
            f"{str(r['id']).ljust(ancho)}  {r['resultado']:<10}  "
            f"{str(r['turnos'] or '-'):>6}  {str(r['herramientas'] or '-'):>4}  "
            f"{str(r['cifras_sin_respaldo'] if r['cifras_sin_respaldo'] is not None else '-'):>12}  {faltantes}"
        )

    automaticas = [r for r in resultados if r["revision"] == "automatica"]
    aprobadas = [r for r in automaticas if r["resultado"] == "PASA"]
    manuales = [r for r in resultados if r["revision"] != "automatica"]

    print(f"\nAutomáticas aprobadas: {len(aprobadas)} de {len(automaticas)}")
    print(f"Manuales (su juicio):  {len(manuales)}")
    for r in manuales:
        print(f"\n  {r['id']} · criterio: {r.get('criterio', '')}")
        print(f"  respuesta: {r['respuesta'][:400]}")

    salida = {
        "corridas": corridas,
        "bitacoras": list(argumentos.bitacoras),
        "totales": {
            "automaticas": len(automaticas),
            "automaticas_aprobadas": len(aprobadas),
            "manuales": len(manuales),
            "sin_corrida": len([r for r in resultados if r["resultado"] == "SIN CORRIDA"]),
        },
        "resultados": [{**r, "pregunta": preguntas.get(str(r["id"]), "")} for r in resultados],
    }
    Path(RUTA_RESULTADOS).parent.mkdir(parents=True, exist_ok=True)
    Path(RUTA_RESULTADOS).write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEscrito {RUTA_RESULTADOS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
