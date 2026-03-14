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
                # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO (REQUERIDOS)
                "user_prompt_objective": {"type": "string"},
                "user_prompt_classification": {
                    "type": "string",
                    "enum": [
                        "single_task",       # Tarea única específica (ej. "crear un archivo", "ejecutar un comando")
                        "research",          # Investigación/análisis (ej. "cómo funciona X", "buscar patrones")
                        "plan",             # Planificación/estrategia (ej. "diseñar arquitectura", "crear plan de implementación")
                        "implementation",   # Implementación de código complejo (múltiples archivos, cambios grandes)
                        "debugging",        # Corrección de errores (ej. "fix bug X", "investigar error")
                        "testing",          # Escribir/pruebas (ej. "agregar tests", "verificar funcionalidad")
                        "code_review",      # Revisión de código (ej. "revisar PR", "mejorar código existente")
                        "documentation",    # Escribir documentación (ej. "agregar comentarios", "crear README")
                        "refactoring",      # Refactorización de código (mejorar estructura, performance)
                        "explanation",      # Explicación de conceptos (ej. "explicar X", "cómo funciona Y")
                        "offtopic",         # Small talk, saludos, conversación casual
                        "meta"              # Metadiscusión sobre el trabajo (ej. "qué hice bien", "mejorar feedback")
                    ]
                },
                # METADATA DE TU RESPUESTA
                "next_suggested_immediate_action": {"type": "string"},
                "is_useful_to_record_in_history": {"type": "boolean"},
                "advances_current_task": {"type": "boolean"},
                "task_phase": {
                    "type": "string",
                    "enum": ["planificacion", "implementacion", "testing", "debugging", "analisis", "otro"]
                },
                "related_files": {"type": "array", "items": {"type": "string"}},
                # NUEVOS CAMPOS: Reflexión y objetivos personales
                "self_reflection": {"type": "string"},
                "personal_goal": {"type": "string"}
            },
            "required": ["user_prompt_objective", "user_prompt_classification", "next_suggested_immediate_action", "is_useful_to_record_in_history", "advances_current_task", "task_phase"],
            "additionalProperties": False
        }
    },
    "required": ["response", "metadata"],
    "additionalProperties": False
}

# NOTA: El SDK maneja el structured output internamente a través de output_format
# No necesitamos un prompt template explícito para instruir al modelo


@dataclass
class ResponseMetadata:
    """Metadata de una respuesta estructurada"""
    # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO (REQUERIDOS)
    user_prompt_objective: str
    user_prompt_classification: Literal[
        "single_task",
        "research",
        "plan",
        "implementation",
        "debugging",
        "testing",
        "code_review",
        "documentation",
        "refactoring",
        "explanation",
        "offtopic",
        "meta"
    ]
    # METADATA DE TU RESPUESTA (REQUERIDOS)
    next_suggested_immediate_action: str
    is_useful_to_record_in_history: bool
    advances_current_task: bool
    task_phase: Literal["planificacion", "implementacion", "testing", "debugging", "analisis", "otro"]
    related_files: list[str] = field(default_factory=list)
    # NUEVOS CAMPOS: Reflexión y objetivos personales (OPCIONALES)
    self_reflection: str = ""
    personal_goal: str = ""


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

        return bonus

    @property
    def should_save_to_history(self) -> bool:
        """Si guardar en historial"""
        return self.metadata.is_useful_to_record_in_history


