"""MCP server in-process que agrupa todos los custom tools."""

from typing import TYPE_CHECKING

from claude_agent_sdk import create_sdk_mcp_server

from termuxcode.custom_tools.registry import inject_lsp_manager
from termuxcode.custom_tools.tools import TOOLS

if TYPE_CHECKING:
    from termuxcode.connection.lsp_manager import LspManager


def get_custom_mcp_server(lsp_manager: "LspManager | None" = None):
    """Retorna un nuevo MCP server con todos los custom tools registrados.

    Args:
        lsp_manager: LspManager de la sesión para inyectar en tools que lo necesiten

    NOTA: Se crea una nueva instancia cada vez para evitar estado corrupto
    entre sesiones del MCP server in-process.
    """
    # Inyectar el LspManager en TODAS las tools que lo necesitan
    inject_lsp_manager(lsp_manager)

    return create_sdk_mcp_server(
        name="termuxcode",
        version="1.0.0",
        tools=TOOLS,
    )
