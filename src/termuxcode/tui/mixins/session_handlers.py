"""Mixin para gestión de sesiones"""
from __future__ import annotations
from typing import TYPE_CHECKING

from textual.widgets import Tabs, Tab

if TYPE_CHECKING:
    from ..app import ClaudeChat
    from .session_state import SessionState


class SessionHandlersMixin:
    """Mixin que maneja la gestión de sesiones para ClaudeChat"""

    async def _load_first_session(self: "ClaudeChat") -> None:
        """Cargar sesiones existentes o crear la primera"""
        sessions = self.session_manager.list_sessions()
        if not sessions:
            session = self.session_manager.create_session("Nueva sesión")
        else:
            last_id = self.session_manager.get_last_active()
            session = self.session_manager.get_session(last_id) or sessions[0]

        await self._switch_to_session(session.id)

    async def _get_or_create_session_state(self: "ClaudeChat", session_id: str) -> "SessionState":
        """Obtener o crear el estado de una sesión"""
        if session_id not in self._session_states:
            from .session_state import SessionState
            from ..history import MessageHistory
            from ..agent import AgentClient

            history = MessageHistory(
                filename="messages.jsonl",
                max_messages=self.max_history,
                session_id=session_id,
                cwd=self.cwd
            )
            # Crear agent con session_id capturado por valor (no por referencia)
            captured_session_id = session_id
            is_active = lambda: self._current_session_id == captured_session_id

            # Callbacks para gamificación con respuestas estructuradas
            def on_structured_response(structured):
                # Este callback se llama cuando se recibe una respuesta estructurada
                self._on_structured_response(structured)

            def on_tool_used():
                # Este callback se llama cuando se usa una herramienta
                self._on_tool_used()

            def get_agent_feedback():
                # Este callback retorna feedback para el agente
                if hasattr(self, 'extended_stats_manager'):
                    return self.extended_stats_manager.get_feedback_for_agent()
                return {}

            agent = AgentClient(
                self.chat_log,
                history,
                self.cwd,
                session_id=session_id,
                is_active_session=is_active,
                on_structured_response=on_structured_response,
                on_tool_used=on_tool_used,
                get_agent_feedback=get_agent_feedback,
            )
            self._session_states[session_id] = SessionState(history, agent)
        return self._session_states[session_id]

    async def _load_history(self: "ClaudeChat", state: "SessionState") -> None:
        """Cargar historial de mensajes de una sesión"""
        history = state.history.load()
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.chat_log.write_user(content)
            elif role == "assistant":
                self.chat_log.write_assistant(content)
            elif role == "tool_use":
                tool_name = content.get("name", "unknown") if isinstance(content, dict) else "unknown"
                tool_input = content.get("input", "") if isinstance(content, dict) else str(content)
                self.chat_log.write_tool(tool_name, str(tool_input) if tool_input else None)
            elif role == "tool_result":
                self.chat_log.write_result(str(content))

    async def _switch_to_session(self: "ClaudeChat", session_id: str, update_tabs: bool = True) -> None:
        """Cambiar a una sesión específica"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return

        # Guardar scroll position de la sesión actual antes de cambiar
        if self._current_session_id and self._current_session_id in self._session_states:
            current_state = self._session_states[self._current_session_id]
            current_state.scroll_position = self.chat_log.scroll_y
            current_state.scroll_x = self.chat_log.scroll_x

        self._current_session_id = session_id
        state = await self._get_or_create_session_state(session_id)

        if update_tabs:
            self.call_later(self._update_tabs)

        self.session_manager.set_last_active(session_id)

        # Limpiar y recargar chat
        self.chat_log.clear()
        await self._load_history(state)

        # Restaurar scroll position de la sesión (o ir al fondo si es nueva)
        self.call_later(lambda: self._restore_scroll(state))

    async def _update_tabs(self: "ClaudeChat") -> None:
        """Actualizar tabs según sesiones existentes"""
        await self.tabs.clear()
        for session in self.session_manager.list_sessions():
            tab_id = f"tab-{session.id}"
            await self.tabs.add_tab(Tab(session.name, id=tab_id))

        if self._current_session_id:
            self.tabs.active = f"tab-{self._current_session_id}"

    async def on_tabs_tab_activated(self: "ClaudeChat", event: Tabs.TabActivated) -> None:
        """Cambio de sesión al hacer clic en tab"""
        tab_id = event.tab.id
        if tab_id and tab_id.startswith("tab-"):
            session_id = tab_id[4:]
            if session_id != self._current_session_id:
                await self._switch_to_session(session_id, update_tabs=False)

    async def action_new_session(self: "ClaudeChat") -> None:
        """Crear nueva sesión (Ctrl+N)"""
        session = self.session_manager.create_session()
        await self._switch_to_session(session.id)

    async def action_close_session(self: "ClaudeChat") -> None:
        """Cerrar sesión actual (Ctrl+W)"""
        sessions = self.session_manager.list_sessions()
        if len(sessions) <= 1:
            self.chat_log.write("[dim]No se puede cerrar la última sesión[/dim]")
            return

        if self._current_session_id:
            # Cancelar task pendiente si existe
            state = self._session_states.get(self._current_session_id)
            if state and state.pending_task and not state.pending_task.done():
                state.pending_task.cancel()

            self.session_manager.delete_session(self._current_session_id)
            if self._current_session_id in self._session_states:
                del self._session_states[self._current_session_id]

            sessions = self.session_manager.list_sessions()
            await self._switch_to_session(sessions[0].id)

    def action_toggle_sessions(self: "ClaudeChat") -> None:
        """Mostrar lista de sesiones (Ctrl+S)"""
        sessions = self.session_manager.list_sessions()
        self.chat_log.write("[bold]Sesiones:[/bold]")
        for s in sessions:
            marker = ">" if s.id == self._current_session_id else " "
            self.chat_log.write(f"  {marker} {s.name}")
        self.chat_log.write("[dim]Ctrl+N nueva, Ctrl+W cerrar[/dim]")

    def _restore_scroll(self: "ClaudeChat", state: "SessionState") -> None:
        """Restaurar posición de scroll de una sesión"""
        if state.scroll_position > 0:
            self.chat_log.scroll_to(y=state.scroll_position, x=state.scroll_x, animate=False)
        else:
            self.chat_log.scroll_end(animate=False)
