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
        self.message_queue = asyncio.Queue()
        self._processor_task = None
        self._stop_processing = asyncio.Event()

    async def handle(self):
        """Maneja el ciclo de vida de la conexión."""
        logger.info(f"[Nueva conexión] {self.remote_address}")

        try:
            await self._initialize_client()

            # Iniciar tarea de fondo para procesar mensajes
            self._processor_task = asyncio.create_task(self._process_messages_continuously())

            # Iniciar loop de mensajes del WebSocket
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
            self._stop_processing.set()
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
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
            logger.info(f"Mensaje recibido: {data.get('type', data.get('command', 'unknown'))}")
            await self.message_queue.put(data)

    async def _process_messages_continuously(self):
        """Procesa mensajes de la cola continuamente (tarea de fondo)."""
        while not self._stop_processing.is_set():
            try:
                # Esperar por un mensaje con timeout para poder verificar _stop_processing
                data = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
                await self._process_message(data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}", exc_info=True)

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

        # Esperar respuesta del usuario - mientras tanto, procesar otros mensajes
        while not self.question_event.is_set():
            # Esperar por: evento de respuesta O un mensaje en la cola
            event_task = asyncio.create_task(self.question_event.wait())
            queue_task = asyncio.create_task(self.message_queue.get())

            done, pending = await asyncio.wait(
                [event_task, queue_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancelar tareas que no terminaron
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Si el evento se seteó, salir
            if self.question_event.is_set():
                break

            # Si llegó un mensaje, procesarlo
            for task in done:
                if task == queue_task:
                    data = queue_task.result()
                    logger.info(f"Procesando mensaje mientras espero respuesta: {data.get('type', 'unknown')}")
                    await self._process_message(data)

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
                # Detectar si hay AskUserQuestion
                tool_id, questions = MessageConverter.extract_ask_user_question(msg)
                if questions:
                    logger.info(f"AskUserQuestion detectado: {len(questions)} preguntas")
                    # Enviar bloques de texto antes de la pregunta (si los hay)
                    await self._send_assistant_message(msg, exclude_ask_user_question=True)
                    # Detener la generación del SDK
                    await self.client.interrupt()
                    # Enviar pregunta al frontend y esperar respuesta
                    responses = await self.send_ask_user_question(questions)
                    # Enviar respuesta al SDK
                    await self._send_question_response_to_sdk(tool_id, responses)
                    continue  # Continuar recibiendo mensajes

                await self._send_assistant_message(msg)

    async def _send_question_response_to_sdk(self, tool_id: str, responses: list):
        """Envía la respuesta del usuario al SDK como tool_result."""
        logger.info(f"Enviando respuesta de pregunta al SDK: {responses}")

        # Formatear respuestas como contenido del tool_result
        # El SDK espera el contenido en formato específico
        if len(responses) == 1 and not isinstance(responses[0], list):
            # Single select: string simple
            content = responses[0]
        else:
            # Multi-select o múltiples preguntas: lista de annotations
            content = []
            for answer in responses:
                if isinstance(answer, list):
                    for a in answer:
                        content.append({"type": "string", "value": a})
                else:
                    content.append({"type": "string", "value": answer})

        # Crear mensaje en el formato que espera el SDK
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": content
                    }
                ]
            },
            "parent_tool_use_id": tool_id,
            "session_id": "default"
        }

        try:
            # Enviar directamente al transporte del SDK
            if hasattr(self.client, '_transport') and self.client._transport:
                import json
                await self.client._transport.write(json.dumps(message) + "\n")
                logger.info("Respuesta enviada via transporte")
            else:
                # Fallback: usar query con string
                logger.warning("No hay transporte directo, usando query string")
                await self.client.query(str(responses))
        except Exception as e:
            logger.error(f"Error enviando respuesta de pregunta: {e}", exc_info=True)

    async def _send_result(self, msg):
        """Envía un mensaje de resultado."""
        result_data = MessageConverter.convert_result_message(msg)
        await self.websocket.send(json.dumps(result_data))

    async def _send_assistant_message(self, msg, exclude_ask_user_question=False):
        """Envía un mensaje del asistente."""
        assistant_data = MessageConverter.convert_assistant_message(msg, exclude_special_tools=exclude_ask_user_question)
        if assistant_data["blocks"]:
            await self.websocket.send(json.dumps(assistant_data))

    async def _cleanup(self):
        """Limpia recursos de la conexión."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
