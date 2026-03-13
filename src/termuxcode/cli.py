"""CLI para ejecutar la TUI de termuxcode"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from .web_server import run_web_server


def main() -> None:
    """Ejecutar la TUI de termuxcode"""
    parser = argparse.ArgumentParser(description="TUI para Claude Agent SDK")
    parser.add_argument("--dev", action="store_true", help="Modo desarrollo (devtools + debug)")
    parser.add_argument("--cwd", type=str, default=None, help="Directorio de trabajo")
    parser.add_argument("--serve", action="store_true", help="Modo servidor (acceso web)")
    parser.add_argument(
        "--font-size",
        "--fs",
        type=int,
        default=16,
        help="Tamaño de fuente en px para modo web (default: 16). Aumentar para pantallas de alto DPI",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host para modo web (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto para modo web (default: 8000)",
    )
    args = parser.parse_args()

    # Activar features de Textual via variable de entorno
    if args.dev:
        os.environ["TEXTUAL"] = "devtools,debug"

    if args.serve:
        # Usar servidor personalizado con soporte DPI alto
        import shlex

        # Construir el comando: python -m termuxcode
        # termuxcode/__main__.py maneja la ejecución de la TUI
        exe = shlex.quote(sys.executable)
        command = f"{exe} -m termuxcode"

        run_web_server(
            command=command,
            font_size=args.font_size,
            host=args.host,
            port=args.port,
            debug=args.dev,
        )
    else:
        # Importar ClaudeChat solo cuando se ejecuta en modo TUI normal
        # para evitar el warning de importación en modo serve
        from .tui.app import ClaudeChat

        app = ClaudeChat(cwd=args.cwd)
        app.run()


if __name__ == "__main__":
    main()
