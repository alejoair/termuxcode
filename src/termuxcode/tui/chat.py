"""Widget de chat con auto-scroll, wrapping y markdown"""
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class ChatLog(RichLog):
    """Widget de chat con auto-scroll, word wrapping y markdown"""

    def __init__(self, **kwargs):
        super().__init__(
            wrap=True,
            auto_scroll=False,
            markup=True,
            min_width=0,
            **kwargs
        )

    def write_user(self, content: str) -> None:
        """Escribir mensaje del usuario con fondo destacado"""
        self.write("")  # Separación superior
        # Crear panel con fondo para mensaje del usuario
        user_text = Text.from_markup(f"[bold cyan]You:[/] {content}")
        panel = Panel(
            user_text,
            style="on #1e3a5f",  # Fondo azul oscuro
            padding=(0, 1),
            expand=False
        )
        self.write(panel)
        self.write("")  # Separación inferior

    def write_assistant(self, content: str) -> None:
        """Escribir mensaje del asistente con soporte markdown"""
        self.write("")  # Separación superior
        self.write("[bold green]Claude:[/]")
        try:
            md = Markdown(content)
            self.write(md)
        except Exception:
            self.write(f"{content}")
        self.write("")  # Separación inferior

    def write_tool(self, tool_name: str, tool_input: str = None) -> None:
        """Escribir herramienta usada (max 2 líneas)"""
        self.write(f"[dim][yellow]🔧 {tool_name}[/yellow][/dim]")
        if tool_input:
            lines = str(tool_input).split('\n')[:2]
            preview = '\n'.join(lines)
            if len(lines) == 2 or len(tool_input) > len(preview):
                preview = preview + "..."
            self.write(f"[dim][sub]{preview}[/sub][/dim]")
        self.write("")

    def write_result(self, content: str) -> None:
        """Escribir resultado de herramienta (max 2 líneas)"""
        self.write(f"[dim][sub]✅ Result:[/sub][/dim]")
        lines = str(content).split('\n')[:2]
        preview = '\n'.join(lines)
        if len(lines) == 2 or len(content) > len(preview):
            preview = preview + "..."
        self.write(f"[dim][sub]{preview}[/sub][/dim]")
        self.write("")

    def write_error(self, error: str) -> None:
        """Escribir error"""
        self.write(f"[bold red]❌ Error: {error}[/]\n")
