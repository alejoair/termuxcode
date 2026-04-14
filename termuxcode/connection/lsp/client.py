#!/usr/bin/env python3
"""Cliente LSP de alto nivel - fachada que combina lifecycle, documentos y features."""

import asyncio
import os

from termuxcode.connection.lsp.diagnostics import DiagnosticsManager
from termuxcode.connection.lsp.document import DocumentManager
from termuxcode.connection.lsp.features import LanguageFeatures
from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import file_path_to_uri
from termuxcode.ws_config import logger


def _normalize_path_cwd(file_path: str, cwd: str) -> str:
    """Normaliza un path relativo a absoluto usando el cwd del LSP.

    Si el path ya es absoluto, no lo modifica.
    Si es relativo, lo convierte a absoluto usando cwd.

    Args:
        file_path: Path del archivo (relativo o absoluto)
        cwd: Directorio de trabajo del servidor LSP

    Returns:
        Path absoluto normalizado
    """
    if os.path.isabs(file_path):
        return file_path
    # Path relativo: convertir a absoluto usando cwd
    return os.path.normpath(os.path.join(cwd, file_path))


class LSPClient:
    """Cliente LSP de alto nivel que combina transporte, documentos y features."""

    def __init__(self, command: list[str], cwd: str) -> None:
        self._transport = StdioTransport(command, cwd)
        self._diagnostics = DiagnosticsManager()
        self._documents = DocumentManager(self._transport, self._diagnostics)
        self._features = LanguageFeatures(self._transport)
        self._server_capabilities: dict = {}
        self._initialized = False
        self._features._client = self
        self._on_diagnostics_callback = None

    def set_diagnostics_callback(self, callback):
        """Establece callback para publishDiagnostics del servidor.

        El callback recibe (uri, diagnostics) cuando el servidor envía
        textDocument/publishDiagnostics.
        """
        self._on_diagnostics_callback = callback

    async def _handle_notification(self, method: str, params: dict) -> None:
        """Despacha notificaciones del servidor LSP."""
        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri", "")
            diagnostics = params.get("diagnostics", [])
            self._diagnostics.handle_notification(uri, diagnostics)
            if self._on_diagnostics_callback:
                result = self._on_diagnostics_callback(uri, diagnostics)
                # Soportar callbacks async y sync
                if asyncio.iscoroutine(result):
                    await result

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
        self._server_capabilities = result.get("capabilities", {})
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

    def supports(self, method: str) -> bool:
        """Verifica si el servidor soporta un feature LSP.

        Args:
            method: Request method completo (ej: "textDocument/documentSymbol").
                    Se mapea al capability path equivalente.
        """
        if not self._server_capabilities:
            return True  # sin info, asumir que sí (backward compatible)

        # Mapeo de method LSP → capability key en ServerCapabilities
        CAPABILITY_MAP = {
            "textDocument/documentSymbol": "documentSymbolProvider",
            "textDocument/hover": "hoverProvider",
            "textDocument/references": "referencesProvider",
            "textDocument/typeDefinition": "typeDefinitionProvider",
            "textDocument/typeHierarchy": "typeHierarchyProvider",
            "textDocument/inlayHint": "inlayHintProvider",
            "textDocument/formatting": "documentFormattingProvider",
            "textDocument/prepareRename": "renameProvider",
            "textDocument/rename": "renameProvider",
            "textDocument/definition": "definitionProvider",
            "textDocument/codeAction": "codeActionProvider",
        }

        cap_key = CAPABILITY_MAP.get(method)
        if not cap_key:
            return True  # feature desconocido, asumir que sí

        # La capability puede ser bool, dict (options), o no existir
        value = self._server_capabilities.get(cap_key)
        if value is None:
            return False
        return bool(value) if isinstance(value, bool) else True

    # ── Delegacion a DocumentManager ─────────────────────────────────────

    async def open_file(self, file_path: str, content: str) -> None:
        """Envia textDocument/didOpen."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        await self._documents.open(normalized, content)

    async def update_file(self, file_path: str, content: str) -> None:
        """Envia textDocument/didChange (full sync)."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        await self._documents.update(normalized, content)

    async def close_file(self, file_path: str) -> None:
        """Envia textDocument/didClose."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        await self._documents.close(normalized)

    async def open_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didOpen y espera publishDiagnostics atomicamente."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._documents.open_and_wait(normalized, content, timeout)

    async def update_and_wait(
        self,
        file_path: str,
        content: str,
        timeout: float = 10.0,
    ) -> list[dict]:
        """Envia didChange y espera publishDiagnostics atomicamente."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._documents.update_and_wait(normalized, content, timeout)

    # ── Delegacion a LanguageFeatures ────────────────────────────────────

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol -> lista de DocumentSymbol."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_symbols(normalized)

    async def get_hover(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> str | None:
        """textDocument/hover -> contenido como texto plano."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_hover(normalized, line, col)

    async def get_references(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/references -> lista de Location."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_references(normalized, line, col)

    async def get_type_definition(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/typeDefinition -> lista de Location."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_type_definition(normalized, line, col)

    async def get_type_hierarchy(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> dict | None:
        """textDocument/typeHierarchy -> jerarquia de tipos."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_type_hierarchy(normalized, line, col)

    async def get_inlay_hints(self, file_path: str) -> list[dict]:
        """textDocument/inlayHint -> hints de tipos inline."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_inlay_hints(normalized)

    async def format_file(self, file_path: str) -> list[dict] | None:
        """textDocument/formatting -> lista de TextEdit."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.format_file(normalized)

    async def prepare_rename(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> dict | None:
        """textDocument/prepareRename -> verifica si se puede renombrar."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.prepare_rename(normalized, line, col)

    async def rename(
        self,
        file_path: str,
        line: int,
        col: int,
        new_name: str,
    ) -> dict[str, list[dict]] | None:
        """textDocument/rename -> edits de renombrado."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.rename(normalized, line, col, new_name)

    async def get_definition(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/definition -> lista de Location."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_definition(normalized, line, col)

    async def get_code_actions(
        self,
        file_path: str,
        line: int | None = None,
        col: int | None = None,
    ) -> list[dict]:
        """textDocument/codeAction -> lista de CodeAction."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        return await self._features.get_code_actions(normalized, line, col)

    # ── Diagnostico cacheado ─────────────────────────────────────────────

    def get_cached_diagnostics(self, file_path: str) -> list[dict]:
        """Retorna diagnosticos cacheados (no bloquea)."""
        normalized = _normalize_path_cwd(file_path, self._transport.cwd)
        uri = file_path_to_uri(normalized)
        return self._diagnostics.get(uri)

    # ── Raw passthrough (para editor sidebar) ──────────────────────────

    async def send_raw_request(self, method: str, params: dict | None = None, timeout: float = 10.0) -> dict | None:
        """Envía un request JSON-RPC crudo al servidor LSP.

        Usado por el editor sidebar para completions, hover, etc.
        """
        return await self._transport.send_request(method, params, timeout)

    async def send_raw_notification(self, method: str, params: dict | None = None) -> None:
        """Envía una notificación JSON-RPC cruda al servidor LSP.

        Usado por el editor sidebar para didChange, etc.
        """
        await self._transport.send_notification(method, params)
