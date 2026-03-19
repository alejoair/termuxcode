"""App principal - TUI optimizada para móvil/Termux.

ClaudeChat es la aplicación Textual que orquesta toda la UI. Hereda de dos
mixins que separan la lógica de sesiones y de queries del código de layout,
manteniendo esta clase enfocada solo en inicialización y eventos de UI.

Flujo de arranque:
    1. __init__  → instancia managers (sesiones, background tasks, notificaciones)
    2. on_mount  → monta widgets, inicializa memoria y lanza agentes en background
    3. _load_first_session → abre o crea la sesión inicial (delegado a SessionHandlersMixin)

Logging:
    Todos los módulos usan logging estándar (logging.getLogger(__name__)).
    En modo --dev, los logs se envían al Textual console via TextualHandler.
    Correr: textual console  (en otra terminal) y luego: termuxcode --dev
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Tabs, Button, Static
from textual.reactive import reactive
from textual.logging import TextualHandler

from termuxcode.tui.chat import ChatLog
from termuxcode.core.session_manager import SessionManager
from termuxcode.tui.styles import CSS
from termuxcode.tui.mixins import SessionHandlersMixin, QueryHandlersMixin
from termuxcode.core.session_manager import SessionState
from termuxcode.core.memory import Initializer
from termuxcode.core.background_manager import BackgroundTaskManager
from termuxcode.core.agents.environment_agent import EnvironmentAgent
from termuxcode.core.agents.architecture_agent import ArchitectureAgent
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.notification_system import NotificationQueue
from termuxcode.tui.project_info import ProjectInfo


class ClaudeChat(
    SessionHandlersMixin,
    QueryHandlersMixin,
    App
):
    """TUI optimizada para móvil: sin header, compacta, touch-friendly.

    Mixins (orden importa para MRO):
        SessionHandlersMixin  → gestión de sesiones (crear, cerrar, cambiar)
        QueryHandlersMixin    → envío de mensajes y streaming de respuestas
    """

    CSS = CSS

    # Reactivo que activa/desactiva el indicador de "pensando" en la UI
    is_thinking = reactive(False)

    BINDINGS = [
        ("ctrl+n", "new_session", "Nuevo"),
        ("ctrl+w", "close_session", "Cerrar"),
        ("ctrl+s", "toggle_sessions", "Sesiones"),
        ("ctrl+h", "stop_query", "Stop"),
    ]

    def __init__(self, cwd: str = None, max_history: int = 100):
        super().__init__()
        # Redirigir logs de todos los módulos al Textual console (visible con --dev)
        logging.basicConfig(level=logging.DEBUG, handlers=[TextualHandler()])
        # Directorio de trabajo del proyecto abierto
        self.cwd = cwd or str(Path.cwd())
        # Máximo de mensajes que se retienen en el historial de cada sesión
        self.max_history = max_history
        # Persiste y carga sesiones desde .claude/sessions/
        self.session_manager = SessionManager(Path(self.cwd) / ".claude" / "sessions")
        # ID de la sesión actualmente visible en la UI
        self._current_session_id: str | None = None
        # Estado en memoria de cada sesión abierta (agente, historial, etc.)
        self._session_states: dict[str, SessionState] = {}
        # Gestor de asyncio tasks en background, una por sesión o por tarea global
        self.background_manager = BackgroundTaskManager()
        # Cola de notificaciones para mostrar eventos asincrónicos en la UI
        self.notification_queue = NotificationQueue()

    def compose(self) -> ComposeResult:
        """Construye el layout: chat central + barra inferior fija.

        La barra inferior contiene las tabs de sesiones, el input y el botón Stop.
        El spacer al final evita que el input quede tapado por la barra de
        navegación del sistema en móvil.
        """
        yield ProjectInfo(id="project-info")
        yield ChatLog(id="messages")
        with Vertical(id="bottom-container"):
            with Horizontal(id="tabs-row"):
                yield Tabs(id="sessions-tabs")
                yield Button("+", id="new-session-btn", flat=True)
            with Horizontal(id="input-row"):
                yield Input(id="message-input", placeholder="Mensaje...", classes="-textual-compact")
                yield Button("⏹", id="stop-btn", classes="-stop-button")
            # Evita que el input quede oculto bajo la barra de navegación del SO
            yield Static(id="bottom-spacer")

    def on_mount(self) -> None:
        """Punto de entrada post-render: resuelve widgets, inicializa memoria y sesión."""
        self.chat_log = self.query_one("#messages", ChatLog)
        self.tabs = self.query_one("#sessions-tabs", Tabs)
        self.input = self.query_one("#message-input", Input)

        # El botón Stop arranca deshabilitado; se habilita cuando hay un query activo
        self._update_stop_button()

        # Carga archivos estáticos (CLAUDE.md, config.json) y lanza agentes en background
        self._initialize_memory()

        self.chat_log.write("[dim]TermuxCode listo. Ctrl+N = nueva sesión[/dim]")
        # call_later garantiza que la sesión se carga después de que Textual
        # termine el ciclo de mount completo
        self.call_later(self._load_first_session)

    def _initialize_memory(self) -> None:
        """Inicializa la memoria de sesión en dos pasos:

        1. Carga sincrónica de archivos estáticos del proyecto (CLAUDE.md, config.json)
           usando Initializer. Si alguno no existe, se ignora silenciosamente.

        2. Lanza los agentes de inicialización en secuencia dentro de un solo
           background task. EnvironmentAgent corre primero para que ArchitectureAgent
           pueda usar su contexto (lenguaje, source_dir, entry_point).
           Cada agente se salta si sus campos ya están en el Blackboard.
           La UI no espera — todo ocurre en paralelo.
        """
        try:
            init = Initializer(cwd=self.cwd)
            init.initialize_all()
        except Exception as e:
            self.chat_log.write(f"[dim]Memoria estática: {e}[/dim]")

        async def _run_init_agents():
            env = EnvironmentAgent(cwd=self.cwd)
            await env.run()
            arch = ArchitectureAgent(cwd=self.cwd)
            await arch.run()

        self.background_manager.start_task("project_init", _run_init_agents())

    def on_click(self, event) -> None:
        """Al hacer click en el chat, enfocar el ChatLog para permitir scroll táctil."""
        if isinstance(event.widget, ChatLog):
            event.widget.focus()

    def on_key(self, event) -> None:
        """Scroll manual del chat con flechas arriba/abajo."""
        if event.key == "up":
            self.chat_log.scroll_relative(y=-1, animate=False)
            event.stop()
        elif event.key == "down":
            self.chat_log.scroll_relative(y=1, animate=False)
            event.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Delega clicks de botones a las acciones correspondientes."""
        if event.button.id == "new-session-btn":
            await self.action_new_session()
        elif event.button.id == "stop-btn":
            await self.action_stop_query()


if __name__ == "__main__":
    app = ClaudeChat()
    app.run()
