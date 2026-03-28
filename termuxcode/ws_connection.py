#!/usr/bin/env python3
"""Manejo de conexiones WebSocket individuales."""

import json
import logging
import asyncio

import websockets
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from termuxcode.ws_config import logger
from termuxcode.message_converter import MessageConverter


class WebSocketConnection:
    """Maneja una conexión WebSocket con su propio cliente SDK."""

    def __init__(self, websocket, resume_id: str = None, cwd: str = None):
        self.websocket = websocket
        self.client = None
        self.remote_address = websocket.remote_address
        self.resume_id = resume_id
        self.cwd = cwd
        self.session_id = None
        self.question_response = None
        self.question_event = asyncio.Event()

    async def handle(self):
        """Maneja el ciclo de vida de la conexión."""
        logger.info(f"[Nueva conexión] {self.remote_address}")

        try:
            await self._initialize_client()
            await self._message_loop()

        except websockets.exceptions.ConnectionClosed:
            logger.info("[Conexion cerrada]")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            try:
                await self._send_system_message(f"Error: {e}")
                # Mantener la conexion abierta para evitar reconnect loop
                await self.websocket.wait_closed()
            except Exception:
                pass
        finally:
            await self._cleanup()

    async def _initialize_client(self):
        """Inicializa el cliente SDK."""
        logger.info("Creando cliente SDK...")
        options = ClaudeAgentOptions(permission_mode="acceptEdits")
        if self.cwd:
            options.cwd = self.cwd
            logger.info(f"Usando cwd: {self.cwd}")
        if self.resume_id:
            logger.info(f"Reanudando sesión: {self.resume_id}")
            options.resume = self.resume_id

        try:
            self.client = ClaudeSDKClient(options)
            await self.client.connect()
            logger.info("Cliente conectado")
            # Enviar session_id inmediatamente despues de conectar
            if hasattr(self.client, 'session_id') and self.client.session_id:
                self.session_id = self.client.session_id
                await self._send_session_id()
                logger.info(f"Session ID enviado: {self.session_id}")
        except Exception as e:
            if self.resume_id:
                logger.warning(f"Falló reanudar sesión {self.resume_id}: {e}. Creando nueva sesión.")
                await self._send_system_message("Sesión anterior corrupta, creando nueva sesión...")
                self.resume_id = None
                options = ClaudeAgentOptions(permission_mode="acceptEdits")
                if self.cwd:
                    options.cwd = self.cwd
                self.client = ClaudeSDKClient(options)
                await self.client.connect()
                logger.info("Nueva sesión creada")
            else:
                raise

    async def _send_system_message(self, message: str):
        """Envía un mensaje del sistema al cliente."""
        await self.websocket.send(json.dumps({"type": "system", "message": message}))

    async def _send_session_id(self):
        """Envia el session_id del SDK al frontend."""
        if self.session_id:
            await self.websocket.send(json.dumps({
                "type": "session_id",
                "session_id": self.session_id
            }))

    async def _message_loop(self):
        """Procesa mensajes entrantes."""
        async for message in self.websocket:
            data = json.loads(message)
            await self._process_message(data)

    async def _process_message(self, data: dict):
        """Procesa un mensaje recibido."""
        command = data.get("command")
        content = data.get("content", "")
        msg_type = data.get("type")

        if msg_type == "question_response":
            await self._handle_question_response(data.get("responses"))
        elif command == "/stop":
            await self._handle_stop()
        elif command == "/disconnect":
            await self._handle_disconnect()
        elif content:
            await self._handle_query(content)

    async def _handle_stop(self):
        """Maneja el comando /stop."""
        if self.client:
            await self.client.interrupt()
        await self._send_system_message("Detenido")

    async def _handle_disconnect(self):
        """Maneja el comando /disconnect."""
        await self._send_system_message("Bye")
        raise websockets.exceptions.ConnectionClosed(1000, "Disconnect requested")

    async def _handle_question_response(self, responses):
        """Maneja la respuesta del usuario a una pregunta."""
        self.question_response = responses
        self.question_event.set()
        logger.info(f"Respuesta recibida: {responses}")

    async def send_ask_user_question(self, questions: list) -> list:
        """
        Envia preguntas al frontend y espera las respuestas.

        Args:
            questions: Lista de preguntas con el formato:
                [{
                    "question": "Texto de la pregunta?",
                    "header": "Header",
                    "multiSelect": False,
                    "options": [
                        {"label": "Opcion 1", "description": "Desc", "preview": "codigo"}
                    ]
                }]

        Returns:
            Lista de respuestas (string o lista de strings segun multiSelect)
        """
        self.question_response = None
        self.question_event.clear()

        await self.websocket.send(json.dumps({
            "type": "ask_user_question",
            "questions": questions
        }))

        # Esperar respuesta del usuario
        await self.question_event.wait()
        return self.question_response

    async def _handle_query(self, content: str):
        """Maneja una consulta del usuario."""
        logger.info(f"Query: {content[:50]}")

        await self.client.query(content)

        async for msg in self.client.receive_response():
            msg_type = type(msg).__name__
            logger.info(f"Msg: {msg_type}")

            if msg_type == "ResultMessage":
                # Capturar session_id del SDK y enviarlo al frontend
                if hasattr(msg, 'session_id') and msg.session_id:
                    self.session_id = msg.session_id
                    logger.info(f"Session ID del SDK: {self.session_id}")
                    await self._send_session_id()
                await self._send_result(msg)
                break

            elif msg_type == "AssistantMessage":
                await self._send_assistant_message(msg)

    async def _send_result(self, msg):
        """Envía un mensaje de resultado."""
        result_data = MessageConverter.convert_result_message(msg)
        await self.websocket.send(json.dumps(result_data))

    async def _send_assistant_message(self, msg):
        """Envía un mensaje del asistente."""
        assistant_data = MessageConverter.convert_assistant_message(msg)
        if assistant_data["blocks"]:
            await self.websocket.send(json.dumps(assistant_data))

    async def _cleanup(self):
        """Limpia recursos de la conexión."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
