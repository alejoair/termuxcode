#!/usr/bin/env python3
# ruff: noqa: ANN401
"""Entry point for the desktop sidecar - runs WebSocket + HTTP API servers."""

import asyncio
import subprocess
import sys
import threading
from typing import Any

# En Windows, patchear subprocess para que no abra ventanas de consola
if sys.platform == "win32":
    _original_popen_init = subprocess.Popen.__init__

    def _no_window_popen_init(
        self: subprocess.Popen[Any], *args: Any, **kwargs: Any
    ) -> None:
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW
        _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _no_window_popen_init


def _start_http_api() -> None:
    """Start the HTTP API server in a background thread (serves /api/file only)."""
    from http.server import HTTPServer
    from termuxcode.serve import ChatHTTPRequestHandler

    host = "localhost"
    port = 1988
    try:
        httpd = HTTPServer((host, port), ChatHTTPRequestHandler)
        print(f"[HTTP] API server on http://{host}:{port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Failed to start API server: {e}")


if __name__ == "__main__":
    # Start HTTP API in background thread
    _http_thread = threading.Thread(target=_start_http_api, daemon=True)
    _http_thread.start()

    from termuxcode.ws_server import main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
