#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.ws_connection import WebSocketConnection


async def handle_connection(websocket):
    """Punto de entrada para nuevas conexiones WebSocket."""
    resume_id = None

    # Esperar primer mensaje para obtener resume_id si existe
    try:
        first_msg = await websocket.recv()
        data = json.loads(first_msg)
        if data.get("type") == "resume":
            resume_id = data.get("session_id")
            logger.info(f"Cliente quiere reanudar sesión: {resume_id}")
    except (json.JSONDecodeError, KeyError):
        pass

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
