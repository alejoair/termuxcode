#!/usr/bin/env python3
"""Servidor WebSocket-to-PTY para terminal funcional (cross-platform)."""

import asyncio
import json
import logging
import os
import sys

import websockets

# Config
_host_override = os.environ.get("TERMUXCODE_HOST")
TERMINAL_HOST = "" if _host_override == "0.0.0.0" else (_host_override or "localhost")
TERMINAL_PORT = 2088

logging.basicConfig(level=logging.INFO, format="%(asctime)s [terminal] %(message)s")
logger = logging.getLogger(__name__)

# Conexión activa (solo una a la vez)
_active_session = None

# --- Platform-conditional imports ---
_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    try:
        from winpty import PTY as WinPTY
    except ImportError:
        WinPTY = None
else:
    import fcntl
    import pty
    import signal
    import struct
    import termios


# ---------------------------------------------------------------------------
# PTY Adapter: Unix (pty/fcntl)
# ---------------------------------------------------------------------------
class UnixPtyProcess:
    """PTY via Unix pty.openpty() + os.fork()."""

    def __init__(self, master_fd: int, child_pid: int) -> None:
        self._master_fd = master_fd
        self._child_pid = child_pid

    def read(self) -> bytes:
        return os.read(self._master_fd, 65536)

    def write(self, data: bytes) -> None:
        os.write(self._master_fd, data)

    def resize(self, cols: int, rows: int) -> None:
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def destroy(self) -> None:
        try:
            os.kill(self._child_pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        try:
            pid, _ = os.waitpid(self._child_pid, os.WNOHANG)
            if pid == 0:
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


def _create_unix_pty(shell, cwd, cols, rows) -> UnixPtyProcess:
    if shell is None:
        shell = os.environ.get("SHELL", "/bin/bash")
    if cwd is None:
        cwd = os.environ.get("TERMUXCODE_CWD", os.getcwd())

    master_fd, slave_fd = pty.openpty()

    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    pid = os.fork()
    if pid == 0:
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        try:
            os.chdir(cwd)
        except OSError:
            pass
        os.environ['TERM'] = 'xterm-256color'
        os.environ['COLUMNS'] = str(cols)
        os.environ['LINES'] = str(rows)
        os.execvp(shell, [shell])
    else:
        os.close(slave_fd)
        return UnixPtyProcess(master_fd, pid)


# ---------------------------------------------------------------------------
# PTY Adapter: Windows (pywinpty / ConPTY)
# ---------------------------------------------------------------------------
class WindowsPtyProcess:
    """PTY via pywinpty (ConPTY on Windows 10 1809+)."""

    def __init__(self, pty_proc, cwd: str | None) -> None:
        self._pty = pty_proc
        self._cwd = cwd
        self._closed = False

    def read(self) -> bytes:
        """Blocking read suitable for run_in_executor.

        pywinpty 3.x read() is non-blocking: returns '' when no data.
        We poll with a small sleep to simulate blocking behavior.
        """
        import time
        while not self._closed:
            data = self._pty.read()
            if data:
                return data.encode("utf-8", errors="replace")
            if not self._pty.isalive():
                self._closed = True
                raise OSError("PTY process exited")
            time.sleep(0.02)  # 50Hz polling
        raise OSError("PTY closed")

    def write(self, data: bytes) -> None:
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        self._pty.write(data)

    def resize(self, cols: int, rows: int) -> None:
        try:
            self._pty.set_size(cols, rows)
        except Exception:
            pass

    def destroy(self) -> None:
        self._closed = True
        try:
            del self._pty
        except Exception:
            pass


def _create_windows_pty(shell, cwd, cols, rows) -> WindowsPtyProcess:
    if WinPTY is None:
        raise RuntimeError(
            "pywinpty no está instalado. "
            "Instálalo con: pip install pywinpty"
        )
    if shell is None:
        shell = os.environ.get("COMSPEC", "cmd.exe")
    if cwd is None:
        cwd = os.environ.get("TERMUXCODE_CWD", os.getcwd())

    pty_proc = WinPTY(cols, rows)
    pty_proc.spawn(shell)

    proc = WindowsPtyProcess(pty_proc, cwd)

    # pywinpty low-level PTY doesn't accept cwd in spawn,
    # so send a cd command after startup
    if cwd:
        proc.write(f'cd /d "{cwd}"\r\n'.encode("utf-8"))

    return proc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_pty(shell=None, cwd=None, cols=80, rows=24):
    """Crea un PTY adaptado a la plataforma actual."""
    if _IS_WINDOWS:
        return _create_windows_pty(shell, cwd, cols, rows)
    return _create_unix_pty(shell, cwd, cols, rows)


# ---------------------------------------------------------------------------
# Terminal Session (bridge WebSocket ↔ PTY)
# ---------------------------------------------------------------------------
class TerminalSession:
    """Sesión de terminal: bridge entre WebSocket y PTY."""

    def __init__(self, websocket, pty_proc):
        self._ws = websocket
        self._pty = pty_proc
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
                data = await loop.run_in_executor(None, self._pty.read)
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
                    self._pty.write(message)
                elif isinstance(message, str):
                    try:
                        parsed = json.loads(message)
                        if isinstance(parsed, dict):
                            msg_type = parsed.get("type")
                            if msg_type == "resize":
                                self._pty.resize(
                                    parsed.get("cols", 80),
                                    parsed.get("rows", 24),
                                )
                            elif msg_type == "ping":
                                pass
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    self._pty.write(message.encode("utf-8"))
        except websockets.ConnectionClosed:
            pass
        except OSError:
            pass
        finally:
            self._running = False

    def destroy(self):
        """Limpia el proceso PTY."""
        self._running = False
        self._pty.destroy()


# ---------------------------------------------------------------------------
# WebSocket Handler
# ---------------------------------------------------------------------------
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
        pty_proc = create_pty(shell=shell, cwd=cwd, cols=cols, rows=rows)
    except (OSError, RuntimeError) as e:
        logger.error(f"Error creando PTY: {e}")
        await websocket.close(1011, f"PTY error: {e}")
        return

    session = TerminalSession(websocket, pty_proc)
    _active_session = session

    logger.info("Sesión terminal creada")

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
        max_size=2**20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor terminal detenido")
