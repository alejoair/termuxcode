"""Registry de tools LSP - sistema de auto-registro sin import circular.

Este módulo está separado de server.py para evitar el ciclo:
server → tools → type_check → server (❌ circular)
server → tools → type_check → registry (✅ no circular)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from termuxcode.connection.lsp_manager import LspManager

# Registry de tools que necesitan LSP (auto-registro)
_LSP_TOOLS: list = []


def register_lsp_tool(setter_func) -> None:
    """Registra una tool que necesita inyección de LspManager.

    Args:
        setter_func: Función que recibe el LspManager (ej: set_lsp_manager)

    Las tools LSP deben llamarse así en su módulo:
        from termuxcode.custom_tools.registry import register_lsp_tool
        register_lsp_tool(set_lsp_manager)
    """
    _LSP_TOOLS.append(setter_func)


def inject_lsp_manager(lsp_manager: "LspManager | None") -> None:
    """Inyecta el LspManager en todas las tools registradas.

    Esta función se llama desde server.py al crear el MCP server.
    """
    for setter_func in _LSP_TOOLS:
        try:
            setter_func(lsp_manager)
        except Exception as e:
            # Fallar silenciosamente - una tool rota no debe romper todas
            pass
