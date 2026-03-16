"""Sistema de filtros para historial de mensajes.

Este módulo permite aplicar filtros al historial antes de pasarlo al LLM.
Los filtros pueden truncar contenido, eliminar mensajes no útiles, etc.

Uso:
    from termuxcode.core.filters import FilterManager

    manager = FilterManager(
        filter_by_useful=True,
        max_tool_result_length=500
    )
    filtered = manager.apply(history)
"""

from .base import MessageFilter
from .manager import FilterManager
from .impl.truncate_filter import TruncateFilter
from .impl.useful_filter import UsefulFilter
from .impl.exponential_truncate_filter import ExponentialTruncateFilter
from .preprocessor import HistoryPreprocessor

__all__ = [
    "MessageFilter",
    "FilterManager",
    "TruncateFilter",
    "UsefulFilter",
    "ExponentialTruncateFilter",
    "HistoryPreprocessor",
]


def estimate_prompt_size(history: list[dict], new_message: str = "") -> dict:
    """Estima el tamaño del prompt reconstruido.

    Args:
        history: Historial de mensajes
        new_message: Nuevo mensaje a agregar

    Returns:
        Dict con estadísticas del tamaño
    """
    from .estimator import estimate_prompt_size as _estimate
    return _estimate(history, new_message)
