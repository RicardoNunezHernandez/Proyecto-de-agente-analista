"""Una pregunta desde la terminal.

    python -m app.cli "¿Cuántas farmacias hay en Tampico?"
    python -m app.cli "¿Cuántas farmacias hay en Tampico?" --simulado
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from app.agente import preparar, responder


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m app.cli", description="Pregunta al agente analista del DENUE."
    )
    analizador.add_argument("pregunta", help="la pregunta en español, entre comillas")
    analizador.add_argument(
        "--simulado", action="store_true", help="usa el modelo simulado: no gasta cuota"
    )
    argumentos = analizador.parse_args(argv)

    load_dotenv()
    try:
        herramientas, sistema, llamar, bitacora = preparar(
            simulado=argumentos.simulado, id_actual="CLI"
        )
        fin = responder(argumentos.pregunta, herramientas, sistema, llamar, bitacora)
    except Exception as falla:
        print(f"No se pudo responder: {falla}", file=sys.stderr)
        return 1

    print(fin["respuesta"])
    print(
        f"\n[turnos: {fin['turnos']} | herramientas: {fin['herramientas']} | "
        f"segundos: {fin['segundos']} | cifras sin respaldo: {fin['cifras_sin_respaldo']}]"
    )
    print(f"[bitácora: {bitacora.ruta}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
