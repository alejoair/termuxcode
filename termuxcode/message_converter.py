#!/usr/bin/env python3
"""Conversión de mensajes del SDK al formato WebSocket."""

from typing import Any

from claude_agent_sdk import AssistantMessage, ResultMessage, UserMessage

# Tipos de bloques de contenido
BLOCK_TYPES = {
    "TextBlock": "text",
    "ToolUseBlock": "tool_use",
    "ToolResultBlock": "tool_result",
    "ThinkingBlock": "thinking",
}

# Tools que se manejan de forma especial (no se envían como tool_use normal)
SPECIAL_TOOLS = {"AskUserQuestion"}


class MessageConverter:
    """Convierte mensajes del SDK al formato WebSocket."""

    @staticmethod
    def convert_assistant_message(msg: AssistantMessage, exclude_special_tools: bool = True) -> dict[str, Any]:
        """Convierte un AssistantMessage a diccionario WebSocket."""
        blocks = []

        for block in msg.content:
            block_type = block.__class__.__name__

            # Saltar tools especiales si se solicita
            if exclude_special_tools and block_type == "ToolUseBlock":
                if hasattr(block, 'name') and block.name in SPECIAL_TOOLS:
                    continue

            block_data = MessageConverter._convert_block(block, block_type)
            if block_data:
                blocks.append(block_data)

        return {
            "type": "assistant",
            "model": getattr(msg, "model", "unknown"),
            "blocks": blocks,
        }

    @staticmethod
    def _convert_block(block: Any, block_type: str) -> dict[str, Any] | None:
        """Convierte un bloque individual."""
        block_format = BLOCK_TYPES.get(block_type)

        if block_format == "text":
            return {"type": "text", "text": block.text}

        if block_format == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            }

        if block_format == "tool_result":
            return {
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": str(block.content)[:500],
                "is_error": block.is_error,
            }

        if block_format == "thinking":
            return {"type": "thinking", "thinking": block.thinking}

        return None

    @staticmethod
    def convert_result_message(msg: ResultMessage) -> dict[str, Any]:
        """Convierte un ResultMessage a diccionario WebSocket."""
        return {
            "type": "result",
            "stop_reason": msg.stop_reason,
            "num_turns": msg.num_turns,
            "is_error": msg.is_error,
        }

    @staticmethod
    def convert_user_message(msg: UserMessage) -> dict[str, Any]:
        """Convierte un UserMessage a diccionario WebSocket.

        Los UserMessage del SDK contienen ToolResultBlock con los resultados
        de las herramientas ejecutadas.
        """
        blocks = []

        for block in msg.content:
            block_type = block.__class__.__name__
            block_data = MessageConverter._convert_block(block, block_type)
            if block_data:
                blocks.append(block_data)

        return {
            "type": "user",
            "blocks": blocks,
        }

    @staticmethod
    def extract_ask_user_question(msg: AssistantMessage) -> list[tuple[str, list]]:
        """
        Extrae todos los AskUserQuestion de un AssistantMessage.
        Returns: Lista de (tool_use_id, questions) o lista vacía si no hay
        """
        questions = []
        for block in msg.content:
            if block.__class__.__name__ == "ToolUseBlock":
                if block.name == "AskUserQuestion":
                    input_data = block.input
                    question_list = input_data.get("questions", [])
                    questions.append((block.id, question_list))
        return questions
