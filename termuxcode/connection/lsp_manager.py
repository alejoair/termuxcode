#!/usr/bin/env python3
"""LSP Manager: registry de servidores + facade para análisis."""

import os
import shutil

from termuxcode.connection.lsp import LSPClient
from termuxcode.connection.lsp_analyzer import SERVERS, LspAnalyzer
from termuxcode.ws_config import logger


class LspManager:
    """Facade: lifecycle + registry + delega análisis a LspAnalyzer.

    Responsabilidades:
    - Lifecycle: inicia y apaga servidores LSP
    - Registry: mapea extensiones → lista de clientes LSP activos
    - Analyzer: delega a LspAnalyzer para enriquecer hooks del SDK
    """

    def __init__(self) -> None:
        self._clients: dict[str, list[LSPClient]] = {}  # extensión → [clientes]
        self._analyzer: LspAnalyzer | None = None
        self._initialized = False

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self, cwd: str) -> None:
        """Inicia los servidores LSP disponibles.

        Por cada entrada en SERVERS, verifica si el comando está instalado
        y arranca el servidor. Un servidor que falle no bloquea los demás.
        """
        for ext, cmds in SERVERS.items():
            for cmd in cmds:
                try:
                    if not shutil.which(cmd[0]):
                        logger.debug(f"LspManager: {cmd[0]} not found, skipping {ext}")
                        continue

                    client = LSPClient(cmd, cwd)
                    await client.start()
                    if ext not in self._clients:
                        self._clients[ext] = []
                    self._clients[ext].append(client)
                    logger.info(f"LspManager: {cmd[0]} started for {ext}")
                except Exception as e:
                    logger.warning(f"LspManager: failed to start {cmd[0]} for {ext}: {e}")

        self._analyzer = LspAnalyzer(self._clients)
        self._initialized = True
        total = sum(len(v) for v in self._clients.values())
        logger.info(
            f"LspManager: initialized with {total} server(s) for {len(self._clients)} language(s)"
        )

    async def shutdown(self) -> None:
        """Apaga todos los servidores LSP."""
        for ext, clients in self._clients.items():
            for client in clients:
                try:
                    await client.shutdown()
                except Exception as e:
                    logger.warning(f"LspManager: error shutting down {ext}: {e}")
        self._clients.clear()
        self._analyzer = None
        self._initialized = False
        logger.info("LspManager: shut down")

    # ── Registry ───────────────────────────────────────────────────────

    def get_client(self, file_path: str) -> LSPClient | None:
        """Retorna el cliente LSP principal para la extensión del archivo.

        El primer cliente es el principal (ty para .py), usado para
        analyze_file (hover, references, symbols).
        """
        _, ext = os.path.splitext(file_path)
        clients = self._clients.get(ext)
        return clients[0] if clients else None

    def get_all_clients(self, file_path: str) -> list[LSPClient]:
        """Retorna TODOS los clientes LSP para la extensión.

        Usado para validate_file, get_pre_edit_diagnostics, etc.
        donde queremos combinar diagnósticos de todos los servidores.
        """
        _, ext = os.path.splitext(file_path)
        return self._clients.get(ext, [])

    def is_supported_file(self, file_path: str) -> bool:
        """True si hay un servidor LSP activo para esta extensión."""
        return self.get_client(file_path) is not None

    # ── Analyzer: delegados a LspAnalyzer ──────────────────────────────

    async def analyze_file(self, file_path: str) -> str:
        """Retorna contexto semántico completo de un archivo via LSP."""
        if not self._analyzer:
            return ""
        return await self._analyzer.analyze_file(file_path)

    async def validate_file(self, file_path: str, content: str) -> list[dict]:
        """Valida código enviándolo a TODOS los LSPs y combinando diagnósticos."""
        if not self._analyzer:
            return []
        return await self._analyzer.validate_file(file_path, content)

    def get_pre_edit_diagnostics(self, file_path: str) -> list[dict]:
        """Snapshot de diagnósticos actuales de TODOS los LSPs (no bloquea)."""
        if not self._analyzer:
            return []
        return self._analyzer.get_pre_edit_diagnostics(file_path)

    def get_new_diagnostics(self, file_path: str, before: list[dict]) -> list[dict]:
        """Compara diagnósticos actuales vs snapshot anterior."""
        if not self._analyzer:
            return []
        return self._analyzer.get_new_diagnostics(file_path, before)
