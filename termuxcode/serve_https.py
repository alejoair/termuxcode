#!/usr/bin/env python3
"""Servidor HTTPS simple para servir el cliente WebSocket con certificado self-signed."""

import http.server
import json
import socketserver
import os
import ssl
import ipaddress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

PORT = 1988
_PKG_DIR = Path(__file__).parent.absolute()
STATIC_DIR = _PKG_DIR / "static"
CERT_DIR = _PKG_DIR / ".certs"


def generate_self_signed_cert():
    """Genera certificado SSL self-signed si no existe."""
    CERT_DIR.mkdir(exist_ok=True)
    cert_file = CERT_DIR / "server.crt"
    key_file = CERT_DIR / "server.key"

    if cert_file.exists() and key_file.exists():
        print(f"[HTTPS] Usando certificado existente en {CERT_DIR}")
        return str(cert_file), str(key_file)

    print(f"[HTTPS] Generando certificado self-signed...")
    
    # Generar clave privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Crear certificado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Termux"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TermuxCode"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Guardar certificado
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Guardar clave privada
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print(f"[HTTPS] ✅ Certificado generado en {CERT_DIR}")
    return str(cert_file), str(key_file)


class ChatHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personalizado que sirve / como index.html."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Log personalizado más limpio."""
        print(f"[HTTPS] {self.address_string()} - {self.path}")

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
        """Resolve a relative path against CWD with traversal check."""
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
        """Write file content via PUT /api/file."""
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
    # Generar certificado SSL
    cert_file, key_file = generate_self_signed_cert()
    
    # Crear servidor HTTP
    with ThreadedHTTPServer(("", PORT), ChatHTTPRequestHandler) as httpd:
        # Envolver con SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print(f"[HTTPS] 🔒 Servidor HTTPS corriendo en https://localhost:{PORT}")
        print(f"[HTTPS] Chat disponible en https://localhost:{PORT}")
        print(f"[HTTPS] ⚠️  El certificado es self-signed, acepta la advertencia del navegador")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
