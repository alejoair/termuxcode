"""Estadísticas extendidas de gamificación con metadata de respuestas"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Callable

from .stats import GameStats
from .change_detector import ChangeManager


@dataclass
class ExtendedGameStats(GameStats):
    """Estadísticas extendidas con metadata de respuestas estructuradas"""

    # Por fase
    phases_count: dict[str, int] = field(default_factory=dict)
    # {"planificacion": 5, "implementacion": 23, "debugging": 2, "testing": 1, "analisis": 3, "otro": 0}

    # Productividad
    advances_task_count: int = 0
    advances_task_ratio: float = 0.0  # advances_task_count / total_messages

    # Sugerencias
    suggestions_made: int = 0
    suggestions_followed: int = 0
    suggestion_follow_ratio: float = 0.0

    # Historial
    messages_saved: int = 0
    messages_filtered: int = 0
    history_efficiency: float = 0.0  # messages_saved / total_messages

    # Streaks
    current_streak: int = 0  # mensajes consecutivos avanzando
    longest_streak: int = 0

    # Otros
    high_confidence_responses: int = 0
    context_refreshes: int = 0

    # NUEVOS: Objetivos personales y reflexiones del agente
    personal_goal: str = ""
    personal_goal_achieved: bool = False
    personal_goal_streak: int = 0
    long_term_goal: str = ""
    long_term_goal_progress: int = 0
    reflections_count: int = 0
    recent_reflections: list[str] = field(default_factory=list)

    # Metadata persistente de la respuesta actual
    current_phase: str = "otro"
    current_advances_task: bool = False
    current_confidence: float = 0.5
    current_confidence_history: list[float] = field(default_factory=list)  # Últimas 20 confianzas

    # Historial de fases (para detectar cambios de fase)
    phase_history: list[dict] = field(default_factory=list)  # [{"phase": "planificacion", "timestamp": "..."}]

    def process_metadata(self, advances_task: bool, phase: str, saved_to_history: bool,
                         has_suggestion: bool, confidence: float | None = None,
                         requires_refresh: bool = False) -> tuple[int, list]:
        """
        Procesar metadata de una respuesta estructurada

        Returns:
            (xp_gained, achievements_to_unlock)
        """
        xp_gained = 0
        achievements = []
        phase_changed = False

        # Detectar cambio de fase
        previous_phase = self.current_phase
        if phase != self.current_phase:
            phase_changed = True
            self.current_phase = phase

            # Agregar al historial de fases
            from datetime import datetime
            self.phase_history.append({
                "phase": phase,
                "from_phase": previous_phase,
                "timestamp": datetime.now().isoformat()
            })
            # Mantener solo los últimos 50 cambios de fase
            if len(self.phase_history) > 50:
                self.phase_history = self.phase_history[-50:]

        # Guardar metadata actual
        self.current_advances_task = advances_task
        self.current_confidence = confidence or self.current_confidence

        # Guardar en historial de confianzas (últimas 20)
        if confidence:
            self.current_confidence_history.append(confidence)
            if len(self.current_confidence_history) > 20:
                self.current_confidence_history = self.current_confidence_history[-20:]

        # Actualizar contadores
        if saved_to_history:
            self.messages_saved += 1
        else:
            self.messages_filtered += 1

        # Actualizar fases
        if phase not in self.phases_count:
            self.phases_count[phase] = 0
        self.phases_count[phase] += 1

        # Productividad
        if advances_task:
            self.advances_task_count += 1
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
        else:
            self.current_streak = 0

        # Sugerencias
        if has_suggestion:
            self.suggestions_made += 1

        # Confianza
        if confidence and confidence >= 0.9:
            self.high_confidence_responses += 1

        # Context refresh
        if requires_refresh:
            self.context_refreshes += 1

        # Calcular ratios
        self._calculate_ratios()

        # XP bonus por advances task
        if advances_task:
            xp_gained += 10

        # XP bonus por fase
        phase_bonus = {
            "implementacion": 5,
            "debugging": 3,
            "testing": 4,
            "planificacion": 3,
            "analisis": 2,
            "otro": 1
        }
        xp_gained += phase_bonus.get(phase, 1)

        # XP bonus por cambio de fase
        if phase_changed:
            xp_gained += 15

        # Verificar logros
        achievements.extend(self._check_metadata_achievements())

        return xp_gained, achievements

    def follow_suggestion(self) -> tuple[int, list]:
        """Usuario siguió una sugerencia"""
        self.suggestions_followed += 1
        self._calculate_ratios()

        xp_gained = 15  # XP por seguir sugerencia
        achievements = self._check_suggestion_achievements()

        return xp_gained, achievements

    def set_personal_goal(self, goal: str) -> None:
        """Establecer nuevo objetivo personal del agente"""
        self.personal_goal = goal
        self.personal_goal_achieved = False

    def mark_personal_goal_achieved(self, achieved: bool) -> tuple[int, list]:
        """
        Marcar si se cumplió el objetivo personal

        Returns:
            (xp_gained, achievements)
        """
        self.personal_goal_achieved = achieved
        xp_gained = 0
        achievements = []

        if achieved:
            self.personal_goal_streak += 1
            xp_gained = 10  # XP por cumplir objetivo personal
            achievements.extend(self._check_personal_goal_achievements())
        else:
            self.personal_goal_streak = 0

        return xp_gained, achievements

    def update_long_term_goal(self, goal: str, progress: int) -> None:
        """Actualizar objetivo a largo plazo y su progreso"""
        if goal != self.long_term_goal:
            # Nuevo objetivo a largo plazo
            self.long_term_goal = goal
        self.long_term_goal_progress = max(0, min(100, progress))

    def add_reflection(self, reflection: str) -> int:
        """
        Agregar reflexión del agente

        Returns:
            XP ganada por reflexión
        """
        if not reflection or len(reflection.strip()) < 10:
            return 0  # Reflexión muy corta no da XP

        self.reflections_count += 1
        self.recent_reflections.append(reflection)

        # Mantener solo las últimas 5 reflexiones
        if len(self.recent_reflections) > 5:
            self.recent_reflections.pop(0)

        return 2  # XP por reflexión constructiva

    def _calculate_ratios(self) -> None:
        """Calcular todos los ratios"""
        total = max(1, self.total_messages)
        self.advances_task_ratio = self.advances_task_count / total

        total_messages = self.messages_saved + self.messages_filtered
        self.history_efficiency = self.messages_saved / max(1, total_messages)

        self.suggestion_follow_ratio = self.suggestions_followed / max(1, self.suggestions_made)

    def _check_metadata_achievements(self) -> list:
        """Verificar logros basados en metadata"""
        unlocked = []

        for ach in self.achievements:
            if ach.unlocked:
                continue

            # Logros por fase
            if ach.id == "phase_first_impl" and self.phases_count.get("implementacion", 0) >= 1:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "phase_master_impl" and self.phases_count.get("implementacion", 0) >= 50:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "phase_debugger" and self.phases_count.get("debugging", 0) >= 10:
                ach.unlocked = True
                unlocked.append(ach)

            # Logros de productividad
            if ach.id == "streak_avancer" and self.current_streak >= 5:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "efficiency_master" and self.advances_task_ratio >= 0.8 and self.total_messages >= 20:
                ach.unlocked = True
                unlocked.append(ach)

            # Logros de historial
            if ach.id == "history_cleaner" and self.messages_filtered >= 10:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "history_efficient" and self.history_efficiency >= 0.7 and self.messages_saved + self.messages_filtered >= 20:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def _check_suggestion_achievements(self) -> list:
        """Verificar logros de seguimiento de sugerencias"""
        unlocked = []

        for ach in self.achievements:
            if ach.unlocked:
                continue

            if ach.id == "suggestion_follower" and self.suggestions_followed >= 10:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "suggestion_master" and self.suggestions_followed >= 50:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "suggestion_streak" and self.suggestion_follow_ratio >= 0.8 and self.suggestions_made >= 10:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def _check_personal_goal_achievements(self) -> list:
        """Verificar logros de objetivos personales"""
        unlocked = []

        for ach in self.achievements:
            if ach.unlocked:
                continue

            if ach.id == "personal_goal_first" and self.personal_goal_streak >= 1:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "personal_goal_streak_5" and self.personal_goal_streak >= 5:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "personal_goal_streak_10" and self.personal_goal_streak >= 10:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "reflector" and self.reflections_count >= 10:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def to_dict(self) -> dict:
        """Serializar a diccionario"""
        base_dict = super().to_dict()
        base_dict.update({
            "phases_count": self.phases_count,
            "advances_task_count": self.advances_task_count,
            "advances_task_ratio": self.advances_task_ratio,
            "suggestions_made": self.suggestions_made,
            "suggestions_followed": self.suggestions_followed,
            "suggestion_follow_ratio": self.suggestion_follow_ratio,
            "messages_saved": self.messages_saved,
            "messages_filtered": self.messages_filtered,
            "history_efficiency": self.history_efficiency,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "high_confidence_responses": self.high_confidence_responses,
            "context_refreshes": self.context_refreshes,
            # NUEVOS CAMPOS
            "personal_goal": self.personal_goal,
            "personal_goal_achieved": self.personal_goal_achieved,
            "personal_goal_streak": self.personal_goal_streak,
            "long_term_goal": self.long_term_goal,
            "long_term_goal_progress": self.long_term_goal_progress,
            "reflections_count": self.reflections_count,
            "recent_reflections": self.recent_reflections,
            # Metadata persistente actual
            "current_phase": self.current_phase,
            "current_advances_task": self.current_advances_task,
            "current_confidence": self.current_confidence,
            "current_confidence_history": self.current_confidence_history,
            "phase_history": self.phase_history
        })
        return base_dict

    def get_latest_phase_change(self) -> dict | None:
        """Retorna el último cambio de fase"""
        if not self.phase_history:
            return None
        return self.phase_history[-1]

    @classmethod
    def from_dict(cls, data: dict) -> ExtendedGameStats:
        """Deserializar desde diccionario"""
        stats = cls(
            xp=data.get("xp", 0),
            level=data.get("level", 1),
            total_messages=data.get("total_messages", 0),
            total_tools=data.get("total_tools", 0),
            phases_count=data.get("phases_count", {}),
            advances_task_count=data.get("advances_task_count", 0),
            advances_task_ratio=data.get("advances_task_ratio", 0.0),
            suggestions_made=data.get("suggestions_made", 0),
            suggestions_followed=data.get("suggestions_followed", 0),
            suggestion_follow_ratio=data.get("suggestion_follow_ratio", 0.0),
            messages_saved=data.get("messages_saved", 0),
            messages_filtered=data.get("messages_filtered", 0),
            history_efficiency=data.get("history_efficiency", 0.0),
            current_streak=data.get("current_streak", 0),
            longest_streak=data.get("longest_streak", 0),
            high_confidence_responses=data.get("high_confidence_responses", 0),
            context_refreshes=data.get("context_refreshes", 0),
            # NUEVOS CAMPOS
            personal_goal=data.get("personal_goal", ""),
            personal_goal_achieved=data.get("personal_goal_achieved", False),
            personal_goal_streak=data.get("personal_goal_streak", 0),
            long_term_goal=data.get("long_term_goal", ""),
            long_term_goal_progress=data.get("long_term_goal_progress", 0),
            reflections_count=data.get("reflections_count", 0),
            recent_reflections=data.get("recent_reflections", []),
            # Metadata persistente actual
            current_phase=data.get("current_phase", "otro"),
            current_advances_task=data.get("current_advances_task", False),
            current_confidence=data.get("current_confidence", 0.5),
            current_confidence_history=data.get("current_confidence_history", []),
            phase_history=data.get("phase_history", [])
        )

        # Restaurar estado de logros
        unlocked_ids = {a["id"] for a in data.get("achievements", []) if a.get("unlocked")}
        for ach in stats.achievements:
            if ach.id in unlocked_ids:
                ach.unlocked = True

        return stats


class ExtendedStatsManager:
    """Gestor de estadísticas extendidas con persistencia"""

    def __init__(self, stats_dir: Path):
        self.stats_dir = stats_dir
        self.stats_file = stats_dir / "extended_game_stats.json"
        self._stats: ExtendedGameStats | None = None
        self._on_achievement: Callable[[object], None] | None = None
        self._on_level_up: Callable[[int], None] | None = None
        self._change_manager: ChangeManager | None = None

    @property
    def change_manager(self) -> ChangeManager:
        """Obtener el ChangeManager (crear si no existe)"""
        if self._change_manager is None:
            # Configurar ChangeManager sin LLM por defecto
            self._change_manager = ChangeManager()
        return self._change_manager

    def set_llm_validator(self, llm_query_func: Callable) -> None:
        """
        Configurar función LLM para validación

        Args:
            llm_query_func: Función async para consultar LLM
        """
        self._change_manager = ChangeManager(llm_query_func=llm_query_func)

    @property
    def stats(self) -> ExtendedGameStats:
        """Obtener estadísticas (cargar si es necesario)"""
        if self._stats is None:
            self._stats = self.load()
        return self._stats

    def load(self) -> ExtendedGameStats:
        """Cargar estadísticas desde disco"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    return ExtendedGameStats.from_dict(json.load(f))
            except Exception:
                pass
        return ExtendedGameStats()

    def save(self) -> None:
        """Guardar estadísticas a disco"""
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w") as f:
            json.dump(self.stats.to_dict(), f, indent=2)

    def add_message(self) -> list:
        """Añadir mensaje, retornar logros desbloqueados"""
        self.stats.add_xp(5)
        unlocked = self.stats.increment_messages()

        # Verificar logros de nivel
        level_achievements = self.stats.check_level_achievements()
        unlocked.extend(level_achievements)

        self.save()

        # Notificar callbacks
        for ach in unlocked:
            if self._on_achievement:
                self._on_achievement(ach)

        return unlocked

    def process_structured_response(self, advances_task: bool, phase: str,
                                    saved_to_history: bool, has_suggestion: bool,
                                    confidence: float | None = None,
                                    requires_refresh: bool = False) -> tuple[int, list]:
        """
        Procesar una respuesta estructurada

        Returns:
            (xp_gained, achievements)
        """
        # XP base
        self.stats.add_xp(2)
        self.stats.total_messages += 1

        # Procesar metadata
        xp_bonus, achievements = self.stats.process_metadata(
            advances_task=advances_task,
            phase=phase,
            saved_to_history=saved_to_history,
            has_suggestion=has_suggestion,
            confidence=confidence,
            requires_refresh=requires_refresh
        )

        # Verificar subida de nivel
        old_level = self.stats.level
        self.stats.add_xp(xp_bonus)
        levels_gained = 0
        while self.stats.level < 10 and self.stats.xp >= self.stats.xp_for_next_level:
            self.stats.level += 1
            levels_gained += 1

        if levels_gained > 0 and self._on_level_up:
            self._on_level_up(self.stats.level)

        # Verificar logros de nivel
        level_achievements = self.stats.check_level_achievements()
        achievements.extend(level_achievements)

        self.save()

        # Notificar logros
        for ach in achievements:
            if self._on_achievement:
                self._on_achievement(ach)

        return xp_bonus, achievements

    def follow_suggestion(self) -> tuple[int, list]:
        """Usuario siguió una sugerencia"""
        xp_gained, achievements = self.stats.follow_suggestion()

        # Verificar subida de nivel
        old_level = self.stats.level
        self.stats.add_xp(xp_gained)
        levels_gained = 0
        while self.stats.level < 10 and self.stats.xp >= self.stats.xp_for_next_level:
            self.stats.level += 1
            levels_gained += 1

        if levels_gained > 0 and self._on_level_up:
            self._on_level_up(self.stats.level)

        self.save()

        # Notificar logros
        for ach in achievements:
            if self._on_achievement:
                self._on_achievement(ach)

        return xp_gained, achievements

    def add_tool_use(self) -> list:
        """Añadir uso de herramienta"""
        self.stats.add_xp(3)
        unlocked = self.stats.increment_tools()

        # Verificar logros de nivel
        level_achievements = self.stats.check_level_achievements()
        unlocked.extend(level_achievements)

        self.save()

        for ach in unlocked:
            if self._on_achievement:
                self._on_achievement(ach)

        return unlocked

    def on_achievement(self, callback: Callable[[object], None]) -> None:
        """Registrar callback para logros"""
        self._on_achievement = callback

    def on_level_up(self, callback: Callable[[int], None]) -> None:
        """Registrar callback para subida de nivel"""
        self._on_level_up = callback

    # NUEVOS MÉTODOS: Objetivos personales y reflexiones

    def process_reflection_and_goal(
        self,
        reflection: str,
        personal_goal: str,
        long_term_goal: str = "",
        long_term_progress: int = 0
    ) -> tuple[int, list]:
        """
        Procesar reflexión y objetivos personales del agente

        Returns:
            (xp_gained, achievements)
        """
        xp_gained = 0
        achievements = []

        # Procesar reflexión
        xp_gained += self.stats.add_reflection(reflection)

        # Establecer nuevo objetivo personal
        self.stats.set_personal_goal(personal_goal)

        # Actualizar objetivo a largo plazo
        if long_term_goal:
            self.stats.update_long_term_goal(long_term_goal, long_term_progress)

        # Verificar logros de reflexiones
        achievements.extend(self._check_reflection_achievements())

        # Verificar subida de nivel
        old_level = self.stats.level
        self.stats.add_xp(xp_gained)
        levels_gained = 0
        while self.stats.level < 10 and self.stats.xp >= self.stats.xp_for_next_level:
            self.stats.level += 1
            levels_gained += 1

        if levels_gained > 0 and self._on_level_up:
            self._on_level_up(self.stats.level)

        self.save()

        # Notificar logros
        for ach in achievements:
            if self._on_achievement:
                self._on_achievement(ach)

        return xp_gained, achievements

    def mark_goal_achieved(self, achieved: bool) -> tuple[int, list]:
        """
        Marcar si el agente cumplió su objetivo personal

        Returns:
            (xp_gained, achievements)
        """
        xp_gained, achievements = self.stats.mark_personal_goal_achieved(achieved)

        # Verificar subida de nivel
        old_level = self.stats.level
        self.stats.add_xp(xp_gained)
        levels_gained = 0
        while self.stats.level < 10 and self.stats.xp >= self.stats.xp_for_next_level:
            self.stats.level += 1
            levels_gained += 1

        if levels_gained > 0 and self._on_level_up:
            self._on_level_up(self.stats.level)

        self.save()

        # Notificar logros
        for ach in achievements:
            if self._on_achievement:
                self._on_achievement(ach)

        return xp_gained, achievements

    def get_feedback_for_agent(self) -> dict:
        """
        Obtener datos de feedback para el agente

        Returns:
            Dict con: last_reflection, personal_goal, goal_achieved,
                     goal_streak, long_term_goal, long_term_progress,
                     recent_achievements
        """
        stats = self.stats

        return {
            "last_reflection": stats.recent_reflections[-1] if stats.recent_reflections else "",
            "personal_goal": stats.personal_goal,
            "goal_achieved": stats.personal_goal_achieved,
            "goal_streak": stats.personal_goal_streak,
            "long_term_goal": stats.long_term_goal,
            "long_term_progress": stats.long_term_goal_progress,
            "recent_achievements": [a for a in stats.achievements if a.unlocked][-5:]  # Últimos 5
        }

    def get_phase_change_info(self) -> dict | None:
        """
        Obtener información del último cambio de fase

        Returns:
            Dict con: from_phase, to_phase, timestamp, context
            o None si no hubo cambios
        """
        change = self.stats.get_latest_phase_change()
        if not change:
            return None

        stats = self.stats

        return {
            "from_phase": change.get("from_phase", "desconocido"),
            "to_phase": change.get("phase", "desconocido"),
            "timestamp": change.get("timestamp", ""),
            "context": {
                "current_confidence": stats.current_confidence,
                "avg_confidence": sum(stats.current_confidence_history) / len(stats.current_confidence_history) if stats.current_confidence_history else 0,
                "advances_task_count": stats.advances_task_count,
                "total_messages": stats.total_messages,
                "phase_counts": stats.phases_count
            }
        }

    def generate_phase_validation_prompt(self, change_info: dict, history: list[dict]) -> str:
        """
        Generar prompt para validar un cambio de fase con otro LLM

        Args:
            change_info: Información del cambio de fase
            history: Historial de conversación

        Returns:
            Prompt completo para el LLM validador
        """
        from_phase = change_info["from_phase"]
        to_phase = change_info["to_phase"]
        context = change_info["context"]

        prompt = f"""# VALIDACIÓN DE CAMBIO DE FASE

## Cambio Detectado
- **Desde**: {from_phase}
- **Hacia**: {to_phase}
- **Timestamp**: {change_info['timestamp']}

## Contexto de la Sesión
- **Confianza actual**: {context['current_confidence']:.2f}
- **Confianza promedio**: {context['avg_confidence']:.2f}
- **Mensajes que avanzan la tarea**: {context['advances_task_count']}
- **Total de mensajes**: {context['total_messages']}
- **Contador por fase**: {context['phase_counts']}

## Instrucciones
Eres un auditor de calidad de código y procesos. Tu tarea es validar que el cambio de fase es correcto.

Responde a estas 3 preguntas:

1. **¿Se completó correctamente la fase {from_phase}?**
   - ¿Qué se hizo en esta fase?
   - ¿Hay evidencia de que se completó?
   - ¿Faltó algo importante?

2. **¿Es apropiado pasar a la fase {to_phase}?**
   - ¿Es el siguiente paso lógico?
   - ¿Hay dependencias no resueltas?
   - ¿Debería volver a una fase anterior?

3. **¿Qué se debe mejorar?**
   - ¿Hay riesgos o problemas identificados?
   - ¿Qué se debe corregir antes de continuar?
   - ¿Recomendaciones para el futuro?

## Tu Respuesta
Proporciona una respuesta clara y concisa. Si detectas problemas, sé específico sobre qué debe corregirse.
"""

        return prompt

    def _check_reflection_achievements(self) -> list:
        """Verificar logros de reflexiones"""
        unlocked = []

        for ach in self.stats.achievements:
            if ach.unlocked:
                continue

            if ach.id == "reflector" and self.stats.reflections_count >= 10:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "deep_thinker" and self.stats.reflections_count >= 50:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    async def process_changes_async(
        self,
        current_values: dict[str, Any],
        context: dict | None = None
    ) -> tuple[int, list]:
        """
        Procesar cambios de forma asíncrona usando ChangeManager

        Args:
            current_values: Valores actuales a monitorear
            context: Contexto adicional para validación

        Returns:
            (xp_gained, achievements)
        """
        xp_gained = 0
        achievements = []

        if not self._change_manager:
            return xp_gained, achievements

        # Detectar y validar cambios
        changes, validations = await self._change_manager.process_changes(
            current_values,
            context=context
        )

        # XP bonus por cambios detectados
        xp_gained += len(changes) * 5

        # XP bonus por validaciones exitosas
        passed_validations = [v for v in validations if v.passed]
        xp_gained += len(passed_validations) * 3

        # Notificar validaciones fallidas
        failed_validations = [v for v in validations if not v.passed]
        if failed_validations and self._on_achievement:
            # Notificar como "warning" en lugar de logro
            for validation in failed_validations:
                self._on_achievement({
                    "type": "validation_warning",
                    "message": validation.message,
                    "recommendations": validation.recommendations,
                    "field": validation.change.field_path
                })

        return xp_gained, achievements
