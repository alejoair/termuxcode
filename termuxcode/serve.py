#!/usr/bin/env python3
# ruff: noqa: ANN401
"""Servidor HTTP simple para servir el cliente WebSocket."""

import http.server
import json
import socketserver
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

PORT = 1988
STATIC_DIR = Path(__file__).parent.absolute() / "static"


class ChatHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personalizado que sirve / como index.html."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Log personalizado más limpio."""
        print(f"[HTTP] {self.address_string()} - {self.path}")

    def end_headers(self) -> None:
        """Inject no-cache headers on all responses."""
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self) -> None:
        """Override: intercept /api/file, delegate the rest to static file serving."""
        if self.path.startswith('/api/file'):
            self._handle_file_api()
            return
        super().do_GET()

    def do_PUT(self) -> None:
        """Handle PUT /api/file — write file content to disk."""
        if self.path.startswith('/api/file'):
            self._handle_file_write()
            return
        self._send_json_error(404, "Not found")

    def _resolve_safe_path(self, rel_path: str) -> tuple[Path | None, str | None]:
        """Resolve a relative path against CWD with traversal check.

        Returns (resolved_path, error_message). If error_message is set, the path is unsafe.
        """
        if not rel_path:
            return None, "Missing 'path' parameter"
        cwd = Path(os.environ.get('TERMUXCODE_CWD', os.getcwd())).resolve()
        file_path = (cwd / rel_path).resolve()
        if not str(file_path).startswith(str(cwd)):
            return None, "Access denied"
        return file_path, None

    def _handle_file_api(self) -> None:
        """Serve project files as JSON via GET /api/file?path=<relative_path>."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        rel_path = params.get('path', [''])[0]

        file_path, err = self._resolve_safe_path(rel_path)
        if err:
            code = 403 if err == "Access denied" else 400
            self._send_json_error(code, err)
            return

        if not file_path.is_file():
            self._send_json_error(404, "File not found")
            return

        try:
            content = file_path.read_text(encoding='utf-8')
            self._send_json(200, {
                "content": content,
                "path": rel_path,
                "name": file_path.name,
                "size": file_path.stat().st_size,
            })
        except UnicodeDecodeError:
            self._send_json_error(415, "Binary file, cannot display")
        except Exception as e:
            self._send_json_error(500, str(e))

    def _handle_file_write(self) -> None:
        """Write file content via PUT /api/file — body: {"path": "...", "content": "..."}."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._send_json_error(400, "Invalid JSON body")
            return

        rel_path = body.get('path', '')
        content = body.get('content')

        if content is None:
            self._send_json_error(400, "Missing 'content' field")
            return

        file_path, err = self._resolve_safe_path(rel_path)
        if err:
            code = 403 if err == "Access denied" else 400
            self._send_json_error(code, err)
            return

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            self._send_json(200, {
                "ok": True,
                "path": rel_path,
                "size": len(content.encode('utf-8')),
            })
        except Exception as e:
            self._send_json_error(500, str(e))

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json_error(self, code: int, message: str) -> None:
        self._send_json(code, {"error": message})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    import os
    host = os.environ.get("TERMUXCODE_HOST", "localhost")
    bind_host = "" if host == "0.0.0.0" else host
    with ThreadedHTTPServer((bind_host, PORT), ChatHTTPRequestHandler) as httpd:
        print(f"[HTTP] Servidor corriendo en http://{host}:{PORT}")
        print(f"[HTTP] Chat disponible en http://{host}:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
