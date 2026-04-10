#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json
import os
from typing import Any

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.connection import WebSocketConnection
from termuxcode.connection import session_registry
from termuxcode.connection.lsp.uri import normalize_path


async def handle_connection(websocket: Any) -> None:
    """Punto de entrada para nuevas conexiones WebSocket."""
    from urllib.parse import parse_qs, unquote, urlparse

    parsed = urlparse(websocket.request.path)
    qs = parse_qs(parsed.query)

    resume_id = qs.get("session_id", [None])[0]
    cwd_raw = qs.get("cwd", [None])[0]
    options_raw = qs.get("options", [None])[0]
    agent_options = json.loads(options_raw) if options_raw else {}

    if cwd_raw:
        cwd = normalize_path(unquote(cwd_raw))
    else:
        cwd = normalize_path(os.environ['TERMUXCODE_CWD'])

    # Verificar si es una reconexión de sesión existente
    if resume_id:
        existing_conn = session_registry.get(resume_id)
        if existing_conn is not None:
            await existing_conn.reconnect(
                websocket, agent_options=agent_options, cwd=cwd
            )
            await existing_conn.handle()
            return

    # Crear nueva conexión (y por ende nueva Session)
    connection = WebSocketConnection(
        websocket, resume_id=resume_id, cwd=cwd,
        agent_options=agent_options,
    )
    await connection.handle()


async def main() -> None:
    """Inicia el servidor WebSocket."""
    logger.info(f"Iniciando servidor en puerto {WS_PORT}")

    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
