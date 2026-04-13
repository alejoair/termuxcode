"""EJEMPLO: Cómo crear un context provider personalizado.

Copia este archivo como base para crear tus propios providers.
"""

from termuxcode.connection.context import register_context_provider


# Ejemplo 1: Provider simple sin dependencias
@register_context_provider("mi_provider", priority=50)
def generate_mi_context(cwd: str) -> str:
    """Genera información personalizada para el CLAUDE.md.

    Args:
        cwd: Directorio del proyecto

    Returns:
        String con el contexto en formato markdown
    """
    # Tu lógica aquí
    return f"""### Mi Contexto Personalizado

- Información importante: ...
- Otro dato: ...
"""


# Ejemplo 2: Provider que requiere git
@register_context_provider("mi_provider_git", priority=51, requires_git=True)
def generate_git_context_custom(cwd: str) -> str:
    """Genera información de git personalizada.

    Solo se ejecutará si el proyecto está en un repo git.
    """
    # Tu lógica de git aquí
    return "### Mi Info de Git\n\n..."


# Ejemplo 3: Provider con prioridad alta (se ejecuta primero)
@register_context_provider("critico", priority=1)
def generate_context_critico(cwd: str) -> str:
    """Información crítica que debe aparecer primero."""
    return "### ⚠️ Crítico\n\nRevisa esto antes de nada."


# -----------------------------------------------------------------------
# PARA AGREGAR UN NUEVO PROVIDER:
#
# 1. Crea un archivo en termuxcode/connection/context/mi_provider.py
# 2. Usa el decorador @register_context_provider()
# 3. Importa tu archivo en claude_md_manager.py:
#
#    from termuxcode.connection.context import mi_provider  # noqa: F401
#
# 4. ¡Listo! Se ejecutará automáticamente antes de cada query
# -----------------------------------------------------------------------
