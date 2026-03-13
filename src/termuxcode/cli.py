"""CLI para ejecutar la TUI de termuxcode"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from .tui.app import ClaudeChat


def main() -> None:
    """Ejecutar la TUI de termuxcode"""
    parser = argparse.ArgumentParser(description="TUI para Claude Agent SDK")
    parser.add_argument("--dev", action="store_true", help="Modo desarrollo (devtools + debug)")
    parser.add_argument("--cwd", type=str, default=None, help="Directorio de trabajo")
    parser.add_argument("--serve", action="store_true", help="Modo servidor (acceso web)")
    args = parser.parse_args()

    # Activar features de Textual via variable de entorno
    if args.dev:
        os.environ["TEXTUAL"] = "devtools,debug"

    if args.serve:
        # Ejecutar en modo servidor usando textual serve (de textual-dev)
        cmd = ["textual", "serve", "-c", f"{sys.executable} -m termuxcode.tui.app"]
        if args.dev:
            cmd.insert(2, "--dev")
        subprocess.run(cmd)
    else:
        app = ClaudeChat(cwd=args.cwd)
        app.run()


if __name__ == "__main__":
    main()
