#!/usr/bin/env python3
"""Tool: quick_fix — aplica correcciones automáticas del LSP (imports, stubs, etc)."""

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
    "quick_fix",
    "Apply automatic fixes from the LSP: add missing imports, implement stub methods, or fix common errors. Use this when you have diagnostics that suggest quick fixes. The LSP will detect issues like missing imports and apply the corrections automatically.",
    {"file_path": str, "line": int, "col": int},
)
async def quick_fix(args: dict[str, Any]) -> dict[str, Any]:
    """Aplica quick fixes del LSP."""
    file_path = normalize_path(args.get("file_path", "").strip())
    line = args.get("line")
    col = args.get("col")

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
        # Paso 1: Obtener code actions disponibles
        # Si no se especifica línea/col, obtener todas las acciones del archivo
        if line is None or col is None:
            actions = await client.get_code_actions(file_path)
        else:
            actions = await client.get_code_actions(file_path, line, col)

        if not actions:
            return {"content": [{"type": "text", "text": "No quick fixes available for this file"}]}

        # Filtrar solo acciones que tienen edits (no solo comandos)
        edit_actions = [a for a in actions if a.get("edit") is not None]
        if not edit_actions:
            return {"content": [{"type": "text", "text": "No applicable quick fixes found"}]}

        # Paso 2: Aplicar los fixes
        lines = [f"Applying {len(edit_actions)} quick fix(es):"]
        total_files = 0

        # Agrupar edits por archivo
        all_edits: dict[str, list[dict]] = {}
        for action in edit_actions:
            title = action.get("title", "Unknown fix")
            edit = action.get("edit", {})
            changes = edit.get("changes", {})
            document_changes = edit.get("documentChanges", [])

            # Procesar 'changes' format (archivo -> lista de edits)
            for file_uri, text_edits in changes.items():
                if file_uri not in all_edits:
                    all_edits[file_uri] = []
                all_edits[file_uri].extend(text_edits)

            # Procesar 'documentChanges' format (lista de edits con metadata)
            for doc_change in document_changes:
                if "edits" in doc_change and "textDocument" in doc_change:
                    file_uri = doc_change["textDocument"].get("uri", "")
                    if file_uri and file_uri not in all_edits:
                        all_edits[file_uri] = []
                    all_edits[file_uri].extend(doc_change["edits"])

        # Paso 3: Aplicar edits a cada archivo
        for file_uri, text_edits in all_edits.items():
            edit_path = uri_to_file_path(file_uri)
            if not edit_path:
                continue

            # Leer contenido actual
            try:
                content = Path(edit_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                lines.append(f"  ⚠ {os.path.relpath(edit_path)}: could not read file")
                continue

            # Aplicar edits en orden inverso (de fin a principio) para no offsets
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

            # Escribir archivo modificado
            try:
                Path(edit_path).write_text(content, encoding="utf-8")
                rel_path = os.path.relpath(edit_path)
                edit_count = len(text_edits)
                lines.append(f"  ✓ {rel_path}: {edit_count} edit(s)")
                total_files += 1
            except OSError as e:
                lines.append(f"  ✗ {rel_path}: failed to write - {e}")

        return {"content": [{"type": "text", "text": f"\n".join(lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error during quick fix: {e}"}]}
