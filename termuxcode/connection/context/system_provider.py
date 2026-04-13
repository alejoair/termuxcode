"""Context provider: Información del sistema (OS, usuario, fecha, etc.)."""

from __future__ import annotations

import datetime
import os
import platform
import socket
import sys
from typing import Any

from termuxcode.connection.context import register_context_provider
from termuxcode.ws_config import logger


def _get_os_info() -> dict[str, str]:
    """Obtiene información del sistema operativo."""
    return {
        "system": platform.system(),           # Windows, Linux, Darwin
        "release": platform.release(),         # Versión del kernel
        "version": platform.version(),         # Versión completa
        "machine": platform.machine(),         # x86_64, ARM64, etc.
    }


def _get_user_info() -> dict[str, str]:
    """Obtiene información del usuario y entorno."""
    try:
        username = os.getlogin()
    except (OSError, Exception):
        username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"

    return {
        "username": username,
        "hostname": hostname,
        "home": os.path.expanduser("~"),
    }


def _get_shell_info() -> dict[str, str]:
    """Obtiene información del shell/terminal."""
    shell = os.getenv("SHELL") or os.getenv("COMSPEC") or "unknown"

    # Detectar si es WSL
    is_wsl = False
    if platform.system() == "Linux":
        try:
            with open("/proc/version", "r") as f:
                is_wsl = "microsoft" in f.read().lower()
        except Exception:
            pass

    return {
        "shell": shell,
        "is_wsl": is_wsl,
    }


def _get_python_info() -> dict[str, str]:
    """Obtiene información de Python."""
    return {
        "version": sys.version.split()[0],  # Solo versión major.minor.micro
        "executable": sys.executable,
    }


def _get_datetime_info() -> dict[str, str]:
    """Obtiene fecha y hora actual."""
    now = datetime.datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo,
        "unix_timestamp": str(int(now.timestamp())),
    }


def _get_env_info() -> dict[str, Any]:
    """Obtiene variables de entorno útiles."""
    return {
        "path": os.getenv("PATH"),
        "lang": os.getenv("LANG") or os.getenv("LANGUAGE") or "unknown",
        "term": os.getenv("TERM") or "unknown",
    }


@register_context_provider("system", priority=5)
def generate_system_context(cwd: str) -> str:
    """Genera información del sistema operativo y entorno.

    Args:
        cwd: Directorio raíz del proyecto (no usado, pero requerido por la interfaz)

    Returns:
        String con la información del sistema en formato markdown
    """
    try:
        os_info = _get_os_info()
        user_info = _get_user_info()
        shell_info = _get_shell_info()
        python_info = _get_python_info()
        datetime_info = _get_datetime_info()

        # Determinar icono/emoji según el OS
        os_icon = {
            "Windows": "🪟",
            "Linux": "🐧",
            "Darwin": "🍎",
        }.get(os_info["system"], "💻")

        # Formatear shell info
        shell_display = shell_info["shell"]
        if shell_info["is_wsl"]:
            shell_display += " (WSL)"

        return f"""### System Info

- **OS**: {os_icon} {os_info["system"]} {os_info["release"]} ({os_info["machine"]})
- **User**: `{user_info["username"]}@{user_info["hostname"]}`
- **Home**: `{user_info["home"]}`
- **Shell**: `{shell_display}`
- **Python**: `{python_info["version"]}` → `{python_info["executable"]}`
- **Date/Time**: {datetime_info["date"]} {datetime_info["time"]} ({datetime_info["timezone"]})
- **Unix Timestamp**: `{datetime_info["unix_timestamp"]}`

"""
    except Exception as e:
        logger.debug(f"Error generando system context: {e}")
        return "### System Info\n\n⚠️ No se pudo obtener información del sistema"


@register_context_provider("extended_system", priority=6)
def generate_extended_system_context(cwd: str) -> str:
    """Genera información extendida del sistema (variables de entorno, etc.).

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con información extendida en formato markdown
    """
    try:
        env_info = _get_env_info()

        # Formatear PATH (mostrar primeros entries si es muy largo)
        path_str = env_info["path"] or "not set"
        if path_str != "not set":
            path_entries = path_str.split(os.pathsep)
            if len(path_entries) > 10:
                path_display = os.pathsep.join(path_entries[:5]) + os.pathsep + "\n  ... " + os.pathsep.join(path_entries[-3:])
            else:
                path_display = path_str
        else:
            path_display = "not set"

        return f"""### Extended System Info

- **LANG**: `{env_info["lang"]}`
- **TERM**: `{env_info["term"]}`
- **PATH**:
  ```
  {path_display}
  ```

"""
    except Exception as e:
        logger.debug(f"Error generando extended system context: {e}")
        return ""
