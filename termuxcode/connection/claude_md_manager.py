#!/usr/bin/env python3
"""Manager para actualizar CLAUDE.md con context providers modulares."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from termuxcode.ws_config import logger


# Importar todos los providers para que se registren automáticamente
from termuxcode.connection.context import (
    get_providers,
    list_providers,
)
from termuxcode.connection.context import filetree_provider  # noqa: F401
from termuxcode.connection.context import git_provider  # noqa: F401
from termuxcode.connection.context import system_provider  # noqa: F401


# Marcador en CLAUDE.md para insertar la información actualizada
SECTION_MARKER = "## Project Context (Auto-generated)"


def _is_git_repo(cwd: str) -> bool:
    """Verifica si el directorio está en un repo git.

    Args:
        cwd: Directorio a verificar

    Returns:
        True si es un repo git
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def update_claude_md(cwd: str, session_id: str | None = None) -> bool:
    """Actualiza el CLAUDE.md con información de todos los providers.

    Args:
        cwd: Directorio de trabajo del proyecto
        session_id: ID de sesión (para logs/debugging)

    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    claude_md_path = os.path.join(cwd, "CLAUDE.md")

    # Si no existe CLAUDE.md, no hacer nada
    if not os.path.isfile(claude_md_path):
        logger.debug(f"CLAUDE.md no encontrado en {cwd}, omitiendo actualización")
        return False

    try:
        # Leer contenido actual
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Detectar si hay git
        has_git = _is_git_repo(cwd)

        # Obtener providers apropiados
        if has_git:
            providers = get_providers()  # Todos (incluye los que requieren git)
        else:
            providers = get_providers(skip_git=True)  # Solo los que NO requieren git

        # Generar contexto de cada provider
        context_parts = []
        for provider in providers:
            try:
                context = provider(cwd)
                if context and context.strip():
                    context_parts.append(context)
            except Exception as e:
                logger.debug(f"Provider {provider.__name__} falló: {e}")

        if not context_parts:
            logger.debug(f"No se generó contexto de ningún provider")
            return False

        # Unir todos los contextos
        combined_context = "\n\n".join(context_parts)

        # Buscar la sección marcada en CLAUDE.md
        lines = original_content.split('\n')
        section_start = -1
        section_end = -1

        for i, line in enumerate(lines):
            if line.strip() == SECTION_MARKER:
                section_start = i
                # Buscar el final de la sección (próximo ## o fin del archivo)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('## ') and j > i + 1:
                        section_end = j
                        break
                if section_end == -1:
                    section_end = len(lines)
                break

        # Crear el nuevo contenido de la sección
        new_section = f"""{SECTION_MARKER}

> **Nota**: Esta sección se genera automáticamente antes de cada query.
> No la edites manualmente ya que se sobrescribirá.
>
> Providers activos: {", ".join(p.__name__ for p in providers)}

{combined_context}

---

"""

        if section_start != -1:
            # Reemplazar sección existente
            lines[section_start:section_end] = new_section.strip().split('\n')
            new_content = '\n'.join(lines)
            logger.debug(f"Sección actualizada en CLAUDE.md (session={session_id})")
        else:
            # Agregar sección al final
            if original_content and not original_content.endswith('\n'):
                new_content = original_content + '\n\n' + new_section
            else:
                new_content = original_content + '\n' + new_section
            logger.debug(f"Sección agregada al CLAUDE.md (session={session_id})")

        # Escribir el contenido actualizado
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info(
            f"CLAUDE.md actualizado con {len(providers)} providers en {cwd} (session={session_id})"
        )
        return True

    except Exception as e:
        logger.warning(f"Error actualizando CLAUDE.md: {e}")
        return False


def build_message_context(cwd: str) -> str:
    """Genera contexto dinámico para inyectar al inicio de cada mensaje del usuario.

    Para agregar un provider nuevo, añadir una entrada a MESSAGE_CONTEXT_PROVIDERS:
        ("nombre", requires_git, callable)

    Args:
        cwd: Directorio de trabajo del proyecto

    Returns:
        String con el contexto listo para prefijar al mensaje, o "" si no hay nada
    """
    from termuxcode.connection.context.system_provider import generate_system_context
    from termuxcode.connection.context.git_provider import generate_git_status_context

    # (nombre, requires_git, función)
    MESSAGE_CONTEXT_PROVIDERS = [
        ("system",     False, generate_system_context),
        ("git_status", True,  generate_git_status_context),
    ]

    has_git = _is_git_repo(cwd)
    parts = []

    for name, requires_git, fn in MESSAGE_CONTEXT_PROVIDERS:
        if requires_git and not has_git:
            continue
        try:
            result = fn(cwd)
            if result and result.strip():
                parts.append(result.strip())
        except Exception as e:
            logger.debug(f"{name} provider falló en build_message_context: {e}")

    if not parts:
        return ""

    combined = "\n\n".join(parts)
    return f"<context>\n{combined}\n</context>\n\n"


def list_active_providers() -> list[dict[str, Any]]:
    """Retorna metadata de todos los providers registrados (para debugging).

    Returns:
        Lista de diccionarios con info de cada provider
    """
    return list_providers()
