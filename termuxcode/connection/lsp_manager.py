#!/usr/bin/env python3
"""LSP Manager: registry de servidores + analyzer semántico combinados."""

import os
import shutil
from pathlib import Path

from termuxcode.connection.lsp import LSPClient, file_path_to_uri, uri_to_file_path
from termuxcode.ws_config import logger

# Configuración de servidores LSP por extensión
SERVERS: dict[str, list[str]] = {
    ".py":  ["pylsp"],
    ".ts":  ["typescript-language-server", "--stdio"],
    ".js":  ["typescript-language-server", "--stdio"],
    ".tsx": ["typescript-language-server", "--stdio"],
    ".jsx": ["typescript-language-server", "--stdio"],
    ".go":  ["gopls"],
}

# SymbolKind del protocolo LSP
_SYMBOL_KINDS: dict[int, str] = {
    1: "File", 2: "Module", 3: "Namespace", 4: "Package",
    5: "Class", 6: "Method", 7: "Property", 8: "Field",
    9: "Constructor", 10: "Enum", 11: "Interface", 12: "Function",
    13: "Variable", 14: "Constant", 15: "String", 16: "Number",
    17: "Boolean", 18: "Array", 19: "Object", 20: "Key",
    21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
    25: "Operator", 26: "TypeParameter",
}


