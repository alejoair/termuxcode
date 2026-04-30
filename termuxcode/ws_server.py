#!/usr/bin/env python3
# ruff: noqa: ANN401
"""Servidor WebSocket principal para Claude Agent SDK."""

import asyncio
import json
import os
import signal
import sys
from typing import Any

import websockets

from termuxcode.ws_config import WS_HOST, WS_PORT, attach_ws_log_handler, logger
from termuxcode.connection import WebSocketConnection
from termuxcode.connection import session_registry
from termuxcode.connection.lsp.uri import normalize_path

# Permitir override del host via env var (cli.py pasa TERMUXCODE_HOST)
_host_override = os.environ.get("TERMUXCODE_HOST")
if _host_override:
    WS_HOST = "" if _host_override == "0.0.0.0" else _host_override


# Evento global para señalizar shutdown graceful
_shutdown_event: asyncio.Event | None = None


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
        cwd = normalize_path(os.environ.get('TERMUXCODE_CWD', os.getcwd()))

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


async def _graceful_shutdown() -> None:
    """Destruye todas las sesiones activas (graceful LSP shutdown)."""
    sessions = session_registry.all_sessions()
    if not sessions:
        return
    logger.info(f"Graceful shutdown: destruyendo {len(sessions)} sesión(es)...")
    # Cada connection puede tener múltiples session_ids (re-key), usar set
    connections = set(sessions.values())
    tasks = [conn.destroy_session() for conn in connections]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"Error en graceful shutdown: {r}")
    logger.info("Graceful shutdown completado")


def _signal_handler() -> None:
    """Signal handler para SIGTERM/SIGINT — programa shutdown graceful."""
    if _shutdown_event is not None:
        _shutdown_event.set()


async def main() -> None:
    """Inicia el servidor WebSocket."""
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    logger.info(f"Iniciando servidor en puerto {WS_PORT}")

    # Adjuntar log handler que transmite logs via WebSocket
    loop = asyncio.get_event_loop()
    attach_ws_log_handler(loop)

    # Registrar signal handlers para shutdown graceful
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows no soporta add_signal_handler, usar signal.signal()
            signal.signal(sig, lambda s, f: _signal_handler())

    async with websockets.serve(handle_connection, WS_HOST, WS_PORT):
        print(f"Servidor WebSocket en ws://{WS_HOST}:{WS_PORT}")
        await _shutdown_event.wait()
        # Señal recibida — cleanup graceful antes de salir
        await _graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
