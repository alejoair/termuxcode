#!/usr/bin/env python3
"""Cliente LSP genérico sobre stdio usando asyncio."""

import asyncio
import json
import os
import urllib.parse
from pathlib import Path, PurePosixPath, PureWindowsPath

from termuxcode.ws_config import logger

# Lenguaje por defecto por servidor, mapeado por extensión
_LANGUAGE_IDS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascriptreact",
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".lua": "lua",
}


def _is_windows() -> bool:
    return os.name == "nt"


def file_path_to_uri(path: str) -> str:
    """Convierte una ruta de archivo a URI file://."""
    p = Path(path)
    if _is_windows():
        # Windows: file:///C:/path/to/file
        return "file:///" + str(PureWindowsPath(path)).replace("\\", "/")
    return "file://" + str(PurePosixPath(path))


def uri_to_file_path(uri: str) -> str:
    """Convierte una URI file:// a ruta de archivo."""
    parsed = urllib.parse.urlparse(uri)
    path = urllib.parse.unquote(parsed.path)
    if _is_windows():
        # file:///C:/path → C:/path
        if path.startswith("/"):
            path = path[1:]
    return path


def extension_to_language_id(file_path: str) -> str:
    """Retorna el Language ID LSP para una extensión dada."""
    _, ext = os.path.splitext(file_path)
    return _LANGUAGE_IDS.get(ext, "")


