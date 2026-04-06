#!/usr/bin/env python3
"""Protocolo JSON-RPC para LSP."""

import json
from typing import Any


def build_request(msg_id: int, method: str, params: Any = None) -> dict:
    """Construye un request JSON-RPC."""
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def build_notification(method: str, params: Any = None) -> dict:
    """Construye una notificación JSON-RPC (sin ID)."""
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def encode_message(msg: dict) -> bytes:
    """Codifica un mensaje JSON-RPC con header Content-Length."""
    body = json.dumps(msg).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    return header + body


def parse_headers(data: bytes) -> dict[str, str]:
    """Parsea headers HTTP-style del protocolo LSP."""
    headers = {}
    for line in data.decode("utf-8", errors="replace").split("\r\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            headers[key.strip()] = val.strip()
    return headers


def parse_message(body: bytes) -> dict | None:
    """Parsea el body de un mensaje JSON-RPC."""
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def is_response(msg: dict) -> bool:
    """True si el mensaje es una respuesta (tiene 'id' pero no 'method')."""
    return "id" in msg and "method" not in msg


def is_notification(msg: dict) -> bool:
    """True si el mensaje es una notificación del servidor (tiene 'method')."""
    return "method" in msg


def get_response_result(msg: dict) -> Any:
    """Extrae el resultado de una respuesta, o None si hay error."""
    if "error" in msg:
        return None
    return msg.get("result")


def get_response_error(msg: dict) -> dict | None:
    """Extrae el error de una respuesta, o None si no hay error."""
    return msg.get("error")
