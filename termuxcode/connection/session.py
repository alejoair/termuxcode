#!/usr/bin/env python3
# ruff: noqa: ANN401
"""Session: encapsula TODOS los recursos de una pestaña.

Cada Session es completamente independiente:
- Su propio LspManager (servidores LSP con su rootUri)
- Su propio SDKClient (con hooks vinculados a su LspManager)
- Sus propios handlers (AskUserQuestion, ToolApproval)
- Su propio MessageProcessor y asyncio.Queue
"""

from __future__ import annotations

import asyncio
from typing import Any

from termuxcode.ws_config import logger
from termuxcode.connection.sdk_client import SDKClient
from termuxcode.connection.sender import MessageSender
from termuxcode.connection.ask_handler import AskUserQuestionHandler
from termuxcode.connection.tool_approval_handler import ToolApprovalHandler
from termuxcode.connection.message_processor import MessageProcessor
from termuxcode.connection.lsp_manager import LspManager
from termuxcode.connection.lsp.uri import file_path_to_uri
from termuxcode.connection import session_registry


BUILTIN_TOOLS = [
    {"name": "Agent", "desc": "Lanza agentes especializados", "source": "builtin"},
    {"name": "Bash", "desc": "Ejecuta comandos de terminal", "source": "builtin"},
    {"name": "Glob", "desc": "Busca archivos por patrón", "source": "builtin"},
    {"name": "Grep", "desc": "Busca contenido en archivos", "source": "builtin"},
    {"name": "Read", "desc": "Lee archivos", "source": "builtin"},
    {"name": "Edit", "desc": "Edita archivos", "source": "builtin"},
    {"name": "Write", "desc": "Crea/escribe archivos", "source": "builtin"},
    {"name": "NotebookEdit", "desc": "Edita celdas de Jupyter notebooks", "source": "builtin"},
    {"name": "TodoWrite", "desc": "Lista de tareas", "source": "builtin"},
    {"name": "WebSearch", "desc": "Búsqueda web", "source": "builtin"},
    {"name": "AskUserQuestion", "desc": "Pregunta al usuario", "source": "builtin"},
    {"name": "EnterPlanMode", "desc": "Entra en modo planificación", "source": "builtin"},
    {"name": "ExitPlanMode", "desc": "Sale del modo planificación", "source": "builtin"},
    {"name": "EnterWorktree", "desc": "Crea git worktree aislado", "source": "builtin"},
    {"name": "TaskOutput", "desc": "Obtiene resultado de tareas en segundo plano", "source": "builtin"},
    {"name": "TaskStop", "desc": "Detiene tarea en segundo plano", "source": "builtin"},
    {"name": "Skill", "desc": "Ejecuta skills especializados", "source": "builtin"},
    {"name": "ListMcpResourcesTool", "desc": "Lista recursos MCP", "source": "builtin"},
    {"name": "ReadMcpResourceTool", "desc": "Lee recurso MCP", "source": "builtin"},
]


