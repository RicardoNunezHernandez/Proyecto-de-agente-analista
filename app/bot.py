"""Parte H - El bot de Telegram: sólo recibe y entrega mensajes.

    python -m app.bot [--simulado]

Aquí NO hay lógica del agente: el manejador recibe el texto, llama al mismo
agente.responder que usa la terminal y devuelve la respuesta. El ciclo, las
herramientas y la guardia no saben de dónde llegó la pregunta.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agente import preparar, responder
from app.herramientas import FUENTE

TOPE_MENSAJE = 4096
SEGUNDOS_ESCRIBIENDO = 4

TEXTO_START = (
    "Soy un analista del DENUE 05/2026 del INEGI para Tampico y Ciudad Madero "
    "(22900 establecimientos).\n\n"
    "Puedo contarte cuántos negocios de un giro hay, en qué colonia se concentran, "
    "cómo se reparten por municipio o estrato de personal ocupado, y darte ejemplos "
    "de establecimientos.\n\n"
    "No tengo: número exacto de empleados (sólo rangos), ventas, ingresos, ganancias, "
    "salarios, horarios ni opiniones de clientes.\n\n"
    "Una respuesta puede tardar de algunos segundos a un par de minutos, porque consulto "
    "los datos varias veces antes de contestar.\n\n"
    "Aviso de privacidad: no escribas datos personales. Tus mensajes pasan por los "
    "servidores de Telegram y por Google para poder responderte.\n\n"
    "Comandos: /start y /fuente."
)

TEXTO_FUENTE = (
    f"Fuente: {FUENTE}.\n"
    "Recorte usado: establecimientos activos de los municipios de Tampico y Ciudad Madero, "
    "Tamaulipas, edición 05/2026 del Directorio Estadístico Nacional de Unidades Económicas. "
    "Publicado por el INEGI bajo sus Términos de Libre Uso de la Información."
)

TEXTO_PRIVADO = (
    "Este bot es privado y sólo atiende a los usuarios autorizados.\n"
    "Tu identificador de Telegram es {identificador}."
)

TEXTO_ERROR = (
    "No pude responder esa pregunta por una falla técnica (puede ser la cuota del modelo "
    "o la red). Vuelve a intentar en un momento."
)


# --------------------------------------------------------------------------- #
# Funciones puras (sin red): se prueban en pruebas/prueba_herramientas.py
# --------------------------------------------------------------------------- #

def leer_permitidos(texto: str | None) -> set[int]:
    """Los identificadores numéricos de TELEGRAM_USUARIOS_PERMITIDOS.

    Con la lista vacía el bot no atiende a nadie.
    """
    if not texto:
        return set()
    permitidos: set[int] = set()
    for parte in str(texto).replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            permitidos.add(int(parte))
        except ValueError:
            continue
    return permitidos


def partir_mensaje(texto: str, tope: int = TOPE_MENSAJE) -> list[str]:
    """Parte un texto en trozos de `tope` caracteres o menos.

    Corta de preferencia en un salto de línea, para no partir una frase a la mitad.
    """
    if not texto:
        return []
    resto = texto
    trozos: list[str] = []
    while len(resto) > tope:
        corte = resto.rfind("\n", 0, tope + 1)
        if corte <= 0:
            corte = tope
            trozos.append(resto[:corte])
            resto = resto[corte:]
        else:
            trozos.append(resto[:corte])
            resto = resto[corte + 1 :]  # el salto de línea se consume en el corte
    trozos.append(resto)
    return [t for t in trozos if t]


def usuario_anonimo(identificador: object) -> str:
    """Los primeros 10 caracteres del SHA-256 del identificador.

    En la bitácora nunca queda el identificador real ni el nombre.
    """
    return hashlib.sha256(str(identificador).encode("utf-8")).hexdigest()[:10]


# --------------------------------------------------------------------------- #
# Plomería de Telegram
# --------------------------------------------------------------------------- #

async def _entregar(mensaje, texto: str) -> None:
    for trozo in partir_mensaje(texto):
        await mensaje.reply_text(trozo)


async def con_escribiendo(chat, funcion, *args):
    """Corre una función lenta en otro hilo y mantiene el aviso «escribiendo...».

    Así el bot no se congela mientras el agente piensa.
    """
    tarea = asyncio.ensure_future(asyncio.to_thread(funcion, *args))
    while not tarea.done():
        await chat.send_action(ChatAction.TYPING)
        await asyncio.wait([tarea], timeout=SEGUNDOS_ESCRIBIENDO)
    return tarea.result()


def _autorizado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return update.effective_user.id in context.bot_data["permitidos"]


async def _rechazar(update: Update) -> None:
    await update.effective_message.reply_text(
        TEXTO_PRIVADO.format(identificador=update.effective_user.id)
    )


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        await _rechazar(update)
        return
    await _entregar(update.effective_message, TEXTO_START)


async def fuente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        await _rechazar(update)
        return
    await _entregar(update.effective_message, TEXTO_FUENTE)


async def pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _autorizado(update, context):
        await _rechazar(update)
        return

    texto = (update.effective_message.text or "").strip()
    if not texto:
        return

    bitacora = context.bot_data["bitacora"]
    context.bot_data["contador"] += 1
    bitacora.id_actual = f"TG-{context.bot_data['contador']}"
    bitacora.contexto = {
        "canal": "telegram",
        "usuario": usuario_anonimo(update.effective_user.id),
    }

    try:
        fin = await con_escribiendo(
            update.effective_chat,
            responder,
            texto,
            context.bot_data["herramientas"],
            context.bot_data["sistema"],
            context.bot_data["llamar"],
            bitacora,
        )
    except Exception as falla:  # nunca un traceback al usuario
        bitacora.evento("error", error=f"{type(falla).__name__}: {falla}")
        logging.warning("falla al responder %s: %s", bitacora.id_actual, falla)
        await update.effective_message.reply_text(TEXTO_ERROR)
        return

    await _entregar(update.effective_message, fin["respuesta"])


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m app.bot", description="Bot de Telegram del agente analista del DENUE."
    )
    analizador.add_argument("--simulado", action="store_true", help="usa el modelo simulado")
    argumentos = analizador.parse_args(argv)

    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # la URL de Telegram trae el token

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("falta TELEGRAM_BOT_TOKEN en el .env", file=sys.stderr)
        return 1

    permitidos = leer_permitidos(os.environ.get("TELEGRAM_USUARIOS_PERMITIDOS"))
    if not permitidos:
        print(
            "TELEGRAM_USUARIOS_PERMITIDOS está vacío: el bot no atenderá a nadie.\n"
            "Escríbele al bot y te dirá tu identificador; ponlo en el .env.",
            file=sys.stderr,
        )

    try:
        herramientas, sistema, llamar, bitacora = preparar(
            simulado=argumentos.simulado, id_actual="TG-0"
        )
    except Exception as falla:
        print(f"No se pudo iniciar el bot: {falla}", file=sys.stderr)
        return 1

    aplicacion = ApplicationBuilder().token(token).build()
    aplicacion.bot_data.update(
        {
            "herramientas": herramientas,
            "sistema": sistema,
            "llamar": llamar,
            "bitacora": bitacora,
            "permitidos": permitidos,
            "contador": 0,
        }
    )
    aplicacion.add_handler(CommandHandler("start", inicio))
    aplicacion.add_handler(CommandHandler("fuente", fuente))
    aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pregunta))

    print(f"Bot en marcha ({'simulado' if argumentos.simulado else bitacora.modelo}).")
    print(f"Usuarios permitidos: {sorted(permitidos) or 'ninguno'}")
    print(f"Bitácora: {bitacora.ruta}")
    print("Ctrl+C para detener.")
    try:
        aplicacion.run_polling()
    except KeyboardInterrupt:
        # En Windows, Ctrl+C sale por aquí a media parada: se detiene igual, pero sin
        # el traceback, que parece una caída y no lo es.
        pass
    print("Bot detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
