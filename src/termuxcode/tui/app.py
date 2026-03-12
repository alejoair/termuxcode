"""App principal - TUI responsive para Claude Agent SDK"""
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Header, Input, Tabs, Tab

from .chat import ChatLog
from .agent import AgentClient
from .history import MessageHistory
from .sessions import SessionManager
from .styles import CSS


class ClaudeChat(App):
    """TUI responsive para chat con Claude Agent SDK"""

    CSS = CSS
    TITLE = "Claude Chat"
    AUTO_FOCUS = "#message-input"

    BINDINGS = [
        ("ctrl+n", "new_session", "Nueva sesión"),
        ("ctrl+w", "close_session", "Cerrar sesión"),
    ]

    def __init__(self, cwd: str = None, max_history: int = 100):
        super().__init__()
        self.cwd = cwd or str(Path.cwd())
        self.max_history = max_history
        self.session_manager = SessionManager(Path(self.cwd) / ".sessions")
        self._current_session_id: str | None = None
        self._sessions: dict[str, MessageHistory] = {}
        self.history: MessageHistory | None = None
        self.agent: AgentClient | None = None

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with VerticalScroll(id="chat-container"):
            yield ChatLog(id="messages")
        with Vertical(id="bottom-container"):
            yield Tabs(id="sessions-tabs")
            with Vertical(id="input-container"):
                yield Input(id="message-input", placeholder="Escribe tu mensaje...")

    def on_mount(self) -> None:
        self.chat_log = self.query_one("#messages", ChatLog)
        self.tabs = self.query_one("#sessions-tabs", Tabs)
        self.input = self.query_one("#message-input", Input)
        self.query_one("#chat-container").anchor()  # Auto-scroll al final
        self.call_later(self._load_first_session)  # Cargar sesión inicial

    async def _load_first_session(self) -> None:
        """Cargar sesiones existentes o crear la primera al iniciar la app"""
        sessions = self.session_manager.list_sessions()
        if not sessions:
            session = self.session_manager.create_session("Nueva sesión")
        else:
            last_id = self.session_manager.get_last_active()
            session = self.session_manager.get_session(last_id) or sessions[0]

        await self._switch_to_session(session.id)

    async def _load_history(self) -> None:
        """Cargar y mostrar el historial de mensajes"""
        history = self.history.load()
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.chat_log.write_user(content)
            elif role == "assistant":
                self.chat_log.write_assistant(content)

    async def _switch_to_session(self, session_id: str) -> None:
        """Cambiar a una sesión específica"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return

        self._current_session_id = session_id

        # Obtener o crear MessageHistory para esta sesión
        if session_id not in self._sessions:
            self._sessions[session_id] = MessageHistory(
                filename="messages.jsonl",
                max_messages=self.max_history,
                session_id=session_id,
                cwd=self.cwd
            )

        self.history = self._sessions[session_id]
        self.agent = AgentClient(self.chat_log, self.history, self.cwd)

        # Actualizar tabs
        self._update_tabs()

        # Guardar última sesión activa
        self.session_manager.set_last_active(session_id)

        # Recargar historial en ChatLog
        self.chat_log.clear()
        await self._load_history()

    def _update_tabs(self) -> None:
        """Actualizar los tabs basado en sesiones existentes"""
        self.tabs.clear()

        for session in self.session_manager.list_sessions():
            tab_id = f"tab-{session.id}"
            self.tabs.add(Tab(session.name, id=tab_id))

        # Activar tab actual
        if self._current_session_id:
            for tab in self.tabs.children:
                if tab.id == f"tab-{self._current_session_id}":
                    self.tabs.active_tab = tab
                    break

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Cambio de sesión al hacer clic o presionar Enter en un tab"""
        tab_id = event.tab.id
        if tab_id and tab_id.startswith("tab-"):
            session_id = tab_id[4:]  # Remover prefijo "tab-"
            self.call_later(self._run_switch_session, session_id)

    def _run_switch_session(self, session_id: str) -> None:
        """Wrapper async para cambiar de sesión"""
        import asyncio
        asyncio.create_task(self._switch_to_session(session_id))

    def action_new_session(self) -> None:
        """Crear nueva sesión (Ctrl+N)"""
        session = self.session_manager.create_session()
        self.call_later(self._run_switch_session, session.id)
        self.input.focus()

    def action_close_session(self) -> None:
        """Cerrar sesión actual (Ctrl+W)"""
        sessions = self.session_manager.list_sessions()
        if len(sessions) <= 1:
            return  # No cerrar la última sesión

        if self._current_session_id:
            self.session_manager.delete_session(self._current_session_id)
            del self._sessions[self._current_session_id]

            # Cambiar a la primera sesión disponible
            sessions = self.session_manager.list_sessions()
            self.call_later(self._run_switch_session, sessions[0].id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return
        prompt = event.value
        event.input.clear()
        self.call_later(self._run_query, prompt)

    async def _run_query(self, prompt: str) -> None:
        """Ejecutar query del agente"""
        if self.agent is None:
            self.chat_log.write_error("No session loaded. Please wait...")
            return
        await self.agent.query(prompt)


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    app = ClaudeChat()
    app.run()
