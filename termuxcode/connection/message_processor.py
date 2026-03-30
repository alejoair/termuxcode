#!/usr/bin/env python3
"""Procesamiento de mensajes del WebSocket."""

import asyncio
import websockets

from termuxcode.ws_config import logger
from termuxcode.connection.history_manager import truncate_history


class MessageProcessor:
    """Procesa mensajes del WebSocket y maneja la comunicación con el SDK."""

    def __init__(self, sdk_client, sender, ask_handler=None, tool_approval_handler=None, cwd=None, session_id=None, rolling_window=100, on_session_id_update=None):
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
        self._message_queue = None  # Se setea en start_processing
        self._stop_event = asyncio.Event()  # Señal de detención

    async def start_processing(self, message_queue: asyncio.Queue):
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

    async def process_message(self, data: dict):
        """Procesa un mensaje recibido del WebSocket.

        Args:
            data: Diccionario con el mensaje
        """
        logger.info(f"=== Frontend request: {data} ===")
        command = data.get("command")
        content = data.get("content", "")
        msg_type = data.get("type")

        if command == "/disconnect":
            await self._handle_disconnect()
        elif content:
            await self._handle_query(content)

    async def request_stop(self):
        """Señala detención e interrumpe el SDK."""
        logger.info("=== /stop detectado - Señalando detención ===")
        self._stop_event.set()
        try:
            await self._sdk_client.interrupt()
        except Exception as e:
            logger.warning(f"Error al interrumpir SDK: {e}")
        await self._sender.send_system_message("Deteniendo...")

    async def _handle_disconnect(self):
        """Maneja el comando /disconnect."""
        await self._sender.send_system_message("Bye")
        raise websockets.exceptions.ConnectionClosed(1000, "Disconnect requested")

    async def _handle_query(self, content: str):
        """Maneja una consulta del usuario.

        Args:
            content: Contenido de la consulta
        """
        from termuxcode.message_converter import MessageConverter

        logger.info(f"Query: {content[:50]}")
        logger.info(f"  session_id={self._session_id}, cwd={self._cwd}, rolling_window={self._rolling_window}")
        self._stop_event.clear()

        # Truncar historial y reconectar para que el SDK cargue el JSONL recortado
        if self._session_id and self._cwd:
            did_truncate = truncate_history(self._cwd, self._session_id, self._rolling_window)
            if did_truncate:
                await self._sdk_client.reconnect(self._session_id)

        await self._sdk_client.query(content)

        # Obtener el async iterator
        response_iterator = self._sdk_client.receive_response()

        # Loop para procesar mensajes del SDK
        async for msg in response_iterator:
            # Verificar si se solicitó detención
            if self._stop_event.is_set():
                logger.info("=== Stop detectado - Drenando mensajes restantes del SDK ===")
                # Drenar mensajes restantes para dejar el SDK en estado limpio
                async for remaining in response_iterator:
                    remaining_type = type(remaining).__name__
                    logger.info(f"=== Drenando: {remaining_type} ===")
                    if remaining_type == "ResultMessage":
                        if hasattr(remaining, 'session_id') and remaining.session_id:
                            self._session_id = remaining.session_id
                            await self._sender.send_session_id(remaining.session_id)
                            if self._on_session_id_update:
                                await self._on_session_id_update(self._session_id)
                        break
                await self._sender.send_system_message("Query detenido")
                break

            msg_type = type(msg).__name__
            logger.info(f"=== Msg recibido: {msg_type} ===")

            if msg_type == "ResultMessage":
                # Capturar session_id del SDK y enviarlo al frontend
                if hasattr(msg, 'session_id') and msg.session_id:
                    self._session_id = msg.session_id
                    logger.info(f"Session ID del SDK: {self._session_id}")
                    await self._sender.send_session_id(self._session_id)
                    # Notificar al callback si existe (para actualizar registry)
                    if self._on_session_id_update:
                        await self._on_session_id_update(self._session_id)
                logger.info(f"ResultMessage: stop_reason={msg.stop_reason}, num_turns={msg.num_turns}")
                result_data = MessageConverter.convert_result_message(msg)
                await self._sender.send_message(result_data)
                break

            elif msg_type == "AssistantMessage":
                # Loggear todos los bloques del mensaje
                if hasattr(msg, 'content'):
                    logger.info(f"AssistantMessage: {len(msg.content)} bloques")
                    for i, block in enumerate(msg.content):
                        block_type = type(block).__name__
                        logger.info(f"  Bloque {i}: {block_type}")

                        if block_type == "TextBlock":
                            logger.info(f"    Text: {block.text[:100]}")
                        elif block_type == "ToolUseBlock":
                            logger.info(f"    Tool: {block.name}, id={block.id}")
                            if hasattr(block, 'input'):
                                logger.info(f"    Input: {str(block.input)[:200]}")
                        elif block_type == "ThinkingBlock":
                            logger.info(f"    Thinking: {block.thinking[:100]}")
                        elif block_type == "ToolResultBlock":
                            logger.info(f"    ToolResult: tool_use_id={block.tool_use_id}")
                            logger.info(f"    Content: {str(block.content)[:200]}")

                assistant_data = MessageConverter.convert_assistant_message(
                    msg, exclude_special_tools=True
                )
                if assistant_data["blocks"]:
                    await self._sender.send_message(assistant_data)

            elif msg_type == "UserMessage":
                # Los UserMessage contienen ToolResultBlock con los resultados de las herramientas
                logger.info(f"UserMessage recibido del SDK")
                user_data = MessageConverter.convert_user_message(msg)
                if user_data["blocks"]:
                    await self._sender.send_message(user_data)
