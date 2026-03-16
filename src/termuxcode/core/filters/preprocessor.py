"""Wrapper para mantener compatibilidad con HistoryPreprocessor."""

from typing import Literal
from termuxcode.core.filters.manager import FilterManager
from termuxcode.core.filters.estimator import estimate_prompt_size


class HistoryPreprocessor:
    """Clase para preprocesar historial con configuración persistente.

    Útil para mantener configuración entre múltiples llamadas.

    Envuelve FilterManager para compatibilidad con código existente.
    """

    def __init__(
        self,
        filter_by_useful: Literal[None, False, True] = True,
        max_tool_result_length: int | None = 500,
        max_assistant_length: int | None = None,
        truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
    ):
        """Inicializa el preprocesador.

        Args:
            filter_by_useful: Controla el filtro de mensajes útiles
            max_tool_result_length: Longitud máxima para tool_result
            max_assistant_length: Longitud máxima para assistant
            truncate_strategy: Estrategia de truncado
        """
        self._filter_by_useful = filter_by_useful
        self._max_tool_result_length = max_tool_result_length
        self._max_assistant_length = max_assistant_length
        self._truncate_strategy = truncate_strategy
        self._manager = FilterManager(
            filter_by_useful,
            max_tool_result_length,
            max_assistant_length,
            truncate_strategy,
        )

    def process(self, history: list[dict]) -> list[dict]:
        """Procesa el historial con la configuración actual.

        Args:
            history: Historial de mensajes

        Returns:
            Historial filtrado
        """
        return self._manager.apply(history)

    def update_config(self, **kwargs) -> None:
        """Actualiza la configuración del preprocesador.

        Args:
            **kwargs: Parámetros a actualizar (filter_by_useful, max_tool_result_length, etc.)
        """
        if 'filter_by_useful' in kwargs:
            self._filter_by_useful = kwargs['filter_by_useful']
        if 'max_tool_result_length' in kwargs:
            self._max_tool_result_length = kwargs['max_tool_result_length']
        if 'max_assistant_length' in kwargs:
            self._max_assistant_length = kwargs['max_assistant_length']
        if 'truncate_strategy' in kwargs:
            self._truncate_strategy = kwargs['truncate_strategy']

        # Recrear manager con nueva configuración
        self._manager = FilterManager(
            self._filter_by_useful,
            self._max_tool_result_length,
            self._max_assistant_length,
            self._truncate_strategy,
        )

    def estimate_size(self, history: list[dict]) -> dict:
        """Estima el tamaño del prompt con el historial dado.

        Returns:
            Estadísticas de tamaño
        """
        return estimate_prompt_size(history)
