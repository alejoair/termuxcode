"""CLI para ejecutar la TUI de termuxcode"""
from .tui.app import ClaudeChat


def main() -> None:
    """Ejecutar la TUI de termuxcode"""
    app = ClaudeChat()
    app.run()


if __name__ == "__main__":
    main()
