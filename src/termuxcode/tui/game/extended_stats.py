"""Estadísticas extendidas de gamificación con metadata de respuestas"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Callable

from .stats import GameStats


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
            "context_refreshes": self.context_refreshes
        })
        return base_dict

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
            context_refreshes=data.get("context_refreshes", 0)
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
