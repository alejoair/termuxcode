#!/usr/bin/env python3
"""CLI para Claude Code Mobile - Inicia todos los servidores."""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path


# Configuración
PACKAGE_DIR = Path(__file__).parent.parent
WS_SERVER = PACKAGE_DIR / "claude_code_mobile" / "ws_server.py"
HTTP_SERVER = PACKAGE_DIR / "claude_code_mobile" / "serve.py"
HTTP_PORT = 8000
WS_PORT = 8769


def print_banner():
    """Muestra el banner de inicio."""
    print("\n" + "=" * 50)
    print("  Claude Code Mobile")
    print("=" * 50)
    print(f"  HTTP: http://localhost:{HTTP_PORT}")
    print(f"  WebSocket: ws://localhost:{WS_PORT}")
    print("=" * 50 + "\n")


def run_servers(mode="both"):
    """
    Ejecuta los servidores.

    Args:
        mode: 'both', 'ws' (solo WebSocket), 'http' (solo HTTP)
    """
    print_banner()
    processes = []

    try:
        if mode in ("both", "ws"):
            print(f"[*] Iniciando servidor WebSocket (puerto {WS_PORT})...")
            ws_proc = subprocess.Popen(
                [sys.executable, str(WS_SERVER)],
                cwd=str(PACKAGE_DIR)
            )
            processes.append(("WebSocket", ws_proc))

        if mode in ("both", "http"):
            print(f"[*] Iniciando servidor HTTP (puerto {HTTP_PORT})...")
            http_proc = subprocess.Popen(
                [sys.executable, str(HTTP_SERVER)],
                cwd=str(PACKAGE_DIR)
            )
            processes.append(("HTTP", http_proc))

        print(f"\n[✓] Servidor(es) iniciado(s)")
        print(f"\nAbre en tu navegador:")
        print(f"  http://localhost:{HTTP_PORT}/chat")
        print(f"\nPresiona Ctrl+C para detener...\n")

        # Esperar a que los procesos terminen
        for name, proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\n\n[!] Deteniendo servidores...")
        for name, proc in processes:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[✓] Servidores detenidos")


def main():
    """Punto de entrada del comando ccm."""
    parser = argparse.ArgumentParser(
        description="Claude Code Mobile - Cliente web para Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  ccm               Inicia todos los servidores (HTTP + WebSocket)
  ccm --ws          Inicia solo el servidor WebSocket
  ccm --http        Inicia solo el servidor HTTP
  ccm --version     Muestra la versión
        """
    )

    parser.add_argument(
        "--ws", "-w",
        action="store_true",
        help="Iniciar solo el servidor WebSocket"
    )

    parser.add_argument(
        "--http", "-H",
        action="store_true",
        help="Iniciar solo el servidor HTTP"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="claude-code-mobile 0.1.0"
    )

    args = parser.parse_args()

    # Determinar modo
    if args.ws and not args.http:
        mode = "ws"
    elif args.http and not args.ws:
        mode = "http"
    else:
        mode = "both"

    run_servers(mode)


if __name__ == "__main__":
    main()
