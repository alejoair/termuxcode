#!/usr/bin/env python3
"""Thin wrapper: conecta WebSocket lifecycle con Session."""

import json

import websockets

from termuxcode.ws_config import logger
from termuxcode.connection.session import Session


class WebSocketConnection:
    """Conecta el ciclo de vida del WebSocket con una Session.

    Responsabilidades:
    - Crear/reanudar la Session cuando llega una conexión
    - Despachar mensajes del WebSocket a Session.handle_message()
    - Detach del WebSocket al desconectarse (sin destruir la Session)
    """

    def __init__(self, websocket, resume_id: str = None, cwd: str = None,
                 agent_options: dict = None):
        self.websocket = websocket
        self.remote_address = websocket.remote_address
        self._resume_id = resume_id
        self._cwd = cwd
        self._agent_options = agent_options or {}
        self._session: Session | None = None

    async def handle(self):
        """Maneja el ciclo de vida de la conexión."""
        logger.info(f"[Nueva conexión] {self.remote_address}")

        try:
            if self._session is None:
                # Crear Session nueva, pasando self como connection wrapper
                self._session = Session(
                    session_id=self._resume_id,
                    cwd=self._cwd,
                    agent_options=self._agent_options,
                    connection=self,
                )
                await self._session.create(self.websocket)
            else:
                # Sesión existente reanudada — attach del nuevo WebSocket
                self._session.attach_websocket(self.websocket)

            # Loop de mensajes del WebSocket
            await self._message_loop()

        except websockets.exceptions.ConnectionClosed:
            logger.info("[Conexión cerrada]")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            try:
                if self._session:
                    await self._session.send_message(
                        {"type": "system", "message": f"Error: {e}"}
                    )
                await self.websocket.wait_closed()
            except Exception:
                pass
        finally:
            # Solo detach del WebSocket — la Session sigue viva para reconexión
            if self._session:
                self._session.detach_websocket()

    async def reconnect(self, new_websocket, agent_options: dict = None,
                        cwd: str = None):
        """Reconecta: resume la Session con nuevo WebSocket.

        Args:
            new_websocket: Nueva conexión WebSocket
            agent_options: Nuevas opciones del agente
            cwd: Nuevo directorio de trabajo
        """
        self.websocket = new_websocket
        self.remote_address = new_websocket.remote_address

        if self._session:
            await self._session.resume(
                new_websocket,
                agent_options=agent_options,
                cwd=cwd,
            )
            if cwd:
                self._cwd = cwd

    async def destroy_session(self):
        """Destruye la Session por completo (cleanup total)."""
        if self._session:
            await self._session.destroy()
            self._session = None

    async def _message_loop(self):
        """Lee mensajes del WebSocket y los despacha a la Session."""
        async for message in self.websocket:
            data = json.loads(message)
            await self._session.handle_message(data)
