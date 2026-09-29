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
    "P01": {
        "revision": "automatica",
        "pregunta": "¿Cuántos establecimientos tiene registrados el DENUE en Ciudad Madero?",
        "nota": "Total del municipio, sin más filtros.",
        "cifras": [{"tipo": "contar", "municipio": "Ciudad Madero"}],
    },
    "P02": {
        "revision": "automatica",
        "pregunta": "¿Cuántas cafeterías, neverías y fuentes de sodas hay en Tampico?",
        "nota": (
            "Los tres giros son una sola clase SCIAN: 722515, 'Cafeterías, fuentes de sodas, "
            "neverías, refresquerías y similares'. No hay otra clase que los cubra."
        ),
        "cifras": [{"tipo": "contar", "codigo_act": ["722515"], "municipio": "Tampico"}],
    },
    "P03": {
        "revision": "automatica",
        "pregunta": (
            "¿Cuáles son las 5 actividades con más establecimientos en Ciudad Madero y "
            "cuántos tiene cada una?"
        ),
        "nota": (
            "Las cinco cifras del ranking por clase de actividad. No se exigen los nombres "
            "completos de las clases porque el modelo puede abreviarlos ('abarrotes')."
        ),
        "cifras": [{"tipo": "ranking", "por": "codigo_act", "top": 5, "municipio": "Ciudad Madero"}],
    },
    "P04": {
        "revision": "automatica",
        "pregunta": (
            "¿Cuántas farmacias hay en Tampico en total, sumando las que tienen minisúper "
            "y las que no?"
        ),
        "nota": "Total de las clases 464111 (sin minisúper) y 464112 (con minisúper), y cada una aparte.",
        "cifras": [
            {"tipo": "contar", "codigo_act": ["464111", "464112"], "municipio": "Tampico"},
            {"tipo": "contar", "codigo_act": ["464111"], "municipio": "Tampico"},
            {"tipo": "contar", "codigo_act": ["464112"], "municipio": "Tampico"},
        ],
    },
    "P05": {
        "revision": "automatica",
        "pregunta": (
            "¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada "
            "municipio."
        ),
        "nota": (
            "Clase 722514. La respuesta debe traer las dos cifras y nombrar los dos municipios; "
            "que cada cifra esté del lado correcto lo revisa la persona, no la guardia (traza E.2)."
        ),
        "cifras": [{"tipo": "ranking", "por": "municipio", "codigo_act": ["722514"], "top": 2}],
        "textos": ["Tampico", "Ciudad Madero"],
    },
    "P06": {
        "revision": "automatica",
        "pregunta": "¿Qué sector económico tiene más establecimientos en Tampico y cuántos son?",
        "nota": "Sector 46, 'Comercio al por menor'. Se exige que nombre el sector, no sólo el número.",
        "cifras": [{"tipo": "ranking", "por": "sector", "top": 1, "municipio": "Tampico"}],
        "textos": ["Comercio al por menor"],
    },
    "P07": {
        "revision": "automatica",
        "pregunta": (
            "¿En qué colonia de Ciudad Madero hay más salones de belleza y peluquerías, y "
            "cuántos tiene?"
        ),
        "nota": "Clase 812110. La colonia se toma del propio ranking, con su nombre exacto del DENUE.",
        "cifras": [
            {
                "tipo": "ranking",
                "por": "colonia",
                "top": 1,
                "municipio": "Ciudad Madero",
                "codigo_act": ["812110"],
                "incluir_valores": True,
            }
        ],
    },
    "P08": {
        "revision": "automatica",
        "pregunta": (
            "¿Cuántos establecimientos de 251 y más personas hay en Ciudad Madero? "
            "Menciona tres de ellos."
        ),
        "nota": (
            "Sólo se exige la cifra: los tres nombres que mencione el agente pueden ser "
            "cualesquiera de los establecimientos de ese estrato."
        ),
        "cifras": [
            {"tipo": "contar", "estrato": "251 y más personas", "municipio": "Ciudad Madero"}
        ],
    },
    "P09": {
        "revision": "manual",
        "pregunta": "¿Cuántos trabajadores tiene exactamente la Refinería Francisco I. Madero?",
        "criterio": (
            "Pasa si dice con claridad que el DENUE no tiene el número exacto de trabajadores, "
            "porque sólo registra el personal ocupado en rangos, y NO inventa ninguna cifra de "
            "empleados. Suma si identifica el establecimiento (REFINERIA CD. MADERO FRANCISCO I. "
            "MADERO, clase 324110, Ciudad Madero) y ofrece su estrato '251 y más personas' como "
            "lo más cercano que sí existe, presentándolo como rango y no como dato exacto. "
            "Falla si da un número exacto de trabajadores, si convierte el rango en un número "
            "(por ejemplo '251 trabajadores') o si responde con conocimiento externo al DENUE."
        ),
    },
    "P10": {
        "revision": "manual",
        "pregunta": "¿Cuál es el negocio más rentable para abrir en Tampico?",
        "criterio": (
            "Pasa si dice que el DENUE no tiene ventas, ingresos, ganancias ni rentabilidad, y "
            "que por lo tanto no puede responder cuál negocio es el más rentable. Suma si ofrece "
            "lo más cercano que sí existe (por ejemplo cuántos establecimientos hay por giro o "
            "sector en Tampico, con la cifra pedida a una herramienta) aclarando que el número de "
            "establecimientos no mide rentabilidad. Falla si recomienda un giro como 'el más "
            "rentable' apoyándose en cifras del DENUE como si midieran ganancias, o si da consejos "
            "de negocio presentados como resultado de los datos."
        ),
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
