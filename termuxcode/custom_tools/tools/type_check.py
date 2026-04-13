#!/usr/bin/env python3
"""Tool: type_check — verifica errores de tipos en un archivo Python usando LSP."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import tool
from termuxcode.connection.lsp.uri import normalize_path

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
    "type_check",
    "Check a Python file for type errors using the LSP server (ty). Returns a list of errors with line, column and message. Use this before and after editing Python files to catch type mistakes.",
    {"file_path": str},
)
async def type_check(args: dict[str, Any]) -> dict[str, Any]:
    """Valida un archivo Python usando el servidor LSP de la sesión."""
    file_path = normalize_path(args.get("file_path", "").strip())

    if not file_path:
        return {"content": [{"type": "text", "text": "Error: file_path is required"}]}

    if not os.path.isfile(file_path):
        return {"content": [{"type": "text", "text": f"Error: file not found: {file_path}"}]}

    if not file_path.endswith(".py"):
        return {"content": [{"type": "text", "text": f"Error: type_check only supports Python files (.py), got: {file_path}"}]}

    # Verificar si hay LSP disponible
    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP server not available for this session"}]}

    try:
        # Leer el contenido del archivo
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")

        # Validar usando el LspManager
        diagnostics = await _lsp_manager.validate_file(file_path, content)

        if not diagnostics:
            return {"content": [{"type": "text", "text": f"No type errors found in {file_path}"}]}

        # Formatear diagnósticos como texto
        lines = [f"Type errors in {file_path}:"]
        for diag in diagnostics:
            line = diag.get("range", {}).get("start", {}).get("line", 0)
            col = diag.get("range", {}).get("start", {}).get("character", 0)
            severity = "error" if diag.get("severity") == 1 else "warning"
            message = diag.get("message", "")
            source = diag.get("source", "LSP")
            lines.append(f"  {file_path}:{line + 1}:{col + 1}: [{source}] {severity}: {message}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error validating with LSP: {e}"}]}
