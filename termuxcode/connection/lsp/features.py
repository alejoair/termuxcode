#!/usr/bin/env python3
"""Operaciones LSP: symbols, hover, references, type hierarchy, inlay hints, formatting."""

from termuxcode.connection.lsp.transport import StdioTransport
from termuxcode.connection.lsp.uri import file_path_to_uri


class LanguageFeatures:
    """Operaciones de lenguaje LSP: symbols, hover, references, type features."""

    def __init__(self, transport: StdioTransport) -> None:
        self._transport = transport

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol -> lista de DocumentSymbol."""
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
