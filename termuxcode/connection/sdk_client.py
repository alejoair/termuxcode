#!/usr/bin/env python3
"""Gestión del cliente SDK para Claude Agent."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import HookMatcher

from termuxcode.connection.hooks import (
    make_pre_tool_use_hook,
    make_post_tool_use_read_hook,
    make_post_tool_use_edit_hook,
)
from termuxcode.ws_config import logger

if TYPE_CHECKING:
    from claude_agent_sdk._internal.transport import Transport
    from termuxcode.connection.lsp_manager import LspManager


async def _dummy_hook(input_data: dict[str, Any], tool_use_id: str, context: dict[str, Any]) -> dict[str, bool]:
    """Hook requerido para que can_use_tool funcione en streaming mode."""
    return {"continue_": True}


class SDKClient:
    """Encapsula la inicialización y comunicación con el Claude SDK."""

    def __init__(self, resume_id: str | None = None, cwd: str | None = None,
                 can_use_tool: Callable[..., Coroutine[Any, Any, bool]] | None = None,
                 agent_options: dict[str, Any] | None = None, lsp_manager: LspManager | None = None) -> None:
        """Inicializa el cliente SDK.

        Args:
            resume_id: ID de sesión para reanudar
            cwd: Directorio de trabajo
            can_use_tool: Callback async para aprobación de herramientas
            agent_options: Opciones del agente desde el frontend
            lsp_manager: LspManager de la sesión (para hooks LSP aislados)
        """
        self._client = None
        self.resume_id = resume_id
        self.cwd = cwd
        self._can_use_tool = can_use_tool
        self._agent_options = agent_options or {}
        self._lsp_manager = lsp_manager

    def _build_options(self, resume: bool = True) -> ClaudeAgentOptions:
        """Construye las opciones del agente.

        Args:
            resume: Si True, incluye resume_id en las opciones

        Returns:
            ClaudeAgentOptions configurado
        """
        o = self._agent_options

        options = ClaudeAgentOptions(
            permission_mode=o.get("permission_mode", "bypassPermissions"),
            model=o.get("model", "glm-5"),
            setting_sources=["user", "project", "local"],
            stderr=lambda line: logger.error(f"Claude CLI stderr: {line}"),
        )
        if o.get("system_prompt"):
            options.system_prompt = o["system_prompt"]
        if o.get("append_system_prompt"):
            options.append_system_prompt = o["append_system_prompt"]
        if o.get("max_turns"):
            options.max_turns = int(o["max_turns"])
        if o.get("allowed_tools"):
            options.allowed_tools = o["allowed_tools"]
        if o.get("disallowed_tools"):
            options.disallowed_tools = o["disallowed_tools"]
        if o.get("tools"):
            options.tools = o["tools"]

        if self._can_use_tool:
            options.can_use_tool = self._can_use_tool

            # Hooks LSP: solo si hay un LspManager asignado a esta sesión
            if self._lsp_manager:
                options.hooks = {
                    "PreToolUse": [
                        HookMatcher(matcher="Write|Edit",
                            hooks=[make_pre_tool_use_hook(self._lsp_manager)]),
                        HookMatcher(matcher=None, hooks=[_dummy_hook]),
                    ],
                    "PostToolUse": [
                        HookMatcher(matcher="Read",
                            hooks=[make_post_tool_use_read_hook(self._lsp_manager)]),
                        HookMatcher(matcher="Write|Edit",
                            hooks=[make_post_tool_use_edit_hook(self._lsp_manager)]),
                    ],
                }
                logger.info("can_use_tool + LSP hooks configurados (per-session)")
            else:
                # Sin LSP — solo el dummy hook
                options.hooks = {
                    "PreToolUse": [
                        HookMatcher(matcher=None, hooks=[_dummy_hook]),
                    ],
                }
                logger.info("can_use_tool configurado sin LSP hooks")

        if self.cwd:
            options.cwd = self.cwd

        if resume and self.resume_id:
            options.resume = self.resume_id

        return options

    async def connect(self) -> None:
        """Conecta al SDK.

        Raises:
            Exception: Si falla la conexión
        """
        options = self._build_options()

        try:
            self._client = ClaudeSDKClient(options)
            await self._client.connect()

        except Exception as e:
            logger.error(f"Error conectando SDK: {e}")
            raise

    async def reconnect(self, session_id: str | None = None) -> None:
        """Crea un nuevo cliente SDK.

        Args:
            session_id: ID de sesión para reanudar (actualiza resume_id)
        """
        if session_id:
            self.resume_id = session_id

        self._client = None
        await self.connect()

    async def disconnect(self) -> None:
        """Desconecta el cliente SDK."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                # anyio cancel scope mismatch es un problema conocido del SDK
                # No es crítico - la conexión se cierra de todas formas
                error_msg = str(e)
                if "cancel scope" in error_msg.lower():
                    logger.debug(f"SDK disconnect: cancel scope issue (known SDK bug)")
                else:
                    logger.warning(f"Error en disconnect: {e}")
            finally:
                self._client = None

    async def query(self, content: str) -> None:
        """Envía una consulta al SDK.

        Args:
            content: Contenido de la consulta
        """
        if not self._client:
            raise RuntimeError("Cliente SDK no conectado")
        await self._client.query(content)

    async def receive_response(self) -> AsyncIterator[Any]:
        """Recibe la respuesta del SDK como un async iterator.

        Yields:
            Mensajes del SDK (AssistantMessage, ResultMessage, etc.)
        """
        if not self._client:
            raise RuntimeError("Cliente SDK no conectado")
        async for msg in self._client.receive_response():
            yield msg

    async def interrupt(self) -> None:
        """Interrumpe la consulta actual del SDK."""
        if self._client:
            await self._client.interrupt()

    async def get_mcp_status(self) -> dict:
        """Devuelve el estado de los servidores MCP conectados."""
        if not self._client:
            return {"mcpServers": []}
        return await self._client.get_mcp_status()

    @property
    def transport(self) -> Transport | None:
        """Retorna el transporte del SDK para envío directo de mensajes."""
        if self._client and hasattr(self._client, '_transport'):
            return self._client._transport
        return None

    @property
    def is_connected(self) -> bool:
        """Verifica si el cliente está conectado."""
        return self._client is not None
