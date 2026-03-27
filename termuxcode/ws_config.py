#!/usr/bin/env python3
"""Configuración del servidor WebSocket."""

import logging
import os
import sys
from pathlib import Path

# Configuración del servidor
WS_HOST = "localhost"
WS_PORT = 8769

# Directorio base del proyecto (source) o temporal (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.absolute()

# Archivo de log — usar directorio del usuario, no el temporal de PyInstaller
LOG_FILE = Path.home() / ".termuxcode" / "websocket_server.log"


def setup_logging():
    """Configura el sistema de logging."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(LOG_FILE)]
    )
    return logging.getLogger(__name__)


logger = setup_logging()
