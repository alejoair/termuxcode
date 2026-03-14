"""Respuestas estructuradas del LLM con metadata para gamificación"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal


# Schema JSON para respuestas estructuradas
STRUCTURED_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "next_suggested_immediate_action": {"type": "string"},
                "is_useful_to_record_in_history": {"type": "boolean"},
                "advances_current_task": {"type": "boolean"},
                "task_phase": {
                    "type": "string",
                    "enum": ["planificacion", "implementacion", "testing", "debugging", "analisis", "otro"]
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "requires_context_refresh": {"type": "boolean"},
                "related_files": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["next_suggested_immediate_action", "is_useful_to_record_in_history", "advances_current_task", "task_phase"],
            "additionalProperties": False
        }
    },
    "required": ["response", "metadata"],
    "additionalProperties": False
}

# Prompt template para estructurar respuestas
STRUCTURED_RESPONSE_PROMPT_TEMPLATE = """
IMPORTANTE: Tu respuesta debe ser estructurada con la siguiente información:

1. **response**: Tu respuesta principal (texto claro y útil)
2. **metadata**: Información adicional sobre tu respuesta:
   - **next_suggested_immediate_action**: Qué acción debe realizar el usuario a continuación (ej. "leer archivo X", "ejecutar comando Y", "revisar documentación")
   - **is_useful_to_record_in_history**: true si este mensaje es útil guardar en el historial, false si es solo small talk
   - **advances_current_task**: true si esta respuesta aporta progreso real a la tarea actual
   - **task_phase**: Fase de la tarea actual (planificacion/implementacion/testing/debugging/analisis/otro)
   - **confidence** (opcional): Confianza en tu respuesta (0.0 a 1.0)
   - **requires_context_refresh** (opcional): true si se necesita recargar archivos del proyecto
   - **related_files** (opcional): Lista de archivos relevantes mencionados

El sistema usará esta metadata para:
- Filtrar mensajes que no aportan valor (ahorrar espacio en historial)
- Sugerir próximas acciones automáticamente
- Rastrear progreso por fases de tarea
- Gamificación basada en productividad

Responde de manera natural y conversacional, pero asegúrate de incluir la metadata correcta.
"""


@dataclass
class ResponseMetadata:
    """Metadata de una respuesta estructurada"""
    next_suggested_immediate_action: str
    is_useful_to_record_in_history: bool
    advances_current_task: bool
    task_phase: Literal["planificacion", "implementacion", "testing", "debugging", "analisis", "otro"]
    confidence: float | None = None
    requires_context_refresh: bool = False
    related_files: list[str] = field(default_factory=list)


@dataclass
class StructuredResponse:
    """Respuesta estructurada del LLM"""
    response: str
    metadata: ResponseMetadata

    @property
    def xp_bonus(self) -> int:
        """XP bonus basado en metadata"""
        bonus = 0

        if self.metadata.advances_current_task:
            bonus += 10  # XP por avanzar tarea

        # XP extra por fases específicas
        phase_bonus = {
            "implementacion": 5,
            "debugging": 3,
            "testing": 4,
            "planificacion": 3,
            "analisis": 2,
            "otro": 1
        }
        bonus += phase_bonus.get(self.metadata.task_phase, 1)

        # XP extra por sugerencias específicas
        if self.metadata.next_suggested_immediate_action:
            # XP por tener una sugerencia útil
            action_lower = self.metadata.next_suggested_immediate_action.lower()
            if any(word in action_lower for word in ["leer", "read", "ejecutar", "run", "revisar", "review", "modificar", "modify", "crear", "create"]):
                bonus += 2

        # XP por alta confianza
        if self.metadata.confidence and self.metadata.confidence >= 0.9:
            bonus += 3

        return bonus

    @property
    def should_save_to_history(self) -> bool:
        """Si guardar en historial"""
        return self.metadata.is_useful_to_record_in_history


def parse_structured_output(data: dict[str, Any] | None) -> StructuredResponse | None:
    """
    Parsear structured_output del SDK

    Args:
        data: El campo structured_output de ResultMessage

    Returns:
        StructuredResponse o None si data es None o inválido
    """
    if not data or not isinstance(data, dict):
        return None

    try:
        response = data.get("response", "")
        metadata_data = data.get("metadata", {})

        if not metadata_data or not isinstance(metadata_data, dict):
            return None

        metadata = ResponseMetadata(
            next_suggested_immediate_action=metadata_data.get("next_suggested_immediate_action", ""),
            is_useful_to_record_in_history=metadata_data.get("is_useful_to_record_in_history", True),
            advances_current_task=metadata_data.get("advances_current_task", True),
            task_phase=metadata_data.get("task_phase", "otro"),
            confidence=metadata_data.get("confidence"),
            requires_context_refresh=metadata_data.get("requires_context_refresh", False),
            related_files=metadata_data.get("related_files", [])
        )

        return StructuredResponse(response=response, metadata=metadata)
    except Exception:
        return None


def format_phase_badge(phase: str) -> str:
    """Formato de badge para fase de tarea"""
    icons = {
        "planificacion": "🔵",
        "implementacion": "🟡",
        "testing": "🟢",
        "debugging": "🔴",
        "analisis": "🟣",
        "otro": "⚪"
    }
    icon = icons.get(phase, "⚪")
    return f"[{icon} {phase.upper()}]"


def format_advances_badge(advances: bool) -> str | None:
    """Formato de badge para 'avanza tarea'"""
    if advances:
        return "[✓ AVANZA TAREA]"
    return None


def format_suggestion_box(suggestion: str) -> str:
    """Formato de caja de sugerencia"""
    return f"""
─── SUGERENCIA ──────────────────────────────────────────────
🎯 {suggestion}
────────────────────────────────────────────────────────────
[Press Tab to execute this suggestion]
"""
