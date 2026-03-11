"""Widget de chat con auto-scroll, wrapping y markdown"""
from textual.widgets import RichLog
from rich.markdown import Markdown


class ChatLog(RichLog):
    """Widget de chat con auto-scroll, word wrapping y markdown"""

    def __init__(self, **kwargs):
        super().__init__(
            wrap=True,
            auto_scroll=True,
            markup=True,
            min_width=0,
            **kwargs
        )

    def write_user(self, content: str) -> None:
        """Escribir mensaje del usuario"""
        self.write_raw(f"[bold cyan]You:[/] {content}\n")

    def write_assistant(self, content: str) -> None:
        """Escribir mensaje del asistente con soporte markdown"""
        self.write_raw(f"[bold green]Claude:[/]\n")
        try:
            md = Markdown(content)
            self.write(md)
        except Exception:
            self.write_raw(f"{content}\n")

    def write_tool(self, tool_name: str, tool_input: str = None) -> None:
        """Escribir herramienta usada (max 2 líneas)"""
        self.write_raw(f"[dim][yellow]🔧 {tool_name}[/yellow][/dim]")
        if tool_input:
            lines = str(tool_input).split('\n')[:2]
            preview = '\n'.join(lines)
            if len(lines) == 2 or len(tool_input) > len(preview):
                preview = preview + "..."
            self.write_raw(f"[dim][sub]{preview}[/sub][/dim]")
        self.write_raw("")

    def write_result(self, content: str) -> None:
        """Escribir resultado de herramienta (max 2 líneas)"""
        self.write_raw(f"[dim][sub]✅ Result:[/sub][/dim]")
        lines = str(content).split('\n')[:2]
        preview = '\n'.join(lines)
        if len(lines) == 2 or len(content) > len(preview):
            preview = preview + "..."
        self.write_raw(f"[dim][sub]{preview}[/sub][/dim]")
        self.write_raw("")

    def write_error(self, error: str) -> None:
        """Escribir error"""
        self.write_raw(f"[bold red]❌ Error: {error}[/]\n")
