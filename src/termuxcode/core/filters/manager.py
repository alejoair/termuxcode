"""Manager que ejecuta todos los filtros en orden."""

from typing import Literal
from termuxcode.core.filters.base import MessageFilter
from termuxcode.core.filters.impl.useful_filter import UsefulFilter
from termuxcode.core.filters.impl.truncate_filter import TruncateFilter
from termuxcode.core.filters.impl.exponential_truncate_filter import ExponentialTruncateFilter


class FilterManager:
    """Manager que aplica todos los filtros al historial.

    Los filtros se ejecutan en orden de registro. Por defecto:
    1. UsefulFilter - Elimina mensajes no útiles
    2. TruncateFilter - Trunca contenido largo (o ExponentialTruncateFilter si está activado)

    Puedes agregar filtros personalizados con register().
    """

    def __init__(
        self,
        # Configuración de UsefulFilter
        filter_by_useful: Literal[None, False, True] = True,
        # Configuración de TruncateFilter
        max_tool_result_length: int | None = 500,
        max_assistant_length: int | None = None,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
        # Configuración de ExponentialTruncateFilter
        exponential_truncate: bool = False,
        exp_base_length: int = 500,
        exp_decay: float = 0.2,
        exp_min_length: int = 100,
    ):
        """Inicializa el manager con filtros por defecto.

        Args:
            filter_by_useful: Controla el filtro de mensajes útiles
            max_tool_result_length: Longitud máxima para tool_result (sin modo exponencial)
            max_assistant_length: Longitud máxima para assistant
            truncate_strategy: Estrategia de truncado
            exponential_truncate: Si True, usa truncamiento exponencial en lugar de fijo
            exp_base_length: Longitud base para el mensaje más reciente (modo exponencial)
            exp_decay: Factor de decremento por cada posición (modo exponencial)
            exp_min_length: Longitud mínima garantizada (modo exponencial)
        """
        self._filters: list[MessageFilter] = []
        self._register_default_filters(
            filter_by_useful,
            max_tool_result_length,
            max_assistant_length,
            truncate_strategy,
            exponential_truncate,
            exp_base_length,
            exp_decay,
            exp_min_length,
        )

    def _register_default_filters(
        self,
        filter_by_useful: Literal[None, False, True],
        max_tool_result_length: int | None,
        max_assistant_length: int | None,
        truncate_strategy: Literal["cut", "ellipsis", "summary"],
        exponential_truncate: bool,
        exp_base_length: int,
        exp_decay: float,
        exp_min_length: int,
    ) -> None:
        """Registra los filtros incluidos por defecto."""
        # Útil primero para eliminar mensajes que no necesitamos truncar
        self.register(UsefulFilter(filter_by_useful))

        # Truncamiento: exponencial o fijo
        if exponential_truncate:
            self.register(ExponentialTruncateFilter(
                base_length=exp_base_length,
                decay=exp_decay,
                min_length=exp_min_length,
                truncate_strategy=truncate_strategy,
            ))
        else:
            self.register(TruncateFilter(
                max_tool_result_length,
                max_assistant_length,
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
