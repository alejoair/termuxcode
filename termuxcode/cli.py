#!/usr/bin/env python3
"""CLI para termuxcode - Inicia todos los servidores."""

import argparse
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


# Configuración
PACKAGE_DIR = Path(__file__).parent.parent
WS_SERVER = PACKAGE_DIR / "termuxcode" / "ws_server.py"
HTTP_SERVER = PACKAGE_DIR / "termuxcode" / "serve.py"
TERMINAL_SERVER = PACKAGE_DIR / "termuxcode" / "terminal_server.py"
HTTP_PORT = 1988
WS_PORT = 2025
TERMINAL_PORT = 2088


def port_in_use(port: int) -> bool:
    """Verifica si un puerto ya está en uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def _find_pids_by_port(port: int) -> list[int]:
    """Encuentra PIDs usando el puerto. Intenta múltiples métodos para compatibilidad con Termux/Android."""
    # 1. /proc/net/tcp (Linux estándar con permisos)
    hex_port = format(port, '04X')
    inodes: set[str] = set()

    for tcp_file in ('/proc/net/tcp', '/proc/net/tcp6'):
        try:
            with open(tcp_file) as f:
                next(f)
                for line in f:
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    local_port = parts[1].split(':')[1] if ':' in parts[1] else ''
                    if local_port.upper() == hex_port:
                        inodes.add(parts[9])
        except OSError:
            pass

    if inodes:
        pids: list[int] = []
        try:
            for entry in os.listdir('/proc'):
                if not entry.isdigit():
                    continue
                fd_dir = f'/proc/{entry}/fd'
                try:
                    for fd in os.listdir(fd_dir):
                        try:
                            link = os.readlink(f'{fd_dir}/{fd}')
                            if link.startswith('socket:[') and link[8:-1] in inodes:
                                pids.append(int(entry))
                                break
                        except OSError:
                            pass
                except OSError:
                    pass
        except OSError:
            pass
        if pids:
            return pids

    # 2. lsof (disponible en Termux)
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )
        if result.stdout.strip():
            return [int(p) for p in result.stdout.strip().split() if p.isdigit()]
    except FileNotFoundError:
        pass

    # 3. fuser (disponible en Termux)
    try:
        result = subprocess.run(
            ["fuser", f"{port}/tcp"], capture_output=True, text=True
        )
        if result.stdout.strip():
            return [int(p) for p in result.stdout.strip().split() if p.isdigit()]
    except FileNotFoundError:
        pass

    return []


def _kill_termuxcode_processes() -> list[int]:
    """Mata procesos de termuxcode por nombre (fallback para Android/Termux).

    Mata ws_server.py y serve.py primero, luego el proceso padre termuxcode stale.
    Nunca mata el proceso actual ni sus padres.
    """
    my_pid = os.getpid()
    my_ppid = os.getppid()
    killed: list[int] = []

    # Primero matar los servidores hijos (son los que realmente ocupan los puertos)
    for script in ['ws_server.py', 'serve.py', 'terminal_server.py']:
        try:
            result = subprocess.run(['ps', '-ef'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) < 8:
                    continue
                pid = int(parts[1])
                if pid in (my_pid, my_ppid):
                    continue
                cmd = ' '.join(parts[7:])
                if script in cmd and 'grep' not in cmd:
                    subprocess.run(['kill', '-9', str(pid)], capture_output=True)
                    print(f"  [kill] PID {pid} ({script})")
                    killed.append(pid)
                    break
        except Exception:
            pass

    # Luego matar proceso termuxcode padre stale (si existe uno anterior)
    try:
        result = subprocess.run(['ps', '-ef'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 8:
                continue
            pid = int(parts[1])
            if pid in (my_pid, my_ppid):
                continue
            cmd = ' '.join(parts[7:])
            if 'termuxcode' in cmd and 'grep' not in cmd \
                    and 'python3 -c' not in cmd \
                    and 'ws_server.py' not in cmd \
                    and 'serve.py' not in cmd:
                subprocess.run(['kill', '-9', str(pid)], capture_output=True)
                print(f"  [kill] PID {pid} (termuxcode)")
                killed.append(pid)
                break
    except Exception:
        pass

    return killed


def kill_port(port: int) -> bool:
    """Mata los procesos que están usando el puerto dado."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        pids = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                try:
                    pids.add(int(parts[4]))
                except ValueError:
                    pass
        for pid in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            print(f"  [kill] PID {pid} (puerto {port})")
        return bool(pids)
    else:
        # Intentar por puerto
        pids = _find_pids_by_port(port)
        if pids:
            for pid in pids:
                subprocess.run(["kill", "-9", str(pid)], capture_output=True)
                print(f"  [kill] PID {pid} (puerto {port})")
            return True

        # Fallback: matar procesos termuxcode por nombre (Android/Termux)
        killed = _kill_termuxcode_processes()
        return bool(killed)


def check_ports(mode: str, force: bool = False) -> None:
    """Verifica que los puertos necesarios estén disponibles. Sale si alguno está ocupado."""
    ports = []
    if mode in ("both", "ws"):
        ports.append(("WebSocket", WS_PORT))
    if mode in ("both", "http"):
        ports.append(("HTTP", HTTP_PORT))
    if mode in ("both", "terminal"):
        ports.append(("Terminal", TERMINAL_PORT))

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


def print_banner() -> None:
    """Muestra el banner de inicio."""
    print("\n" + "=" * 50)
    print("  termuxcode")
    print("=" * 50)
    print(f"  HTTP: http://localhost:{HTTP_PORT}")
    print(f"  WebSocket: ws://localhost:{WS_PORT}")
    print(f"  Terminal: ws://localhost:{TERMINAL_PORT}")
    print("=" * 50 + "\n")


def _acquire_wake_lock() -> bool:
    """Adquiere un wake lock en Android/Termux para mantener CPU y red activos."""
    if shutil.which('termux-wake-lock'):
        try:
            subprocess.Popen(
                ['termux-wake-lock'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("[wake-lock] CPU y red se mantendran activos con pantalla apagada")
            return True
        except OSError:
            pass
    return False


def _release_wake_lock() -> None:
    """Libera el wake lock al detener los servidores."""
    if shutil.which('termux-wake-unlock'):
        try:
            subprocess.Popen(
                ['termux-wake-unlock'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass


def run_servers(mode: str = "both", force: bool = False) -> None:
    """
    Ejecuta los servidores.

    Args:
        mode: 'both', 'ws' (solo WebSocket), 'http' (solo HTTP)
        force: si True, mata procesos en los puertos necesarios
    """
    check_ports(mode, force=force)
    print_banner()

    wake_lock_held = _acquire_wake_lock()

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

        if mode in ("both", "terminal"):
            print(f"[*] Iniciando servidor de terminal (puerto {TERMINAL_PORT})...")
            terminal_proc = subprocess.Popen(
                [sys.executable, str(TERMINAL_SERVER)],
                cwd=original_cwd,
                env=env
            )
            processes.append(("Terminal", terminal_proc))

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
    finally:
        if wake_lock_held:
            _release_wake_lock()


def main() -> None:
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
