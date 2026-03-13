"""CLI para ejecutar la TUI de termuxcode"""
import argparse
import os
from pathlib import Path

from .tui.app import ClaudeChat


def main() -> None:
    """Ejecutar la TUI de termuxcode"""
    parser = argparse.ArgumentParser(description="TUI para Claude Agent SDK")
    parser.add_argument("--dev", action="store_true", help="Modo desarrollo (devtools + debug)")
    parser.add_argument("--cwd", type=str, default=None, help="Directorio de trabajo")
    args = parser.parse_args()

    # Activar features de Textual via variable de entorno
    if args.dev:
        os.environ["TEXTUAL"] = "devtools,debug"

    app = ClaudeChat(cwd=args.cwd)
    app.run()


if __name__ == "__main__":
    main()
