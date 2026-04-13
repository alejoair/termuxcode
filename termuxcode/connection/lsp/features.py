#!/usr/bin/env python3
"""Operaciones LSP: symbols, hover, references, type hierarchy, inlay hints, formatting."""

from typing import Any

from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import file_path_to_uri


class LanguageFeatures:
    """Operaciones de lenguaje LSP: symbols, hover, references, type features."""

    def __init__(self, transport: StdioTransport) -> None:
        self._transport = transport
        self._client: Any = None  # LSPClient, set after construction

    def _supports(self, method: str) -> bool:
        """Check if the server supports this feature."""
        return self._client.supports(method) if self._client else True

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol -> lista de DocumentSymbol."""
        if not self._supports("textDocument/documentSymbol"):
            return []
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/documentSymbol",
            {"textDocument": {"uri": uri}},
        )
        if isinstance(result, list):
            return result
        return []

    async def get_hover(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> str | None:
        """textDocument/hover -> contenido como texto plano."""
        if not self._supports("textDocument/hover"):
            return None
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/hover",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
            },
        )
        if not result or "contents" not in result:
            return None
        contents = result["contents"]
        if isinstance(contents, str):
            return contents
        if isinstance(contents, dict):
            return contents.get("value", "")
        if isinstance(contents, list):
            parts: list[str] = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            return "\n".join(parts) if parts else None
        return None

    async def get_references(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/references -> lista de Location."""
        if not self._supports("textDocument/references"):
            return []
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
                "context": {"includeDeclaration": False},
            },
        )
        if isinstance(result, list):
            return result
        return []

    async def get_type_definition(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/typeDefinition -> lista de Location.

        Retorna donde esta definido el TIPO del simbolo (no el simbolo mismo).
        Util para saltar a definiciones de tipos en librerias/stdlib.
        """
        if not self._supports("textDocument/typeDefinition"):
            return []
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/typeDefinition",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
            },
        )
        if isinstance(result, list):
            return result
        return []

    async def get_type_hierarchy(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> dict | None:
        """textDocument/typeHierarchy -> jerarquia de tipos.

        Returns:
            TypeHierarchy item con subtypes/supertypes, o None si no aplica.
        """
        if not self._supports("textDocument/typeHierarchy"):
            return None
        uri = file_path_to_uri(file_path)

        result = await self._transport.send_request(
            "textDocument/typeHierarchy",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
                "resolve": 1,
            },
        )
        if not result:
            return None

        resolved = await self._transport.send_request(
            "typeHierarchy/resolve",
            {"item": result, "resolve": 2},
        )
        return resolved if resolved else result

    async def get_inlay_hints(self, file_path: str) -> list[dict]:
        """textDocument/inlayHint -> hints de tipos inline.

        Retorna hints como:
        - Tipos de variables sin anotacion
        - Tipos de parametros en llamadas
        """
        if not self._supports("textDocument/inlayHint"):
            return []
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/inlayHint",
            {
                "textDocument": {"uri": uri},
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 100000, "character": 0},
                },
            },
        )
        if isinstance(result, list):
            return result
        return []

    async def format_file(self, file_path: str) -> list[dict] | None:
        """textDocument/formatting -> lista de TextEdit.

        Retorna ediciones de formato para todo el archivo.
        None si el servidor no soporta formato o falla.
        """
        if not self._supports("textDocument/formatting"):
            return None
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": uri},
                "options": {"tabSize": 4, "insertSpaces": True},
            },
        )
        if isinstance(result, list) and len(result) > 0:
            return result
        return None

    async def prepare_rename(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> dict | None:
        """textDocument/prepareRename -> verifica si se puede renombrar.

        Retorna:
            Placeholder con rango del símbolo, o None si no se puede renombrar.
        """
        if not self._supports("textDocument/prepareRename"):
            return None
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/prepareRename",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
            },
        )
        return result

    async def rename(
        self,
        file_path: str,
        line: int,
        col: int,
        new_name: str,
    ) -> dict[str, list[dict]] | None:
        """textDocument/rename -> edits de renombrado.

        Retorna:
            {file_uri: [TextEdit, ...], ...} mapeando URIs a lista de edits.
            None si el servidor no soporta rename o falla.
        """
        if not self._supports("textDocument/rename"):
            return None
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/rename",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
                "newName": new_name,
            },
        )
        if not result or "changes" not in result:
            return None
        return result["changes"]

    async def get_definition(
        self,
        file_path: str,
        line: int,
        col: int,
    ) -> list[dict]:
        """textDocument/definition -> lista de Location.

        Retorna:
            Lista de Location con uri, range. Vacío si no hay definición.
        """
        if not self._supports("textDocument/definition"):
            return []
        uri = file_path_to_uri(file_path)
        result = await self._transport.send_request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
            },
        )
        if isinstance(result, list):
            return result
        return []

    async def get_code_actions(
        self,
        file_path: str,
        line: int | None = None,
        col: int | None = None,
    ) -> list[dict]:
        """textDocument/codeAction -> lista de CodeAction.

        Retorna:
            Lista de CodeAction con title, kind, edit. Vacío si no hay acciones.
        """
        if not self._supports("textDocument/codeAction"):
            return []
        uri = file_path_to_uri(file_path)

        # Si no se especifica línea/col, pedir acciones para todo el archivo
        range_val = (
            {
                "start": {"line": line, "character": col},
                "end": {"line": line, "character": col},
            }
            if line is not None and col is not None
            else None
        )

        result = await self._transport.send_request(
            "textDocument/codeAction",
            {
                "textDocument": {"uri": uri},
                "range": range_val,
                "context": {"diagnostics": []},
            },
        )
        if isinstance(result, list):
            return result
        return []
