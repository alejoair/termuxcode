"""Widget de chat con mensajes diferenciados"""
import json
import re
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel


class ChatLog(RichLog):
    """Widget de chat con mensajes claramente diferenciados"""

    def action_scroll_up(self) -> None:
        self.scroll_relative(y=-1, animate=False)

    def action_scroll_down(self) -> None:
        self.scroll_relative(y=1, animate=False)

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
        """Mensaje del usuario - fondo destacado, separador dinámico"""
        self.write("")
        self.write("")  # Espaciado extra entre mensajes
        # Separador dinámico basado en ancho disponible
        width = self.content_size.width if self.content_size.width > 0 else 80
        # Separador superior: ocupa todo el espacio después del header (~12 chars)
        sep_len = max(5, width - 15)
        separator = "─" * sep_len
        self.write(f"[bold white on #1e5f74] ▶ USUARIO [/bold white on #1e5f74] [dim]{separator}[/dim]")
        self.write(f"[cyan]{content}[/cyan]")
        # Separador inferior: 80% del ancho disponible
        bottom_sep = max(10, int(width * 0.8))
        self.write(f"[dim]{'─' * bottom_sep}[/dim]")

    def write_assistant(self, content: str, structured_tag: str = None) -> None:
        """Mensaje del asistente

        Args:
            content: Contenido del mensaje.
            structured_tag: Tag desde la respuesta estructurada (INFO, WARNING, ERROR, SUCCESS).
                            Ignorado en esta versión simplificada.
        """
        self._is_thinking = False
        self.write("")
        self.write("")  # Espaciado extra entre mensajes

        # Header simple con color verde por defecto
        self.write("[bold black on #4a7c59] ◆ CLAUDE [/bold black on #4a7c59]")

        try:
            md = Markdown(content, code_theme="monokai")
            self.write(md)
        except Exception:
            self.write(f"[green]{content}[/green]")

        # Separador dinámico: 80% del ancho disponible
        width = self.content_size.width if self.content_size.width > 0 else 80
        sep_len = max(10, int(width * 0.8))
        self.write(f"[dim]{'─' * sep_len}[/dim]")

    def write_thinking(self) -> None:
        """Indicador de que Claude está procesando"""
        self._is_thinking = True
        self.write("")
        self.write("[dim italic]  ◆ procesando...[/dim italic]")

    def write_tool(self, tool_name: str, tool_input: str = None) -> None:
        """Herramienta usada - truncado dinámico"""
        if tool_input:
            # Truncado dinámico basado en ancho disponible
            # Reserva espacio para: prefijo (4) + nombre + separadores (6) + "..."
            width = self.content_size.width if self.content_size.width > 0 else 80
            available = max(15, width - len(tool_name) - 12)
            preview = str(tool_input).replace('\n', ' ')[:available]
            if len(str(tool_input)) > available:
                preview += "..."
            self.write(f"  [dim yellow]│[/] [bold yellow]{tool_name}[/bold yellow] [dim]{preview}[/dim]")
        else:
            self.write(f"  [dim yellow]│[/] [bold yellow]{tool_name}[/bold yellow]")

    def write_result(self, content: str) -> None:
        """Resultado de herramienta - truncado dinámico"""
        # Truncado dinámico basado en ancho disponible
        # Reserva espacio para: prefijo (6) + "..."
        width = self.content_size.width if self.content_size.width > 0 else 80
        available = max(20, width - 10)
        preview = str(content).replace('\n', ' ')[:available]
        if len(str(content)) > available:
            preview += "..."
        self.write(f"  [dim green]└►[/] [dim]{preview}[/dim]")

    def write_error(self, error: str) -> None:
        """Error - visible"""
        self.write("")
        self.write("")  # Espaciado extra entre mensajes
        self.write(f"[bold white on #8b0000] ✗ ERROR [/bold white on #8b0000]")
        self.write(f"[red]{error}[/red]")
