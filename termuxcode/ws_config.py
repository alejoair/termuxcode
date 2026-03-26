#!/usr/bin/env python3
"""Configuración del servidor WebSocket."""

import logging
import os
from pathlib import Path

# Configuración del servidor
WS_HOST = "localhost"
WS_PORT = 8769

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent.absolute()

# Archivo de log
LOG_FILE = BASE_DIR / "websocket_server.log"


def setup_logging():
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(LOG_FILE)]
    )
    return logging.getLogger(__name__)


logger = setup_logging()
