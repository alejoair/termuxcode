#!/usr/bin/env python3
"""Registry global de sesiones activas.

Mapea session_id → WebSocketConnection para reconexión.
Un mismo WebSocketConnection puede tener múltiples session_ids (por re-key).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from termuxcode.connection.base import WebSocketConnection

# session_id → WebSocketConnection
_sessions: dict[str, WebSocketConnection] = {}


def register(session_id: str, connection: WebSocketConnection) -> None:
    """Registra un session_id apuntando a una WebSocketConnection."""
    _sessions[session_id] = connection


def unregister(session_id: str) -> None:
    """Elimina un session_id del registry."""
    _sessions.pop(session_id, None)


def get(session_id: str) -> WebSocketConnection | None:
    """Busca una WebSocketConnection por session_id."""
    return _sessions.get(session_id)


def all_sessions() -> dict[str, WebSocketConnection]:
    """Retorna el dict completo (solo para debugging)."""
    return _sessions
