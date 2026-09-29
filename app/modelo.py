"""Parte B - El unico archivo que habla con Gemini.

Aqui se crea el cliente del SDK google-genai y se arman los mensajes del historial.
La ejecucion automatica de herramientas queda DESACTIVADA: el modelo solo pide, y
el ciclo de app/agente.py decide que hacer.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

from google import genai
from google.genai import types

MODELO_OMISION = "gemini-3.6-flash"

_cliente: genai.Client | None = None


def modelo_en_uso() -> str:
    """El identificador del modelo, tomado del .env."""
    return os.environ.get("GEMINI_MODEL", "").strip() or MODELO_OMISION


def _obtener_cliente() -> genai.Client:
    """Crea el cliente una sola vez, con reintentos ante fallas de red."""
    global _cliente
    if _cliente is None:
        clave = os.environ.get("GEMINI_API_KEY", "").strip()
        if not clave:
            raise RuntimeError(
                "falta GEMINI_API_KEY: copie .env.example a .env y ponga su clave de Google AI Studio"
            )
        _cliente = genai.Client(
            api_key=clave,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0)
            ),
        )
    return _cliente


def llamar_modelo(
    historial: Sequence[Any],
    sistema: str,
    declaraciones: list[dict[str, Any]],
    forzar_texto: bool = False,
) -> types.GenerateContentResponse:
    """Una llamada al modelo. Devuelve la respuesta del SDK tal cual.

    forzar_texto=True usa el modo NONE, que le prohibe al modelo pedir
    herramientas: es el cierre forzado del ciclo.
    """
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        tools=[types.Tool(function_declarations=declaraciones)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="NONE" if forzar_texto else "AUTO"
            )
        ),
    )
    return _obtener_cliente().models.generate_content(
        model=modelo_en_uso(), contents=list(historial), config=config
    )


# --------------------------------------------------------------------------- #
# Armado del historial (lo usa el ciclo, para no esparcir types por el proyecto)
# --------------------------------------------------------------------------- #

def mensaje_usuario(texto: str) -> types.Content:
    """Un mensaje de usuario: la pregunta o la correccion de la guardia."""
    return types.Content(role="user", parts=[types.Part(text=texto)])


def mensaje_respuestas(peticiones: Sequence[Any], resultados: Sequence[dict]) -> types.Content:
    """UN mensaje de usuario con todas las function_response del turno.

    Cada resultado lleva el MISMO id que la peticion que responde, incluidas las
    rechazadas por presupuesto.
    """
    partes = [
        types.Part(
            function_response=types.FunctionResponse(
                id=peticion.id, name=peticion.name, response=resultado
            )
        )
        for peticion, resultado in zip(peticiones, resultados)
    ]
    return types.Content(role="user", parts=partes)


def contenido_del_modelo(respuesta: Any) -> Any:
    """El turno del modelo TAL COMO LLEGO, para reenviarlo en el historial.

    No se reconstruye a mano: trae firmas internas que Gemini exige de vuelta.
    """
    candidatos = getattr(respuesta, "candidates", None) or []
    if not candidatos:
        return types.Content(role="model", parts=[])
    return candidatos[0].content


def tokens_entrada(respuesta: Any) -> int | None:
    """Tokens de entrada, si el SDK los informo (el simulado no los trae)."""
    metadatos = getattr(respuesta, "usage_metadata", None)
    if metadatos is None:
        return None
    return getattr(metadatos, "prompt_token_count", None)
