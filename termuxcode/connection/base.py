#!/usr/bin/env python3
"""Clase principal de conexión WebSocket."""

import asyncio
import websockets

from termuxcode.ws_config import logger
from termuxcode.connection.sdk_client import SDKClient
from termuxcode.connection.sender import MessageSender
from termuxcode.connection.ask_handler import AskUserQuestionHandler
from termuxcode.connection.tool_approval_handler import ToolApprovalHandler
from termuxcode.connection.message_processor import MessageProcessor


# Referencia al registry de sesiones activas (se setea desde ws_server.py)
_active_sessions_registry: dict = None


class WebSocketConnection:
    """Maneja una conexión WebSocket con sus componentes asociados."""

    def __init__(self, websocket, resume_id: str = None, cwd: str = None, agent_options: dict = None):
        """Inicializa la conexión.

        Args:
            websocket: Conexión WebSocket
            resume_id: ID de sesión para reanudar
            cwd: Directorio de trabajo
            agent_options: Opciones del agente desde el frontend
        """
        self.websocket = websocket
        self.remote_address = websocket.remote_address
        self.resume_id = resume_id
        self.cwd = cwd
        self.agent_options = agent_options or {}

        # Componentes
        self._sdk_client = None
        self._sender = None
        self._ask_handler = None
        self._tool_approval_handler = None
        self._processor = None

        # Control de flujo
        self.message_queue = asyncio.Queue()
        self._processor_task = None

    async def handle(self):
        """Maneja el ciclo de vida de la conexión."""
        logger.info(f"[Nueva conexión] {self.remote_address}")

        try:
            # Solo inicializar componentes si no están ya inicializados (reconexión)
            if self._sender is None:
                original_ws = self.websocket
                await self._initialize_components()

                # Iniciar tarea de fondo para procesar mensajes
                self._processor_task = asyncio.create_task(
                    self._processor.start_processing(self.message_queue)
                )

                # Si el websocket fue reemplazado durante la inicialización (reconexión
                # llegó mientras conectábamos al SDK), ceder el control al handle() que
                # ya arrancó _message_loop en el nuevo websocket.
                if self.websocket is not original_ws:
                    logger.info("WebSocket reemplazado durante init, cediendo control al handle de reconexión")
                    return

            # Iniciar loop de mensajes del WebSocket
            await self._message_loop()

        except websockets.exceptions.ConnectionClosed:
            logger.info("[Conexión cerrada]")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            try:
                await self._sender.send_system_message(f"Error: {e}")
                # Mantener la conexión abierta para evitar reconnect loop
                await self.websocket.wait_closed()
            except Exception:
                pass
        finally:
            await self._cleanup()

    async def _initialize_components(self):
        """Inicializa todos los componentes de la conexión."""
        # Inicializar sender primero (lo necesitan los handlers)
        self._sender = MessageSender(self.websocket)

        # Inicializar tool_approval_handler (su callback se pasa al SDK)
        self._tool_approval_handler = ToolApprovalHandler(self._sender)

        # Inicializar cliente SDK con el callback de aprobación
        self._sdk_client = SDKClient(
            resume_id=self.resume_id,
            cwd=self.cwd,
            can_use_tool=self._tool_approval_handler.can_use_tool,
            agent_options=self.agent_options,
        )
        session_id = await self._sdk_client.connect()
        logger.info("Cliente conectado")

        # Ahora que el SDK está conectado, darle referencia al approval handler
        self._tool_approval_handler._sdk_client = self._sdk_client

        # Enviar session_id inmediatamente después de conectar
        if session_id:
            await self._send_session_id(session_id)
            logger.info(f"Session ID enviado: {session_id}")

        # Inicializar ask_handler
        self._ask_handler = AskUserQuestionHandler(self._sender)
        self._tool_approval_handler._ask_handler = self._ask_handler

        # Callback para actualizar el registry cuando el SDK genera un nuevo session_id
        async def on_session_id_update(new_session_id: str):
            if _active_sessions_registry is not None and new_session_id:
                # Si teníamos un resume_id anterior y es diferente, actualizar el registry
                if self.resume_id and self.resume_id in _active_sessions_registry:
                    del _active_sessions_registry[self.resume_id]
                self.resume_id = new_session_id
                _active_sessions_registry[new_session_id] = self
                logger.info(f"Registry actualizado con nuevo session_id: {new_session_id}")

        # Inicializar message_processor
        rolling_window = self.agent_options.get('rolling_window', 100) if self.agent_options else 100
        self._processor = MessageProcessor(
            sdk_client=self._sdk_client,
            sender=self._sender,
            ask_handler=self._ask_handler,
            tool_approval_handler=self._tool_approval_handler,
            cwd=self.cwd,
            session_id=self.resume_id,
            rolling_window=rolling_window,
            on_session_id_update=on_session_id_update,
        )

        # Callback para cuando se rechaza un plan: setear stop_event del processor
        async def on_plan_rejected():
            self._processor._stop_event.set()
            await self._sender.send_system_message("Plan rechazado")

        self._tool_approval_handler._on_plan_rejected = on_plan_rejected

    async def _send_session_id(self, session_id: str):
        """Envía el session_id del SDK al frontend.

        Args:
            session_id: ID de sesión a enviar
        """
        await self._sender.send_session_id(session_id)

    async def _message_loop(self):
        """Procesa mensajes entrantes del WebSocket."""
        async for message in self.websocket:
            data = __import__('json').loads(message)
            # Determinar el tipo de mensaje para el log
            msg_type = data.get('type') or data.get('command') or ('chat' if data.get('content') else 'unknown')
            logger.info(f"Mensaje recibido: {msg_type}")

            # Mensajes que se manejan directamente (sin encolar) para evitar deadlock
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
            else:
                await self.message_queue.put(data)

    async def _cleanup(self):
        """Limpia recursos de la conexión.

        NOTA: Solo desconecta el WebSocket, mantiene el SDK activo para reconexión.
        El SDK y el processor continúan ejecutándose para acumular mensajes en el buffer.
        """
        # Solo desconectar WebSocket, mantener SDK activo para reconexión
        self._sender.set_websocket(None)
        logger.info("WebSocket desconectado, SDK sigue activo para reconexión")

    async def _full_cleanup(self):
        """Limpieza completa cuando la sesión ya no se necesita."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        if self._sdk_client:
            await self._sdk_client.disconnect()

        if self._ask_handler:
            self._ask_handler.reset()

        if self._tool_approval_handler:
            self._tool_approval_handler.reset()

    async def reconnect(self, new_websocket):
        """Reconecta con un nuevo WebSocket.

        Args:
            new_websocket: Nueva conexión WebSocket
        """
        logger.info(f"Reconectando sesión: {self.resume_id}")
        self.websocket = new_websocket
        self.remote_address = new_websocket.remote_address
        self._sender.set_websocket(new_websocket)
        await self._sender.replay_buffer()
