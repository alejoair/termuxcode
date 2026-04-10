#!/usr/bin/env python3
"""CLI para termuxcode - Inicia todos los servidores."""

import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path


# Configuración
PACKAGE_DIR = Path(__file__).parent.parent
WS_SERVER = PACKAGE_DIR / "termuxcode" / "ws_server.py"
HTTP_SERVER = PACKAGE_DIR / "termuxcode" / "serve.py"
HTTP_PORT = 1988
WS_PORT = 2025


def port_in_use(port):
    """Verifica si un puerto ya está en uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def kill_port(port):
    """Mata los procesos que están usando el puerto dado."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        pids = set()
        for line in result.stdout.splitlines():
            # Match lines like: TCP    127.0.0.1:2025    ...    LISTENING    12345
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                try:
                    pids.add(int(parts[4]))
                except ValueError:
                    pass
        for pid in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True)
            print(f"  [kill] PID {pid} (puerto {port})")
        return bool(pids)
    else:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            subprocess.run(["kill", "-9", pid], capture_output=True)
            print(f"  [kill] PID {pid} (puerto {port})")
        return bool(pids)


def check_ports(mode, force=False):
    """Verifica que los puertos necesarios estén disponibles. Sale si alguno está ocupado."""
    ports = []
    if mode in ("both", "ws"):
        ports.append(("WebSocket", WS_PORT))
    if mode in ("both", "http"):
        ports.append(("HTTP", HTTP_PORT))

    occupied = [(name, port) for name, port in ports if port_in_use(port)]
    if not occupied:
        return

    if force:
        print("\n[force] Puertos en uso, matando procesos...\n")
        for name, port in occupied:
            killed = kill_port(port)
            if killed:
                print(f"  [force] {name}: puerto {port} liberado")
            else:
                print(f"  [force] {name}: no se pudo liberar puerto {port}")
        print()
        # Verificar de nuevo
        still_occupied = [(n, p) for n, p in occupied if port_in_use(p)]
        if still_occupied:
            print("=" * 50)
            print("  ERROR: No se pudieron liberar:")
            for name, port in still_occupied:
                print(f"  ✗ {name}: puerto {port}")
            print("=" * 50 + "\n")
            sys.exit(1)
    else:
        print("\n" + "=" * 50)
        print("  ERROR: Puertos en uso")
        print("=" * 50)
        for name, port in occupied:
            print(f"  ✗ {name}: puerto {port} ya está en uso")
        print()
        print("  Usa --force para matar los procesos automáticamente.")
        print("=" * 50 + "\n")
        sys.exit(1)


def print_banner():
    """Muestra el banner de inicio."""
    print("\n" + "=" * 50)
    print("  termuxcode")
    print("=" * 50)
    print(f"  HTTP: http://localhost:{HTTP_PORT}")
    print(f"  WebSocket: ws://localhost:{WS_PORT}")
    print("=" * 50 + "\n")


def run_servers(mode="both", force=False):
    """
    Ejecuta los servidores.

    Args:
        mode: 'both', 'ws' (solo WebSocket), 'http' (solo HTTP)
        force: si True, mata procesos en los puertos necesarios
    """
    check_ports(mode, force=force)
    print_banner()
    processes = []

    # Capturar el directorio actual antes de lanzar subprocesos
    original_cwd = os.getcwd()

    # Pasar el CWD original a los subprocesos via variable de entorno
    env = os.environ.copy()
    env['TERMUXCODE_CWD'] = original_cwd

    try:
        if mode in ("both", "ws"):
            print(f"[*] Iniciando servidor WebSocket (puerto {WS_PORT})...")
            ws_proc = subprocess.Popen(
                [sys.executable, str(WS_SERVER)],
                cwd=original_cwd,
                env=env
            )
            processes.append(("WebSocket", ws_proc))

        if mode in ("both", "http"):
            print(f"[*] Iniciando servidor HTTP (puerto {HTTP_PORT})...")
            http_proc = subprocess.Popen(
                [sys.executable, str(HTTP_SERVER)],
                cwd=original_cwd,
                env=env
            )
            processes.append(("HTTP", http_proc))

        print("\n[OK] Servidor(es) iniciado(s)")
        print("\nAbre en tu navegador:")
        print(f"  http://localhost:{HTTP_PORT}")
        print("\nPresiona Ctrl+C para detener...\n")

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
        print("[OK] Servidores detenidos")


def main():
    """Punto de entrada del comando ccm."""
    parser = argparse.ArgumentParser(
        description="termuxcode - Cliente web para Claude",
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
        version="termuxcode 1.1.3"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Matar procesos que estén usando los puertos necesarios"
    )

    args = parser.parse_args()

    # Determinar modo
    if args.ws and not args.http:
        mode = "ws"
    elif args.http and not args.ws:
        mode = "http"
    else:
        mode = "both"

    run_servers(mode, force=args.force)


if __name__ == "__main__":
    main()
