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
    """Handler personalizado que sirve /chat como index.html."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        # Archivos estáticos (app.js, etc.)
        if self.path == "/app.js":
            self.path = "/static/app.js"
        # Ruta /chat sirve el index.html
        elif self.path == "/chat" or self.path == "/chat/":
            self.path = "/static/index.html"
        # Redirigir /chat/* a /static/*
        elif self.path.startswith("/chat/"):
            self.path = "/static/" + self.path[6:]

        super().do_GET()

    def log_message(self, format, *args):
        """Log personalizado más limpio."""
        print(f"[HTTP] {self.address_string()} - {self.path}")


def main():
    with socketserver.TCPServer(("", PORT), ChatHTTPRequestHandler) as httpd:
        print(f"[HTTP] Servidor corriendo en http://localhost:{PORT}")
        print(f"[HTTP] Chat disponible en http://localhost:{PORT}/chat")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
