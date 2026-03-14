"""Módulo para filtrar feedback del agente antes de incluirlo en el prompt.

Este módulo controla qué información del sistema de auto-mejora se envía al agente
en cada prompt, limitando el tamaño y seleccionando la información más relevante.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeedbackFilterConfig:
    """Configuración de filtros para feedback del agente.

    Atributos:
        max_reflections: Cantidad máxima de reflexiones a incluir (default: 3).
        max_achievements: Cantidad máxima de logros a mostrar (default: 1).
        include_goal_streak: Si incluir el streak de objetivos cumplidos.
        include_achievement_icons: Si incluir emojis de logros.
    """
    max_reflections: int = 3
    max_achievements: int = 1
    include_goal_streak: bool = True
    include_achievement_icons: bool = True


@dataclass
class FeedbackHistory:
    """Historial de feedback para filtrar por tiempo.

    Esta clase mantiene un registro de las reflexiones y logros
    a lo largo del tiempo, permitiendo filtrar por "turnos atrás".
    """
    # Registro de reflexiones con timestamp (turno)
    reflections: list[tuple[int, str]] = field(default_factory=list)
    # Registro de logros desbloqueados con timestamp
    achievements: list[tuple[int, dict]] = field(default_factory=list)

    def add_reflection(self, turn: int, reflection: str) -> None:
        """Agregar una reflexión al historial"""
        if reflection.strip():  # Solo agregar si no está vacía
            self.reflections.append((turn, reflection))

    def add_achievement(self, turn: int, achievement: dict) -> None:
        """Agregar un logro al historial"""
        self.achievements.append((turn, achievement))

    def get_recent_reflections(self, count: int) -> list[str]:
        """Obtener las últimas N reflexiones"""
        return [r for _, r in self.reflections[-count:]]

    def get_recent_achievements(self, count: int, turns_ago: int = 0) -> list[dict]:
        """
        Obtener los últimos N logros, opcionalmente filtrados por turnos atrás.

        Args:
            count: Cantidad máxima de logros a retornar
            turns_ago: Si 0, los más recientes. Si > 0, los de hace X turnos.

        Returns:
            Lista de logros (dict con name, icon, description)
        """
        if turns_ago <= 0:
            # Los más recientes
            return [ach for _, ach in self.achievements[-count:]]

        # Filtrar por turnos atrás (implementación básica)
        # Por ahora retornamos los más recientes
        return [ach for _, ach in self.achievements[-count:]]


@dataclass
class FilteredAgentFeedback:
    """Feedback filtrado listo para enviar al agente.

    Esta estructura contiene solo la información relevante que debe enviarse
    al agente en el prompt, según la configuración de filtros.
    """
    reflections: list[str]
    """Reflexiones a incluir (ya filtradas por cantidad)"""

    personal_goal: str
    """Objetivo personal actual del agente"""

    goal_achieved: bool
    """Si el agente cumplió su objetivo personal"""

    goal_streak: int | None
    """Streak de objetivos cumplidos (None si no incluir)"""

    achievements: list[dict]
    """Logros a mostrar (ya filtrados por cantidad)"""

    include_icons: bool
    """Si incluir emojis en la salida"""


class FeedbackFilter:
    """Filtro para feedback del agente en el prompt.

    Esta clase procesa el feedback del ExtendedStatsManager y aplica
    filtros para limitar el tamaño y seleccionar la información más
    relevante para el agente.
    """

    def __init__(self, config: FeedbackFilterConfig | None = None):
        """
        Inicializar el filtro de feedback.

        Args:
            config: Configuración de filtros. Si es None, usa defaults.
        """
        self.config = config or FeedbackFilterConfig()
        self.history = FeedbackHistory()
        self._turn_counter = 0

    def filter_feedback(
        self,
        raw_feedback: dict[str, Any]
    ) -> FilteredAgentFeedback:
        """
        Filtrar feedback crudo según la configuración.

        Args:
            raw_feedback: Dict retornado por get_feedback_for_agent()

        Returns:
            FilteredAgentFeedback con la información filtrada
        """
        # Registrar información en el historial
        self._turn_counter += 1
        if raw_feedback.get("last_reflection"):
            self.history.add_reflection(self._turn_counter, raw_feedback["last_reflection"])
        if raw_feedback.get("recent_achievements"):
            for ach in raw_feedback["recent_achievements"]:
                self.history.add_achievement(self._turn_counter, {
                    "name": getattr(ach, "name", str(ach)),
                    "icon": getattr(ach, "icon", "🏆"),
                    "description": getattr(ach, "description", "")
                })

        # Filtrar reflexiones (últimas N)
        all_reflections = self.history.get_recent_reflections(self.config.max_reflections)

        # Filtrar logros (últimos N)
        achievements_to_show = self.history.get_recent_achievements(self.config.max_achievements)

        # Filtrar goal_streak
        goal_streak = raw_feedback.get("goal_streak", 0) if self.config.include_goal_streak else None

        return FilteredAgentFeedback(
            reflections=all_reflections,
            personal_goal=raw_feedback.get("personal_goal", ""),
            goal_achieved=raw_feedback.get("goal_achieved", False),
            goal_streak=goal_streak,
            achievements=achievements_to_show,
            include_icons=self.config.include_achievement_icons
        )


def format_filtered_feedback(feedback: FilteredAgentFeedback) -> str:
    """
    Formatear feedback filtrado para el prompt del agente.

    Args:
        feedback: Feedback filtrado

    Returns:
        String formateado listo para incluir en el prompt
    """
    lines = []
    lines.append("╔════════════════════════════════════════════════════╗")
    lines.append("║         FEEDBACK PERSONALIZADO                    ║")
    lines.append("╚════════════════════════════════════════════════════╝")
    lines.append("")

    # Reflexiones
    if feedback.reflections:
        lines.append("📝 Reflexiones anteriores:")
        for i, ref in enumerate(feedback.reflections, 1):
            lines.append(f"   {i}. {ref}")
        lines.append("")

    # Objetivo personal
    if feedback.personal_goal:
        icon = "✅" if feedback.goal_achieved else "⏳"
        status = "CUMPLIDO" if feedback.goal_achieved else "EN PROGRESO"
        lines.append(f"🎯 Objetivo personal: [{icon} {status}]")
        lines.append(f"   {feedback.personal_goal}")

        if feedback.goal_streak is not None and feedback.goal_streak > 0:
            lines.append(f"   🔥 Streak: {feedback.goal_streak} objetivos cumplidos consecutivamente")

        lines.append("")

    # Logros
    if feedback.achievements:
        lines.append("🏆 Logro desbloqueado:")
        for ach in feedback.achievements:
            icon = ach.get("icon", "🏆") if feedback.include_icons else ""
            name = ach.get("name", "Unknown")
            lines.append(f"   {icon} {name}")
        lines.append("")

    lines.append("════════════════════════════════════════════════════")
    lines.append("¡Felicidades por tu progreso! Continúa")
    lines.append("trabajando en tu fase actual y sigue")
    lines.append("esforzándote en tus objetivos personales.")
    lines.append("════════════════════════════════════════════════════")

    return "\n".join(lines)
