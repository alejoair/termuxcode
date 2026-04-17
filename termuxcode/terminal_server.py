#!/usr/bin/env python3
"""Servidor WebSocket-to-PTY para terminal funcional."""

import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import termios

import websockets

# Config
TERMINAL_HOST = "localhost"
TERMINAL_PORT = 2088

logging.basicConfig(level=logging.INFO, format="%(asctime)s [terminal] %(message)s")
logger = logging.getLogger(__name__)

# Conexión activa (solo una a la vez)
_active_session = None


def create_pty(shell=None, cwd=None, cols=80, rows=24):
    """Crea un PTY y forkea un proceso shell.

    Returns (master_fd, child_pid).
    """
    if shell is None:
        shell = os.environ.get("SHELL", "/bin/bash")
    if cwd is None:
        cwd = os.environ.get("TERMUXCODE_CWD", os.getcwd())

    master_fd, slave_fd = pty.openpty()

    # Tamaño inicial del terminal
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    pid = os.fork()
    if pid == 0:
        # Proceso hijo
        os.close(master_fd)
        os.setsid()

        # Hacer el slave el controlling terminal
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

        os.dup2(slave_fd, 0)  # stdin
        os.dup2(slave_fd, 1)  # stdout
        os.dup2(slave_fd, 2)  # stderr
        if slave_fd > 2:
            os.close(slave_fd)

        try:
            os.chdir(cwd)
        except OSError:
            pass

        # Set terminal environment for TUI apps (nano, vim, htop, etc.)
        os.environ['TERM'] = 'xterm-256color'
        os.environ['COLUMNS'] = str(cols)
        os.environ['LINES'] = str(rows)

        os.execvp(shell, [shell])
        # No llega aquí
    else:
        # Proceso padre
        os.close(slave_fd)
        return master_fd, pid


class TerminalSession:
    """Sesión de terminal: bridge entre WebSocket y PTY."""

    def __init__(self, websocket, master_fd, child_pid):
        self._ws = websocket
        self._master_fd = master_fd
        self._child_pid = child_pid
        self._running = True

    async def handle(self):
        """Loop principal: PTY → WS y WS → PTY concurrentemente."""
        loop = asyncio.get_event_loop()

        read_task = asyncio.create_task(self._read_pty(loop))
        write_task = asyncio.create_task(self._write_pty())

        _, pending = await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancelar la tarea que sigue corriendo
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _read_pty(self, loop):
        """Lee del PTY y envía al WebSocket."""
        try:
            while self._running:
                data = await loop.run_in_executor(
                    None, os.read, self._master_fd, 65536
                )
                if not data:
                    break
                try:
                    await self._ws.send(data)
                except websockets.ConnectionClosed:
                    break
        except OSError:
            pass
        finally:
            self._running = False

    async def _write_pty(self):
        """Lee del WebSocket y escribe al PTY."""
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    # Input binario directo
                    os.write(self._master_fd, message)
                elif isinstance(message, str):
                    # Podría ser input de texto o un comando JSON
                    try:
                        parsed = json.loads(message)
                        if isinstance(parsed, dict):
                            msg_type = parsed.get("type")
                            if msg_type == "resize":
                                self.resize(
                                    parsed.get("cols", 80),
                                    parsed.get("rows", 24),
                                )
                            elif msg_type == "ping":
                                # Keepalive, no hacer nada
                                pass
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    # Texto plano → escribir al PTY
                    os.write(self._master_fd, message.encode("utf-8"))
        except websockets.ConnectionClosed:
            pass
        except OSError:
            pass
        finally:
            self._running = False

    def resize(self, cols, rows):
        """Redimensiona el PTY."""
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def destroy(self):
        """Limpia el proceso hijo y el file descriptor."""
        self._running = False
        try:
            os.kill(self._child_pid, signal.SIGHUP)
        except ProcessLookupError:
            pass

        # Esperar brevemente al hijo
        try:
            pid, _ = os.waitpid(self._child_pid, os.WNOHANG)
            if pid == 0:
                # Hijo aún vivo, esperar un poco más
                import time
                time.sleep(0.1)
                os.kill(self._child_pid, signal.SIGKILL)
                os.waitpid(self._child_pid, 0)
        except ChildProcessError:
            pass

        try:
            os.close(self._master_fd)
        except OSError:
            pass


async def handle_terminal_connection(websocket):
    """Handler principal para conexiones WebSocket de terminal."""
    global _active_session

    # Parsear query params
    path = websocket.request.path if hasattr(websocket, 'request') else "/"
    import urllib.parse
    params = {}
    if '?' in path:
        params = dict(urllib.parse.parse_qsl(path.split('?', 1)[1]))

    shell = params.get("shell")
    cwd = params.get("cwd")
    cols = int(params.get("cols", 80))
    rows = int(params.get("rows", 24))

    # Si ya hay una sesión activa, desconectarla
    if _active_session is not None:
        logger.info("Desconectando sesión anterior")
        _active_session.destroy()
        _active_session = None

    # Crear PTY
    try:
        master_fd, child_pid = create_pty(shell=shell, cwd=cwd, cols=cols, rows=rows)
    except OSError as e:
        logger.error(f"Error creando PTY: {e}")
        await websocket.close(1011, f"PTY error: {e}")
        return

    session = TerminalSession(websocket, master_fd, child_pid)
    _active_session = session

    logger.info(f"Sesión terminal creada (PID={child_pid})")

    try:
        await session.handle()
    finally:
        session.destroy()
        if _active_session is session:
            _active_session = None
        logger.info("Sesión terminal cerrada")


async def main():
    """Punto de entrada del servidor."""
    logger.info(f"Iniciando servidor terminal en ws://{TERMINAL_HOST}:{TERMINAL_PORT}")

    async with websockets.serve(
        handle_terminal_connection,
        TERMINAL_HOST,
        TERMINAL_PORT,
        max_size=2**20,  # 1MB max message
    ):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor terminal detenido")
