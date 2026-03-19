"""Filtro que aplica truncamiento exponencial basado en porcentajes."""

from typing import Literal


class ExponentialTruncateFilter:
    """Aplica truncamiento exponencial basado en porcentaje del contenido.

    Los mensajes más recientes se mantienen más completos que los antiguos.
    El porcentaje del contenido mantenido decrece exponencialmente con la distancia,
    pero nunca baja de `min_percent` (piso mínimo).

    Fórmula:
        distance = total - 1 - index  (0 = más reciente)
        capped_distance = min(distance, full_content_distance)
        percent = base_percent - (capped_distance * decay_per_message)
        percent = max(percent, min_percent)

    Ejemplo con defaults (base=100%, decay=7%, min=30%, full_distance=10):
        - Últimos 10 mensajes (distance 0-9): 100% - (distance × 7%)
          * distance 0: 100%
          * distance 5:  100% - 35% = 65%
          * distance 9:  100% - 63% = 37%
        - Distance 10+: igual que 9 = 37% (capped, pero > min=30%)
        - Distance muy grande: 30% (piso mínimo)

    Args:
        base_percent: Porcentaje inicial para mensajes recientes (0-100).
        decay_per_message: Cuánto porcentaje se pierde por mensaje de distancia (0-100).
        min_percent: Porcentaje mínimo (piso). Nunca se trunca por debajo de esto.
        full_content_distance: Distancia en mensajes que mantienen contenido completo
            antes de empezar a decaer.
        truncate_strategy: Cómo truncar el contenido:
            - "cut": Cortar directamente
            - "ellipsis": Agregar "..." al final
            - "summary": Agregar indicador con porcentaje mantenido
    """

    def __init__(
        self,
        base_percent: float = 100.0,
        decay_per_message: float = 7.0,
        min_percent: float = 30.0,
        full_content_distance: int = 10,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        self.base_percent = base_percent
        self.decay_per_message = decay_per_message
        self.min_percent = min_percent
        self.full_content_distance = full_content_distance
        self.truncate_strategy = truncate_strategy

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica truncamiento exponencial basado en porcentaje a todos los mensajes."""
        total = len(messages)
        if total == 0:
            return messages

        result = []
        for index, msg in enumerate(messages):
            distance = total - 1 - index

            # Calcular el porcentaje permitido para este mensaje
            percent = self._calculate_percent(distance)

            result.append(self._truncate_message(msg, percent))
        return result

    def _calculate_percent(self, distance: int) -> float:
        """Calcula el porcentaje permitido según la distancia del mensaje.

        Args:
            distance: Distancia desde el mensaje más reciente (0 = más reciente)

        Returns:
            Porcentaje a mantener (0-100)
        """
        # Mensajes dentro de full_content_distance mantienen 100%
        if distance < self.full_content_distance:
            return 100.0

        # Calcular distancia desde donde empieza el decaimiento
        decay_distance = distance - self.full_content_distance

        # Aplicar decaimiento
        percent = self.base_percent - (decay_distance * self.decay_per_message)

        # Aplicar piso mínimo
        return max(percent, self.min_percent)

    def _truncate_message(self, msg: dict, percent: float) -> dict:
        """Trunca un mensaje individual al porcentaje especificado.

        Args:
            msg: Mensaje a truncar
            percent: Porcentaje del contenido a mantener (0-100)

        Returns:
            Mensaje truncado (si aplica) o original
        """
        content = msg.get("content", "")
        content_str = str(content)

        original_length = len(content_str)

        # Si el porcentaje es 100% o el mensaje está vacío/corto, no truncar
        if percent >= 100.0 or original_length == 0:
            return msg

        # Calcular cuántos caracteres mantener
        max_length = max(1, int(original_length * percent / 100))

        if original_length <= max_length:
            return msg

        truncated = content_str[:max_length]
        new_content = self._apply_strategy(truncated, content_str, percent)
        return {
            "role": msg.get("role", ""),
            "content": new_content,
        }

    def _apply_strategy(self, truncated: str, original: str, percent: float) -> str:
        """Aplica la estrategia de truncado.

        Args:
            truncated: Texto truncado
            original: Texto original
            percent: Porcentaje mantenido

        Returns:
            Texto con la estrategia aplicada
        """
        if self.truncate_strategy == "cut":
            return truncated
        elif self.truncate_strategy == "ellipsis":
            return f"{truncated}..."
        elif self.truncate_strategy == "summary":
            return f"{truncated}... [mantenido {percent:.0f}% de {len(original)} chars]"
        return truncated
