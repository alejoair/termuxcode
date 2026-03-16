"""Manager que ejecuta todos los filtros en orden."""

from typing import Literal
from termuxcode.core.filters.base import MessageFilter
from termuxcode.core.filters.impl.useful_filter import UsefulFilter
from termuxcode.core.filters.impl.exponential_truncate_filter import ExponentialTruncateFilter


class FilterManager:
    """Manager que aplica todos los filtros al historial.

    Los filtros se ejecutan en orden de registro. Por defecto:
    1. UsefulFilter - Elimina mensajes no útiles
    2. ExponentialTruncateFilter - Trunca contenido con decaimiento exponencial

    Puedes agregar filtros personalizados con register().
    """

    def __init__(
        self,
        # Configuración de UsefulFilter
        filter_by_useful: Literal[None, False, True] = True,
        # Configuración de ExponentialTruncateFilter
        base_length: int = 2000,
        decay: float = 0.08,
        min_length: int = 200,
        max_decay_distance: int = 10,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        """Inicializa el manager con filtros por defecto.

        Args:
            filter_by_useful: Controla el filtro de mensajes útiles
            base_length: Longitud máxima para el mensaje más reciente
            decay: Factor de decaimiento por posición
            min_length: Longitud mínima (piso del truncado)
            max_decay_distance: Distancia máxima para el decaimiento
            truncate_strategy: Estrategia de truncado (cut/ellipsis/summary)
        """
        self._filters: list[MessageFilter] = []
        self._register_default_filters(
            filter_by_useful,
            base_length,
            decay,
            min_length,
            max_decay_distance,
            truncate_strategy,
        )

    def _register_default_filters(
        self,
        filter_by_useful: Literal[None, False, True],
        base_length: int,
        decay: float,
        min_length: int,
        max_decay_distance: int,
        truncate_strategy: Literal["cut", "ellipsis", "summary"],
    ) -> None:
        """Registra los filtros incluidos por defecto."""
        # Útil primero para eliminar mensajes que no necesitamos truncar
        self.register(UsefulFilter(filter_by_useful))

        # Truncamiento exponencial para todos los mensajes
        self.register(ExponentialTruncateFilter(
            base_length,
            decay,
            min_length,
            max_decay_distance,
            truncate_strategy,
        ))

    def register(self, filter_instance: MessageFilter) -> None:
        """Registra un nuevo filtro.

        Los filtros se ejecutan en el orden de registro.
        Útil primero los filtros que eliminan mensajes para evitar trabajo innecesario.

        Args:
            filter_instance: Instancia del filtro a registrar
        """
        self._filters.append(filter_instance)

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica todos los filtros registrados a los mensajes.

        Args:
            messages: Lista de mensajes a filtrar

        Returns:
            Lista de mensajes filtrados/transformados
        """
        result = messages
        for filter_instance in self._filters:
            result = filter_instance.apply(result)
        return result

    def clear(self) -> None:
        """Elimina todos los filtros registrados."""
        self._filters.clear()