class LspManager:
    """Maneja servidores LSP y provee análisis semántico multi-lenguaje.

    Responsabilidades:
    - Registry: mapea extensiones → clientes LSP activos
    - Analyzer: usa los clientes para enriquecer hooks del SDK
    """

    def __init__(self):
        self._clients: dict[str, LSPClient] = {}  # extensión → cliente
        self._initialized = False

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self, cwd: str) -> None:
        """Inicia los servidores LSP disponibles.

        Por cada entrada en SERVERS, verifica si el comando está instalado
        y arranca el servidor. Un servidor que falle no bloquea los demás.
        """
        for ext, cmd in SERVERS.items():
            try:
                if not shutil.which(cmd[0]):
                    logger.debug(f"LspManager: {cmd[0]} not found, skipping {ext}")
                    continue

                client = LSPClient(cmd, cwd)
                await client.start()
                self._clients[ext] = client
                logger.info(f"LspManager: {cmd[0]} started for {ext}")
            except Exception as e:
                logger.warning(f"LspManager: failed to start {cmd[0]} for {ext}: {e}")

        self._initialized = True
        logger.info(f"LspManager: initialized with {len(self._clients)} server(s)")

    async def shutdown(self) -> None:
        """Apaga todos los servidores LSP."""
        for ext, client in self._clients.items():
            try:
                await client.shutdown()
            except Exception as e:
                logger.warning(f"LspManager: error shutting down {ext}: {e}")
        self._clients.clear()
        self._initialized = False
        logger.info("LspManager: shut down")

    # ── Registry ───────────────────────────────────────────────────────

    def get_client(self, file_path: str) -> LSPClient | None:
        """Retorna el cliente LSP para la extensión del archivo."""
        _, ext = os.path.splitext(file_path)
        return self._clients.get(ext)

    def is_supported_file(self, file_path: str) -> bool:
        """True si hay un servidor LSP activo para esta extensión."""
        return self.get_client(file_path) is not None

    # ── Analyzer: contexto semántico (PostToolUse Read) ────────────────

    async def analyze_file(self, file_path: str) -> str:
        """Retorna contexto semántico completo de un archivo via LSP.

        Usa documentSymbol + hover + references para extraer:
        - Signatures con tipos
        - Métodos de clases
        - Referencias cross-file
        - Imports

        Returns:
            String formateado con el contexto, o vacío si falla.
        """
        client = self.get_client(file_path)
        if not client:
            return ""

        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"LspManager: error reading {file_path}: {e}")
            return ""

        try:
            await client.open_file(file_path, source)
            symbols = await client.get_symbols(file_path)

            logger.debug(f"analyze_file({os.path.basename(file_path)}): {len(symbols)} symbols returned")
            if symbols:
                logger.debug(f"analyze_file: sample symbol keys={list(symbols[0].keys())}")

            basename = os.path.basename(file_path)
            lines = [f"[LSP Context for {basename}]"]

            # ── Signatures (símbolos top-level con hover) ──
            # pylsp retorna SymbolInformation[] con "location.range"
            # Solo incluir kinds significativos: Class, Function, Method, Constructor, Interface
            _MEANINGFUL_KINDS = {5, 6, 9, 11, 12, 23}  # Class, Method, Constructor, Interface, Function, Struct
            top_syms = [s for s in symbols if ("location" in s or "range" in s) and s.get("kind") in _MEANINGFUL_KINDS]
            logger.debug(f"analyze_file: {len(top_syms)}/{len(symbols)} meaningful symbols")
            if top_syms:
                sig_lines = []
                for sym in top_syms:
                    try:
                        sig = await self._format_symbol_with_hover(
                            client, file_path, sym, source
                        )
                        if sig:
                            sig_lines.append(sig)
                    except Exception:
                        sig_lines.append(self._format_symbol_bare(sym))
                if sig_lines:
                    lines.append("Signatures:")
                    lines.extend(f"  {s}" for s in sig_lines)

            # ── Methods (métodos dentro de clases) ──
            # pylsp usa SymbolInformation plano con containerName en vez de children
            # Agrupar métodos por su containerName (clase padre)
            classes = {s["name"] for s in top_syms if s.get("kind") == 5}  # Class
            method_lines = []
            for sym in top_syms:
                kind = sym.get("kind", 0)
                container = sym.get("containerName")
                if kind in (6, 9, 12) and container in classes:  # Method/Constructor/Function dentro de clase
                    try:
                        hover = await self._safe_hover(
                            client, file_path, sym, source
                        )
                        if hover:
                            method_lines.append(
                                f"    L{self._sym_line(sym)}: {hover}"
                            )
                        else:
                            method_lines.append(
                                f"    L{self._sym_line(sym)}: {sym['name']}()"
                            )
                    except Exception:
                        method_lines.append(
                            f"    L{self._sym_line(sym)}: {sym['name']}()"
                        )
            if method_lines:
                lines.append("Methods:")
                lines.extend(method_lines)

            # ── References (símbolos top-level function/class) ──
            ref_lines = []
            symbols_checked = 0
            for sym in top_syms:
                kind = sym.get("kind", 0)
                if kind not in (5, 12, 23):  # Class, Function, Struct
                    continue
                if symbols_checked >= 10:
                    break
                try:
                    refs = await client.get_references(
                        file_path,
                        self._sym_line(sym),
                        self._sym_col(sym, source),
                    )
                    if not refs:
                        continue
                    name = sym["name"]
                    ref_lines.append(f"  {name} -> {len(refs)} usage(s):")
                    for r in refs[:8]:
                        r_uri = r.get("uri", "")
                        r_path = uri_to_file_path(r_uri)
                        r_file = os.path.basename(r_path)
                        r_line = r.get("range", {}).get("start", {}).get("line", "?")
                        ref_lines.append(f"    {r_file} L{r_line}")
                    if len(refs) > 8:
                        ref_lines.append(f"    ... +{len(refs) - 8} more")
                    symbols_checked += 1
                except Exception:
                    continue

            if ref_lines:
                lines.append("References:")
                lines.extend(ref_lines)

            if len(lines) <= 1:
                logger.debug(f"analyze_file({basename}): no context generated (lines={len(lines)})")
                return ""

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"LspManager: analyze_file failed for {file_path}: {e}")
            return ""

    # ── Analyzer: validación (PreToolUse Write|Edit) ──────────────────

    async def validate_file(self, file_path: str, content: str) -> list[dict]:
        """Valida código enviándolo al LSP y esperando diagnósticos.

        Usa operaciones atómicas (clear event → send → wait) para evitar
        race conditions con diagnósticos stale.

        Returns:
            Lista de diagnósticos con severity=1 (errors) o severity=2 (warnings).
            Vacía si no hay servidor o si no hay problemas.
        """
        client = self.get_client(file_path)
        if not client:
            return []

        try:
            uri = file_path_to_uri(file_path)
            if uri not in client._version:
                diags = await client.open_and_wait(file_path, content)
            else:
                diags = await client.update_and_wait(file_path, content)
            # Incluir errors (1) y warnings (2) - esto incluye Ruff ANN001/ANN201/ANN202
            return [d for d in diags if d.get("severity") in (1, 2)]
        except Exception as e:
            logger.warning(f"LspManager: validate_file failed for {file_path}: {e}")
            return []

    def get_pre_edit_diagnostics(self, file_path: str) -> list[dict]:
        """Snapshot de diagnósticos actuales (no bloquea, lee cache).

        Se llama antes de una edición para comparar después.
        Aplica el mismo filtro de severity que validate_file para
        que la comparación sea válida.
        """
        client = self.get_client(file_path)
        if not client:
            return []
        return [d for d in client.get_cached_diagnostics(file_path)
                if d.get("severity") in (1, 2)]

    # ── Analyzer: post-edit check (PostToolUse Write|Edit) ────────────

    def get_new_diagnostics(self, file_path: str, before: list[dict]) -> list[dict]:
        """Compara diagnósticos actuales vs snapshot anterior.

        Retorna solo los diagnósticos nuevos (que no estaban antes).
        """
        client = self.get_client(file_path)
        if not client:
            return []

        after = client.get_cached_diagnostics(file_path)
        if not after:
            return []

        # Comparar por mensaje + rango (no por referencia)
        before_keys = set()
        for d in before:
            key = self._diag_key(d)
            if key:
                before_keys.add(key)

        new_diags = []
        for d in after:
            key = self._diag_key(d)
            if key and key not in before_keys:
                new_diags.append(d)

        return new_diags

    # ── Helpers ────────────────────────────────────────────────────────

    async def _format_symbol_with_hover(
        self, client: LSPClient, file_path: str, sym: dict, source: str
    ) -> str | None:
        """Formatea un símbolo con su hover (tipo/signature completa)."""
        line = self._sym_line(sym)
        col = self._sym_col(sym, source)
        hover = await client.get_hover(file_path, line, col)
        if hover:
            # Limpiar el hover: sacar líneas vacías, limitar
            hover_text = hover.strip().split("\n")[0]
            return f"L{line}: {hover_text}"
        return None

    def _format_symbol_bare(self, sym: dict) -> str:
        """Formatea un símbolo sin hover (fallback)."""
        kind_name = _SYMBOL_KINDS.get(sym.get("kind", 0), "Unknown")
        line = self._sym_line(sym)
        return f"L{line}: [{kind_name}] {sym['name']}"

    async def _safe_hover(
        self, client: LSPClient, file_path: str, sym: dict, source: str
    ) -> str | None:
        """Hover seguro que no lanza excepciones."""
        try:
            return await client.get_hover(
                file_path, self._sym_line(sym), self._sym_col(sym, source)
            )
        except Exception:
            return None

    @staticmethod
    def _sym_line(sym: dict) -> int:
        """Extrae línea de inicio de un símbolo (0-based → 1-based para hover).

        pylsp retorna SymbolInformation[] con ``location.range``;
        otros servers (tsserver, gopls) pueden usar ``range`` directo.
        """
        try:
            rng = sym.get("location", {}).get("range") or sym.get("range")
            return rng["start"]["line"]
        except (KeyError, TypeError):
            return 0

    @staticmethod
    def _sym_col(sym: dict, source: str = "") -> int:
        """Extrae columna del nombre del símbolo buscando en el source.

        pylsp retorna SymbolInformation[] con ``location.range`` que apunta
        al inicio de la línea (columna 0), no al nombre. Buscamos el nombre
        en el source para obtener la columna correcta para hover.

        Args:
            sym: Símbolo del LSP con 'name' y 'location.range'
            source: Contenido del archivo (opcional para backward compatibility)
        """
        try:
            rng = sym.get("location", {}).get("range") or sym.get("range")
            line_idx = rng["start"]["line"]
            name = sym.get("name", "")

            # Si tenemos source, buscar el nombre en la línea
            if source and name:
                lines = source.split("\n")
                if line_idx < len(lines):
                    line_text = lines[line_idx]
                    col = line_text.find(name)
                    if col >= 0:
                        return col

            # Fallback: usar columna del range (generalmente 0)
            return rng["start"]["character"]
        except (KeyError, TypeError):
            return 0

    @staticmethod
    def _diag_key(diag: dict) -> str | None:
        """Clave para comparar diagnósticos por mensaje (sin línea).

        Usa solo el mensaje para evitar falsos positivos cuando un edit
        agrega/remueve líneas y los diagnósticos preexistentes shift de línea.
        """
        msg = diag.get("message", "")
        return msg if msg else None
