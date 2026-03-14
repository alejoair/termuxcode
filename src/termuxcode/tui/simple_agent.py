"""Agente stateless para consultas simples sin historial ni contexto

Este módulo proporciona un agente simple para consultas puntuales como:
- Validaciones de cambios de fase
- Preguntas rápidas sin contexto
- Auditorías de código
- Cualquier consulta que no requiera historial ni persistencia

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
        include_tools: bool = False,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Ejecutar una consulta simple sin historial

        Args:
            prompt: Texto de la consulta
            model: Modelo a usar (sonnet, opus, haiku). Si es None, usa default_model
            include_tools: Si incluir herramientas en el query
            timeout: Timeout en segundos
            max_tokens: Máximo de tokens de respuesta

        Returns:
            Respuesta del agente como texto
        """
        model = model or self.default_model

        # Opciones del agente
        options = ClaudeAgentOptions(
            permission_mode=self.permission_mode,
            cwd=self.cwd,
            include_partial_messages=False,
            model=model,
            setting_sources=["project"] if include_tools else [],
        )

        # Ejecutar query
        response_parts = []
        try:
            async for message in query(prompt=prompt, options=options, timeout=timeout):
                await self._process_message(message, response_parts, include_tools)
        except Exception as e:
            if self.chat_log:
                self.chat_log.write(f"[red]Error en query stateless: {e}[/red]")
            raise

        return "".join(response_parts)

    async def query_with_validation(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        include_tools: bool = False,
    ) -> str:
        """Ejecutar consulta con prompt del sistema personalizado

        Args:
            prompt: Texto de la consulta
            model: Modelo a usar
            system_prompt: Prompt del sistema (rol/instrucciones)
            include_tools: Si incluir herramientas

        Returns:
            Respuesta del agente
        """
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        return await self.query(full_prompt, model=model, include_tools=include_tools)

    async def validate_phase_change(
        self,
        validation_prompt: str,
        model: str = MODEL_SONNET,
    ) -> str:
        """Validar un cambio de fase (caso de uso específico)

        Args:
            validation_prompt: Prompt de validación generado por el sistema
            model: Modelo a usar (por defecto sonnet para auditoría)

        Returns:
            Respuesta de validación
        """
        # Agregar contexto adicional para la validación
        system_prompt = """Eres un auditor de calidad de código y procesos.
Tu tarea es validar cambios de fase y proporcionar feedback constructivo."""

        result = await self.query_with_validation(
            prompt=validation_prompt,
            model=model,
            system_prompt=system_prompt,
            include_tools=False,
        )

        if self.chat_log:
            self.chat_log.write(f"[bold yellow]🔍 Validación:[/bold yellow]")
            self.chat_log.write(result)

        return result

    async def code_review(
        self,
        code: str,
        language: Optional[str] = None,
        focus: Optional[str] = None,
    ) -> str:
        """Hacer un code review rápido

        Args:
            code: Código a revisar
            language: Lenguaje de programación (opcional)
            focus: Foco de la revisión (ej. "seguridad", "performance", "estilo")

        Returns:
            Review del código
        """
        lang_suffix = f" en {language}" if language else ""
        focus_suffix = f". Enfócate en: {focus}" if focus else "."

        prompt = f"""Revisa este código{lang_suffix}{focus_suffix}

```{language or ''}
{code}
```

Proporciona:
1. Problemas encontrados (si hay)
2. Sugerencias de mejora
3. Calificación general (1-10)
"""

        return await self.query(prompt, model=self.MODEL_SONNET, include_tools=False)

    async def ask_question(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> str:
        """Hacer una pregunta rápida

        Args:
            question: Pregunta
            context: Contexto adicional (opcional)

        Returns:
            Respuesta
        """
        prompt = question
        if context:
            prompt = f"{context}\n\nPregunta: {question}"

        return await self.query(prompt, model=self.MODEL_HAIKU, include_tools=False)

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
