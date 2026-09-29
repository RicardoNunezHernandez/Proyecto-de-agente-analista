"""Parte F - Las respuestas esperadas, calculadas con pandas y ANTES de la corrida.

    python -m evaluacion.calcular_esperadas

Este script NO importa nada de app/: si una herramienta tuviera un error, la
esperada tendría el mismo error y la evaluación no lo vería. Aquí se cuenta con
pandas directo, y por eso `normalizar` está escrito otra vez a propósito.

Cada pregunta del banco necesita su entrada en CALCULOS. Las que no la tengan
quedan con revision "pendiente" y el script termina con código 1, para que no se
confunda un archivo incompleto con uno terminado.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_PREGUNTAS = "data/preguntas_prueba.json"
RUTA_SALIDA = "evaluacion/esperadas.json"


def normalizar(texto: Any) -> str:
    """Copia deliberada de app.herramientas.normalizar: este script es independiente."""
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return " ".join(descompuesto.encode("ascii", "ignore").decode("ascii").lower().split())


# --------------------------------------------------------------------------- #
# Qué se calcula para cada pregunta del banco
#
# tipo "contar":  cifras = [total que cumple los filtros]
# tipo "ranking": cifras = [total de cada fila del top]; con incluir_valores=True
#                 agrega los nombres a textos_clave (por ejemplo la colonia)
#
# "pregunta" es el texto que se supuso al escribir el cálculo: si el banco del
# docente trae otro, el script avisa en vez de callarse.
# --------------------------------------------------------------------------- #

CALCULOS: dict[str, dict[str, Any]] = {
    "P04": {
        "revision": "automatica",
        "pregunta": (
            "¿Cuántas farmacias hay en Tampico en total, sumando las que tienen minisúper "
            "y las que no?"
        ),
        "nota": "Clases 464111 (sin minisúper) y 464112 (con minisúper).",
        "cifras": [
            {"tipo": "contar", "codigo_act": ["464111", "464112"], "municipio": "Tampico"},
            {"tipo": "contar", "codigo_act": ["464111"], "municipio": "Tampico"},
            {"tipo": "contar", "codigo_act": ["464112"], "municipio": "Tampico"},
        ],
    },
}


def filtrar(
    datos: pd.DataFrame,
    codigo_act: Any = None,
    municipio: str | None = None,
    sector: str | None = None,
    estrato: str | None = None,
    colonia: str | None = None,
) -> pd.DataFrame:
    """Los mismos filtros, con pandas directo y a mano."""
    marco = datos
    if codigo_act:
        codigos = [codigo_act] if isinstance(codigo_act, str) else list(codigo_act)
        mascara = pd.Series(False, index=marco.index)
        for codigo in codigos:
            mascara = mascara | marco["codigo_act"].str.startswith(str(codigo))
        marco = marco[mascara]
    if municipio:
        marco = marco[marco["municipio"].map(normalizar) == normalizar(municipio)]
    if sector:
        marco = marco[marco["sector"] == str(sector)]
    if estrato:
        marco = marco[marco["estrato"].map(normalizar) == normalizar(estrato)]
    if colonia:
        marco = marco[marco["colonia"].map(normalizar) == normalizar(colonia)]
    return marco


def calcular(datos: pd.DataFrame, especificacion: dict[str, Any]) -> tuple[list[int], list[str]]:
    """Devuelve (cifras_clave, textos_clave) de una especificación."""
    tipo = especificacion.get("tipo", "contar")
    filtros = {
        clave: valor
        for clave, valor in especificacion.items()
        if clave in ("codigo_act", "municipio", "sector", "estrato", "colonia")
    }
    marco = filtrar(datos, **filtros)

    if tipo == "contar":
        return [int(len(marco))], []

    if tipo == "ranking":
        campo = especificacion["por"]
        conteo = (
            marco.loc[marco[campo] != "", campo]
            .value_counts()
            .rename_axis("valor")
            .reset_index(name="total")
            .sort_values(["total", "valor"], ascending=[False, True])
            .head(int(especificacion.get("top", 5)))
        )
        cifras = [int(t) for t in conteo["total"]]
        textos = [str(v) for v in conteo["valor"]] if especificacion.get("incluir_valores") else []
        return cifras, textos

    raise ValueError(f"tipo de cálculo desconocido: {tipo}")


def leer_banco(ruta: str = RUTA_PREGUNTAS) -> list[tuple[str, str]]:
    crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(crudo, dict):
        for clave in ("preguntas", "banco", "items", "reactivos"):
            if isinstance(crudo.get(clave), list):
                crudo = crudo[clave]
                break
        else:
            return [(str(k), str(v)) for k, v in crudo.items() if isinstance(v, str)]
    banco: list[tuple[str, str]] = []
    for posicion, renglon in enumerate(crudo, start=1):
        if isinstance(renglon, str):
            banco.append((f"P{posicion:02d}", renglon))
        elif isinstance(renglon, dict):
            identificador = next(
                (str(renglon[c]) for c in ("id", "clave", "identificador") if c in renglon),
                f"P{posicion:02d}",
            )
            texto = next(
                (str(renglon[c]) for c in ("pregunta", "texto", "enunciado") if c in renglon), ""
            )
            banco.append((identificador, texto))
    return banco


def main() -> int:
    for ruta in (RUTA_DENUE, RUTA_PREGUNTAS):
        if not Path(ruta).exists():
            print(f"Falta {ruta}: copie el material del docente en data/", file=sys.stderr)
            return 1

    datos = pd.read_csv(RUTA_DENUE, dtype=str, keep_default_na=False)
    banco = leer_banco()
    print(f"Banco: {len(banco)} preguntas · DENUE: {len(datos)} establecimientos\n")

    esperadas: list[dict[str, Any]] = []
    pendientes: list[str] = []

    for identificador, texto in banco:
        receta = CALCULOS.get(identificador)
        if receta is None:
            pendientes.append(identificador)
            esperadas.append(
                {
                    "id": identificador,
                    "pregunta": texto,
                    "revision": "pendiente",
                    "nota": "falta escribir su cálculo en CALCULOS de este script",
                }
            )
            print(f"{identificador}  PENDIENTE  {texto}")
            continue

        supuesta = receta.get("pregunta")
        if supuesta and normalizar(supuesta) != normalizar(texto):
            print(
                f"{identificador}  AVISO: el banco dice otra cosa de la que se supuso.\n"
                f"          banco:   {texto}\n"
                f"          supuesta: {supuesta}",
                file=sys.stderr,
            )

        if receta["revision"] == "manual":
            esperadas.append(
                {
                    "id": identificador,
                    "pregunta": texto,
                    "revision": "manual",
                    "criterio": receta["criterio"],
                }
            )
            print(f"{identificador}  MANUAL     {receta['criterio']}")
            continue

        cifras: list[int] = []
        textos: list[str] = []
        for especificacion in receta.get("cifras", []):
            nuevas_cifras, nuevos_textos = calcular(datos, especificacion)
            cifras.extend(nuevas_cifras)
            textos.extend(nuevos_textos)
        textos.extend(receta.get("textos", []))

        renglon: dict[str, Any] = {
            "id": identificador,
            "pregunta": texto,
            "revision": "automatica",
            "cifras_clave": sorted(set(cifras)),
        }
        if textos:
            renglon["textos_clave"] = sorted(set(textos))
        if receta.get("nota"):
            renglon["nota"] = receta["nota"]
        esperadas.append(renglon)
        print(f"{identificador}  AUTOMÁTICA cifras={renglon['cifras_clave']} textos={textos}")

    Path(RUTA_SALIDA).parent.mkdir(parents=True, exist_ok=True)
    Path(RUTA_SALIDA).write_text(
        json.dumps({"esperadas": esperadas}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEscrito {RUTA_SALIDA}")

    if pendientes:
        print(
            f"\nFALTA: {len(pendientes)} preguntas sin cálculo ({', '.join(pendientes)}).\n"
            "Agrégueles su entrada en CALCULOS y verifique cada cifra a mano con pandas "
            "antes de la corrida real.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
