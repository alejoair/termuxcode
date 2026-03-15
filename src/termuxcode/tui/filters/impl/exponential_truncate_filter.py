"""Filtro que aplica truncamiento exponencial a tool_result messages."""

from typing import Literal
from ..base import MessageFilter


class ExponentialTruncateFilter(MessageFilter):
    """Aplica truncamiento exponencial a tool_result messages.

    Los mensajes más recientes se mantienen más completos que los antiguos.
    La fórmula es: length = base_length * (1.0 - ((total - 1 - index) * decay))

    El más reciente (último) siempre tiene 100%, los anteriores se reducen.

    Args:
        base_length: Longitud base para el mensaje más reciente.
        decay: Factor de decremento por cada posición (0.2 = 20% menos).
        min_length: Longitud mínima garantizada para cualquier mensaje.
        truncate_strategy: Estrategia de truncado (cut, ellipsis, summary).
    """

    def __init__(
        self,
        base_length: int = 500,
        decay: float = 0.2,
        min_length: int = 100,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        self.base_length = base_length
        self.decay = decay
        self.min_length = min_length
        self.truncate_strategy = truncate_strategy

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica truncamiento exponencial."""
        # Primero identificar índices de tool_result
        tool_result_indices = [i for i, m in enumerate(messages)
                               if m.get("role") == "tool_result"]

        if not tool_result_indices:
            return messages

        # Calcular longitud para cada tool_result
        # El más reciente (último en la lista) tiene 100%
        total_tool_results = len(tool_result_indices)
        lengths = {}

        for pos, msg_index in enumerate(tool_result_indices):
            # Calcular distancia desde el más reciente
            # pos 0 = más antiguo, pos total-1 = más reciente
            distance = (total_tool_results - 1) - pos

            # Factor exponencial: más cercano al final = más alto
            factor = 1.0 - (distance * self.decay)
            factor = max(0.0, factor)  # No negativo

            length = int(self.base_length * factor)
            length = max(length, self.min_length)
            lengths[msg_index] = length

        # Aplicar truncado
        result = []
        for i, msg in enumerate(messages):
            if i in lengths:
                msg = self._truncate_message(msg, lengths[i])
            result.append(msg)

        return result

    def _truncate_message(self, msg: dict, max_len: int) -> dict:
        """Trunca un mensaje individual."""
        content = msg.get("content", "")
        content_str = str(content)

        if len(content_str) > max_len:
            truncated = content_str[:max_len]
            content = self._apply_strategy(truncated, content_str)
            return {"role": msg["role"], "content": content,
                    "is_useful": msg.get("is_useful", True)}

        return msg

    def _apply_strategy(self, truncated: str, original: str) -> str:
        """Aplica la estrategia de truncado."""
        if self.truncate_strategy == "cut":
            return truncated
        elif self.truncate_strategy == "ellipsis":
            return f"{truncated}..."
        elif self.truncate_strategy == "summary":
            return f"{truncated}... [truncado de {len(original)} caracteres]"
        return truncated
