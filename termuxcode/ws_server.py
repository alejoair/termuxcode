#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.ws_connection import WebSocketConnection


async def handle_connection(websocket):
    """Punto de entrada para nuevas conexiones WebSocket."""
    # Obtener session_id del query param
    params = dict(pair.split("=") for pair in (websocket.request.path.split("?", 1)[1:] or [""])[0].split("&") if "=" in pair)
    resume_id = params.get("session_id") or None

    if resume_id:
        logger.info(f"Reanudando sesion SDK: {resume_id}")

    connection = WebSocketConnection(websocket, resume_id=resume_id)
    await connection.handle()


async def main():
    """Inicia el servidor WebSocket."""
    logger.info(f"Iniciando servidor en puerto {WS_PORT}")
    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
