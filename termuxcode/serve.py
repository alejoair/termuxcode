#!/usr/bin/env python3
"""Servidor HTTP simple para servir el cliente WebSocket."""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).parent.parent.absolute()
STATIC_DIR = BASE_DIR / "static"


class ChatHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personalizado que sirve / como index.html."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format, *args):
        """Log personalizado más limpio."""
        print(f"[HTTP] {self.address_string()} - {self.path}")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def main():
    with ThreadedHTTPServer(("", PORT), ChatHTTPRequestHandler) as httpd:
        print(f"[HTTP] Servidor corriendo en http://localhost:{PORT}")
        print(f"[HTTP] Chat disponible en http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
