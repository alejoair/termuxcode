"""Sistema modular de context providers para CLAUDE.md.

Cada provider es una función que genera información contextual del proyecto
y se registra automáticamente en el sistema.
"""

from __future__ import annotations

from typing import Any


# Registry global de providers
_CONTEXT_PROVIDERS: list[dict[str, Any]] = []


def register_context_provider(
    name: str,
    priority: int = 100,
    requires_git: bool = False,
) -> callable:
    """Decorador para registrar un context provider.

    Args:
        name: Nombre del provider (para logs/debugging)
        priority: Menor = mayor prioridad (se ejecuta primero)
        requires_git: True si el provider requiere estar en un repo git

    Returns:
        Decorador que registra la función y la retorna intacta

    Example:
        @register_context_provider("filetree", priority=10)
        def generate_filetree_context(cwd: str) -> str:
            return "## File Tree\\n..."
    """
    def decorator(func: callable) -> callable:
        _CONTEXT_PROVIDERS.append({
            "name": name,
            "priority": priority,
            "requires_git": requires_git,
            "func": func,
        })
        # Ordenar por prioridad
        _CONTEXT_PROVIDERS.sort(key=lambda p: p["priority"])
        return func
    return decorator


def get_providers(
    require_git: bool = False,
    skip_git: bool = False,
) -> list[callable]:
    """Retorna los providers registrados filtrados por criterios.

    Args:
        require_git: Solo retorna providers que requieren git
        skip_git: Excluye providers que requieren git

    Returns:
        Lista de funciones de provider ordenadas por prioridad
    """
    providers = _CONTEXT_PROVIDERS

    if require_git:
        providers = [p for p in providers if p["requires_git"]]
    elif skip_git:
        providers = [p for p in providers if not p["requires_git"]]

    return [p["func"] for p in providers]


def list_providers() -> list[dict[str, Any]]:
    """Retorna metadata de todos los providers registrados (para debugging)."""
    return [
        {
            "name": p["name"],
            "priority": p["priority"],
            "requires_git": p["requires_git"],
        }
        for p in _CONTEXT_PROVIDERS
    ]
