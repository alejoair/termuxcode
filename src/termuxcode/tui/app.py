"""App principal - TUI optimizada para móvil/Termux"""
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Tabs, Button, Static
from textual.reactive import reactive

from .chat import ChatLog
from .sessions import SessionManager
from .styles import CSS
from .mixins import SessionHandlersMixin, QueryHandlersMixin, SessionState
from .memory import Initializer


class ClaudeChat(
    SessionHandlersMixin,
    QueryHandlersMixin,
    App
):
    """TUI optimizada para móvil: sin header, compacta, touch-friendly"""

    CSS = CSS

    is_thinking = reactive(False)

    BINDINGS = [
        ("ctrl+n", "new_session", "Nuevo"),
        ("ctrl+w", "close_session", "Cerrar"),
        ("ctrl+s", "toggle_sessions", "Sesiones"),
    ]

    def __init__(self, cwd: str = None, max_history: int = 100):
        super().__init__()
        self.cwd = cwd or str(Path.cwd())
        self.max_history = max_history
        self.session_manager = SessionManager(Path(self.cwd) / ".sessions")
        self._current_session_id: str | None = None
        self._session_states: dict[str, SessionState] = {}

    def compose(self) -> ComposeResult:
        """Layout minimalista: solo chat + input compacto"""
        # Chat en el medio (ocupa el espacio restante)
        yield ChatLog(id="messages")
        # Input en la parte inferior
        with Vertical(id="bottom-container"):
            with Horizontal(id="tabs-row"):
                yield Tabs(id="sessions-tabs")
                yield Button("+", id="new-session-btn")
            yield Input(id="message-input", placeholder="Mensaje...", classes="-textual-compact")
            # Spacer de 2 líneas para evitar que el input quede tapado por la barra de navegación
            yield Static(id="bottom-spacer")

    def on_mount(self) -> None:
        self.chat_log = self.query_one("#messages", ChatLog)
        self.tabs = self.query_one("#sessions-tabs", Tabs)
        self.input = self.query_one("#message-input", Input)

        # Inicializar sistema de memoria (CLAUDE.md, config.json, etc.)
        self._initialize_memory()

        self.chat_log.write("[dim]TermuxCode listo. Ctrl+N = nueva sesión[/dim]")
        self.call_later(self._load_first_session)

    def _initialize_memory(self) -> None:
        """Inicializa el sistema de memoria al iniciar la app."""
        try:
            init = Initializer(cwd=self.cwd)
            results = init.initialize_all()
        except Exception as e:
            # Silencioso - si falla, la app sigue funcionando
            self.chat_log.write(f"[dim]Memoria: {e}[/dim]")

    def on_click(self, event) -> None:
        if isinstance(event.widget, ChatLog):
            event.widget.focus()

    def on_key(self, event) -> None:
        if event.key == "up":
            self.chat_log.scroll_relative(y=-1, animate=False)
            event.stop()
        elif event.key == "down":
            self.chat_log.scroll_relative(y=1, animate=False)
            event.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Manejar click en botón nueva sesión"""
        if event.button.id == "new-session-btn":
            await self.action_new_session()



if __name__ == "__main__":
    app = ClaudeChat()
    app.run()
