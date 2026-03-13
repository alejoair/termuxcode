"""Widget de chat con mensajes diferenciados"""
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel


class ChatLog(RichLog):
    """Widget de chat con mensajes claramente diferenciados"""

    def __init__(self, **kwargs):
        super().__init__(
            wrap=True,
            auto_scroll=False,
            markup=True,
            min_width=0,
            highlight=True,
            **kwargs
        )
        self._is_thinking = False

    def write_user(self, content: str) -> None:
        """Mensaje del usuario - fondo destacado, alineado derecha visualmente"""
        # Línea vacía para separar
        self.write("")
        # Usuario con prefijo destacado y contenido
        self.write(f"[bold white on #1e5f74] ▶ USUARIO [/bold white on #1e5f74] [dim]─────────────────[/dim]")
        self.write(f"[cyan]{content}[/cyan]")
        self.write("[dim]─[/dim]")

    def write_assistant(self, content: str) -> None:
        """Mensaje del asistente - estilo diferente"""
        self._is_thinking = False
        # Línea vacía para separar
        self.write("")
        # Asistente con prefijo diferente
        self.write(f"[bold black on #4a7c59] ◆ CLAUDE [/bold black on #4a7c59] [dim]─────────────────[/dim]")
        try:
            md = Markdown(content, code_theme="monokai")
            self.write(md)
        except Exception:
            self.write(f"[green]{content}[/green]")
        self.write("[dim]─[/dim]")

    def write_thinking(self) -> None:
        """Indicador de que Claude está procesando"""
        self._is_thinking = True
        self.write("")
        self.write("[dim italic]  ◆ procesando...[/dim italic]")

    def write_tool(self, tool_name: str, tool_input: str = None) -> None:
        """Herramienta usada"""
        if tool_input:
            preview = str(tool_input).replace('\n', ' ')[:40]
            if len(str(tool_input)) > 40:
                preview += "..."
            self.write(f"  [dim yellow]│[/dim yellow] [bold yellow]{tool_name}[/bold yellow] [dim]{preview}[/dim]")
        else:
            self.write(f"  [dim yellow]│[/dim yellow] [bold yellow]{tool_name}[/bold yellow]")

    def write_result(self, content: str) -> None:
        """Resultado de herramienta"""
        preview = str(content).replace('\n', ' ')[:50]
        if len(str(content)) > 50:
            preview += "..."
        self.write(f"  [dim green]└►[/dim green] [dim]{preview}[/dim]")

    def write_error(self, error: str) -> None:
        """Error - visible"""
        self.write("")
        self.write(f"[bold white on #8b0000] ✗ ERROR [/bold white on #8b0000]")
        self.write(f"[red]{error}[/red]")

    def write_streaming(self, chunk: str) -> None:
        """Escribir chunk durante streaming"""
        pass
