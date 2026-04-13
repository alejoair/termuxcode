"""Context provider: Información de Git."""

from __future__ import annotations

import subprocess

from termuxcode.connection.context import register_context_provider
from termuxcode.ws_config import logger


@register_context_provider("git", priority=30, requires_git=True)
def generate_git_context(cwd: str) -> str:
    """Genera información de git del proyecto.

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con información de git en formato markdown
    """
    try:
        # Verificar si estamos en un repo git
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode != 0:
            return ""

        # Obtener branch actual
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Obtener commits recientes (últimos 3)
        log_result = subprocess.run(
            ["git", "log", "-3", "--pretty=format:%h %s"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        recent_commits = ""
        if log_result.returncode == 0:
            commits = log_result.stdout.strip().split('\n')
            if commits and commits[0]:
                recent_commits = "\n" + "\n".join(f"  - {c}" for c in commits)

        return f"""### Git Info

- **Branch**: `{branch}`{recent_commits}"""

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"Error obteniendo info de git: {e}")
        return ""


@register_context_provider("git_status", priority=31, requires_git=True)
def generate_git_status_context(cwd: str) -> str:
    """Genera un resumen de git status (archivos modificados).

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con git status en formato markdown
    """
    try:
        # Verificar si estamos en un repo git
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode != 0:
            return ""

        # Obtener status corto
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        if status_result.returncode != 0 or not status_result.stdout.strip():
            return ""

        lines = status_result.stdout.strip().split('\n')
        if not lines or lines == ['']:
            return ""

        # Contar tipos de cambios
        modified = sum(1 for line in lines if line.startswith(' M') or line.startswith('M'))
        staged = sum(1 for line in lines if line.startswith('M ') or line.startswith('A'))
        untracked = sum(1 for line in lines if line.startswith('??'))

        # Si hay muchos archivos, solo mostrar el conteo
        if len(lines) > 20:
            return f"""### Git Status

- **Modified**: {modified}
- **Staged**: {staged}
- **Untracked**: {untracked}
- **Total**: {len(lines)} archivos

"""

        # Mostrar hasta 20 archivos
        files_display = "\n".join(f"  {line}" for line in lines[:20])
        if len(lines) > 20:
            files_display += f"\n  ... y {len(lines) - 20} más"

        return f"""### Git Status

```
{files_display}
```"""

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"Error obteniendo git status: {e}")
        return ""
