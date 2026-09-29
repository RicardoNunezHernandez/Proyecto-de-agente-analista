"""El banco de preguntas, de corrido.

    python -m app.lote --simulado
    python -m app.lote --desde P01 --hasta P05

Si una pregunta falla, registra el evento error y sigue con la siguiente.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from app.agente import preparar, responder

RUTA_PREGUNTAS = "data/preguntas_prueba.json"
PAUSA_SEGUNDOS = 4

# El banco lo entrega el docente; se lee sin asumir como se llaman las llaves.
_CLAVES_LISTA = ("preguntas", "banco", "items", "reactivos")
_CLAVES_ID = ("id", "clave", "identificador", "numero")
_CLAVES_TEXTO = ("pregunta", "texto", "enunciado", "question")


def leer_banco(ruta: str = RUTA_PREGUNTAS) -> list[tuple[str, str]]:
    """Devuelve [(id, pregunta), ...] del banco del docente."""
    crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))

    if isinstance(crudo, dict):
        for clave in _CLAVES_LISTA:
            if isinstance(crudo.get(clave), list):
                crudo = crudo[clave]
                break
        else:
            # {"P01": "texto", ...}
            return [(str(k), str(v)) for k, v in crudo.items() if isinstance(v, str)]

    if not isinstance(crudo, list):
        raise ValueError(f"{ruta} no trae una lista de preguntas")

    banco: list[tuple[str, str]] = []
    for posicion, renglon in enumerate(crudo, start=1):
        if isinstance(renglon, str):
            banco.append((f"P{posicion:02d}", renglon))
            continue
        if not isinstance(renglon, dict):
            continue
        identificador = next(
            (str(renglon[c]) for c in _CLAVES_ID if c in renglon), f"P{posicion:02d}"
        )
        texto = next((str(renglon[c]) for c in _CLAVES_TEXTO if c in renglon), "")
        if texto:
            banco.append((identificador, texto))
    if not banco:
        raise ValueError(f"{ruta} no trae preguntas legibles")
    return banco


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m app.lote", description="Corre el banco de preguntas del DENUE."
    )
    analizador.add_argument("--desde", default=None, help="identificador inicial, por ejemplo P01")
    analizador.add_argument("--hasta", default=None, help="identificador final, por ejemplo P05")
    analizador.add_argument("--simulado", action="store_true", help="usa el modelo simulado")
    argumentos = analizador.parse_args(argv)

    load_dotenv()
    try:
        banco = leer_banco()
        herramientas, sistema, llamar, bitacora = preparar(simulado=argumentos.simulado)
    except Exception as falla:
        print(f"No se pudo iniciar el lote: {falla}", file=sys.stderr)
        return 1

    seleccion = [
        (identificador, texto)
        for identificador, texto in banco
        if (argumentos.desde is None or identificador >= argumentos.desde)
        and (argumentos.hasta is None or identificador <= argumentos.hasta)
    ]
    if not seleccion:
        print("Ninguna pregunta cae en el rango pedido.", file=sys.stderr)
        return 1

    print(f"Bitácora: {bitacora.ruta}")
    print(f"Preguntas: {len(seleccion)} ({'simulado' if argumentos.simulado else bitacora.modelo})\n")

    fallas = 0
    for posicion, (identificador, pregunta) in enumerate(seleccion, start=1):
        bitacora.id_actual = identificador
        print(f"--- {identificador} · {pregunta}")
        try:
            fin = responder(pregunta, herramientas, sistema, llamar, bitacora)
            print(fin["respuesta"])
            print(
                f"[turnos: {fin['turnos']} | herramientas: {fin['herramientas']} | "
                f"segundos: {fin['segundos']} | cifras sin respaldo: {fin['cifras_sin_respaldo']}]\n"
            )
        except Exception as falla:
            fallas += 1
            bitacora.evento("error", error=f"{type(falla).__name__}: {falla}")
            print(f"[error: {type(falla).__name__}: {falla}]\n", file=sys.stderr)

        # Pausa solo entre preguntas reales, para no castigar la cuota.
        if not argumentos.simulado and posicion < len(seleccion):
            time.sleep(PAUSA_SEGUNDOS)

    print(f"Terminado: {len(seleccion) - fallas} respondidas, {fallas} con error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
