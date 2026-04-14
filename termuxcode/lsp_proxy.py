#!/usr/bin/env python3
"""LSP WebSocket-to-Stdio Proxy.

Bridges CodeMirror in the browser to language servers (ty, ruff, etc.)
over stdio via a WebSocket connection.

Usage:
    python -m termuxcode.lsp_proxy
    python -m termuxcode.lsp_proxy --port 2087 --log-level DEBUG

WebSocket protocol:
    ws://localhost:2087/?language=python&cwd=/path/to/project

The browser sends/receives plain JSON-RPC (no Content-Length headers).
The proxy translates to/from LSP stdio protocol (with Content-Length).
"""

import argparse
import asyncio
import logging
import shutil
import sys
from urllib.parse import parse_qs, urlparse

import websockets

logger = logging.getLogger("lsp_proxy")

LSP_SERVERS: dict[str, list[list[str]]] = {
    "python": [["ty", "server"], ["ruff", "server"]],
    "typescript": [["typescript-language-server", "--stdio"]],
    "javascript": [["typescript-language-server", "--stdio"]],
    "tsx": [["typescript-language-server", "--stdio"]],
    "jsx": [["typescript-language-server", "--stdio"]],
    "go": [["gopls"]],
}


def find_server_cmd(language_id: str) -> list[str] | None:
    """Find the first available LSP server command for a language."""
    for cmd in LSP_SERVERS.get(language_id, []):
        if shutil.which(cmd[0]):
            return cmd
    return None


class LspSession:
    """Bridges a single WebSocket connection to an LSP stdio process."""

    def __init__(self, websocket, process: asyncio.subprocess.Process):
        self.ws = websocket
        self.proc = process
        self._done = False

    async def ws_to_stdio(self):
        """Forward JSON-RPC messages from browser (plain JSON) to LSP stdin (Content-Length)."""
        try:
            async for raw in self.ws:
                body = raw.encode("utf-8") if isinstance(raw, str) else raw
                header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
                self.proc.stdin.write(header + body)
                await self.proc.stdin.drain()
        except (websockets.exceptions.ConnectionClosed, ConnectionError, OSError):
            pass
        finally:
            self._done = True

    async def stdio_to_ws(self):
        """Forward JSON-RPC messages from LSP stdout (Content-Length) to browser (plain JSON)."""
        reader = self.proc.stdout
        try:
            while not self._done:
                # Read until we find Content-Length header
                line = await reader.readline()
                if not line:
                    break
                if not line.lower().startswith(b"content-length:"):
                    continue

                length = int(line.split(b":", 1)[1].strip())

                # Read blank line separator
                await reader.readline()

                # Read JSON body
                body = await reader.readexactly(length)
                await self.ws.send(body.decode("utf-8"))
        except (
            asyncio.IncompleteReadError,
            websockets.exceptions.ConnectionClosed,
            ConnectionError,
            OSError,
        ):
            pass
        finally:
            self._done = True

    async def drain_stderr(self):
        """Consume LSP stderr to prevent pipe blocking."""
        try:
            while not self._done:
                line = await self.proc.stderr.readline()
                if not line:
                    break
                logger.debug(
                    "LSP stderr: %s", line.decode("utf-8", errors="replace").strip()
                )
        except Exception:
            pass

    async def cleanup(self):
        self._done = True
        if self.proc.returncode is None:
            self.proc.kill()
            await self.proc.wait()


async def handle(websocket):
    """Handle a new LSP WebSocket connection."""
    path = websocket.request.path
    params = parse_qs(urlparse(path).query)

    language = params.get("language", ["python"])[0]
    cwd = params.get("cwd", ["."])[0]

    cmd = find_server_cmd(language)
    if not cmd:
        logger.error("No LSP server for language=%s", language)
        await websocket.close(4000, f"No LSP server for {language}")
        return

    logger.info("New session: language=%s cwd=%s cmd=%s", language, cwd, cmd)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    session = LspSession(websocket, proc)
    try:
        await asyncio.gather(
            session.ws_to_stdio(),
            session.stdio_to_ws(),
            session.drain_stderr(),
        )
    except Exception as e:
        logger.error("Session error: %s", e)
    finally:
        await session.cleanup()
        logger.info("Session closed: language=%s", language)


async def run(host: str, port: int):
    async with websockets.serve(handle, host, port):
        logger.info("LSP proxy listening on ws://%s:%s", host, port)
        await asyncio.Future()  # run forever


def main():
    parser = argparse.ArgumentParser(description="LSP WebSocket-to-Stdio Proxy")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2087)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("Available LSP servers:")
    for lang, cmds in LSP_SERVERS.items():
        for cmd in cmds:
            status = "OK" if shutil.which(cmd[0]) else "MISSING"
            logger.info("  %s: %s [%s]", lang, cmd[0], status)

    try:
        asyncio.run(run(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
