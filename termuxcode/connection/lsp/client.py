#!/usr/bin/env python3
"""Cliente LSP de alto nivel."""

import asyncio
import os

from termuxcode.connection.lsp.diagnostics import DiagnosticsManager
from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import (
    extension_to_language_id,
    file_path_to_uri,
)
from termuxcode.ws_config import logger


class LSPClient:
    """Cliente LSP de alto nivel que combina transporte, diagnósticos y operaciones de texto."""

    def __init__(self, command: list[str], cwd: str):
        self._transport = StdioTransport(command, cwd)
        self._diagnostics = DiagnosticsManager()
        self._initialized = False
        self._version: dict[str, int] = {}  # URI → version counter

    def _handle_notification(self, method: str, params: dict) -> None:
        """Despacha notificaciones del servidor LSP."""
        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri", "")
            diagnostics = params.get("diagnostics", [])
            self._diagnostics.handle_notification(uri, diagnostics)

    async def start(self) -> None:
        """Inicia el servidor LSP y completa el handshake initialize."""
        self._transport.set_notification_handler(self._handle_notification)
        await self._transport.start()

        root_uri = file_path_to_uri(self._transport.cwd)
        init_params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "rootPath": self._transport.cwd,
            "capabilities": {
                "textDocument": {
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "references": {},
                    "publishDiagnostics": {"relatedInformation": True},
                    "synchronization": {
                        "dynamicRegistration": False,
                        "willSave": False,
                        "willSaveWaitUntil": False,
                        "didSave": False,
                    },
                },
            },
        }

        result = await self._transport.send_request(
            "initialize", init_params, timeout=60.0
        )
        if result is None:
            await self._transport.shutdown()
            raise RuntimeError(
                f"LSP server {self._transport.command[0]} did not respond to initialize"
            )

        await self._transport.send_notification("initialized", {})
        self._initialized = True
        logger.info(f"LSPClient: {self._transport.command[0]} initialized")

    async def shutdown(self) -> None:
        """Apaga el servidor LSP limpiamente."""
        self._initialized = False
        try:
            await self._transport.send_request("shutdown", None, timeout=3.0)
        except Exception:
            pass
        try:
            await self._transport.send_notification("exit", {})
        except Exception:
            pass
        await self._transport.shutdown()

    async def open_file(self, file_path: str, content: str) -> None:
        """Envía textDocument/didOpen."""
        uri = file_path_to_uri(file_path)
        language_id = extension_to_language_id(file_path)
        self._version[uri] = 1
        await self._transport.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })

    async def update_file(self, file_path: str, content: str) -> None:
        """Envía textDocument/didChange (full sync)."""
        uri = file_path_to_uri(file_path)
        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._transport.send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}],
        })

    async def close_file(self, file_path: str) -> None:
        """Envía textDocument/didClose."""
        uri = file_path_to_uri(file_path)
        await self._transport.send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol → lista de DocumentSymbol."""
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/documentSymbol",
            {"textDocument": {"uri": uri}}
        )
        if isinstance(result, list):
            return result
        return []

    async def get_hover(self, file_path: str, line: int, col: int) -> str | None:
        """textDocument/hover → contenido como texto plano."""
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
        })
        if not result or "contents" not in result:
            return None
        contents = result["contents"]
        if isinstance(contents, str):
            return contents
        if isinstance(contents, dict):
            return contents.get("value", "")
        if isinstance(contents, list):
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            return "\n".join(parts) if parts else None
        return None

    async def get_references(self, file_path: str, line: int, col: int) -> list[dict]:
        """textDocument/references → lista de Location."""
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
            "context": {"includeDeclaration": False},
        })
        if isinstance(result, list):
            return result
        return []

    async def open_and_wait(
        self, file_path: str, content: str, timeout: float = 10.0
    ) -> list[dict]:
        """Envía didOpen y espera publishDiagnostics atómicamente."""
        uri = file_path_to_uri(file_path)
        self._diagnostics.clear_event(uri)

        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._transport.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": extension_to_language_id(file_path),
                "version": version,
                "text": content,
            },
        })

        try:
            event = self._diagnostics.get_event(uri)
            if event:
                await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri)

    async def update_and_wait(
        self, file_path: str, content: str, timeout: float = 10.0
    ) -> list[dict]:
        """Envía didChange y espera publishDiagnostics atómicamente."""
        uri = file_path_to_uri(file_path)
        self._diagnostics.clear_event(uri)

        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._transport.send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}],
        })

        try:
            event = self._diagnostics.get_event(uri)
            if event:
                await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri)

    def get_cached_diagnostics(self, file_path: str) -> list[dict]:
        """Retorna diagnósticos cacheados (no bloquea)."""
        uri = file_path_to_uri(file_path)
        return self._diagnostics.get(uri)

