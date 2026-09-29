"""Parte C - La guardia de cifras.

El prompt pide que el modelo no calcule; esta guardia lo comprueba con codigo.
Cada cifra de la respuesta debe aparecer en la pregunta o en los resultados de las
herramientas de esa misma pregunta. Si no aparece, la guardia la senala: no oculta
nada, avisa.
"""

from __future__ import annotations

import re
from typing import Any

# Marca de lista al inicio de un renglon: "1. ", "2) ". Se borra antes de buscar
# cifras para que el numero del inciso no cuente como dato.
_MARCA_DE_LISTA = re.compile(r"^[ \t]*\d+[.)]\s+", re.MULTILINE)

# Enteros, enteros con comas de miles y decimales con punto: 7,184 / 5.5 / 05
_CIFRA = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _a_numero(bruto: str) -> int | float:
    """'7,184' -> 7184; '5.5' -> 5.5; '05' -> 5; '5.0' -> 5."""
    valor = float(bruto.replace(",", ""))
    entero = int(valor)
    return entero if valor == entero else valor


def numeros(texto: Any) -> set[int | float]:
    """Conjunto de cifras de un texto, ya como numeros."""
    if texto is None:
        return set()
    if not isinstance(texto, str):
        texto = str(texto)
    limpio = _MARCA_DE_LISTA.sub("", texto)
    return {_a_numero(bruto) for bruto in _CIFRA.findall(limpio)}


def numeros_en(objeto: Any) -> set[int | float]:
    """Todas las cifras de una estructura anidada (diccionarios, listas, textos).

    Los numeros de Python se tratan como su texto. True, False y None no aportan
    cifras. Las llaves de los diccionarios no cuentan: solo sus valores.
    """
    encontrados: set[int | float] = set()
    _juntar(objeto, encontrados)
    return encontrados


def _juntar(objeto: Any, acumulado: set[int | float]) -> None:
    if objeto is None or isinstance(objeto, bool):
        return
    if isinstance(objeto, (int, float)):
        acumulado |= numeros(str(objeto))
        return
    if isinstance(objeto, str):
        acumulado |= numeros(objeto)
        return
    if isinstance(objeto, dict):
        for valor in objeto.values():
            _juntar(valor, acumulado)
        return
    if isinstance(objeto, (list, tuple, set, frozenset)):
        for elemento in objeto:
            _juntar(elemento, acumulado)
        return
    acumulado |= numeros(str(objeto))


def cifras_sin_respaldo(
    respuesta: Any, pregunta: Any, resultados: Any
) -> list[int | float]:
    """Cifras de la respuesta que no estan ni en la pregunta ni en los resultados."""
    respaldo = numeros(pregunta) | numeros_en(resultados)
    return sorted(numeros(respuesta) - respaldo)


def _lista_legible(cifras: list[int | float]) -> str:
    return "[" + ", ".join(str(c) for c in cifras) + "]"


def mensaje_correccion(cifras: list[int | float]) -> str:
    """El mensaje de usuario de la seccion 8.3: la unica oportunidad de corregir."""
    return (
        "Revisión automática: estas cifras de tu respuesta no aparecen en la pregunta ni en "
        f"los resultados de las herramientas: {_lista_legible(cifras)}. No calcules sumas ni "
        "porcentajes: si necesitas un total, pídelo a una herramienta. Corrige la respuesta."
    )


def aviso(cifras: list[int | float]) -> str:
    """El aviso que se pega a la respuesta cuando el modelo insiste."""
    return f"[Aviso] Cifras sin respaldo en los datos: {_lista_legible(cifras)}"
