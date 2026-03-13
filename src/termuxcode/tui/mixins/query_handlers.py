"""Mixin para manejo de queries"""
from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio

from textual.widgets import Input

if TYPE_CHECKING:
    from ..app import ClaudeChat
    from .session_state import SessionState


class QueryHandlersMixin:
    """Mixin que maneja las queries y el input para ClaudeChat"""

    def watch_is_thinking(self: "ClaudeChat", thinking: bool) -> None:
        """Actualizar placeholder según estado"""
        if thinking:
            self.input.placeholder = "Pensando..."
        else:
            self.input.placeholder = "Mensaje..."

    def on_input_submitted(self: "ClaudeChat", event: Input.Submitted) -> None:
        """Manejar envío de mensaje"""
        if not event.value.strip():
            return

        prompt = event.value
        event.input.clear()

        # Verificar que tenemos una sesión activa
        if not self._current_session_id:
            self.chat_log.write_error("No hay sesión activa")
            return

        state = self._session_states.get(self._current_session_id)
        if not state:
            self.chat_log.write_error("Estado de sesión no encontrado")
            return

        # Cancelar task anterior si existe y no ha terminado
        if state.pending_task and not state.pending_task.done():
            state.pending_task.cancel()
            self.chat_log.write("[dim]Query anterior cancelado[/dim]")

        # Mostrar mensaje del usuario inmediatamente
        self.chat_log.write_user(prompt)
        self.chat_log.write_thinking()
        self.is_thinking = True

        # Gamificación: mensaje enviado
        self._on_message_sent()

        # Crear nuevo task para esta query
        state.pending_task = asyncio.create_task(
            self._run_query_safe(state, prompt)
        )

    async def _run_query_safe(self: "ClaudeChat", state: "SessionState", prompt: str) -> None:
        """Ejecutar query con manejo de errores y cancelación"""
        try:
            await state.agent.query(prompt)
        except asyncio.CancelledError:
            # Query cancelada por el usuario (cambio de sesión o nuevo mensaje)
            self.chat_log.write("[dim]Query cancelada[/dim]")
        except Exception as e:
            # Error durante la query
            if self._current_session_id == state.agent.session_id:
                self.chat_log.write_error(f"Error: {e}")
        finally:
            # Solo actualizar estado thinking si seguimos en la misma sesión
            if self._current_session_id == state.agent.session_id:
                self.is_thinking = False
                # Gamificación: respuesta recibida
                self._on_response_received()
