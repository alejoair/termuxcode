#!/usr/bin/env python3
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json
import os

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, logger
from termuxcode.connection import WebSocketConnection

# Registry de sesiones activas para reconexión
_active_sessions: dict[str, WebSocketConnection] = {}


def set_registry_reference():
    """Conecta el registry con el módulo base para que pueda actualizarse."""
    import termuxcode.connection.base as base_module
    base_module._active_sessions_registry = _active_sessions


# Inicializar la referencia al registry
set_registry_reference()


async def handle_connection(websocket):
    """Punto de entrada para nuevas conexiones WebSocket."""
    from urllib.parse import urlparse, parse_qs, unquote

    parsed = urlparse(websocket.request.path)
    qs = parse_qs(parsed.query)

    resume_id = qs.get("session_id", [None])[0]
    cwd_raw = qs.get("cwd", [None])[0]
    cwd = unquote(cwd_raw) if cwd_raw else os.getcwd()
    options_raw = qs.get("options", [None])[0]
    agent_options = json.loads(options_raw) if options_raw else {}

    if resume_id:
        logger.info(f"Reanudando sesión SDK: {resume_id}")
    if cwd:
        logger.info(f"CWD del cliente: {cwd}")
    if agent_options:
        logger.info(f"Opciones del agente: {agent_options}")

    # Verificar si es una reconexión de sesión existente
    if resume_id and resume_id in _active_sessions:
        logger.info(f"Reconectando sesión existente: {resume_id}")
        conn = _active_sessions[resume_id]
        await conn.reconnect(websocket, agent_options=agent_options)
        await conn.handle()  # Entra al loop de mensajes
    else:
        # Crear nueva sesión
        connection = WebSocketConnection(websocket, resume_id=resume_id, cwd=cwd, agent_options=agent_options)
        if resume_id:
            _active_sessions[resume_id] = connection
        await connection.handle()


async def main():
    """Inicia el servidor WebSocket."""
    logger.info(f"Iniciando servidor en puerto {WS_PORT}")
    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
