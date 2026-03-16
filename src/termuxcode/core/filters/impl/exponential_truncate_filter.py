"""Filtro que aplica truncamiento exponencial a todos los mensajes."""

from typing import Literal
from termuxcode.core.filters.base import MessageFilter


class ExponentialTruncateFilter(MessageFilter):
    """Aplica truncamiento exponencial a todos los mensajes.

    Los mensajes más recientes se mantienen más completos que los antiguos.
    La longitud permitida decrece exponencialmente con la distancia al final,
    pero nunca baja de `min_length` (piso mínimo).

    Fórmula:
        distance = total - 1 - index  (0 = más reciente)
        capped_distance = min(distance, max_decay_distance)
        length = base_length * (1.0 - capped_distance * decay)
        length = max(length, min_length)

    Ejemplo con defaults (base=2000, decay=0.08, min_length=200, max_decay_distance=10):
        - Mensaje más reciente (distance=0): 2000 chars
        - Distance 5:  2000 * (1 - 5*0.08)  = 2000 * 0.6  = 1200 chars
        - Distance 10: 2000 * (1 - 10*0.08) = 2000 * 0.2  = 400 chars
        - Distance 15: igual que 10 (capped) = 400 chars (> min_length=200)

    Args:
        base_length: Longitud máxima para el mensaje más reciente.
        decay: Factor de decaimiento por posición (0.0-1.0).
        min_length: Longitud mínima (piso). Nunca se trunca por debajo de esto.
        max_decay_distance: Distancia máxima para el decaimiento. Más allá de
            esta distancia el truncado ya no se reduce más.
        truncate_strategy: Cómo truncar el contenido:
            - "cut": Cortar directamente
            - "ellipsis": Agregar "..." al final
            - "summary": Agregar indicador con tamaño original
    """

    def __init__(
        self,
        base_length: int = 2000,
        decay: float = 0.08,
        min_length: int = 200,
        max_decay_distance: int = 10,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        self.base_length = base_length
        self.decay = decay
        self.min_length = min_length
        self.max_decay_distance = max_decay_distance
        self.truncate_strategy = truncate_strategy

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica truncamiento exponencial a todos los mensajes."""
        total = len(messages)
        if total == 0:
            return messages

        result = []
        for index, msg in enumerate(messages):
            distance = total - 1 - index
            capped_distance = min(distance, self.max_decay_distance)
            allowed = self.base_length * (1.0 - capped_distance * self.decay)
            allowed = max(allowed, self.min_length)
            result.append(self._truncate_message(msg, int(allowed)))
        return result

    def _truncate_message(self, msg: dict, max_length: int) -> dict:
        """Trunca un mensaje individual si excede max_length.

        Args:
            msg: Mensaje a truncar
            max_length: Longitud máxima permitida

        Returns:
            Mensaje truncado (si aplica) o original
        """
        content = msg.get("content", "")
        content_str = str(content)

        if len(content_str) <= max_length:
            return msg

        truncated = content_str[:max_length]
        new_content = self._apply_strategy(truncated, content_str)
        return {
            "role": msg.get("role", ""),
            "content": new_content,
            "is_useful": msg.get("is_useful", True),
        }

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
