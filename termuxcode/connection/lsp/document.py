#!/usr/bin/env python3
"""Gestion de sincronizacion de documentos LSP."""

import asyncio

from termuxcode.connection.lsp.diagnostics import DiagnosticsManager
from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import (
    extension_to_language_id,
    file_path_to_uri,
)


class DocumentManager:
    """Maneja textDocument/didOpen|didChange|didClose con sincronizacion completa."""

    def __init__(
        self,
        transport: StdioTransport,
        diagnostics: DiagnosticsManager,
    ) -> None:
        self._transport = transport
        self._diagnostics = diagnostics
        self._version: dict[str, int] = {}

    async def open(self, file_path: str, content: str) -> None:
        """Envia textDocument/didOpen (o didChange si ya está abierto)."""
        uri = file_path_to_uri(file_path)
        if self._version.get(uri, 0) > 0:
            await self.update(file_path, content)
            return
        language_id = extension_to_language_id(file_path)
        self._version[uri] = 1
        await self._transport.send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": content,
                }
            },
        )

    async def update(self, file_path: str, content: str) -> None:
        """Envia textDocument/didChange (full sync)."""
        uri = file_path_to_uri(file_path)
        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._transport.send_notification(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": version},
                "contentChanges": [{"text": content}],
            },
        )

    async def close(self, file_path: str) -> None:
        """Envia textDocument/didClose solo si el documento está abierto."""
        uri = file_path_to_uri(file_path)
        if self._version.pop(uri, 0) == 0:
            return  # Nunca se abrió o ya fue cerrado — no enviar didClose
        await self._transport.send_notification(
            "textDocument/didClose",
            {"textDocument": {"uri": uri}},
        )

    async def open_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didOpen (o didChange si ya está abierto) y espera publishDiagnostics."""
        uri = file_path_to_uri(file_path)
        if self._version.get(uri, 0) > 0:
            return await self.update_and_wait(file_path, content, timeout)
        self._diagnostics.clear_event(uri)

        self._version[uri] = 1
        await self._transport.send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": extension_to_language_id(file_path),
                    "version": 1,
                    "text": content,
                },
            },
        )

        try:
            event = self._diagnostics.get_event(uri)
            if event:
                await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri)

    async def update_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didChange y espera publishDiagnostics atomicamente."""
        uri = file_path_to_uri(file_path)
        self._diagnostics.clear_event(uri)

        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._transport.send_notification(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": version},
                "contentChanges": [{"text": content}],
            },
        )

        try:
            event = self._diagnostics.get_event(uri)
            if event:
                await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri)
