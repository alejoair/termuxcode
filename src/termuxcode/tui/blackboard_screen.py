"""Modal screen that displays the Blackboard contents as a tree."""
import json
from textual.screen import ModalScreen
from textual.widgets import RichLog
from textual.app import ComposeResult
from textual.binding import Binding
from rich.tree import Tree
from rich.text import Text

from termuxcode.core.memory.blackboard import Blackboard


class BlackboardScreen(ModalScreen):
    """Overlay that shows the current Blackboard state as a tree."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cerrar"),
        Binding("q", "dismiss", "Cerrar"),
    ]

    DEFAULT_CSS = """
    BlackboardScreen {
        align: center middle;
    }
    BlackboardScreen #bb-log {
        width: 90%;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="bb-log", wrap=True, markup=True, highlight=True)

    def on_mount(self) -> None:
        log = self.query_one("#bb-log", RichLog)
        bb = Blackboard("app")
        data = bb.get_all()

        if not data:
            log.write("[dim]Blackboard vacío[/dim]")
            return

        tree = Tree("[bold]Blackboard[/bold]")
        self._build_tree(tree, data)
        log.write(tree)

    def _build_tree(self, parent: Tree, data: dict) -> None:
        """Recursively build a Rich tree from nested dict."""
        for key, value in data.items():
            if isinstance(value, dict):
                branch = parent.add(f"[bold cyan]{key}[/bold cyan]")
                self._build_tree(branch, value)
            elif isinstance(value, list):
                if not value:
                    parent.add(f"[green]{key}[/green] = [dim][ ][/dim]")
                elif len(value) <= 5:
                    items = ", ".join(str(v) for v in value)
                    parent.add(f"[green]{key}[/green] = [yellow]{items}[/yellow]")
                else:
                    branch = parent.add(f"[green]{key}[/green] [dim]({len(value)} items)[/dim]")
                    for item in value:
                        text = str(item)
                        if len(text) > 80:
                            text = text[:77] + "..."
                        branch.add(f"[yellow]{text}[/yellow]")
            else:
                text = str(value)
                if len(text) > 100:
                    text = text[:97] + "..."
                parent.add(f"[green]{key}[/green] = [white]{text}[/white]")
