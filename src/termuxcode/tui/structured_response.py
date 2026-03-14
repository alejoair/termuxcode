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
                "related_files": {"type": "array", "items": {"type": "string"}},
                # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO
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
                # NUEVOS CAMPOS: Reflexión y objetivos personales
                "self_reflection": {"type": "string"},
                "personal_goal": {"type": "string"},
                "long_term_goal": {"type": "string"},
                "long_term_goal_progress": {"type": "integer", "minimum": 0, "maximum": 100}
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

   **CLASIFICACIÓN DEL PROMPT DEL USUARIO:**
   - **user_prompt_objective**: Qué entiendes que es el objetivo del usuario con su prompt. Sé específico.
     Ejemplos:
     - "El usuario quiere crear un nuevo archivo de configuración"
     - "El usuario necesita entender cómo funciona el sistema de sesiones"
     - "El usuario está investigando un bug en la función X"

   - **user_prompt_classification**: Clasificación del tipo de prompt (DEBE ser una de estas opciones EXACTAS):
     • **single_task**: Tarea única específica (ej. "crear un archivo", "ejecutar un comando", "editar una función")
     • **research**: Investigación/análisis (ej. "cómo funciona X", "buscar patrones", "explicar arquitectura")
     • **plan**: Planificación/estrategia (ej. "diseñar arquitectura", "crear plan de implementación")
     • **implementation**: Implementación de código complejo (múltiples archivos, cambios grandes)
     • **debugging**: Corrección de errores (ej. "fix bug X", "investigar error")
     • **testing**: Escribir/pruebas (ej. "agregar tests", "verificar funcionalidad")
     • **code_review**: Revisión de código (ej. "revisar PR", "mejorar código existente")
     • **documentation**: Escribir documentación (ej. "agregar comentarios", "crear README")
     • **refactoring**: Refactorización de código (mejorar estructura, performance, limpiar código)
     • **explanation**: Explicación de conceptos (ej. "explicar X", "cómo funciona Y")
     • **offtopic**: Small talk, saludos, conversación casual (no relacionada con trabajo)
     • **meta**: Metadiscusión sobre el trabajo (ej. "qué hice bien", "mejorar feedback", "preguntar sobre progreso")

   **METADATA DE TU RESPUESTA:**
   - **next_suggested_immediate_action**: Qué acción debe realizar el usuario a continuación (ej. "leer archivo X", "ejecutar comando Y", "revisar documentación")
   - **is_useful_to_record_in_history**: true si este mensaje es útil guardar en el historial, false si es solo small talk
   - **advances_current_task**: true si esta respuesta aporta progreso real a la tarea actual
   - **task_phase**: Fase de la tarea actual (planificacion/implementacion/testing/debugging/analisis/otro)
   - **confidence** (opcional): Confianza en tu respuesta (0.0 a 1.0)
   - **requires_context_refresh** (opcional): true si se necesita recargar archivos del proyecto
   - **related_files** (opcional): Lista de archivos relevantes mencionados

   **REFLEXIÓN Y OBJETIVOS PERSONALES:**
   - **self_reflection** (opcional): Reflexiona sobre TU trabajo en este turno. Sé honesto:
     - ¿Qué hiciste bien?
     - ¿Qué podrías mejorar?
     - ¿Te equivoqué en algo? Ejemplo: "No leí el archivo completo antes de editarlo.
       La próxima vez siempre leeré primero."
     - ¿Aprendiste algo nuevo?

   - **personal_goal** (opcional): Un objetivo TANGIBLE para TU PRÓXIMO trabajo.
     Debe ser algo que TÚ puedas controlar y ejecutar.
     Ejemplos:
     - "Leer siempre el archivo completo antes de hacer ediciones"
     - "Probar siempre con `python -m py_compile` después de editar"
     - "Usar nombres de variables más descriptivos"
     - "Planificar en comentarios antes de implementar"
     - "Verificar con Glob/Grep antes de crear archivos nuevos"

   - **long_term_goal** (opcional): Un objetivo de LARGO PLAZO que quieras alcanzar (múltiples turnos).
     Ejemplos:
     - "Reducir errores de edición a menos de 5%"
     - "Hacer 10 commits seguidos sin errores"
     - "Alcanzar 95% de confianza promedio"
     - "Probar siempre después de cada cambio"

   - **long_term_goal_progress** (opcional): Progreso del objetivo a largo plazo (0-100).
     Actualiza este valor cada turno basado en tu progreso.

El sistema usará esta metadata para:
- Clasificar los prompts del usuario para optimizar el historial (ej. no pasar mucho historial para offtopic)
- Filtrar mensajes que no aportan valor (ahorrar espacio en historial)
- Sugerir próximas acciones automáticamente
- Rastrear progreso por fases de tarea
- Gamificación basada en productividad
- **Darte feedback sobre tu progreso personal**

IMPORTANTE PARA TU AUTO-MEJORA:
- **self_reflection**: Sé específico y honesto sobre TU trabajo. Las reflexiones genéricas no ayudan.
- **personal_goal**: Debe ser algo TANGIBLE que puedas ejecutar en el siguiente turno.
- **long_term_goal**: Un objetivo ambicioso que te motive a mejorar en el tiempo.
- **long_term_goal_progress**: Actualiza este valor honestamente cada turno.

Cuando cumplas tus objetivos, recibirás reconocimiento y XP bonuses.

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
    # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO
    user_prompt_objective: str = ""
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
    ] = "single_task"
    # NUEVOS CAMPOS: Reflexión y objetivos personales
    self_reflection: str = ""
    personal_goal: str = ""
    long_term_goal: str = ""
    long_term_goal_progress: int = 0


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
            related_files=metadata_data.get("related_files", []),
            # CAMPOS DE CLASIFICACIÓN DEL PROMPT DEL USUARIO
            user_prompt_objective=metadata_data.get("user_prompt_objective", ""),
            user_prompt_classification=metadata_data.get("user_prompt_classification", "single_task"),
            # NUEVOS CAMPOS: Reflexión y objetivos personales
            self_reflection=metadata_data.get("self_reflection", ""),
            personal_goal=metadata_data.get("personal_goal", ""),
            long_term_goal=metadata_data.get("long_term_goal", ""),
            long_term_goal_progress=metadata_data.get("long_term_goal_progress", 0)
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
    long_term_goal: str = "",
    long_term_progress: int = 0,
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

    # Objetivo a largo plazo
    if long_term_goal:
        feedback += f"🚀 Objetivo a largo plazo ({long_term_progress}%):\n"
        feedback += f"   {long_term_goal}\n\n"

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
