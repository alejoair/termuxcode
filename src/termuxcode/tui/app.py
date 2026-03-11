"""App principal - TUI responsive para Claude Agent SDK"""
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Input

from .chat import ChatLog
from .agent import AgentClient
from .styles import CSS


class ClaudeChat(App):
    """TUI responsive para chat con Claude Agent SDK"""

    CSS = CSS
    TITLE = "Claude Chat"
    AUTO_FOCUS = "#message-input"

    def __init__(self, cwd: str = None, max_history: int = 100):
        super().__init__()
        self.cwd = cwd
        self.max_history = max_history

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Vertical(id="chat-container"):
            yield ChatLog(id="messages")
        with Vertical(id="input-container"):
            yield Input(id="message-input", placeholder="Escribe tu mensaje...")

    def on_mount(self) -> None:
        self.chat_log = self.query_one("#messages", ChatLog)
        self.input = self.query_one("#message-input", Input)
        self.agent = AgentClient(self.chat_log, self.cwd, self.max_history)
        self._update_breakpoint()

    def on_resize(self, event) -> None:
        self._update_breakpoint()

    def _update_breakpoint(self) -> None:
        width = self.size.width
        self.screen.set_class(width < 60, "-small")
        self.screen.set_class(60 <= width < 100, "-medium")
        self.screen.set_class(width >= 100, "-large")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return
        prompt = event.value
        event.input.clear()
        self.call_later(self._run_query, prompt)

    def _run_query(self, prompt: str) -> None:
        self.agent.query(prompt)


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    app = ClaudeChat()
    app.run()