class LSPClient:
    """Cliente LSP genérico que se comunica con un language server via stdio.

    Maneja el protocolo JSON-RPC sobre stdin/stdout:
    - Envía requests/notificaciones al server
    - Recibe responses y notificaciones (publishDiagnostics)
    - Cachea diagnósticos por archivo
    """

    def __init__(self, command: list[str], cwd: str):
        self._command = command
        self._cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._diagnostics: dict[str, list[dict]] = {}  # URI → diagnostics
        self._diag_events: dict[str, asyncio.Event] = {}  # URI → Event
        self._diag_gen: dict[str, int] = {}  # URI → generation counter
        self._next_id = 0
        self._initialized = False
        self._version: dict[str, int] = {}  # URI → version counter
        self._write_lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Inicia el servidor LSP y completa el handshake initialize."""
        self._process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._read_stderr())
        logger.info(f"LSPClient: started {self._command[0]} (pid={self._process.pid})")

        # Handshake LSP: initialize → initialized
        root_uri = file_path_to_uri(self._cwd)
        init_params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "rootPath": self._cwd,
            "capabilities": {
                "textDocument": {
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "references": {},
                    "publishDiagnostics": {"relatedInformation": True},
                    "synchronization": {
                        "dynamicRegistration": False,
                        "willSave": False,
                        "willSaveWaitUntil": False,
                        "didSave": False,
                    },
                },
            },
        }
        result = await self._send_request("initialize", init_params, timeout=60.0)
        if result is None:
            # Timeout o error — no proceder con initialized
            logger.warning(
                f"LSPClient: {self._command[0]} initialize failed/timeout, "
                f"aborting handshake"
            )
            # Limpiar proceso
            if self._reader_task:
                self._reader_task.cancel()
            if self._stderr_task:
                self._stderr_task.cancel()
            if self._process and self._process.returncode is None:
                self._process.kill()
            self._process = None
            self._reader_task = None
            self._stderr_task = None
            raise RuntimeError(
                f"LSP server {self._command[0]} did not respond to initialize"
            )
        await self._send_notification("initialized", {})
        self._initialized = True
        logger.info(f"LSPClient: {self._command[0]} initialized (root={self._cwd})")

    async def shutdown(self) -> None:
        """Apaga el servidor LSP limpiamente."""
        self._initialized = False
        try:
            await self._send_request("shutdown", None, timeout=3.0)
        except Exception:
            pass
        try:
            await self._send_notification("exit", {})
        except Exception:
            pass

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

        # Resolver Futures pendientes con None para no dejar colgados
        for fut in self._pending.values():
            if not fut.done():
                fut.set_result(None)
        self._pending.clear()
        logger.info(f"LSPClient: {self._command[0]} shut down")

    # ── Lectura (background) ──────────────────────────────────────────

    async def _read_loop(self) -> None:
        """Lee mensajes JSON-RPC del stdout del servidor indefinidamente."""
        try:
            while self._process and self._process.returncode is None:
                # Leer header Content-Length
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

                try:
                    msg = json.loads(body)
                except json.JSONDecodeError:
                    logger.warning(f"LSPClient: invalid JSON from server")
                    continue

                if "id" in msg and "method" not in msg:
                    # Response a un request nuestro
                    msg_id = msg["id"]
                    future = self._pending.pop(msg_id, None)
                    if future and not future.done():
                        if "error" in msg:
                            future.set_result(None)
                            logger.debug(f"LSPClient: request {msg_id} error: {msg['error']}")
                        else:
                            future.set_result(msg.get("result"))
                    elif future is None:
                        # Respuesta tardía - el request ya fue removido por timeout
                        logger.debug(
                            f"LSPClient: received response for unknown request {msg_id} "
                            f"(possibly late response after timeout)"
                        )
                elif "method" in msg:
                    # Notificación del servidor
                    method = msg["method"]
                    params = msg.get("params", {})
                    self._handle_notification(method, params)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"LSPClient: _read_loop crashed: {e}")

    async def _read_stderr(self) -> None:
        """Lee stderr del servidor para evitar que el buffer se llene y bloquee el proceso."""
        try:
            while self._process and self._process.returncode is None:
                line = await self._process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug(f"LSPClient[{self._command[0]}] stderr: {text}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"LSPClient: _read_stderr crashed: {e}")

    def _handle_notification(self, method: str, params: dict) -> None:
        """Despacha notificaciones del servidor."""
        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri", "")
            diags = params.get("diagnostics", [])
            self._diagnostics[uri] = diags
            self._diag_gen[uri] = self._diag_gen.get(uri, 0) + 1
            event = self._diag_events.get(uri)
            if event:
                event.set()

    # ── Envío de mensajes ─────────────────────────────────────────────

    async def _send_request(self, method: str, params, timeout: float = 10.0):
        """Envía un request JSON-RPC y espera la response."""
        if not self._process or self._process.returncode is not None:
            return None

        self._next_id += 1
        msg_id = self._next_id
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            msg["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        import time
        start_time = time.monotonic()
        logger.debug(f"LSPClient: sending request {method} (id={msg_id}, timeout={timeout}s)")

        async with self._write_lock:
            await self._write(msg)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            elapsed = time.monotonic() - start_time
            logger.debug(f"LSPClient: request {method} (id={msg_id}) completed in {elapsed:.2f}s")
            return result
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start_time
            self._pending.pop(msg_id, None)
            logger.warning(
                f"LSPClient: request {method} (id={msg_id}) timed out "
                f"after {elapsed:.2f}s (timeout was {timeout}s)"
            )
            return None

    async def _send_notification(self, method: str, params) -> None:
        """Envía una notificación JSON-RPC (sin ID, sin response)."""
        if not self._process or self._process.returncode is not None:
            return
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        async with self._write_lock:
            await self._write(msg)

    async def _write(self, msg: dict) -> None:
        """Escribe un mensaje JSON-RPC al stdin del servidor."""
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        self._process.stdin.write(header + body)
        await self._process.stdin.drain()

    # ── Text Document operations ──────────────────────────────────────

    async def open_file(self, file_path: str, content: str) -> None:
        """Envía textDocument/didOpen."""
        uri = file_path_to_uri(file_path)
        language_id = extension_to_language_id(file_path)
        self._version[uri] = 1
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })

    async def update_file(self, file_path: str, content: str) -> None:
        """Envía textDocument/didChange (full sync)."""
        uri = file_path_to_uri(file_path)
        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}],
        })

    async def close_file(self, file_path: str) -> None:
        """Envía textDocument/didClose."""
        uri = file_path_to_uri(file_path)
        await self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })

    # ── Queries ───────────────────────────────────────────────────────

    async def get_symbols(self, file_path: str) -> list[dict]:
        """textDocument/documentSymbol → lista de DocumentSymbol."""
        uri = file_path_to_uri(file_path)
        result = await self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        if isinstance(result, list) and result:
            logger.debug(f"LSP RAW documentSymbol: {json.dumps(result[:3], indent=2)}")
        else:
            logger.debug(f"LSP RAW documentSymbol: result={result}")
        if isinstance(result, list):
            return result
        return []

    async def get_hover(self, file_path: str, line: int, col: int) -> str | None:
        """textDocument/hover → contenido como texto plano."""
        uri = file_path_to_uri(file_path)
        result = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
        })
        logger.debug(f"LSP RAW hover (L{line}:C{col}): {json.dumps(result, indent=2) if result else result}")
        if not result or "contents" not in result:
            return None
        contents = result["contents"]
        # LSP hover contents puede ser string, MarkedString, o MarkupContent
        if isinstance(contents, str):
            return contents
        if isinstance(contents, dict):
            return contents.get("value", "")
        if isinstance(contents, list):
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            return "\n".join(parts) if parts else None
        return None

    async def get_references(self, file_path: str, line: int, col: int) -> list[dict]:
        """textDocument/references → lista de Location."""
        uri = file_path_to_uri(file_path)
        result = await self._send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
            "context": {"includeDeclaration": False},
        })
        if isinstance(result, list) and result:
            logger.debug(f"LSP RAW references: {json.dumps(result[:3], indent=2)}")
        else:
            logger.debug(f"LSP RAW references: result={result}")
        if isinstance(result, list):
            return result
        return []

    # ── Diagnostics ───────────────────────────────────────────────────

    async def open_and_wait(self, file_path: str, content: str, timeout: float = 10.0) -> list[dict]:
        """Envía didOpen y espera publishDiagnostics atómicamente.

        1. Limpia el event ANTES de enviar
        2. Envía didOpen
        3. Espera el event — el próximo publishDiagnostics es para este archivo
        """
        uri = file_path_to_uri(file_path)

        # 1. Limpiar event ANTES de enviar
        event = self._diag_events.get(uri)
        if event:
            event.clear()
        else:
            event = asyncio.Event()
            self._diag_events[uri] = event

        # 2. Enviar didOpen
        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": extension_to_language_id(file_path),
                "version": version,
                "text": content,
            },
        })

        # 3. Esperar respuesta del servidor
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri, [])

    async def update_and_wait(self, file_path: str, content: str, timeout: float = 10.0) -> list[dict]:
        """Envía didChange y espera publishDiagnostics atómicamente.

        1. Limpia el event ANTES de enviar
        2. Envía didChange
        3. Espera el event — el próximo publishDiagnostics es para nuestra versión
        """
        uri = file_path_to_uri(file_path)

        # 1. Limpiar event ANTES de enviar
        event = self._diag_events.get(uri)
        if event:
            event.clear()
        else:
            event = asyncio.Event()
            self._diag_events[uri] = event

        # 2. Enviar didChange
        version = self._version.get(uri, 0) + 1
        self._version[uri] = version
        await self._send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}],
        })

        # 3. Esperar respuesta del servidor
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        return self._diagnostics.get(uri, [])

    def get_cached_diagnostics(self, file_path: str) -> list[dict]:
        """Retorna diagnósticos cacheados (no bloquea)."""
        uri = file_path_to_uri(file_path)
        return self._diagnostics.get(uri, [])
