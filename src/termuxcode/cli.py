"""CLI para ejecutar la TUI de termuxcode"""
import argparse
import os
import subprocess
import sys
import warnings
from pathlib import Path

from termuxcode.web_server import run_web_server

# Suprimir warnings de asyncio sobre "unclosed transport" en Windows
# Estos son falsos positivos cuando se cierran subprocess
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed transport")


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
        default=32,
        help="Tamaño de fuente en px para modo web (default: 32). Aumentar para pantallas de alto DPI",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host para modo web (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Puerto para modo web (default: 8001)",
    )
    args = parser.parse_args()

    # Activar features de Textual via variable de entorno
    if args.dev:
        os.environ["TEXTUAL"] = "devtools,debug"

    if args.serve:
        # Usar servidor personalizado con soporte DPI alto
        # Construir el comando para ejecutar la TUI
        # En Windows, usamos sys.executable directamente
        if os.name == "nt":
            command = f'"{sys.executable}" -m termuxcode'
        else:
            import shlex
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
        from termuxcode.tui.app import ClaudeChat

        app = ClaudeChat(cwd=args.cwd)
        app.run()


if __name__ == "__main__":
    main()
