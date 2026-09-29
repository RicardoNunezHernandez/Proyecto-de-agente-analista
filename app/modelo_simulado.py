"""Parte D - El modelo simulado: un guion fijo de cuatro pasos, sin red.

Sirve para desarrollar y probar el ciclo completo sin gastar cuota. Se invoca con
la misma firma que llamar_modelo y devuelve respuestas fabricadas del SDK, que se
comportan como las reales (function_calls, text y candidates funcionan).
"""

from __future__ import annotations

from typing import Any, Sequence

from google.genai import types

TEXTO_PASO_3 = "Respuesta: En Tampico hay 160 farmacias.\nDatos: DENUE 05/2026, INEGI"
TEXTO_PASO_4 = (
    "Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112)."
    "\nDatos: DENUE 05/2026, INEGI"
)
TEXTO_SIN_PRESUPUESTO = "Respuesta: No pude completar la consulta con el presupuesto."

PASOS = 4


def respuesta_falsa(partes: Sequence[types.Part]) -> types.GenerateContentResponse:
    """Una respuesta del SDK fabricada a mano."""
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(partes)))]
    )


def _peticion(identificador: str, nombre: str, argumentos: dict[str, Any]) -> types.Part:
    return types.Part(
        function_call=types.FunctionCall(id=identificador, name=nombre, args=argumentos)
    )


class ModeloSimulado:
    """Invocable con la misma firma que llamar_modelo.

    Avanza un paso en cada llamada y vuelve al inicio despues del cuarto:

    1. pide buscar_actividades(texto="farmacia")            id "sim-1"
    2. pide contar(codigo_act="464111,464112", municipio="Tampico")  id "sim-2"
    3. texto con una cifra inventada (160): la guardia debe detenerla
    4. texto corregido (154), el que si viene de la herramienta

    Si forzar_texto es verdadero y el paso que toca es una peticion, devuelve en su
    lugar el texto de presupuesto agotado (y de todos modos avanza un paso).
    """

    def __init__(self) -> None:
        self.paso = 0

    def __call__(
        self,
        historial: Sequence[Any],
        sistema: str,
        declaraciones: list[dict[str, Any]],
        forzar_texto: bool = False,
    ) -> types.GenerateContentResponse:
        self.paso = self.paso % PASOS + 1
        paso = self.paso

        if paso == 1:
            if forzar_texto:
                return respuesta_falsa([types.Part(text=TEXTO_SIN_PRESUPUESTO)])
            return respuesta_falsa([_peticion("sim-1", "buscar_actividades", {"texto": "farmacia"})])

        if paso == 2:
            if forzar_texto:
                return respuesta_falsa([types.Part(text=TEXTO_SIN_PRESUPUESTO)])
            return respuesta_falsa(
                [
                    _peticion(
                        "sim-2",
                        "contar",
                        {"codigo_act": "464111,464112", "municipio": "Tampico"},
                    )
                ]
            )

        if paso == 3:
            return respuesta_falsa([types.Part(text=TEXTO_PASO_3)])

        return respuesta_falsa([types.Part(text=TEXTO_PASO_4)])
