"""Agente stateless para consultas simples sin historial ni contexto

Este módulo proporciona un agente simple para consultas puntuales.
El agente es "stateless": no mantiene ningún estado entre llamadas,
no tiene historial, y no se integra con el sistema de sesiones.
"""
from __future__ import annotations

from claude_agent_sdk import query, ClaudeAgentOptions
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .chat import ChatLog


class SimpleAgent:
    """Agente stateless para consultas simples sin historial

    Este agente está diseñado para consultas rápidas y validaciones
    que no requieren mantener contexto entre llamadas.
    """

    # Modelos disponibles
    MODEL_SONNET = "sonnet"
    MODEL_OPUS = "opus"
    MODEL_HAIKU = "haiku"

    def __init__(
        self,
        chat_log: Optional['ChatLog'] = None,
        cwd: Optional[str] = None,
        default_model: str = MODEL_SONNET,
        permission_mode: str = "bypassPermissions",
    ):
        """Inicializar agente stateless

        Args:
            chat_log: ChatLog opcional para mostrar respuestas
            cwd: Directorio de trabajo para las herramientas
            default_model: Modelo por defecto (sonnet, opus, haiku)
            permission_mode: Modo de permisos para herramientas
        """
        self.chat_log = chat_log
        self.cwd = cwd
        self.default_model = default_model
        self.permission_mode = permission_mode

    async def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        include_tools: bool = False,
    ) -> str:
        """Ejecutar una consulta simple sin historial

        Args:
            prompt: Texto de la consulta
            model: Modelo a usar (sonnet, opus, haiku). Si es None, usa default_model
            system_prompt: Prompt del sistema opcional
            include_tools: Si incluir herramientas en el query

        Returns:
            Respuesta del agente como texto
        """
        model = model or self.default_model

        # Prepend system prompt si se proporciona
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        # Opciones del agente
        options = ClaudeAgentOptions(
            permission_mode=self.permission_mode,
            cwd=self.cwd,
            include_partial_messages=False,
            model=model,
            setting_sources=["project"] if include_tools else [],
        )

        # Ejecutar query (SDK query() solo acepta prompt, options, transport)
        response_parts = []
        try:
            async for message in query(prompt=prompt, options=options):
                await self._process_message(message, response_parts, include_tools)
        except Exception as e:
            if self.chat_log:
                self.chat_log.write(f"[red]Error en query stateless: {e}[/red]")
            raise

        return "".join(response_parts)

    async def query_structured(
        self,
        prompt: str,
        output_schema: dict,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Ejecutar query con structured output (JSON schema)

        Args:
            prompt: Prompt principal
            output_schema: JSON schema para la salida estructurada
            model: Modelo a usar (por defecto usa default_model)
            system_prompt: System prompt opcional

        Returns:
            Dict con la respuesta estructurada

        Raises:
            Exception: Si hay error en el query o parsing de respuesta
        """
        model = model or self.default_model

        # Prepend system prompt si se proporciona
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        # Opciones del agente con output format
        options = ClaudeAgentOptions(
            permission_mode=self.permission_mode,
            cwd=self.cwd,
            include_partial_messages=False,
            model=model,
            setting_sources=[],
            output_format={
                "type": "json_schema",
                "json_schema": output_schema,
            },
        )

        # Ejecutar query y extraer structured_output
        structured_result = None
        text_parts = []
        try:
            async for message in query(prompt=prompt, options=options):
                # Procesar para mostrar en chat log
                await self._process_message(message, text_parts, include_tools=False)

                # Extraer structured_output de ResultMessage
                msg_type = message.__class__.__name__
                if msg_type == "ResultMessage":
                    if hasattr(message, 'structured_output'):
                        structured_result = message.structured_output

        except Exception as e:
            if self.chat_log:
                self.chat_log.write(f"[red]Error en query_structured: {e}[/red]")
            raise

        if not structured_result:
            raise ValueError("No se recibió structured_output en la respuesta")

        return structured_result

    async def _process_message(
        self,
        message,
        response_parts: list[str],
        include_tools: bool,
    ) -> None:
        """Procesar mensaje del SDK"""
        msg_type = message.__class__.__name__

        if msg_type == "AssistantMessage":
            if hasattr(message, 'content') and isinstance(message.content, list):
                for block in message.content:
                    block_type = block.__class__.__name__

                    if block_type == "TextBlock":
                        text = block.text
                        response_parts.append(text)

                        if self.chat_log:
                            self.chat_log.write_assistant(text)

                    elif block_type == "ToolUseBlock" and include_tools:
                        if self.chat_log:
                            tool_input = str(block.input) if hasattr(block, 'input') else None
                            self.chat_log.write_tool(block.name, tool_input)

        elif msg_type == "UserMessage" and include_tools:
            if hasattr(message, 'content') and isinstance(message.content, list):
                for block in message.content:
                    if block.__class__.__name__ == "ToolResultBlock":
                        if self.chat_log:
                            self.chat_log.write_result(str(block.content))
