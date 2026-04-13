#!/usr/bin/env python3
"""Thin wrapper: conecta WebSocket lifecycle con Session."""

from __future__ import annotations

import json

import websockets
from websockets import ServerConnection

from termuxcode.ws_config import logger
from termuxcode.connection.session import Session


class WebSocketConnection:
    """Conecta el ciclo de vida del WebSocket con una Session.

    Responsabilidades:
    - Crear/reanudar la Session cuando llega una conexión
    - Despachar mensajes del WebSocket a Session.handle_message()
    - Detach del WebSocket al desconectarse (sin destruir la Session)
    """

    def __init__(self, websocket: ServerConnection, resume_id: str | None = None, cwd: str | None = None,
                 agent_options: dict | None = None) -> None:
        self.websocket = websocket
        self.remote_address = websocket.remote_address
        self._resume_id = resume_id
        self._cwd = cwd
        self._agent_options = agent_options or {}
        self._session: Session | None = None

    async def handle(self) -> None:
        """Maneja el ciclo de vida de la conexión."""
        logger.info(f"[Nueva conexión] {self.remote_address}")
        # Capturar referencia al WebSocket de esta llamada para detectar si
        # un reconnect() lo reemplazó mientras esperábamos session.create().
        original_ws = self.websocket
        ran_loop = False

        try:
            if self._session is None:
                # Crear Session nueva, pasando self como connection wrapper
                self._session = Session(
                    session_id=self._resume_id,
                    cwd=self._cwd,
                    agent_options=self._agent_options,
                    connection=self,
                )
                await self._session.create(original_ws)
            else:
                # Sesión existente reanudada — attach del nuevo WebSocket
                self._session.attach_websocket(self.websocket)

            # Si durante create() llegó un reconnect() que actualizó self.websocket,
            # el otro handle() ya correrá el message loop — evitar dos recv() en paralelo.
            if self.websocket is original_ws:
                ran_loop = True
                await self._message_loop()
            else:
                logger.debug(
                    f"WebSocket reemplazado durante create() — saltando message loop "
                    f"({original_ws.remote_address} → {self.websocket.remote_address})"
                )

        except websockets.exceptions.ConnectionClosed:
            logger.info("[Conexión cerrada]")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            try:
                if self._session:
                    await self._session.send_message(
                        {"type": "system", "message": f"Error: {e}"}
                    )
                await original_ws.wait_closed()
            except Exception:
                pass
        finally:
            # Solo detach si este handle() fue el que corrió el message loop
            if ran_loop and self._session:
                self._session.detach_websocket()

    async def reconnect(self, new_websocket: ServerConnection, agent_options: dict | None = None,
                        cwd: str | None = None) -> None:
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

    async def destroy_session(self) -> None:
        """Destruye la Session por completo (cleanup total)."""
        if self._session:
            await self._session.destroy()
            self._session = None

    async def _message_loop(self) -> None:
        """Lee mensajes del WebSocket y los despacha a la Session."""
        async for message in self.websocket:
            data = json.loads(message)
            if data.get('command') == '/destroy':
                await self.destroy_session()
                return
            if data.get('command') == '/disconnect':
                await self._session.handle_message(data)
                await self.websocket.close(1000, "Disconnect requested")
                return
            await self._session.handle_message(data)