def parse_structured_output(data: dict[str, Any] | None) -> StructuredResponse | None:
    """
    Parsear structured_output del SDK.

    El SDK ya valida el JSON contra el esquema, así que asumimos que
    el formato es correcto y solo necesitamos mapearlo a StructuredResponse.

    Args:
        data: El campo structured_output de ResultMessage (dict válido ya validado por SDK)

    Returns:
        StructuredResponse o None si data es None
    """
    if not data or not isinstance(data, dict):
        return None

    # El SDK ya validó el formato, solo mapeamos directamente
    response = data.get("response", "")
    metadata_data = data.get("metadata", {})

    if not metadata_data or not isinstance(metadata_data, dict):
        return None

    metadata = ResponseMetadata(
        # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO (REQUERIDOS)
        user_prompt_objective=metadata_data.get("user_prompt_objective", ""),
        user_prompt_classification=metadata_data.get("user_prompt_classification", "single_task"),
        # METADATA DE TU RESPUESTA (REQUERIDOS)
        next_suggested_immediate_action=metadata_data.get("next_suggested_immediate_action", ""),
        is_useful_to_record_in_history=metadata_data.get("is_useful_to_record_in_history", True),
        advances_current_task=metadata_data.get("advances_current_task", True),
        task_phase=metadata_data.get("task_phase", "otro"),
        related_files=metadata_data.get("related_files", []),
        # NUEVOS CAMPOS: Reflexión y objetivos personales (OPCIONALES)
        self_reflection=metadata_data.get("self_reflection", ""),
        personal_goal=metadata_data.get("personal_goal", "")
    )

    return StructuredResponse(response=response, metadata=metadata)


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


def format_classification_badge(classification: str) -> str | None:
    """Formato de badge para clasificación del prompt del usuario"""
    icons = {
        "single_task": "🔧",
        "research": "🔍",
        "plan": "📋",
        "implementation": "🏗️",
        "debugging": "🐛",
        "testing": "✅",
        "code_review": "👀",
        "documentation": "📝",
        "refactoring": "♻️",
        "explanation": "💬",
        "offtopic": "💭",
        "meta": "🔄"
    }
    icon = icons.get(classification, "❓")
    return f"[{icon} {classification.upper()}]"


def format_suggestion_box(suggestion: str) -> str:
    """Formato de caja de sugerencia"""
    return f"""
─── SUGERENCIA ──────────────────────────────────────────────
🎯 {suggestion}
────────────────────────────────────────────────────────────
[Press Tab to execute this suggestion]
"""


def format_agent_feedback(
    last_reflection: str = "",
    personal_goal: str = "",
    goal_achieved: bool = False,
    goal_streak: int = 0,
    recent_achievements: list = None
) -> str:
    """Formato de feedback personalizado para el agente

    Este feedback se incluye en el prompt del agente para motiverlo.
    """
    if recent_achievements is None:
        recent_achievements = []

    feedback = "╔════════════════════════════════════════════════════╗\n"
    feedback += "║         FEEDBACK PERSONALIZADO                    ║\n"
    feedback += "╚════════════════════════════════════════════════════╝\n\n"

    # Reflexión del agente
    if last_reflection:
        feedback += "📝 Tu reflexión anterior:\n"
        feedback += f"   {last_reflection}\n\n"

    # Objetivo personal
    if personal_goal:
        status_icon = "✅" if goal_achieved else "⏳"
        status_text = "CUMPLIDO" if goal_achieved else "EN PROGRESO"
        feedback += f"🎯 Objetivo personal: [{status_icon} {status_text}]\n"
        feedback += f"   {personal_goal}\n"

        if goal_streak > 0:
            feedback += f"   🔥 Streak: {goal_streak} objetivos cumplidos consecutivamente\n\n"
        else:
            feedback += "\n"

    # Logros recientes
    if recent_achievements:
        feedback += "🏆 Logros recientes:\n"
        for ach in recent_achievements[:3]:  # Máx 3 logros recientes
            feedback += f"   • {ach.name}\n"
        feedback += "\n"

    feedback += "════════════════════════════════════════════════════\n"
    feedback += "¡Felicidades por tu progreso! Continúa\n"
    feedback += "trabajando en tu fase actual y sigue\n"
    feedback += "esforzándote en tus objetivos personales.\n"
    feedback += "════════════════════════════════════════════════════\n"

    return feedback
