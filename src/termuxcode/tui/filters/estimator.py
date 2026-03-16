"""Funciones para estimar el tamaño del prompt."""

from typing import Any


def estimate_prompt_size(history: list[dict[str, Any]], new_message: str = "") -> dict[str, Any]:
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
