"""Filtro que trunca el contenido de mensajes."""

from typing import Literal
from termuxcode.core.filters.base import MessageFilter


class TruncateFilter(MessageFilter):
    """Trunca el contenido de tool_result y assistant messages.

    Controla el tamaño del prompt limitando la longitud de mensajes
    específicos que pueden ser muy largos.

    Args:
        max_tool_result_length: Longitud máxima en caracteres para tool_result.
            Si es None, no se trunca.
        max_assistant_length: Longitud máxima para mensajes de assistant.
            Si es None, no se trunca.
        truncate_strategy: Cómo truncar el contenido.
            - "cut": Cortar directamente
            - "ellipsis": Agregar "..." al final
            - "summary": Resumir con indicador de truncado
    """

    def __init__(
        self,
        max_tool_result_length: int | None = 500,
        max_assistant_length: int | None = None,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        self.max_tool_result_length = max_tool_result_length
        self.max_assistant_length = max_assistant_length
        self.truncate_strategy = truncate_strategy

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica truncado a los mensajes.

        Args:
            messages: Lista de mensajes a truncar

        Returns:
            Lista de mensajes con contenido truncado
        """
        if self.max_tool_result_length is None and self.max_assistant_length is None:
            return messages

        return [
            self._truncate_message(msg)
            for msg in messages
        ]

    def _truncate_message(self, msg: dict) -> dict:
        """Trunca un mensaje individual.

        Args:
            msg: Mensaje a truncar

        Returns:
            Mensaje truncado (si aplica) o original
        """
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "tool_result" and self.max_tool_result_length:
            content_str = str(content)
            if len(content_str) > self.max_tool_result_length:
                truncated = content_str[:self.max_tool_result_length]
                content = self._apply_strategy(truncated, content_str)
                return {"role": role, "content": content, "is_useful": msg.get("is_useful", True)}

        if role == "assistant" and self.max_assistant_length:
            content_str = str(content)
            if len(content_str) > self.max_assistant_length:
                truncated = content_str[:self.max_assistant_length]
                content = self._apply_strategy(truncated, content_str)
                return {"role": role, "content": content, "is_useful": msg.get("is_useful", True)}

        return msg

    def _apply_strategy(self, truncated: str, original: str) -> str:
        """Aplica la estrategia de truncado.

        Args:
            truncated: Texto truncado
            original: Texto original

        Returns:
            Texto con la estrategia aplicada
        """
        if self.truncate_strategy == "cut":
            return truncated
        elif self.truncate_strategy == "ellipsis":
            return f"{truncated}..."
        elif self.truncate_strategy == "summary":
            return f"{truncated}... [truncado de {len(original)} caracteres]"
        return truncated
