#!/usr/bin/env python3
"""Transporte stdio para comunicación con servidores LSP."""

import asyncio
from typing import Any, Callable

from termuxcode.connection.lsp import protocol
from termuxcode.ws_config import logger


class StdioTransport:
    """Maneja comunicación JSON-RPC sobre stdin/stdout con un proceso LSP."""

    def __init__(self, command: list[str], cwd: str):
        self._command = command
        self._cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 0
        self._write_lock = asyncio.Lock()
        self._on_notification: Callable | None = None

    @property
    def pid(self) -> int | None:
        """PID del proceso LSP, o None si no está corriendo."""
        return self._process.pid if self._process else None

    @property
    def cwd(self) -> str:
        """Directorio de trabajo del servidor LSP."""
        return self._cwd

    @property
    def command(self) -> list[str]:
        """Comando usado para iniciar el servidor LSP."""
        return self._command

    @property
    def is_running(self) -> bool:
        """True si el proceso está corriendo."""
        return self._process is not None and self._process.returncode is None

    def set_notification_handler(self, handler: Callable) -> None:
        """Establece el callback para notificaciones del servidor."""
        self._on_notification = handler

    async def start(self) -> None:
        """Inicia el proceso LSP."""
        self._process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._read_stderr())
        logger.info(f"StdioTransport: started {self._command[0]} (pid={self._process.pid})")

    async def shutdown(self) -> None:
        """Apaga el proceso LSP limpiamente."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
                await self._process.wait()
            except Exception:
                pass

        # Resolver Futures pendientes con None
        for fut in self._pending.values():
            if not fut.done():
                fut.set_result(None)
        self._pending.clear()
        logger.info(f"StdioTransport: {self._command[0]} shut down")

    async def send_request(self, method: str, params: Any = None, timeout: float = 10.0) -> Any:
        """Envía un request JSON-RPC y espera la respuesta."""
        if not self.is_running:
            return None

        self._next_id += 1
        msg_id = self._next_id
        msg = protocol.build_request(msg_id, method, params)

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        async with self._write_lock:
            await self._write(msg)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            logger.warning(
                f"StdioTransport: request {method} (id={msg_id}) timed out"
            )
            return None

    async def send_notification(self, method: str, params: Any = None) -> None:
        """Envía una notificación JSON-RPC (sin esperar respuesta)."""
        if not self.is_running:
            return
        msg = protocol.build_notification(method, params)
        async with self._write_lock:
            await self._write(msg)

    async def _write(self, msg: dict) -> None:
        """Escribe un mensaje al stdin del proceso."""
        data = protocol.encode_message(msg)
        self._process.stdin.write(data)
        await self._process.stdin.drain()

    async def _read_loop(self) -> None:
        """Lee mensajes JSON-RPC del stdout del servidor."""
        try:
            while self.is_running:
                # Leer headers
                headers = {}
                while True:
                    line = await self._process.stdout.readline()
                    if not line or line == b"\r\n":
                        break
                    if line.endswith(b"\r\n"):
                        line = line[:-2]
                    if b":" in line:
                        key, _, val = line.partition(b":")
                        headers[key.strip().decode()] = val.strip().decode()

                length = int(headers.get("Content-Length", 0))
                if length <= 0:
                    continue

                body = await self._process.stdout.read(length)
                if not body:
                    continue

                msg = protocol.parse_message(body)
                if msg is None:
                    logger.warning("StdioTransport: invalid JSON from server")
                    continue

                self._handle_message(msg)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"StdioTransport: _read_loop crashed: {e}")

    async def _read_stderr(self) -> None:
        """Lee stderr del servidor para evitar bloqueos."""
        try:
            while self.is_running:
                line = await self._process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug(f"StdioTransport[{self._command[0]}] stderr: {text}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"StdioTransport: _read_stderr crashed: {e}")

    def _handle_message(self, msg: dict) -> None:
        """Despacha mensajes recibidos del servidor."""
        if protocol.is_response(msg):
            msg_id = msg["id"]
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                result = protocol.get_response_result(msg)
                future.set_result(result)
        elif protocol.is_notification(msg):
            method = msg["method"]
            params = msg.get("params", {})
            if self._on_notification:
                self._on_notification(method, params)
