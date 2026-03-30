#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.connection import WebSocketConnection


async def handle_connection(websocket):
    """Punto de entrada para nuevas conexiones WebSocket."""
    from urllib.parse import urlparse, parse_qs, unquote

    parsed = urlparse(websocket.request.path)
    qs = parse_qs(parsed.query)

    resume_id = qs.get("session_id", [None])[0]
    cwd_raw = qs.get("cwd", [None])[0]
    cwd = unquote(cwd_raw) if cwd_raw else None
    options_raw = qs.get("options", [None])[0]
    agent_options = json.loads(options_raw) if options_raw else {}

    if resume_id:
        logger.info(f"Reanudando sesión SDK: {resume_id}")
    if cwd:
        logger.info(f"CWD del cliente: {cwd}")
    if agent_options:
        logger.info(f"Opciones del agente: {agent_options}")

    connection = WebSocketConnection(websocket, resume_id=resume_id, cwd=cwd, agent_options=agent_options)
    await connection.handle()


async def main():
    """Inicia el servidor WebSocket."""
    logger.info(f"Iniciando servidor en puerto {WS_PORT}")
    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
