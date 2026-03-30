#!/usr/bin/env python3
"""Gestión del historial de conversaciones JSONL."""

import os
from pathlib import Path

from termuxcode.ws_config import logger


def get_history_path(cwd: str, session_id: str) -> Path | None:
    """Obtiene la ruta al archivo JSONL de historial.

    Args:
        cwd: Directorio de trabajo del proyecto
        session_id: ID de la sesión

    Returns:
        Path al archivo JSONL o None si no existe
    """
    # Transformar cwd a nombre de carpeta igual que Claude Code:
    # C:\Users\foo\bar -> C--Users-foo-bar  (: -> -, \ -> -)
    # /home/foo/bar -> -home-foo-bar
    project_name = cwd.replace(":", "-").replace("\\", "-").replace("/", "-").replace(".", "-")
    claude_dir = Path.home() / ".claude" / "projects" / project_name
    history_file = claude_dir / f"{session_id}.jsonl"

    if history_file.exists():
        return history_file

    logger.warning(f"Archivo de historial no encontrado: {history_file}")
    return None


def truncate_history(cwd: str, session_id: str, keep_last: int = 100) -> bool:
    """Trunca el historial a los últimos N mensajes.

    Args:
        cwd: Directorio de trabajo del proyecto
        session_id: ID de la sesión
        keep_last: Número de mensajes a conservar (default: 100)

    Returns:
        True si se truncó exitosamente, False en caso contrario
    """
    history_path = get_history_path(cwd, session_id)
    if not history_path:
        return False

    try:
        # Leer todas las líneas
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)

        if total_lines <= keep_last:
            logger.info(f"Historial tiene {total_lines} líneas, no necesita truncado")
            return False  # No se truncó

        # Conservar solo las últimas N líneas
        truncated_lines = lines[-keep_last:]

        # Escribir de vuelta
        with open(history_path, "w", encoding="utf-8") as f:
            f.writelines(truncated_lines)

        logger.info(f"Historial truncado: {total_lines} -> {keep_last} líneas")
        return True

    except Exception as e:
        logger.error(f"Error truncando historial: {e}", exc_info=True)
        return False
