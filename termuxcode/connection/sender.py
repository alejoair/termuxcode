#!/usr/bin/env python3
"""Envío de mensajes al frontend WebSocket."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import AssistantMessage, ResultMessage

from termuxcode.message_converter import MessageConverter
from termuxcode.ws_config import logger

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection


class MessageSender:
    """Envía mensajes al cliente WebSocket."""

    MAX_BUFFER_SIZE = 1000

    def __init__(self, websocket: ClientConnection | None) -> None:
        """Inicializa el sender.

        Args:
            websocket: Conexión WebSocket activa
        """
        self._websocket = websocket
        self._buffer: list[dict[str, Any]] = []  # Buffer para mensajes cuando no hay conexión

    def set_websocket(self, ws: ClientConnection | None) -> None:
        """Actualiza el WebSocket (None para desconectar).

        Args:
            ws: Nuevo WebSocket o None para desconectar
        """
        self._websocket = ws

    async def _send_or_buffer(self, message: dict[str, Any]) -> None:
        """Envía si hay conexión, sino acumula en buffer.

        Args:
            message: Mensaje a enviar o acumular
        """
        if self._websocket:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                # Si falla el envío (conexión rota), bufferizar
                logger.warning(f"Error enviando mensaje, bufferizando: {e}")
                self._buffer.append(message)
                self._evict_if_needed()
        else:
            self._buffer.append(message)
            self._evict_if_needed()

    async def replay_buffer(self) -> None:
        """Envía todos los mensajes acumulados en el buffer."""
        if not self._websocket or not self._buffer:
            return
        buffer_copy = self._buffer[:]
        self._buffer = []
        logger.info(f"Replay de {len(buffer_copy)} mensajes del buffer")
        for i, msg in enumerate(buffer_copy):
            try:
                await self._websocket.send(json.dumps(msg))
            except Exception as e:
                logger.error(f"Replay falló en mensaje {i}/{len(buffer_copy)}: {e}")
                self._buffer = buffer_copy[i:] + self._buffer
                raise

    def _evict_if_needed(self) -> None:
        """Evict oldest messages if buffer exceeds MAX_BUFFER_SIZE."""
        if len(self._buffer) > self.MAX_BUFFER_SIZE:
            evicted = len(self._buffer) - self.MAX_BUFFER_SIZE
            self._buffer = self._buffer[evicted:]
            logger.warning(f"Buffer evicted {evicted} oldest messages (limit: {self.MAX_BUFFER_SIZE})")

    async def send_cwd(self, cwd: str) -> None:
        """Envía el CWD de la sesión al frontend.

        Args:
            cwd: Directorio de trabajo actual
        """
        if cwd:
            await self._send_or_buffer({"type": "cwd", "cwd": cwd})

    async def send_system_message(self, message: str) -> None:
        """Envía un mensaje del sistema al cliente.

        Args:
            message: Mensaje a enviar
        """
        await self._send_or_buffer({"type": "system", "message": message})

    async def send_session_id(self, session_id: str) -> None:
        """Envía el session_id del SDK al frontend.

        Args:
            session_id: ID de sesión a enviar
        """
        if session_id:
            await self._send_or_buffer({
                "type": "session_id",
                "session_id": session_id
            })

    async def send_assistant_message(self, msg: AssistantMessage, exclude_special_tools: bool = False) -> None:
        """Envía un mensaje del asistente al frontend.

        Args:
            msg: AssistantMessage del SDK
            exclude_special_tools: Si es True, filtra tools especiales (AskUserQuestion)
        """
        assistant_data = MessageConverter.convert_assistant_message(msg, exclude_special_tools=exclude_special_tools)
        if assistant_data["blocks"]:
            await self._send_or_buffer(assistant_data)

    async def send_result(self, msg: ResultMessage) -> None:
        """Envía un mensaje de resultado al frontend.

        Args:
            msg: ResultMessage del SDK
        """
        result_data = MessageConverter.convert_result_message(msg)
        await self._send_or_buffer(result_data)

    async def send_ask_user_question(self, questions: list[dict[str, Any]]) -> None:
        """Envía preguntas al frontend para mostrar en un modal.

        Args:
            questions: Lista de preguntas con formato AskUserQuestion
        """
        await self._send_or_buffer({
            "type": "ask_user_question",
            "questions": questions
        })

    async def send_file_view(self, file_path: str, content: str) -> None:
        """Envía contenido de un archivo para mostrar en el frontend.

        Args:
            file_path: Ruta del archivo
            content: Contenido del archivo (markdown)
        """
        await self._send_or_buffer({
            "type": "file_view",
            "file_path": file_path,
            "content": content
        })

    async def send_tool_approval_request(self, tool_name: str, input_data: dict[str, Any]) -> None:
        """Envía solicitud de aprobación de herramienta al frontend.

        Args:
            tool_name: Nombre de la herramienta (ej: "Bash", "Write")
            input_data: Parámetros de la herramienta
        """
        await self._send_or_buffer({
            "type": "tool_approval_request",
            "tool_name": tool_name,
            "input": input_data
        })

    async def send_tools_list(self, tools: list[dict[str, Any]]) -> None:
        """Envía la lista de tools disponibles al frontend.

        Args:
            tools: Lista de tools con formato {name, desc, source, server?}
        """
        await self._send_or_buffer({"type": "tools_list", "tools": tools})

    async def send_mcp_status(self, servers: list[dict[str, Any]]) -> None:
        """Envía el estado detallado de los MCP servers al frontend.

        Args:
            servers: Lista de servers con formato {name, status, tools, error?}
        """
        await self._send_or_buffer({"type": "mcp_status", "servers": servers})

    async def send_message(self, message: dict[str, Any]) -> None:
        """Envía un mensaje genérico al frontend.

        Args:
            message: Diccionario con el mensaje a enviar
        """
        await self._send_or_buffer(message)
