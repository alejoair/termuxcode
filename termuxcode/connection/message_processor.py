#!/usr/bin/env python3
"""Procesamiento de mensajes del WebSocket."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

import websockets

from termuxcode.connection.history_manager import truncate_history
from termuxcode.ws_config import logger

if TYPE_CHECKING:
    from termuxcode.connection.ask_handler import AskUserQuestionHandler
    from termuxcode.connection.sdk_client import SDKClient
    from termuxcode.connection.sender import MessageSender
    from termuxcode.connection.tool_approval_handler import ToolApprovalHandler


class MessageProcessor:
    """Procesa mensajes del WebSocket y maneja la comunicación con el SDK."""

    def __init__(
        self,
        sdk_client: SDKClient,
        sender: MessageSender,
        ask_handler: AskUserQuestionHandler | None = None,
        tool_approval_handler: ToolApprovalHandler | None = None,
        cwd: str | None = None,
        session_id: str | None = None,
        rolling_window: int = 100,
        on_session_id_update: Callable[[str], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Inicializa el procesador.

        Args:
            sdk_client: Instancia de SDKClient
            sender: Instancia de MessageSender
            ask_handler: Handler para AskUserQuestion
            tool_approval_handler: Handler para tool approval
            cwd: Directorio de trabajo
            session_id: ID de sesión inicial (del frontend, para reconexión)
            rolling_window: Número de líneas a conservar en historial
            on_session_id_update: Callback async que se llama cuando el SDK envía un nuevo session_id
        """
        self._sdk_client = sdk_client
        self._sender = sender
        self._ask_handler = ask_handler
        self._tool_approval_handler = tool_approval_handler
        self._cwd = cwd
        self._session_id = session_id
        self._rolling_window = rolling_window
        self._on_session_id_update = on_session_id_update
        self._message_queue: asyncio.Queue[dict[str, Any]] | None = None  # Se setea en start_processing
        self._stop_event = asyncio.Event()  # Señal de detención

    async def start_processing(self, message_queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Procesa mensajes de la cola continuamente (tarea de fondo).

        Args:
            message_queue: Cola de mensajes entrantes
        """
        self._message_queue = message_queue

        while True:
            data = await message_queue.get()
            try:
                await self.process_message(data)
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}", exc_info=True)

    async def process_message(self, data: dict[str, Any]) -> None:
        """Procesa un mensaje recibido del WebSocket.

        Args:
            data: Diccionario con el mensaje
        """
        command = data.get("command")
        content = data.get("content", "")

        if command == "/disconnect":
            await self._handle_disconnect()
        elif content:
            await self._handle_query(content)

    async def request_stop(self) -> None:
        """Señala detención e interrumpe el SDK."""
        self._stop_event.set()
        try:
            await self._sdk_client.interrupt()
        except Exception as e:
            logger.warning(f"Error al interrumpir SDK: {e}")
        await self._sender.send_system_message("Deteniendo...")

    async def _handle_disconnect(self) -> None:
        """Maneja el comando /disconnect.

        Envía mensaje de despedida y retorna. El base.py detecta
        que el mensaje era /disconnect y cierra el WebSocket limpiamente.
        """
        await self._sender.send_system_message("Bye")

    async def _handle_query(self, content: str) -> None:
        """Maneja una consulta del usuario.

        Args:
            content: Contenido de la consulta
        """
        from termuxcode.message_converter import MessageConverter

        # Log del mensaje del usuario
        session_info = f"session={self._session_id}" if self._session_id else "no session"
        logger.info(f"Usuario envió mensaje ({session_info}): {content[:100]}{'...' if len(content) > 100 else ''}")

        self._stop_event.clear()

        # Truncar historial y reconectar para que el SDK cargue el JSONL recortado
        if self._session_id and self._cwd:
            did_truncate = truncate_history(self._cwd, self._session_id, self._rolling_window)
            if did_truncate:
                await self._sdk_client.reconnect(self._session_id)

        # Actualizar CLAUDE.md con información actualizada del proyecto
        # El SDK lo leerá antes de procesar la query
        if self._cwd:
            try:
                from termuxcode.connection.claude_md_manager import update_claude_md
                update_claude_md(self._cwd, self._session_id)
            except Exception as e:
                logger.debug(f"Error actualizando CLAUDE.md (no crítico): {e}")

        # Inyectar contexto dinámico (fecha/hora + git status) al inicio del mensaje
        query_content = content
        if self._cwd:
            try:
                from termuxcode.connection.claude_md_manager import build_message_context
                ctx = build_message_context(self._cwd)
                if ctx:
                    query_content = ctx + content
            except Exception as e:
                logger.debug(f"Error generando context para mensaje (no crítico): {e}")

        try:
            await self._sdk_client.query(query_content)
        except Exception as e:
            logger.warning(f"Query falló (SDK posiblemente muerto): {e}, intentando recovery...")
            await self._try_recover_sdk()
            try:
                await self._sdk_client.query(content)
            except Exception as retry_e:
                logger.error(f"Query falló tras recovery: {retry_e}")
                await self._sender.send_system_message(f"Error del SDK: {retry_e}")
                return

        # Obtener el async iterator
        try:
            response_iterator = self._sdk_client.receive_response()
        except Exception as e:
            logger.error(f"Error iniciando receive_response: {e}")
            await self._sender.send_system_message(f"Error del SDK: {e}")
            await self._try_recover_sdk()
            return

        # Loop para procesar mensajes del SDK
        try:
            async for msg in response_iterator:
                # Verificar si se solicitó detención
                if self._stop_event.is_set():
                    # Drenar mensajes restantes para dejar el SDK en estado limpio
                    async for remaining in response_iterator:
                        remaining_type = type(remaining).__name__
                        if remaining_type == "ResultMessage":
                            if hasattr(remaining, 'session_id') and remaining.session_id:
                                self._session_id = remaining.session_id
                                if self._on_session_id_update:
                                    await self._on_session_id_update(self._session_id)
                                await self._sender.send_session_id(remaining.session_id)
                                await self._sender.send_cwd(self._cwd)
                            break
                    await self._sender.send_system_message("Query detenido")
                    break

                msg_type = type(msg).__name__

                if msg_type == "ResultMessage":
                    # Capturar session_id del SDK y enviarlo al frontend
                    if hasattr(msg, 'session_id') and msg.session_id:
                        self._session_id = msg.session_id
                        # Registrar en registry ANTES de enviar al frontend
                        # para evitar que un reconnect inmediato no encuentre la sesión
                        if self._on_session_id_update:
                            await self._on_session_id_update(self._session_id)
                        await self._sender.send_session_id(self._session_id)
                        # Enviar CWD junto con el session_id (sesión establecida)
                        await self._sender.send_cwd(self._cwd)
                    result_data = MessageConverter.convert_result_message(msg)
                    await self._sender.send_message(result_data)

                    # Enviar filetree actualizado tras cada query
                    if self._cwd:
                        try:
                            from termuxcode.connection.filetree_watcher import generate_filetree_json
                            tree = generate_filetree_json(self._cwd)
                            await self._sender.send_message({
                                "type": "filetree_snapshot",
                                "cwd": self._cwd,
                                "entries": tree,
                            })
                        except Exception as e:
                            logger.debug(f"Error enviando filetree: {e}")

                    break

                elif msg_type == "AssistantMessage":
                    assistant_data = MessageConverter.convert_assistant_message(
                        msg, exclude_special_tools=True
                    )
                    if assistant_data["blocks"]:
                        await self._sender.send_message(assistant_data)

                    # Extraer todos de TodoWrite y enviar al frontend
                    todos = MessageConverter.extract_todo_write(msg)
                    if todos is not None:
                        await self._sender.send_message({
                            "type": "todo_update",
                            "todos": todos,
                        })

                elif msg_type == "UserMessage":
                    user_data = MessageConverter.convert_user_message(msg)
                    if user_data["blocks"]:
                        await self._sender.send_message(user_data)
        except Exception as e:
            logger.error(f"Fatal error en response loop: {e}", exc_info=True)
            # Avisar al frontend para que quite el estado loading
            short_msg = str(e)
            if len(short_msg) > 200:
                short_msg = short_msg[:200] + "..."
            await self._sender.send_system_message(f"Error del SDK: {short_msg}")
            # Intentar reconectar el SDK para que la siguiente consulta funcione
            await self._try_recover_sdk()

    async def _try_recover_sdk(self) -> None:
        """Intenta reconectar el SDK después de un error fatal."""
        try:
            await self._sdk_client.disconnect()
        except Exception as e:
            logger.warning(f"Error en disconnect durante recovery: {e}")

        try:
            await self._sdk_client.reconnect(self._session_id)
            await self._sender.send_system_message("SDK reconectado. Puedes enviar otro mensaje.")
        except Exception as e:
            logger.error(f"No se pudo recuperar el SDK: {e}")
            await self._sender.send_system_message("No se pudo reconectar el SDK. Recarga la página.")
