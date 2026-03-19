"""Mixin para manejo de queries"""
from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio

from textual.widgets import Input

if TYPE_CHECKING:
    from ..app import ClaudeChat
    from ...core.session_state import SessionState
    from ...core.notification_system import NotificationType


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

        # Procesar la query
        self._handle_query(prompt)

    def _handle_query(self: "ClaudeChat", prompt: str) -> None:
        """Procesar la query"""
        # Verificar que tenemos una sesión activa
        if not self._current_session_id:
            self.chat_log.write_error("No hay sesión activa")
            return

        state = self._session_states.get(self._current_session_id)
        if not state:
            self.chat_log.write_error("Estado de sesión no encontrado")
            return

        # Mostrar mensaje del usuario inmediatamente
        self.chat_log.write_user(prompt)
        # Guardar mensaje del usuario inmediatamente en historial (siempre útil)
        state.history.append("user", prompt)
        self.chat_log.write_thinking()
        self.is_thinking = True

        # Crear callback para cuando termine la query
        def on_complete(session_id: str, error: Exception | None):
            from ...core.notification_system import NotificationType

            session = self.session_manager.get_session(session_id)
            if not session:
                return

            if error:
                # Solo mostrar error si estamos en esa sesión
                if session_id == self._current_session_id:
                    self.chat_log.write_error(f"Error: {error}")
                else:
                    # Guardar notificación para cuando vuelva
                    self.notification_queue.add(
                        session_id=session_id,
                        session_name=session.name,
                        message=f"Query terminó con error: {error}",
                        notification_type=NotificationType.ERROR
                    )
                    # Actualizar tabs para mostrar indicador de notificación
                    self.call_later(self._update_tabs)
            else:
                # Notificar que terminó si no estamos en esa sesión
                if session_id != self._current_session_id:
                    self.notification_queue.add(
                        session_id=session_id,
                        session_name=session.name,
                        message="Query completada",
                        notification_type=NotificationType.SUCCESS
                    )
                    # Actualizar tabs para mostrar indicador de notificación
                    self.call_later(self._update_tabs)

            # Actualizar estado thinking si seguimos en la misma sesión
            if session_id == self._current_session_id:
                self.is_thinking = False

            # Actualizar botón Stop (deshabilitado cuando terminó)
            self.call_later(self._update_stop_button)
            # Actualizar tabs para quitar indicador de corriendo
            self.call_later(self._update_tabs)

        # Crear nuevo task para esta query
        coro = self._run_query_safe(state, prompt)

        # Guardar referencia en SessionState
        state.pending_task = asyncio.create_task(coro)

        # Registrar en background_manager con callback
        self.background_manager.start_task(
            session_id=self._current_session_id,
            coro=state.pending_task,
            on_complete=on_complete
        )

        # Actualizar tabs para mostrar indicador de que está corriendo
        self.call_later(self._update_tabs)
        # Actualizar botón Stop (habilitado cuando está corriendo)
        self.call_later(self._update_stop_button)

    async def _run_query_safe(self: "ClaudeChat", state: "SessionState", prompt: str) -> None:
        """Ejecutar query con manejo de errores y cancelación"""
        try:
            await state.agent.query(prompt)
        except asyncio.CancelledError:
            # Query cancelada por el usuario (el callback se encarga de manejar esto)
            pass
        except Exception as e:
            # Error durante la query (el callback se encarga de mostrarlo)
            if self._current_session_id == state.agent.session_id:
                self.chat_log.write_error(f"Error: {e}")
            # Re-lanzar para que el callback maneje el error
            raise
