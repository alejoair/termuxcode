"""Módulo para preprocesamiento y filtrado de mensajes del historial.

Este módulo transforma los mensajes del historial antes de reconstruirlos en el prompt,
aplicando filtros como truncado de tool results, resumen de mensajes largos, etc.
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class FilterConfig:
    """Configuración de filtros para el preprocesamiento de mensajes.

    Atributos:
        max_tool_result_length: Longitud máxima en caracteres para tool_result.
            Si es None, no se trunca.
        max_assistant_length: Longitud máxima para mensajes de assistant.
            Si es None, no se trunca.
        truncate_strategy: Cómo truncar el contenido.
            - "cut": Cortar directamente
            - "ellipsis": Agregar "..." al final
            - "summary": Resumir con indicador de truncado
        filter_messages_by_type: Si True, permite filtrar tipos de mensajes.
            (ej. excluir messages antiguos de tool_result)
    """
    max_tool_result_length: int | None = 500
    max_assistant_length: int | None = None
    truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis"
    filter_messages_by_type: bool = False


def truncate_text(
    text: str,
    max_length: int | None,
    strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis"
) -> str:
    """Trunca un texto según la estrategia especificada.

    Args:
        text: Texto a truncar
        max_length: Longitud máxima. Si es None, no se trunca.
        strategy: Estrategia de truncado:
            - "cut": Corta directamente
            - "ellipsis": Corta y agrega "..."
            - "summary": Corta y agrega "[truncado: X caracteres]"

    Returns:
        Texto truncado o original si no necesita truncado
    """
    if max_length is None or len(text) <= max_length:
        return text

    truncated = text[:max_length]

    if strategy == "cut":
        return truncated
    elif strategy == "ellipsis":
        return f"{truncated}..."
    elif strategy == "summary":
        return f"{truncated}... [truncado de {len(text)} caracteres]"
    else:
        return truncated


def preprocess_message(
    msg: dict[str, Any],
    config: FilterConfig
) -> dict[str, Any]:
    """Aplica filtros a un mensaje individual.

    Args:
        msg: Mensaje del historial con 'role' y 'content'
        config: Configuración de filtros

    Returns:
        Mensaje transformado (se mantiene la estructura original)
    """
    role = msg.get("role", "")
    content = msg.get("content", "")

    # Truncar tool_result
    if role == "tool_result" and config.max_tool_result_length:
        content_str = str(content)
        truncated = truncate_text(
            content_str,
            config.max_tool_result_length,
            config.truncate_strategy
        )
        return {"role": role, "content": truncated}

    # Truncar assistant
    if role == "assistant" and config.max_assistant_length:
        content_str = str(content)
        truncated = truncate_text(
            content_str,
            config.max_assistant_length,
            config.truncate_strategy
        )
        return {"role": role, "content": truncated}

    # Otros roles no se modifican
    return msg


def preprocess_history(
    history: list[dict[str, Any]],
    config: FilterConfig
) -> list[dict[str, Any]]:
    """Aplica filtros a todo el historial de conversación.

    Esta función transforma los mensajes antes de reconstruirlos en el prompt,
    controlando el tamaño y contenido de cada tipo de mensaje.

    Args:
        history: Lista de mensajes del historial
        config: Configuración de filtros

    Returns:
        Historial transformado con filtros aplicados

    Example:
        >>> config = FilterConfig(max_tool_result_length=300)
        >>> filtered = preprocess_history(history, config)
        >>> prompt = build_prompt(filtered, new_message)
    """
    filtered = []

    for msg in history:
        processed = preprocess_message(msg, config)
        filtered.append(processed)

    return filtered


def estimate_prompt_size(
    history: list[dict[str, Any]],
    new_message: str = ""
) -> dict[str, Any]:
    """Estima el tamaño del prompt reconstruido.

    Útil para evaluar si es necesario aplicar filtros más agresivos.

    Args:
        history: Historial de mensajes
        new_message: Nuevo mensaje a agregar

    Returns:
        Dict con estadísticas del tamaño:
            - character_count: Total de caracteres
            - line_count: Total de líneas
            - message_breakdown: Cantidad de mensajes por tipo
            - tool_result_total_size: Tamaño total de todos los tool_result
    """
    # Simular reconstrucción básica
    prompt_parts = []

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            prompt_parts.append(f"User: {content}\n\n")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}\n\n")
        elif role == "tool_use":
            # Simular el formato de build_prompt
            if isinstance(content, dict):
                tool_name = content.get("name", "unknown")
                tool_input = content.get("input", "")
                prompt_parts.append(f"Assistant: [Used tool: {tool_name}, input: {tool_input}]\n\n")
            else:
                prompt_parts.append(f"Assistant: [Used tool: unknown]\n\n")
        elif role == "tool_result":
            prompt_parts.append(f"[Tool result: {content}]\n\n")

    # Agregar nuevo mensaje
    prompt_parts.append(f"User: {new_message}\n\nAssistant:")

    full_prompt = "".join(prompt_parts)

    # Calcular estadísticas
    message_breakdown = {}
    for msg in history:
        role = msg.get("role", "")
        message_breakdown[role] = message_breakdown.get(role, 0) + 1

    tool_result_total_size = 0
    for msg in history:
        if msg.get("role") == "tool_result":
            tool_result_total_size += len(str(msg.get("content", "")))

    return {
        "character_count": len(full_prompt),
        "line_count": full_prompt.count("\n"),
        "message_breakdown": message_breakdown,
        "tool_result_total_size": tool_result_total_size,
    }


def suggest_config(
    stats: dict[str, Any],
    target_max_chars: int | None = 50000
) -> FilterConfig:
    """Sugiere una configuración de filtros basada en estadísticas.

    Args:
        stats: Estadísticas retornadas por estimate_prompt_size()
        target_max_chars: Tamaño objetivo máximo del prompt

    Returns:
        Configuración sugerida de filtros
    """
    current_size = stats["character_count"]

    if target_max_chars is None or current_size <= target_max_chars:
        # No necesita filtros
        return FilterConfig()

    # Calcular reducción necesaria
    reduction_factor = target_max_chars / current_size

    # El tool_result suele ser el principal contributor
    tool_result_size = stats["tool_result_total_size"]
    if tool_result_size > 0:
        # Ajustar max_tool_result_length proporcionalmente
        suggested_max = int(tool_result_size * reduction_factor * 0.8)
        return FilterConfig(max_tool_result_length=max(100, suggested_max))

    # Si no hay tool_result, ajustar assistant length
    return FilterConfig(max_assistant_length=int(1000 * reduction_factor))


class HistoryPreprocessor:
    """Clase para preprocesar historial con configuración persistente.

    Útil para mantener configuración entre múltiples llamadas.
    """

    def __init__(self, config: FilterConfig | None = None):
        """Inicializa el preprocesador.

        Args:
            config: Configuración de filtros. Si es None, usa defaults.
        """
        self.config = config or FilterConfig()

    def process(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Procesa el historial con la configuración actual.

        Args:
            history: Historial de mensajes

        Returns:
            Historial filtrado
        """
        return preprocess_history(history, self.config)

    def update_config(self, **kwargs) -> None:
        """Actualiza la configuración del preprocesador.

        Args:
            **kwargs: Parámetros de FilterConfig a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def estimate_size(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Estima el tamaño del prompt con el historial dado.

        Returns:
            Estadísticas de tamaño
        """
        return estimate_prompt_size(history)
