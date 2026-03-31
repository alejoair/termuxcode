#!/usr/bin/env python3
"""Gestión del cliente SDK para Claude Agent."""

import asyncio

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import HookMatcher

from termuxcode.ws_config import logger


async def _dummy_hook(input_data, tool_use_id, context):
    """Hook requerido para que can_use_tool funcione en streaming mode."""
    return {"continue_": True}


class SDKClient:
    """Encapsula la inicialización y comunicación con el Claude SDK."""

    def __init__(self, resume_id: str = None, cwd: str = None, can_use_tool=None, agent_options: dict = None):
        """Inicializa el cliente SDK.

        Args:
            resume_id: ID de sesión para reanudar
            cwd: Directorio de trabajo
            can_use_tool: Callback async para aprobación de herramientas
            agent_options: Opciones del agente desde el frontend
        """
        self._client = None
        self.resume_id = resume_id
        self.cwd = cwd
        self._can_use_tool = can_use_tool
        self._agent_options = agent_options or {}

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

        if self._can_use_tool:
            options.can_use_tool = self._can_use_tool
            options.hooks = {"PreToolUse": [HookMatcher(matcher=None, hooks=[_dummy_hook])]}
            logger.info("can_use_tool callback configurado")

        if self.cwd:
            options.cwd = self.cwd
            logger.info(f"Usando cwd: {self.cwd}")

        if resume and self.resume_id:
            logger.info(f"Reanudando sesión: {self.resume_id}")
            options.resume = self.resume_id

        return options

    async def connect(self) -> str | None:
        """Conecta al SDK y retorna el session_id si está disponible.

        Returns:
            El session_id del SDK o None si no está disponible aún

        Raises:
            Exception: Si falla la conexión
        """
        logger.info("Creando cliente SDK...")
        options = self._build_options()

        try:
            self._client = ClaudeSDKClient(options)
            await self._client.connect()
            logger.info("Cliente conectado")

            # Retornar resume_id como session_id para reconexiones
            if self.resume_id:
                logger.info(f"Usando resume_id como session_id: {self.resume_id}")
                return self.resume_id

            return None

        except Exception as e:
            logger.error(f"Error conectando SDK: {e}")
            raise

    async def reconnect(self, session_id: str = None) -> str | None:
        """Crea un nuevo cliente SDK.

        Args:
            session_id: ID de sesión para reanudar (actualiza resume_id)

        Returns:
            El session_id o None
        """
        if session_id:
            self.resume_id = session_id

        self._client = None
        return await self.connect()

    async def disconnect(self):
        """Desconecta el cliente SDK."""
        if self._client:
            try:
                # Verificar si el proceso está vivo antes de desconectar
                if hasattr(self._client, '_transport') and self._client._transport:
                    transport = self._client._transport
                    if hasattr(transport, '_process') and transport._process:
                        logger.info(f"Proceso CLI antes de disconnect: returncode={transport._process.returncode}")

                await self._client.disconnect()

                # Verificar si el proceso murió después de desconectar
                if hasattr(self._client, '_transport') and self._client._transport:
                    transport = self._client._transport
                    if hasattr(transport, '_process') and transport._process:
                        logger.info(f"Proceso CLI después de disconnect: returncode={transport._process.returncode}")

            except Exception as e:
                logger.warning(f"Error en disconnect: {e}")
            finally:
                self._client = None
                logger.info("Referencia al cliente SDK limpiada")

    async def query(self, content: str):
        """Envía una consulta al SDK.

        Args:
            content: Contenido de la consulta
        """
        if not self._client:
            raise RuntimeError("Cliente SDK no conectado")
        await self._client.query(content)

    async def receive_response(self):
        """Recibe la respuesta del SDK como un async iterator.

        Yields:
            Mensajes del SDK (AssistantMessage, ResultMessage, etc.)
        """
        if not self._client:
            raise RuntimeError("Cliente SDK no conectado")
        async for msg in self._client.receive_response():
            yield msg

    async def interrupt(self):
        """Interrumpe la consulta actual del SDK."""
        if self._client:
            await self._client.interrupt()

    @property
    def transport(self):
        """Retorna el transporte del SDK para envío directo de mensajes."""
        if self._client and hasattr(self._client, '_transport'):
            return self._client._transport
        return None

    @property
    def is_connected(self) -> bool:
        """Verifica si el cliente está conectado."""
        return self._client is not None