class Session:
    """Encapsula todos los recursos de una pestaña. Completamente aislada."""

    def __init__(self, session_id: str | None, cwd: str, agent_options: dict,
                 connection: Any = None) -> None:
        """Inicializa la Session.

        Args:
            session_id: ID de sesión para reanudar (del frontend)
            cwd: Directorio de trabajo
            agent_options: Opciones del agente desde el frontend
            connection: Referencia al WebSocketConnection wrapper (para registry)
        """
        self.session_id = session_id
        self.cwd = cwd
        self.agent_options = agent_options
        self._connection = connection  # WebSocketConnection wrapper
        self._known_session_ids: set[str] = set()

        # Registrar session_id inicial en el registry si existe
        if session_id and connection:
            session_registry.register(session_id, connection)
            self._known_session_ids.add(session_id)

        # Recursos propios (ninguno compartido)
        self._lsp_manager: LspManager | None = None
        self._lsp_init_task: asyncio.Task | None = None
        self._sdk_client: SDKClient | None = None
        self._sender: MessageSender | None = None
        self._ask_handler: AskUserQuestionHandler | None = None
        self._tool_approval_handler: ToolApprovalHandler | None = None
        self._processor: MessageProcessor | None = None
        self._processor_task: asyncio.Task | None = None
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._lsp_editor_path: str | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def create(self, websocket: Any) -> None:
        """Crea sesión nueva: inicializa LSP, SDK, hooks, processor.

        Args:
            websocket: Conexión WebSocket del frontend
        """
        # 1. Sender
        self._sender = MessageSender(websocket)

        # Enviar historial de logs del servidor al frontend
        try:
            from termuxcode.connection.log_handler import get_log_history
            history = get_log_history()
            if history:
                await self._sender.send_message({
                    "type": "server_log_history",
                    "entries": history,
                })
        except Exception as e:
            logger.warning(f"Error enviando log history: {e}")

        # Enviar filetree inicial al frontend
        try:
            from termuxcode.connection.filetree_watcher import generate_filetree_json
            tree = generate_filetree_json(self.cwd)
            await self._sender.send_message({
                "type": "filetree_snapshot",
                "cwd": self.cwd,
                "entries": tree,
            })
        except Exception as e:
            logger.debug(f"Error enviando filetree inicial: {e}")

        # 2. LspManager propio (init en background para no bloquear)
        self._lsp_manager = LspManager()
        self._lsp_init_task = asyncio.create_task(
            self._init_lsp_background()
        )

        # 3. ToolApprovalHandler (su callback se pasa al SDK)
        self._tool_approval_handler = ToolApprovalHandler(
            session=self,
            agent_options=self.agent_options,
        )

        # 4. SDKClient con hooks vinculados a ESTE LspManager
        self._sdk_client = SDKClient(
            resume_id=self.session_id,
            cwd=self.cwd,
            can_use_tool=self._tool_approval_handler.can_use_tool,
            agent_options=self.agent_options,
            lsp_manager=self._lsp_manager,
        )
        await self._sdk_client.connect()

        # Sincronizar estado de MCP servers: deshabilitar/habilitar explícitamente
        # para sobrescribir cualquier estado heredado de la sesión anterior (resume).
        # Si disabledMcpServers viene en las opciones, es reconexión: habilitar los
        # que NO están en la lista, deshabilitar los que sí.
        # Si no viene (sesión nueva): deshabilitar todos por defecto.
        has_explicit_prefs = 'disabledMcpServers' in self.agent_options
        disabled_set = set(self.agent_options.get('disabledMcpServers', []))
        mcp_status = await self._sdk_client.get_mcp_status()
        all_servers = [s['name'] for s in mcp_status.get('mcpServers', [])]
        for name in all_servers:
            try:
                if has_explicit_prefs:
                    if name in disabled_set:
                        await self._sdk_client.toggle_mcp_server(name, False)
                    else:
                        await self._sdk_client.toggle_mcp_server(name, True)
                else:
                    await self._sdk_client.toggle_mcp_server(name, False)
            except Exception as e:
                logger.warning(f"No se pudo cambiar estado de MCP '{name}': {e}")
        if not has_explicit_prefs:
            logger.info(f"Sesión nueva: todos los MCP servers deshabilitados por defecto")
        else:
            if disabled_set:
                logger.info(f"MCP servers desactivados al reconectar: {sorted(disabled_set)}")
            enabled = [n for n in all_servers if n not in disabled_set]
            if enabled:
                logger.info(f"MCP servers habilitados al reconectar: {enabled}")

        # Enviar lista de tools al frontend tras dar tiempo a MCP servers de conectar
        asyncio.create_task(self._send_tools_list())

        # Ahora que el SDK está conectado, darle referencia al approval handler
        self._tool_approval_handler._sdk_client = self._sdk_client

        # 5. AskHandler
        self._ask_handler = AskUserQuestionHandler(session=self)
        self._tool_approval_handler._ask_handler = self._ask_handler

        # 6. Callback para actualizar registry cuando el SDK genera nuevo session_id
        async def on_session_id_update(new_session_id: str) -> None:
            if new_session_id and self._connection:
                session_registry.register(new_session_id, self._connection)
                self._known_session_ids.add(new_session_id)
                self.session_id = new_session_id

        # 7. MessageProcessor
        rolling_window = self.agent_options.get('rolling_window', 100)
        self._processor = MessageProcessor(
            sdk_client=self._sdk_client,
            sender=self._sender,
            ask_handler=self._ask_handler,
            tool_approval_handler=self._tool_approval_handler,
            cwd=self.cwd,
            session_id=self.session_id,
            rolling_window=rolling_window,
            on_session_id_update=on_session_id_update,
        )

        # Callback para cuando se rechaza un plan
        async def on_plan_rejected() -> None:
            self._processor._stop_event.set()
            await self._sender.send_system_message("Plan rechazado")

        self._tool_approval_handler._on_plan_rejected = on_plan_rejected

        # 8. Lanzar processor en background
        self._processor_task = asyncio.create_task(
            self._processor.start_processing(self.message_queue)
        )

        logger.info(f"Session created: cwd={self.cwd}, session_id={self.session_id}")

    async def _wait_for_mcp_ready(self, timeout: float = 15.0, poll_interval: float = 0.5) -> dict:
        """Espera a que los MCP servers terminen de conectar (ninguno en estado 'pending').

        Hace polling de get_mcp_status() hasta que todos los servers tengan un estado
        definitivo (connected, failed, disabled, etc.) o se alcance el timeout.

        Args:
            timeout: Tiempo máximo de espera en segundos
            poll_interval: Intervalo entre consultas en segundos

        Returns:
            Último resultado de get_mcp_status()
        """
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            mcp_status = await self._sdk_client.get_mcp_status()
            servers = mcp_status.get("mcpServers", [])

            # Si no hay servers configurados, no hay nada que esperar
            if not servers:
                return mcp_status

            pending = [s["name"] for s in servers if s.get("status") == "pending"]
            if not pending:
                return mcp_status

            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                logger.warning(f"Timeout esperando MCP servers: {pending} siguen en pending")
                return mcp_status

            await asyncio.sleep(min(poll_interval, remaining))

    async def _send_tools_list(self, wait_for_mcp: bool = True) -> None:
        """Espera a que los MCP servers estén listos y envía la lista de tools al frontend.

        Args:
            wait_for_mcp: Si True, espera polling hasta que no haya servers en 'pending'.
                          Si False, consulta el estado inmediatamente (re-attach).
        """
        try:
            if not self._sdk_client or not self._sdk_client.is_connected:
                return

            if wait_for_mcp:
                mcp_status = await self._wait_for_mcp_ready()
            else:
                mcp_status = await self._sdk_client.get_mcp_status()
            mcp_tools = []
            disabled = set(self.agent_options.get('disabledMcpServers', []))
            for server in mcp_status.get("mcpServers", []):
                if server.get("status") == "connected" and server["name"] not in disabled:
                    for tool in server.get("tools", []):
                        mcp_tools.append({
                            "name": tool["name"],
                            "desc": tool.get("description", ""),
                            "source": "mcp",
                            "server": server["name"],
                            "mcp_name": f"mcp__{server['name']}__{tool['name']}",
                        })
            all_tools = BUILTIN_TOOLS + mcp_tools
            await self._sender.send_tools_list(all_tools)
            logger.info(f"Tools list enviada: {len(BUILTIN_TOOLS)} builtins + {len(mcp_tools)} MCP")
            # Enviar estado detallado de MCP servers al frontend
            await self._send_mcp_status(mcp_status)
        except Exception as e:
            logger.warning(f"Error enviando tools list: {e}")

    async def _send_mcp_status(self, mcp_status: dict | None = None) -> None:
        """Consulta el estado de los MCP servers y lo envía al frontend.

        Args:
            mcp_status: Resultado pre-obtenido de get_mcp_status(), o None para consultarlo.
        """
        if not self._sdk_client or not self._sdk_client.is_connected:
            return
        try:
            if mcp_status is None:
                mcp_status = await self._sdk_client.get_mcp_status()
            servers = []
            for s in mcp_status.get("mcpServers", []):
                tools = s.get("tools", [])
                servers.append({
                    "name": s.get("name", ""),
                    "status": s.get("status", "unknown"),
                    "tools": [
                        {"name": t["name"], "desc": t.get("description", "")}
                        for t in tools
                    ],
                    "error": s.get("error"),
                })
                logger.info(f"MCP server '{s.get('name')}': status={s.get('status')}, tools={len(tools)}, error={s.get('error')}")
            await self._sender.send_mcp_status(servers)
            logger.debug(f"MCP status enviado: {len(servers)} servers")
        except Exception as e:
            logger.warning(f"Error enviando mcp_status: {e}")

    async def resume(self, websocket: Any, agent_options: dict | None = None,
                     cwd: str | None = None) -> None:
        """Reanuda sesión: re-attach WebSocket o rebuild según cambios.

        Si no cambiaron las opciones ni el CWD, solo re-attacha el WebSocket
        nuevo al sender existente. El SDK sigue vivo y las respuestas en vuelo
        se entregan normalmente via replay_buffer().

        Si cambiaron opciones o CWD, destruye y recrea todo (comportamiento anterior).

        Args:
            websocket: Nueva conexión WebSocket
            agent_options: Nuevas opciones del agente
            cwd: Nuevo directorio de trabajo
        """
        if not self._needs_rebuild(agent_options, cwd):
            # Re-attach: solo actualizar WebSocket, SDK sigue vivo
            if cwd:
                self.cwd = cwd
            if agent_options:
                self.agent_options = agent_options
            self._sender.set_websocket(websocket)
            await self._sender.replay_buffer()
            asyncio.create_task(self._send_tools_list(wait_for_mcp=False))

            # Reenviar filetree al frontend reconectado
            try:
                from termuxcode.connection.filetree_watcher import generate_filetree_json
                tree = generate_filetree_json(self.cwd)
                await self._sender.send_message({
                    "type": "filetree_snapshot",
                    "cwd": self.cwd,
                    "entries": tree,
                })
            except Exception as e:
                logger.debug(f"Error enviando filetree en resume: {e}")
            logger.info(
                f"Session re-attached (no rebuild): session_id={self.session_id}"
            )
            return

        # Rebuild: opciones o CWD cambiaron
        if cwd:
            self.cwd = cwd
        if agent_options:
            self.agent_options = agent_options

        # Destruir todo
        await self._destroy_resources()

        # Recrear con nuevo WebSocket
        await self.create(websocket)

        logger.info(f"Session rebuilt: cwd={self.cwd}, session_id={self.session_id}")

    async def destroy(self) -> None:
        """Cleanup total: LSP shutdown, SDK disconnect, cancel tasks, limpiar registry."""
        await self._destroy_resources()

        # Limpiar registry
        for sid in self._known_session_ids:
            session_registry.unregister(sid)
        self._known_session_ids.clear()

        logger.info(f"Session destroyed: session_id={self.session_id}")

    # ── WebSocket attach/detach ────────────────────────────────────────

    def attach_websocket(self, ws: Any) -> None:
        """Actualiza el WebSocket del sender."""
        if self._sender:
            self._sender.set_websocket(ws)

    def detach_websocket(self) -> None:
        """Desconecta WebSocket sin destruir la sesión (para reconexión)."""
        if self._sender:
            self._sender.set_websocket(None)

        # Cancelar esperas activas para desbloquear el SDK
        if self._tool_approval_handler:
            self._tool_approval_handler.cancel()
        if self._ask_handler:
            self._ask_handler.cancel()

    # ── Message dispatch ───────────────────────────────────────────────

    async def handle_message(self, data: dict) -> None:
        """Despacha un mensaje del WebSocket al handler correcto.

        Args:
            data: Mensaje parseado del WebSocket
        """
        if data.get('command') == '/stop':
            await self._processor.request_stop()
        elif data.get('type') == 'tool_approval_response':
            self._tool_approval_handler.handle_response(data)
        elif data.get('type') == 'question_response':
            await self._ask_handler.handle_response(
                data.get("responses"),
                cancelled=data.get("cancelled", False)
            )
        elif data.get('type') == 'request_buffer_replay':
            await self._sender.replay_buffer()
        elif data.get('type') == 'request_mcp_status':
            mcp_status = await self._wait_for_mcp_ready()
            await self._send_mcp_status(mcp_status)
        elif data.get('type') == 'lsp_document_open':
            await self._handle_lsp_document_open(data)
        elif data.get('type') == 'lsp_document_close':
            await self._handle_lsp_document_close(data)
        elif data.get('type') == 'lsp_request':
            await self._handle_lsp_request(data)
        elif data.get('type') == 'lsp_notification':
            await self._handle_lsp_notification(data)
        else:
            try:
                self.message_queue.put_nowait(data)
            except asyncio.QueueFull:
                logger.warning("Cola de mensajes llena, descartando mensaje antiguo")
                await self.message_queue.get()
                await self.message_queue.put(data)

    # ── Send message ───────────────────────────────────────────────────

    async def send_message(self, msg: dict) -> None:
        """Envía un mensaje al frontend (delegado al sender).

        Args:
            msg: Diccionario con el mensaje a enviar
        """
        await self._sender.send_message(msg)

    # ── Internos ───────────────────────────────────────────────────────

    async def _get_lsp_client(self, file_path: str, timeout: float = 5.0) -> LSPClient | None:
        """Espera a que LspManager esté inicializado y retorna el cliente LSP.

        Args:
            file_path: Path absoluto del archivo
            timeout: Tiempo máximo de espera en segundos

        Returns:
            LSPClient o None si no está disponible
        """
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            if self._lsp_manager and self._lsp_manager._initialized:
                return self._lsp_manager.get_client(file_path)
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return None
            await asyncio.sleep(min(0.5, remaining))

    async def _handle_lsp_document_open(self, data: dict) -> None:
        """Abre un archivo en el LSP para el editor sidebar."""
        file_path = data.get('file_path', '')
        content = data.get('content', '')
        if not file_path:
            return

        # Resolver path relativo a absoluto
        import os
        abs_path = file_path if os.path.isabs(file_path) else os.path.normpath(os.path.join(self.cwd, file_path))

        client = await self._get_lsp_client(abs_path)
        if not client:
            await self._sender.send_message({
                "type": "lsp_open_result",
                "uri": file_path_to_uri(abs_path),
                "capabilities": {},
                "error": "No LSP server available for this file type",
            })
            return

        # Registrar callback de diagnostics que envía al frontend
        async def _on_diagnostics(uri: str, diagnostics: list) -> None:
            await self._sender.send_message({
                "type": "lsp_notification",
                "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": diagnostics},
            })

        client.set_diagnostics_callback(_on_diagnostics)

        # Abrir o actualizar archivo en el LSP
        try:
            # Check si el agente ya tiene este archivo abierto
            if client._documents._version.get(file_path_to_uri(abs_path), 0) > 0:
                await client.update_file(abs_path, content)
            else:
                await client.open_file(abs_path, content)
        except Exception as e:
            logger.warning(f"Error abriendo archivo en LSP: {e}")

        self._lsp_editor_path = abs_path

        await self._sender.send_message({
            "type": "lsp_open_result",
            "uri": file_path_to_uri(abs_path),
            "capabilities": client._server_capabilities,
        })

    async def _handle_lsp_document_close(self, data: dict) -> None:
        """Cierra un archivo en el LSP."""
        file_path = data.get('file_path', '')
        if not file_path or not self._lsp_editor_path:
            return

        try:
            client = await self._get_lsp_client(self._lsp_editor_path, timeout=1.0)
            if client:
                client.set_diagnostics_callback(None)
                await client.close_file(self._lsp_editor_path)
        except Exception as e:
            logger.debug(f"Error cerrando archivo en LSP: {e}")
        finally:
            self._lsp_editor_path = None

    async def _handle_lsp_request(self, data: dict) -> None:
        """Forward de un request LSP del editor al servidor."""
        lsp_id = data.get('lsp_id')
        method = data.get('method', '')
        params = data.get('params')

        if not self._lsp_editor_path:
            await self._sender.send_message({
                "type": "lsp_response",
                "lsp_id": lsp_id,
                "error": {"code": -1, "message": "No document open"},
            })
            return

        client = await self._get_lsp_client(self._lsp_editor_path, timeout=2.0)
        if not client:
            await self._sender.send_message({
                "type": "lsp_response",
                "lsp_id": lsp_id,
                "error": {"code": -1, "message": "LSP not available"},
            })
            return

        try:
            result = await client.send_raw_request(method, params, timeout=10.0)
            await self._sender.send_message({
                "type": "lsp_response",
                "lsp_id": lsp_id,
                "result": result,
            })
        except Exception as e:
            await self._sender.send_message({
                "type": "lsp_response",
                "lsp_id": lsp_id,
                "error": {"code": -1, "message": str(e)},
            })

    async def _handle_lsp_notification(self, data: dict) -> None:
        """Forward de una notificación LSP del editor al servidor."""
        method = data.get('method', '')
        params = data.get('params')

        if not self._lsp_editor_path:
            return

        client = await self._get_lsp_client(self._lsp_editor_path, timeout=2.0)
        if not client:
            return

        try:
            await client.send_raw_notification(method, params)
        except Exception as e:
            logger.debug(f"Error enviando notificación LSP: {e}")

    def _needs_rebuild(self, agent_options: dict | None = None, cwd: str | None = None) -> bool:
        """Determina si se necesita reconstruir el SDK al reconectar.

        Returns:
            True si algo cambió que requiere rebuild (modelo, CWD, opciones)
        """
        if cwd and cwd != self.cwd:
            return True
        if agent_options:
            rebuild_keys = {
                'model', 'system_prompt', 'append_system_prompt',
                'max_turns', 'permission_mode', 'tools',
            }
            for key in rebuild_keys:
                if agent_options.get(key) != self.agent_options.get(key):
                    return True
            # disabledMcpServers es un conjunto (el orden no importa)
            old_disabled = set(self.agent_options.get('disabledMcpServers') or [])
            new_disabled = set(agent_options.get('disabledMcpServers') or [])
            if old_disabled != new_disabled:
                return True
        return False

    async def _init_lsp_background(self) -> None:
        """Inicializa el LspManager en background (no bloquea al usuario)."""
        try:
            await self._lsp_manager.initialize(self.cwd)
            logger.info(
                f"Session LSP initialized: {len(self._lsp_manager._clients)} server(s) "
                f"for cwd={self.cwd}"
            )
        except Exception as e:
            logger.warning(f"Session LSP init failed for cwd={self.cwd}: {e}")

    async def _destroy_resources(self) -> None:
        """Destruye todos los recursos de la sesión (sin limpiar registry)."""
        # Cancelar processor
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None

        # Desconectar SDK
        if self._sdk_client:
            await self._sdk_client.disconnect()
            self._sdk_client = None

        # Apagar LSP
        if self._lsp_manager:
            await self._lsp_manager.shutdown()
            self._lsp_manager = None

        # Cancelar LSP init task si aún está corriendo
        if self._lsp_init_task:
            self._lsp_init_task.cancel()
            try:
                await self._lsp_init_task
            except asyncio.CancelledError:
                pass
            self._lsp_init_task = None

        # Resetear handlers
        if self._ask_handler:
            self._ask_handler.reset()
            self._ask_handler = None

        if self._tool_approval_handler:
            self._tool_approval_handler.reset()
            self._tool_approval_handler = None

        # Limpiar referencias
        self._processor = None
        self._sender = None
        self._lsp_editor_path = None
