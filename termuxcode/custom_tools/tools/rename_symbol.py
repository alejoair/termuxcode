#!/usr/bin/env python3
"""Tool: rename_symbol — renombra clases/funciones/variables en todo el codebase usando LSP."""

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
    "rename_symbol",
    "Rename a class, function, or variable across the entire codebase safely using LSP. This will find ALL references and rename them atomically. Use this when you need to refactor names - it's safer than using Edit tool which might miss references in other files.",
    {"file_path": str, "line": int, "col": int, "new_name": str},
)
async def rename_symbol(args: dict[str, Any]) -> dict[str, Any]:
    """Renombra un símbolo en todo el codebase usando LSP."""
    file_path = normalize_path(args.get("file_path", "").strip())
    line = args.get("line", 0)
    col = args.get("col", 0)
    new_name = args.get("new_name", "").strip()

    if not file_path:
        return {"content": [{"type": "text", "text": "Error: file_path is required"}]}

    if not os.path.isfile(file_path):
        return {"content": [{"type": "text", "text": f"Error: file not found: {file_path}"}]}

    if not new_name:
        return {"content": [{"type": "text", "text": "Error: new_name is required"}]}

    # Verificar si hay LSP disponible
    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP server not available for this session"}]}

    client = _lsp_manager.get_client(file_path)
    if not client:
        return {"content": [{"type": "text", "text": "Error: No LSP server available for this file type"}]}

    try:
        # Paso 1: Verificar si se puede renombrar (prepareRename)
        prepare_result = await client.prepare_rename(file_path, line, col)
        if not prepare_result:
            return {"content": [{"type": "text", "text": "Error: Cannot rename this symbol (prepareRename failed)"}]}

        # Paso 2: Ejecutar el rename
        edits = await client.rename(file_path, line, col, new_name)
        if not edits:
            return {"content": [{"type": "text", "text": "No changes made - rename returned no edits"}]}

        # Paso 3: Aplicar los edits a cada archivo
        lines = [f"Renamed symbol to '{new_name}':"]
        total_edits = 0

        for file_uri, text_edits in edits.items():
            # Convertir URI a file path
            edit_path = uri_to_file_path(file_uri)
            if not edit_path:
                continue

            # Leer contenido actual
            try:
                content = Path(edit_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                lines.append(f"  ⚠ {edit_path}: could not read file")
                continue

            # Aplicar edits en orden inverso (de fin a principio) para no offsets
            # Los edits de LSP vienen ordenados por start position
            sorted_edits = sorted(
                text_edits,
                key=lambda e: (
                    e.get("range", {}).get("start", {}).get("line", 0),
                    e.get("range", {}).get("start", {}).get("character", 0),
                ),
                reverse=True,
            )

            for edit in sorted_edits:
                rng = edit.get("range", {})
                start = rng.get("start", {})
                end = rng.get("end", {})

                start_line = start.get("line", 0)
                start_col = start.get("character", 0)
                end_line = end.get("line", 0)
                end_col = end.get("character", 0)

                # Convertir posición de línea/columna a offset
                lines_list = content.splitlines(keepends=True)
                if start_line >= len(lines_list):
                    continue

                # Encontrar offset de inicio
                start_offset = sum(len(l) for l in lines_list[:start_line]) + start_col
                # Encontrar offset de fin
                end_offset = sum(len(l) for l in lines_list[:end_line]) + end_col

                # Aplicar el edit
                new_text = edit.get("newText", "")
                content = content[:start_offset] + new_text + content[end_offset:]
                total_edits += 1

            # Escribir archivo modificado
            try:
                Path(edit_path).write_text(content, encoding="utf-8")
                edit_count = len(text_edits)
                rel_path = os.path.relpath(edit_path)
                lines.append(f"  ✓ {rel_path}: {edit_count} edit(s)")
            except OSError as e:
                lines.append(f"  ✗ {edit_path}: failed to write - {e}")

        return {"content": [{"type": "text", "text": f"\n".join(lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error during rename: {e}"}]}
