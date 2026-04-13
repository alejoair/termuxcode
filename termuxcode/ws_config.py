#!/usr/bin/env python3
"""Configuración del servidor WebSocket."""

import logging
import sys
from pathlib import Path
from typing import Any

# Configuración del servidor
WS_HOST = "localhost"
WS_PORT = 2025

# Directorio base del proyecto (source) o temporal (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.absolute()

# Archivo de log — usar directorio del usuario, no el temporal de PyInstaller
LOG_FILE = Path.home() / ".termuxcode" / "websocket_server.log"


def setup_logging() -> logging.Logger:
    """Configura el sistema de logging."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Configurar handlers
    handlers = [
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]

    # Agregar handler de consola con soporte UTF-8 (necesario para emojis en Windows)
    # Reconfigurar stdout para usar UTF-8
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    # Silenciar keepalive ping/pong de websockets
    logging.getLogger("websockets").setLevel(logging.INFO)

    return logging.getLogger(__name__)


logger = setup_logging()


def attach_ws_log_handler(loop: Any) -> None:
    """Adjunta el WebSocketLogHandler al root logger.

    Debe llamarse después de que el event loop arranque.

    Args:
        loop: Event loop de asyncio activo
    """
    from termuxcode.connection.log_handler import WebSocketLogHandler

    handler = WebSocketLogHandler(loop)
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    logger.info("WebSocketLogHandler adjuntado al root logger")
