"""Parte B - El ciclo del agente: percibir, decidir, actuar, observar.

El ciclo es de este archivo, no del SDK. El modelo solo pide herramientas; aqui se
ejecutan con presupuesto, se registran en la bitacora y se le devuelven con el
mismo id. Al final, la guardia revisa las cifras antes de entregar la respuesta.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.guardia import aviso, cifras_sin_respaldo, mensaje_correccion
from app.herramientas import DECLARACIONES, Herramientas, cargar_datos
from app.modelo import contenido_del_modelo, mensaje_respuestas, mensaje_usuario, tokens_entrada

MAX_TURNOS = 5
MAX_HERRAMIENTAS = 6

HERRAMIENTAS_VALIDAS: tuple[str, ...] = ("buscar_actividades", "contar", "ranking", "listar")

RUTA_DENUE = "data/denue_tampico_madero.csv"
RUTA_SECTORES = "data/sectores_scian.csv"
RUTA_SISTEMA = "prompts/sistema.md"

MARCA_SIMULADO = "simulado"


# --------------------------------------------------------------------------- #
# Bitacora
# --------------------------------------------------------------------------- #

class Bitacora:
    """Una linea JSON por evento en logs/corrida-AAAAMMDD-HHMMSS.jsonl.

    id_actual identifica la pregunta (P01, TG-3, CLI) y contexto agrega campos
    fijos al evento inicio (por ejemplo el canal de Telegram y el usuario anonimo).
    Con ruta=None no escribe archivo: asi las pruebas revisan los eventos en memoria.
    """

    def __init__(
        self,
        modelo: str,
        carpeta: str = "logs",
        ruta: str | Path | None = "",
        id_actual: str = "CLI",
    ) -> None:
        self.corrida = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.modelo = modelo
        self.id_actual = id_actual
        self.contexto: dict[str, Any] = {}
        self.eventos: list[dict[str, Any]] = []
        if ruta == "":
            self.ruta: Path | None = Path(carpeta) / f"corrida-{self.corrida}.jsonl"
        else:
            self.ruta = Path(ruta) if ruta is not None else None

    def evento(self, evento: str, **campos: Any) -> dict[str, Any]:
        linea = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "corrida": self.corrida,
            "modelo": self.modelo,
            "id": self.id_actual,
            "evento": evento,
            **campos,
        }
        self.eventos.append(linea)
        if self.ruta is not None:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ruta, "a", encoding="utf-8") as archivo:
                archivo.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")
        return linea

    def nombres_de_eventos(self) -> list[str]:
        """La secuencia de eventos, para las pruebas y la traza."""
        return [e["evento"] for e in self.eventos]


# --------------------------------------------------------------------------- #
# ejecutar: ninguna excepcion llega al modelo
# --------------------------------------------------------------------------- #

def ejecutar(herramientas: Herramientas, nombre: str, args: Any) -> dict[str, Any]:
    """Ejecuta una herramienta pedida por el modelo. NUNCA lanza excepciones.

    Nunca usa eval ni exec: solo puede llamar a las cuatro herramientas declaradas.
    """
    if nombre not in HERRAMIENTAS_VALIDAS:
        return {
            "ok": False,
            "error": f"herramienta inexistente: {nombre}",
            "valores_validos": list(HERRAMIENTAS_VALIDAS),
        }

    metodo = getattr(herramientas, nombre, None)
    if not callable(metodo):
        return {
            "ok": False,
            "error": f"herramienta inexistente: {nombre}",
            "valores_validos": list(HERRAMIENTAS_VALIDAS),
        }

    if args is None:
        args = {}
    if not isinstance(args, dict):
        return {
            "ok": False,
            "error": f"los argumentos de {nombre} deben ser un objeto con nombre y valor",
            "valores_validos": None,
        }
    if any(not isinstance(clave, str) for clave in args):
        return {
            "ok": False,
            "error": f"los nombres de los argumentos de {nombre} deben ser texto",
            "valores_validos": None,
        }

    try:
        resultado = metodo(**args)
    except TypeError as falla:
        return {
            "ok": False,
            "error": f"argumentos no validos para {nombre}: {falla}",
            "valores_validos": None,
        }
    except Exception as falla:  # cinturon de seguridad: nada tumba el ciclo
        return {
            "ok": False,
            "error": f"la herramienta {nombre} fallo: {type(falla).__name__}: {falla}",
            "valores_validos": None,
        }

    if not isinstance(resultado, dict):
        return {
            "ok": False,
            "error": f"{nombre} devolvio algo que no es un objeto JSON",
            "valores_validos": None,
        }
    return resultado


# --------------------------------------------------------------------------- #
# responder: el ciclo
# --------------------------------------------------------------------------- #

def responder(
    pregunta: str,
    herramientas: Herramientas,
    sistema: str,
    llamar: Callable[..., Any],
    bitacora: Bitacora,
) -> dict[str, Any]:
    """Contesta una pregunta con el ciclo de function calling controlado aqui.

    Devuelve {respuesta, turnos, herramientas, cifras_sin_respaldo, segundos}.
    """
    reloj = time.perf_counter()
    bitacora.evento("inicio", pregunta=pregunta, **bitacora.contexto)

    historial: list[Any] = [mensaje_usuario(pregunta)]
    resultados: list[dict[str, Any]] = []
    usadas = 0
    corregida = False
    forzar_texto = False

    for turno in range(1, MAX_TURNOS + 1):
        if turno == MAX_TURNOS:
            forzar_texto = True

        respuesta = llamar(historial, sistema, DECLARACIONES, forzar_texto)
        bitacora.evento(
            "modelo",
            turno=turno,
            forzar_texto=forzar_texto,
            tokens_entrada=tokens_entrada(respuesta),
        )

        # El turno del modelo se agrega TAL COMO LLEGO: trae firmas internas.
        historial.append(contenido_del_modelo(respuesta))

        peticiones = list(getattr(respuesta, "function_calls", None) or [])
        if peticiones:
            resultados_del_turno: list[dict[str, Any]] = []
            for peticion in peticiones:
                argumentos = dict(peticion.args or {})
                if usadas >= MAX_HERRAMIENTAS:
                    resultado = {
                        "ok": False,
                        "error": (
                            f"presupuesto agotado: ya se ejecutaron {MAX_HERRAMIENTAS} "
                            "herramientas en esta pregunta. Responde con lo que ya tienes"
                        ),
                        "valores_validos": None,
                    }
                else:
                    usadas += 1
                    resultado = ejecutar(herramientas, peticion.name, argumentos)
                    resultados.append(resultado)

                bitacora.evento(
                    "herramienta",
                    nombre=peticion.name,
                    args=argumentos,
                    ok=bool(resultado.get("ok")),
                    error=resultado.get("error"),
                )
                resultados_del_turno.append(resultado)

            # Un solo mensaje con todas las function_response, con el mismo id.
            historial.append(mensaje_respuestas(peticiones, resultados_del_turno))
            if usadas >= MAX_HERRAMIENTAS:
                forzar_texto = True
            continue

        texto = getattr(respuesta, "text", None) or ""
        sin_respaldo = cifras_sin_respaldo(texto, pregunta, resultados)
        bitacora.evento("guardia", cifras_sin_respaldo=sin_respaldo, corregida=corregida)

        # La correccion consume un turno y se da una sola vez.
        if sin_respaldo and not corregida and turno < MAX_TURNOS:
            corregida = True
            historial.append(mensaje_usuario(mensaje_correccion(sin_respaldo)))
            continue

        if sin_respaldo:
            texto = f"{texto}\n\n{aviso(sin_respaldo)}"

        fin = {
            "respuesta": texto,
            "turnos": turno,
            "herramientas": usadas,
            "cifras_sin_respaldo": sin_respaldo,
            "segundos": round(time.perf_counter() - reloj, 2),
        }
        bitacora.evento("fin", **fin)
        return fin

    bitacora.evento("error", error="se agotaron los turnos sin texto")
    raise RuntimeError("se agotaron los turnos sin texto")


# --------------------------------------------------------------------------- #
# Armado comun de la terminal, el lote y el bot
# --------------------------------------------------------------------------- #

def leer_sistema(ruta: str = RUTA_SISTEMA) -> str:
    """El prompt de sistema."""
    return Path(ruta).read_text(encoding="utf-8")


def crear_herramientas(
    ruta_denue: str = RUTA_DENUE, ruta_sectores: str = RUTA_SECTORES
) -> Herramientas:
    """Carga los datos una sola vez y arma las herramientas."""
    for ruta in (ruta_denue, ruta_sectores):
        if not Path(ruta).exists():
            raise FileNotFoundError(
                f"falta {ruta}: copie los archivos de material_proyecto_u1.zip en data/"
            )
    datos, sectores = cargar_datos(ruta_denue, ruta_sectores)
    return Herramientas(datos, sectores)


def preparar(simulado: bool = False, id_actual: str = "CLI") -> tuple[Herramientas, str, Callable[..., Any], Bitacora]:
    """Todo lo que necesitan cli.py, lote.py y bot.py: mismos datos, mismo ciclo.

    Devuelve (herramientas, sistema, llamar, bitacora).
    """
    herramientas = crear_herramientas()
    sistema = leer_sistema()
    if simulado:
        from app.modelo_simulado import ModeloSimulado

        llamar: Callable[..., Any] = ModeloSimulado()
        nombre_modelo = MARCA_SIMULADO
    else:
        from app.modelo import llamar_modelo, modelo_en_uso

        llamar = llamar_modelo
        nombre_modelo = modelo_en_uso()
    return herramientas, sistema, llamar, Bitacora(modelo=nombre_modelo, id_actual=id_actual)
