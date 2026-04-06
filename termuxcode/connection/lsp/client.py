#!/usr/bin/env python3
"""Cliente LSP de alto nivel - fachada que combina lifecycle, documentos y features."""

import os

from termuxcode.connection.lsp.diagnostics import DiagnosticsManager
from termuxcode.connection.lsp.document import DocumentManager
from termuxcode.connection.lsp.features import LanguageFeatures
from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import file_path_to_uri
from termuxcode.ws_config import logger


class LSPClient:
    """Cliente LSP de alto nivel que combina transporte, documentos y features."""

    def __init__(self, command: list[str], cwd: str) -> None:
        self._transport = StdioTransport(command, cwd)
        self._diagnostics = DiagnosticsManager()
        self._documents = DocumentManager(self._transport, self._diagnostics)
        self._features = LanguageFeatures(self._transport)
        self._initialized = False

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

    # ── Delegacion a DocumentManager ─────────────────────────────────────

    async def open_file(self, file_path: str, content: str) -> None:
        """Envia textDocument/didOpen."""
        await self._documents.open(file_path, content)

    async def update_file(self, file_path: str, content: str) -> None:
        """Envia textDocument/didChange (full sync)."""
        await self._documents.update(file_path, content)

    async def close_file(self, file_path: str) -> None:
        """Envia textDocument/didClose."""
        await self._documents.close(file_path)

    async def open_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didOpen y espera publishDiagnostics atomicamente."""
        return await self._documents.open_and_wait(file_path, content, timeout)

    async def update_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didChange y espera publishDiagnostics atomicamente."""
        return await self._documents.update_and_wait(file_path, content, timeout)

    # ── Delegacion a LanguageFeatures ────────────────────────────────────

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol -> lista de DocumentSymbol."""
        return await self._features.get_symbols(file_path)

    async def get_hover(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> str | None:
        """textDocument/hover -> contenido como texto plano."""
        return await self._features.get_hover(file_path, line, col)

    async def get_references(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/references -> lista de Location."""
        return await self._features.get_references(file_path, line, col)

    async def get_type_definition(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/typeDefinition -> lista de Location."""
        return await self._features.get_type_definition(file_path, line, col)

    async def get_type_hierarchy(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> dict | None:
        """textDocument/typeHierarchy -> jerarquia de tipos."""
        return await self._features.get_type_hierarchy(file_path, line, col)

    async def get_inlay_hints(self, file_path: str) -> list[dict]:
        """textDocument/inlayHint -> hints de tipos inline."""
        return await self._features.get_inlay_hints(file_path)

    async def format_file(self, file_path: str) -> list[dict] | None:
        """textDocument/formatting -> lista de TextEdit."""
        return await self._features.format_file(file_path)

    # ── Diagnostico cacheado ─────────────────────────────────────────────

    def get_cached_diagnostics(self, file_path: str) -> list[dict]:
        """Retorna diagnosticos cacheados (no bloquea)."""
        uri = file_path_to_uri(file_path)
        return self._diagnostics.get(uri)
