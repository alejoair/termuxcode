#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.ws_connection import WebSocketConnection


async def handle_connection(websocket):
    """Punto de entrada para nuevas conexiones WebSocket."""
    connection = WebSocketConnection(websocket)
    await connection.handle()


async def main():
    """Inicia el servidor WebSocket."""
    logger.info(f"Iniciando servidor en puerto {WS_PORT}")
    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
