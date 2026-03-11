"""Widget de chat con auto-scroll, wrapping y markdown"""
from textual.widgets import RichLog
from rich.markdown import Markdown


class ChatLog(RichLog):
    """Widget de chat con auto-scroll, word wrapping y markdown"""

    DEFAULT_CSS = """
    ChatLog {
        height: 1fr;
        width: 100%;
        background: $surface;
        color: $foreground;
        overflow-y: scroll;
        scrollbar-gutter: auto;
    }

    ChatLog > .vertical-scrollbar {
        background: $panel;
    }

    ChatLog > .vertical-scrollbar--thumb {
        background: $primary;
    }

    ChatLog:focus {
        background-tint: $foreground 5%;
    }

    ChatLog Rich {
        width: 100%;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(
            wrap=True,
            auto_scroll=True,
            markup=True,
            min_width=0,
            **kwargs
        )

    def write_raw(self, content: str) -> None:
        """Escribir contenido con markup directo"""
        super().write(content)

    def write_user(self, content: str) -> None:
        """Escribir mensaje del usuario"""
        # El contenido del usuario no necesita markdown (es texto plano)
        self.write_raw(f"[bold cyan]You:[/] {content}\n")

    def write_assistant(self, content: str) -> None:
        """Escribir mensaje del asistente con soporte markdown"""
        # Escribir el título
        self.write_raw(f"[bold green]Claude:[/]\n")
        # Renderizar el contenido como markdown
        try:
            md = Markdown(content)
            self.write(md)
        except Exception:
            # Si falla el markdown, escribir como texto plano
            self.write_raw(f"{content}\n")

    def write_tool(self, tool_name: str, tool_input: str = None) -> None:
        """Escribir herramienta usada (max 2 líneas, texto pequeño)"""
        self.write_raw(f"[dim][yellow]🔧 {tool_name}[/yellow][/dim]")
        if tool_input:
            # Limitar a 2 líneas máximo
            lines = str(tool_input).split('\n')[:2]
            preview = '\n'.join(lines)
            if len(lines) == 2 or len(tool_input) > len(preview):
                preview = preview + "..."
            self.write_raw(f"[dim][sub]{preview}[/sub][/dim]")
        self.write_raw("")

    def write_result(self, content: str) -> None:
        """Escribir resultado de herramienta (max 2 líneas, texto pequeño)"""
        self.write_raw(f"[dim][sub]✅ Result:[/sub][/dim]")
        # Limitar a 2 líneas máximo
        lines = str(content).split('\n')[:2]
        preview = '\n'.join(lines)
        if len(lines) == 2 or len(content) > len(preview):
            preview = preview + "..."
        self.write_raw(f"[dim][sub]{preview}[/sub][/dim]")
        self.write_raw("")

    def write_error(self, error: str) -> None:
        """Escribir error"""
        self.write_raw(f"[bold red]❌ Error: {error}[/]\n")

    def write_thinking(self, text: str) -> None:
        """Escribir thinking (opcional)"""
        self.write_raw(f"[dim]... {text} ...[/dim]\n")

    def clear(self) -> None:
        """Limpiar todos los mensajes del log"""
        self.remove_children()
        self.lines.clear()
