#!/usr/bin/env python3
"""Analizador semántico de archivos via LSP."""

import os
from pathlib import Path

from termuxcode.connection.lsp import LSPClient, file_path_to_uri, normalize_path
from termuxcode.ws_config import logger

from .formatters import (
    format_inlay_hints,
    format_methods,
    format_references,
    format_signatures,
    format_type_definitions,
    format_type_hierarchy,
)
from .symbols import diag_key


class LspAnalyzer:
    """Encapsula análisis LSP: contexto semántico + validación.

    Recibe un registry de clientes LSP y provee métodos para:
    - analyze_file: contexto semántico para hooks PostToolUse Read
    - validate_file: validación para hooks PreToolUse Write|Edit
    - get_pre_edit_diagnostics / get_new_diagnostics: comparación de diagnósticos
    """

    def __init__(self, clients: dict[str, list[LSPClient]]) -> None:
        self._clients = clients

    def get_client(self, file_path: str) -> LSPClient | None:
        """Retorna el cliente LSP principal para la extensión del archivo."""
        _, ext = os.path.splitext(file_path)
        client_list = self._clients.get(ext)
        return client_list[0] if client_list else None

    def get_all_clients(self, file_path: str) -> list[LSPClient]:
        """Retorna TODOS los clientes LSP para la extensión."""
        _, ext = os.path.splitext(file_path)
        return self._clients.get(ext, [])

    # ── Analyzer: contexto semántico (PostToolUse Read) ────────────────

    async def analyze_file(self, file_path: str) -> str:
        """Retorna contexto semántico completo de un archivo via LSP.

        Usa documentSymbol + hover + references para extraer:
        - Signatures con tipos
        - Métodos de clases
        - Referencias cross-file
        - Type hierarchy
        - Inlay hints
        - Type definitions

        Returns:
            String formateado con el contexto, o vacío si falla.
        """
        client = self.get_client(file_path)
        if not client:
            return ""

        try:
            source = Path(normalize_path(file_path)).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"LspAnalyzer: error reading {file_path}: {e}")
            return ""

        try:
            await client.open_file(file_path, source)
            symbols = await client.get_symbols(file_path)

            logger.debug(
                f"analyze_file({os.path.basename(file_path)}): {len(symbols)} symbols returned"
            )
            if symbols:
                logger.debug(f"analyze_file: sample symbol keys={list(symbols[0].keys())}")

            basename = os.path.basename(file_path)
            lines = [f"[LSP Context for {basename}]"]

            # Signatures
            sig_lines = await format_signatures(client, file_path, symbols, source)
            if sig_lines:
                lines.append("Signatures:")
                lines.extend(f"  {s}" for s in sig_lines)

            # Methods
            method_lines = await format_methods(client, file_path, symbols, source)
            if method_lines:
                lines.append("Methods:")
                lines.extend(method_lines)

            # References
            ref_lines = await format_references(client, file_path, symbols, source)
            if ref_lines:
                lines.append("References:")
                lines.extend(ref_lines)

            # Type Hierarchy
            hierarchy_lines = await format_type_hierarchy(
                client, file_path, symbols, source
            )
            if hierarchy_lines:
                lines.append("Type Hierarchy (subtypes):")
                lines.extend(hierarchy_lines)

            # Inlay Hints
            hint_lines = await format_inlay_hints(client, file_path)
            if hint_lines:
                lines.append("Inferred Types:")
                lines.extend(hint_lines)

            # Type Definitions
            typedef_lines = await format_type_definitions(
                client, file_path, symbols, source
            )
            if typedef_lines:
                lines.append("Type Definitions:")
                lines.extend(typedef_lines)

            if len(lines) <= 1:
                logger.debug(
                    f"analyze_file({basename}): no context generated (lines={len(lines)})"
                )
                return ""

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"LspAnalyzer: analyze_file failed for {file_path}: {e}")
            return ""

    # ── Analyzer: validación (PreToolUse Write|Edit) ──────────────────

    async def validate_file(self, file_path: str, content: str) -> list[dict]:
        """Valida código enviándolo a TODOS los LSPs y combinando diagnósticos.

        Usa operaciones atómicas (clear event → send → wait) para evitar
        race conditions con diagnósticos stale.

        Combina diagnósticos de todos los servidores para la extensión
        (ej: ty para type errors + ruff para lint errors).

        Returns:
            Lista de diagnósticos con severity=1 (errors) o severity=2 (warnings).
            Vacía si no hay servidor o si no hay problemas.
        """
        all_clients = self.get_all_clients(file_path)
        if not all_clients:
            return []

        all_diags = []
        for client in all_clients:
            try:
                uri = file_path_to_uri(file_path)
                if uri not in client._documents._version:
                    diags = await client.open_and_wait(file_path, content)
                else:
                    diags = await client.update_and_wait(file_path, content)
                all_diags.extend(d for d in diags if d.get("severity") in (1, 2))
            except Exception as e:
                cmd_name = (
                    client._transport.command[0] if client._transport else "unknown"
                )
                logger.warning(
                    f"LspAnalyzer: validate_file failed for {file_path} ({cmd_name}): {e}"
                )

        return all_diags

    def get_pre_edit_diagnostics(self, file_path: str) -> list[dict]:
        """Snapshot de diagnósticos actuales de TODOS los LSPs (no bloquea).

        Se llama antes de una edición para comparar después.
        Aplica el mismo filtro de severity que validate_file para
        que la comparación sea válida.
        """
        all_clients = self.get_all_clients(file_path)
        if not all_clients:
            return []
        all_diags = []
        for client in all_clients:
            all_diags.extend(
                d
                for d in client.get_cached_diagnostics(file_path)
                if d.get("severity") in (1, 2)
            )
        return all_diags

    # ── Analyzer: post-edit check (PostToolUse Write|Edit) ────────────

    def get_new_diagnostics(self, file_path: str, before: list[dict]) -> list[dict]:
        """Compara diagnósticos actuales vs snapshot anterior (de TODOS los LSPs).

        Retorna solo los diagnósticos nuevos (que no estaban antes).
        """
        all_clients = self.get_all_clients(file_path)
        if not all_clients:
            return []

        # Recopilar diagnósticos actuales de todos los clientes
        after = []
        for client in all_clients:
            after.extend(client.get_cached_diagnostics(file_path))
        if not after:
            return []

        # Comparar por mensaje (no por referencia)
        before_keys = set()
        for d in before:
            key = diag_key(d)
            if key:
                before_keys.add(key)

        new_diags = []
        for d in after:
            key = diag_key(d)
            if key and key not in before_keys:
                new_diags.append(d)

        return new_diags
