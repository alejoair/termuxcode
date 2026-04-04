#!/usr/bin/env python3
"""Manejo de diagnósticos LSP con cache y eventos async."""

import asyncio


class DiagnosticsManager:
    """Cache de diagnósticos LSP con eventos para sincronización async."""

    def __init__(self):
        self._diagnostics: dict[str, list[dict]] = {}  # URI → diagnostics
        self._events: dict[str, asyncio.Event] = {}  # URI → Event
        self._generation: dict[str, int] = {}  # URI → counter

    def handle_notification(self, uri: str, diagnostics: list[dict]) -> None:
        """Procesa notificación publishDiagnostics del servidor."""
        self._diagnostics[uri] = diagnostics
        self._generation[uri] = self._generation.get(uri, 0) + 1
        event = self._events.get(uri)
        if event:
            event.set()

    def get(self, uri: str) -> list[dict]:
        """Retorna diagnósticos cacheados para una URI."""
        return self._diagnostics.get(uri, [])

    def clear_event(self, uri: str) -> asyncio.Event:
        """Limpia y retorna el event para una URI (antes de enviar request)."""
        event = self._events.get(uri)
        if event:
            event.clear()
        else:
            event = asyncio.Event()
            self._events[uri] = event
        return event

    async def wait_for(self, uri: str, timeout: float = 10.0) -> list[dict]:
        """Espera la próxima notificación de diagnósticos para una URI."""
        event = self.clear_event(uri)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self.get(uri)

    def get_event(self, uri: str) -> asyncio.Event:
        """Retorna el event para una URI (sin limpiar)."""
        return self._events.get(uri)
