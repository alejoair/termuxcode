#!/usr/bin/env python3
"""Gestión del cliente SDK para Claude Agent."""

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import HookMatcher

from termuxcode.ws_config import logger


async def _dummy_hook(input_data, tool_use_id, context):
    """Hook requerido para que can_use_tool funcione en streaming mode."""
    return {"continue_": True}


class SDKClient:
    """Encapsula la inicialización y comunicación con el Claude SDK."""

    def __init__(self, resume_id: str = None, cwd: str = None, can_use_tool=None):
        """Inicializa el cliente SDK.

        Args:
            resume_id: ID de sesión para reanudar
            cwd: Directorio de trabajo
            can_use_tool: Callback async para aprobación de herramientas
        """
        self._client = None
        self.resume_id = resume_id
        self.cwd = cwd
        self._can_use_tool = can_use_tool
        self._session_id = None

    def _build_options(self, resume: bool = True) -> ClaudeAgentOptions:
        """Construye las opciones del agente.

        Args:
            resume: Si True, incluye resume_id en las opciones

        Returns:
            ClaudeAgentOptions configurado
        """
        options = ClaudeAgentOptions(
            permission_mode="acceptEdits",
            model="sonnet",
            setting_sources=["user", "project", "local"],
            stderr=lambda line: logger.error(f"Claude CLI stderr: {line}"),
        )

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
        """Conecta al SDK y retorna el session_id.

        Returns:
            El session_id del SDK o None si no está disponible

        Raises:
            Exception: Si falla la conexión y no hay resume_id
        """
        logger.info("Creando cliente SDK...")
        options = self._build_options()

        try:
            self._client = ClaudeSDKClient(options)
            await self._client.connect()
            logger.info("Cliente conectado")

            if hasattr(self._client, 'session_id') and self._client.session_id:
                self._session_id = self._client.session_id
                logger.info(f"Session ID obtenido: {self._session_id}")
                return self._session_id

        except Exception as e:
            if self.resume_id:
                logger.warning(f"Falló reanudar sesión {self.resume_id}: {e}. Creando nueva sesión.")
                self.resume_id = None
                options = self._build_options(resume=False)
                self._client = ClaudeSDKClient(options)
                await self._client.connect()
                logger.info("Nueva sesión creada")

                if hasattr(self._client, 'session_id') and self._client.session_id:
                    self._session_id = self._client.session_id
                    return self._session_id
            else:
                raise

        return None

    async def disconnect(self):
        """Desconecta el cliente SDK."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass

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
    def session_id(self) -> str | None:
        """Retorna el session_id actual del SDK."""
        if self._client and hasattr(self._client, 'session_id'):
            self._session_id = self._client.session_id
        return self._session_id

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
