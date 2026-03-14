"""App principal - TUI optimizada para móvil/Termux"""
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Tabs, Button, Static
from textual.reactive import reactive

from .chat import ChatLog
from .sessions import SessionManager
from .styles import CSS
from .game import StatsManager, XPBar, AchievementPopup, LevelUpBanner, ExtendedStatsManager
from .game.metadata_achievements import get_all_metadata_achievements
from .mixins import SessionHandlersMixin, QueryHandlersMixin, GamificationMixin, SessionState


class ClaudeChat(
    SessionHandlersMixin,
    QueryHandlersMixin,
    GamificationMixin,
    App
):
    """TUI optimizada para móvil: sin header, compacta, touch-friendly"""

    CSS = CSS

    is_thinking = reactive(False)

    BINDINGS = [
        ("ctrl+n", "new_session", "Nuevo"),
        ("ctrl+w", "close_session", "Cerrar"),
        ("ctrl+s", "toggle_sessions", "Sesiones"),
        ("tab", "execute_suggestion", "Ejecutar sugerencia"),
    ]

    def __init__(self, cwd: str = None, max_history: int = 100):
        super().__init__()
        self.cwd = cwd or str(Path.cwd())
        self.max_history = max_history
        self.session_manager = SessionManager(Path(self.cwd) / ".sessions")
        self._current_session_id: str | None = None
        self._session_states: dict[str, SessionState] = {}

        # Sistema de gamificación
        self.stats_manager = StatsManager(Path(self.cwd) / ".sessions")

        # Sistema de gamificación extendido (respuestas estructuradas)
        self.extended_stats_manager = ExtendedStatsManager(Path(self.cwd) / ".sessions")

        # Guardar última sugerencia para ejecutar con Tab
        self._last_suggestion: str | None = None

    def compose(self) -> ComposeResult:
        """Layout minimalista: solo chat + input compacto"""
        # XPBar en el top
        yield XPBar(id="xp-bar")
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
        # Popups de gamificación al final (overlays, no afectan layout)
        yield AchievementPopup()
        yield LevelUpBanner()

    def on_mount(self) -> None:
        self.chat_log = self.query_one("#messages", ChatLog)
        self.tabs = self.query_one("#sessions-tabs", Tabs)
        self.input = self.query_one("#message-input", Input)
        self.xp_bar = self.query_one("#xp-bar", XPBar)

        # Configurar callbacks de gamificación
        self.stats_manager.on_achievement(self._show_achievement)
        self.stats_manager.on_level_up(self._show_level_up)

        # Actualizar XP bar con stats actuales
        self._update_xp_bar()

        self.chat_log.write("[dim]TermuxCode listo. Ctrl+N = nueva sesión[/dim]")
        self.call_later(self._load_first_session)

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

    async def action_execute_suggestion(self) -> None:
        """Ejecutar la última sugerencia (Tab)"""
        if not self._last_suggestion:
            self.chat_log.write("[dim]No hay sugerencia para ejecutar[/dim]")
            return

        self.chat_log.write(f"[dim]Ejecutando: {self._last_suggestion}[/dim]")

        # Envíar la sugerencia como si fuera un mensaje del usuario
        self._handle_query(self._last_suggestion)

        # Marcar que el usuario siguió la sugerencia (gamificación)
        self._on_suggestion_followed()
        self._last_suggestion = None


if __name__ == "__main__":
    app = ClaudeChat()
    app.run()
