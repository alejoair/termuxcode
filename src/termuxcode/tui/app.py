"""App principal - TUI responsive para Claude Agent SDK"""
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Input, Static

from .chat import ChatLog
from .agent import AgentClient, RollingWindowConfig
from .styles import CSS


class ClaudeChat(App):
    """TUI responsive para chat con Claude Agent SDK"""

    CSS = CSS
    TITLE = "Claude Chat"
    AUTO_FOCUS = "#message-input"

    def __init__(self, cwd: str = None):
        super().__init__()
        self.cwd = cwd
        self.agent: AgentClient = None
        # Configuración de rolling window
        self.window_config = RollingWindowConfig(
            max_visible=50,   # 50 mensajes visibles
            max_session=200,  # 200 mensajes guardados en sesión
            max_turns=50,    # 50 turnos a Claude
        )

    def compose(self) -> ComposeResult:
        """Componer la UI responsive"""
        # Header (oculto en pantallas pequeñas)
        yield Header(id="header")

        # Contenedor del chat - ocupa espacio disponible
        with Vertical(id="chat-container"):
            yield ChatLog(id="messages")

        # Input siempre visible en la parte inferior
        with Vertical(id="input-container"):
            yield Input(
                id="message-input",
                placeholder="Escribe tu mensaje...",
            )

    def on_mount(self) -> None:
        """Inicializar componentes"""
        self.chat_log = self.query_one("#messages", ChatLog)
        self.input = self.query_one("#message-input", Input)
        self.agent = AgentClient(
            self.chat_log,
            self.cwd,
            config=self.window_config,
        )

        # Detectar tamaño de pantalla para breakpoint
        self._update_breakpoint()

    async def on_mount_async(self) -> None:
        """Inicializar async - cargar historial y reconstruir UI"""
        # Cargar historial del archivo de sesión
        await self.agent.load_history_only()
        # Reconstruir UI con mensajes del rolling window
        await self.agent.rebuild_ui()
        # Conectar al SDK (continúa sesión existente)
        await self.agent.connect()

    def on_resize(self, event) -> None:
        """Actualizar breakpoint cuando cambia el tamaño"""
        self._update_breakpoint()

    def _update_breakpoint(self) -> None:
        """Actualizar clases de breakpoint según tamaño"""
        width = self.size.width

        # Asignar clase según tamaño usando set_class
        is_small = width < 60
        is_medium = width >= 60 and width < 100
        is_large = width >= 100

        self.screen.set_class(is_small, "-small")
        self.screen.set_class(is_medium, "-medium")
        self.screen.set_class(is_large, "-large")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Cuando el usuario presiona Enter"""
        if not event.value.strip():
            return

        prompt = event.value
        event.input.clear()
        self.call_later(self._run_query, prompt)

    def on_unmount(self) -> None:
        """Desconectar agente al cerrar la app"""
        if self.agent:
            self.call_later(self._disconnect_agent)

    async def _disconnect_agent(self) -> None:
        """Desconectar el agente de forma segura"""
        if self.agent and self.agent.is_connected:
            await self.agent.disconnect()

    async def _run_query(self, prompt: str) -> None:
        """Ejecutar query del agente"""
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
