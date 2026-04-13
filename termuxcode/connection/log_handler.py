#!/usr/bin/env python3
"""WebSocket log handler: captura logs y los envía a todas las sesiones conectadas."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from termuxcode.connection import session_registry
from termuxcode.ws_config import logger

# Ring buffer global con los últimos logs (thread-safe)
_buffer_lock = threading.Lock()
_log_buffer: deque[dict[str, str]] = deque(maxlen=500)


class WebSocketLogHandler(logging.Handler):
    """Handler que captura log records y los transmite via WebSocket."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(level=logging.INFO)
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        """Formatea el record, agrega al buffer, y programa broadcast async."""
        try:
            entry = {
                "type": "server_log",
                "level": record.levelname,
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).strftime("%H:%M:%S"),
                "logger": record.name,
                "message": self.format(record),
            }

            with _buffer_lock:
                _log_buffer.append(entry)

            # Programar broadcast en el event loop (thread-safe)
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(_broadcast_log(entry))
            )
        except Exception:
            # Nunca romper por un error de logging
            self.handleError(record)


async def _broadcast_log(log_dict: dict[str, Any]) -> None:
    """Envía un log a todas las sesiones WebSocket conectadas."""
    # Desduplicar: el mismo connection wrapper puede tener múltiples session_ids
    seen_connections: set[int] = set()
    for _sid, conn in session_registry.all_sessions().items():
        conn_id = id(conn)
        if conn_id in seen_connections:
            continue
        seen_connections.add(conn_id)

        session = conn._session
        if session and session._sender and session._sender._websocket:
            try:
                await session._sender.send_message(log_dict)
            except Exception:
                pass  # Silenciar errores de envío de logs


def get_log_history() -> list[dict[str, str]]:
    """Retorna el contenido actual del ring buffer."""
    with _buffer_lock:
        return list(_log_buffer)
