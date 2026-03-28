#!/usr/bin/env python3
"""Procesamiento de mensajes del WebSocket."""

import asyncio
import websockets

from termuxcode.ws_config import logger


class MessageProcessor:
    """Procesa mensajes del WebSocket y maneja la comunicación con el SDK."""

    def __init__(self, sdk_client, sender):
        """Inicializa el procesador.

        Args:
            sdk_client: Instancia de SDKClient
            sender: Instancia de MessageSender
        """
        self._sdk_client = sdk_client
        self._sender = sender
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
        command = data.get("command")
        content = data.get("content", "")
        msg_type = data.get("type")

        if command == "/disconnect":
            await self._handle_disconnect()
        elif content:
            await self._handle_query(content)

    async def request_stop(self):
        """Señala detención e interrumpe el SDK. Se llama desde fuera de la cola."""
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
        logger.info(f"Query: {content[:50]}")
        self._stop_event.clear()

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
                            await self._sender.send_session_id(remaining.session_id)
                        break
                await self._sender.send_system_message("Query detenido")
                break

            msg_type = type(msg).__name__
            logger.info(f"=== Msg recibido: {msg_type} ===")

            if msg_type == "ResultMessage":
                # Capturar session_id del SDK y enviarlo al frontend
                if hasattr(msg, 'session_id') and msg.session_id:
                    session_id = msg.session_id
                    logger.info(f"Session ID del SDK: {session_id}")
                    await self._sender.send_session_id(session_id)
                logger.info(f"ResultMessage: stop_reason={msg.stop_reason}, num_turns={msg.num_turns}")
                await self._sender.send_result(msg)
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

                await self._sender.send_assistant_message(msg)

            elif msg_type == "UserMessage":
                logger.info(f"UserMessage recibido del SDK")
                if hasattr(msg, 'content'):
                    for block in msg.content:
                        block_type = type(block).__name__
                        logger.info(f"  Bloque: {block_type}")
                        if block_type == "ToolResultBlock":
                            logger.info(f"    tool_use_id: {block.tool_use_id[:8] if hasattr(block, 'tool_use_id') else 'N/A'}...")
                            logger.info(f"    content: {str(block.content)[:200] if hasattr(block, 'content') else 'N/A'}")

            elif msg_type == "SystemMessage":
                logger.info(f"SystemMessage: {str(msg)[:200] if hasattr(msg, '__str__') else 'N/A'}")
