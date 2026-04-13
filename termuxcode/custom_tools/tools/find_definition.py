#!/usr/bin/env python3
"""Tool: find_definition — encuentra dónde está definido un símbolo usando LSP."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import tool
from termuxcode.connection.lsp.uri import normalize_path, uri_to_file_path

if TYPE_CHECKING:
    from termuxcode.connection.lsp_manager import LspManager

# Variable global para almacenar el LspManager (inyectada por el server)
_lsp_manager: "LspManager | None" = None


def set_lsp_manager(lsp_manager: "LspManager | None") -> None:
    """Inyecta el LspManager para ser usado por la tool."""
    global _lsp_manager
    _lsp_manager = lsp_manager


# Auto-registro en el sistema de inyección de LSP
import termuxcode.custom_tools.registry as registry_module

registry_module.register_lsp_tool(set_lsp_manager)


@tool(
    "find_definition",
    "Find where a symbol (class, function, variable) is defined using LSP. This jumps to the definition even if it's in another file. Use this when you need to understand how a function or class works - it will show you the actual implementation code.",
    {"file_path": str, "line": int, "col": int},
)
async def find_definition(args: dict[str, Any]) -> dict[str, Any]:
    """Encuentra la definición de un símbolo usando LSP."""
    file_path = normalize_path(args.get("file_path", "").strip())
    line = args.get("line", 0)
    col = args.get("col", 0)

    if not file_path:
        return {"content": [{"type": "text", "text": "Error: file_path is required"}]}

    if not os.path.isfile(file_path):
        return {"content": [{"type": "text", "text": f"Error: file not found: {file_path}"}]}

    # Verificar si hay LSP disponible
    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP server not available for this session"}]}

    client = _lsp_manager.get_client(file_path)
    if not client:
        return {"content": [{"type": "text", "text": "Error: No LSP server available for this file type"}]}

    try:
        # Obtener definiciones usando LSP
        locations = await client.get_definition(file_path, line, col)

        if not locations:
            # Intentar con type definition como fallback
            locations = await client.get_type_definition(file_path, line, col)
            if not locations:
                return {"content": [{"type": "text", "text": "No definition found for this symbol"}]}

        # Limitar a primeras 5 definiciones para no saturar
        locations = locations[:5]

        lines = [f"Found {len(locations)} definition(s):"]
        lines.append("")

        for i, loc in enumerate(locations, 1):
            uri = loc.get("uri", "")
            if not uri:
                continue

            path = uri_to_file_path(uri)
            if not path:
                lines.append(f"{i}. {uri}")
                continue

            rng = loc.get("range", {})
            start = rng.get("start", {})
            def_line = start.get("line", 0)
            def_col = start.get("character", 0)

            # Obtener ruta relativa para mostrar
            try:
                rel_path = os.path.relpath(path)
            except ValueError:
                rel_path = path

            # Leer las líneas alrededor de la definición para contexto
            context_lines = []
            try:
                content = Path(path).read_text(encoding="utf-8", errors="replace")
                lines_list = content.splitlines()

                # Mostrar 3 líneas antes y después
                start_ctx = max(0, def_line - 2)
                end_ctx = min(len(lines_list), def_line + 3)

                for ctx_line in range(start_ctx, end_ctx):
                    prefix = ">>>" if ctx_line == def_line else "   "
                    ctx_content = lines_list[ctx_line] if ctx_line < len(lines_list) else ""
                    context_lines.append(f"{prefix} L{ctx_line + 1}: {ctx_content}")

            except Exception:
                context_lines.append(f"   (Could not read file content)")

            # Formatear salida
            lines.append(f"{i}. {rel_path}:{def_line + 1}:{def_col + 1}")
            if context_lines:
                lines.extend(context_lines)
            lines.append("")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error finding definition: {e}"}]}
