#!/usr/bin/env python3
"""Envío de mensajes al frontend WebSocket."""

import json

from claude_agent_sdk import AssistantMessage, ResultMessage

from termuxcode.message_converter import MessageConverter
from termuxcode.ws_config import logger


class MessageSender:
    """Envía mensajes al cliente WebSocket."""

    def __init__(self, websocket):
        """Inicializa el sender.

        Args:
            websocket: Conexión WebSocket activa
        """
        self._websocket = websocket
        self._buffer = []  # Buffer para mensajes cuando no hay conexión

    def set_websocket(self, ws):
        """Actualiza el WebSocket (None para desconectar).

        Args:
            ws: Nuevo WebSocket o None para desconectar
        """
        self._websocket = ws

    async def _send_or_buffer(self, message: dict):
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
        else:
            self._buffer.append(message)

    async def replay_buffer(self):
        """Envía todos los mensajes acumulados en el buffer."""
        if self._websocket and self._buffer:
            logger.info(f"Replay de {len(self._buffer)} mensajes del buffer")
            for msg in self._buffer:
                await self._websocket.send(json.dumps(msg))
            self._buffer.clear()

    async def send_system_message(self, message: str):
        """Envía un mensaje del sistema al cliente.

        Args:
            message: Mensaje a enviar
        """
        await self._send_or_buffer({"type": "system", "message": message})

    async def send_session_id(self, session_id: str):
        """Envía el session_id del SDK al frontend.

        Args:
            session_id: ID de sesión a enviar
        """
        if session_id:
            await self._send_or_buffer({
                "type": "session_id",
                "session_id": session_id
            })

    async def send_assistant_message(self, msg: AssistantMessage, exclude_special_tools: bool = False):
        """Envía un mensaje del asistente al frontend.

        Args:
            msg: AssistantMessage del SDK
            exclude_special_tools: Si es True, filtra tools especiales (AskUserQuestion)
        """
        assistant_data = MessageConverter.convert_assistant_message(msg, exclude_special_tools=exclude_special_tools)
        if assistant_data["blocks"]:
            await self._send_or_buffer(assistant_data)

    async def send_result(self, msg: ResultMessage):
        """Envía un mensaje de resultado al frontend.

        Args:
            msg: ResultMessage del SDK
        """
        result_data = MessageConverter.convert_result_message(msg)
        await self._send_or_buffer(result_data)

    async def send_ask_user_question(self, questions: list):
        """Envía preguntas al frontend para mostrar en un modal.

        Args:
            questions: Lista de preguntas con formato AskUserQuestion
        """
        await self._send_or_buffer({
            "type": "ask_user_question",
            "questions": questions
        })

    async def send_file_view(self, file_path: str, content: str):
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

    async def send_tool_approval_request(self, tool_name: str, input_data: dict):
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

    async def send_message(self, message: dict):
        """Envía un mensaje genérico al frontend.

        Args:
            message: Diccionario con el mensaje a enviar
        """
        await self._send_or_buffer(message)
