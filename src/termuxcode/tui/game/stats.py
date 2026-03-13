"""Estadísticas de gamificación - XP, niveles, logros"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Callable


@dataclass
class Achievement:
    """Logro desbloqueado"""
    id: str
    name: str
    xp: int
    icon: str = "*"
    unlocked: bool = False


@dataclass
class GameStats:
    """Estadísticas del jugador - XP, nivel, logros"""
    xp: int = 0
    level: int = 1
    total_messages: int = 0
    total_tools: int = 0
    achievements: list[Achievement] = field(default_factory=list)

    # XP necesaria por nivel (nivel -> XP acumulada)
    XP_PER_LEVEL: dict[int, int] = field(default_factory=lambda: {
        1: 0,
        2: 50,
        3: 150,
        4: 300,
        5: 500,
        6: 800,
        7: 1200,
        8: 1700,
        9: 2300,
        10: 3000,
    })

    # Logros predefinidos
    DEFAULT_ACHIEVEMENTS: list[dict] = field(default_factory=lambda: [
        {"id": "first_msg", "name": "First Steps", "xp": 10, "icon": ">"},
        {"id": "msg_10", "name": "Chatterbox", "xp": 30, "icon": "*"},
        {"id": "msg_50", "name": "Conversationalist", "xp": 100, "icon": "+"},
        {"id": "tool_first", "name": "Tool User", "xp": 15, "icon": "|"},
        {"id": "tool_10", "name": "Power User", "xp": 50, "icon": "!"},
        {"id": "level_5", "name": "Rising Star", "xp": 0, "icon": "#"},
        {"id": "level_10", "name": "Master", "xp": 0, "icon": "@"},
    ])

    def __post_init__(self):
        if not self.achievements:
            self.achievements = [Achievement(**a) for a in self.DEFAULT_ACHIEVEMENTS]

    @property
    def xp_for_next_level(self) -> int:
        """XP necesaria para el siguiente nivel"""
        next_level = min(self.level + 1, 10)
        return self.XP_PER_LEVEL.get(next_level, 9999)

    @property
    def xp_progress(self) -> float:
        """Progreso hacia el siguiente nivel (0.0 - 1.0)"""
        current_xp = self.XP_PER_LEVEL.get(self.level, 0)
        needed = self.xp_for_next_level - current_xp
        if needed <= 0:
            return 1.0
        progress = (self.xp - current_xp) / needed
        return min(1.0, max(0.0, progress))

    def add_xp(self, amount: int) -> tuple[bool, int]:
        """Añadir XP. Retorna (subió_nivel, niveles_subidos)"""
        self.xp += amount
        levels_gained = 0

        while self.level < 10 and self.xp >= self.xp_for_next_level:
            self.level += 1
            levels_gained += 1

        return levels_gained > 0, levels_gained

    def increment_messages(self) -> list[Achievement]:
        """Incrementar contador de mensajes y verificar logros"""
        self.total_messages += 1
        unlocked = []

        # Verificar logros de mensajes
        for ach in self.achievements:
            if ach.unlocked:
                continue
            if ach.id == "first_msg" and self.total_messages >= 1:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "msg_10" and self.total_messages >= 10:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "msg_50" and self.total_messages >= 50:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def increment_tools(self) -> list[Achievement]:
        """Incrementar contador de herramientas y verificar logros"""
        self.total_tools += 1
        unlocked = []

        for ach in self.achievements:
            if ach.unlocked:
                continue
            if ach.id == "tool_first" and self.total_tools >= 1:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "tool_10" and self.total_tools >= 10:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def check_level_achievements(self) -> list[Achievement]:
        """Verificar logros de nivel"""
        unlocked = []

        for ach in self.achievements:
            if ach.unlocked:
                continue
            if ach.id == "level_5" and self.level >= 5:
                ach.unlocked = True
                unlocked.append(ach)
            elif ach.id == "level_10" and self.level >= 10:
                ach.unlocked = True
                unlocked.append(ach)

        return unlocked

    def to_dict(self) -> dict:
        """Serializar a diccionario"""
        return {
            "xp": self.xp,
            "level": self.level,
            "total_messages": self.total_messages,
            "total_tools": self.total_tools,
            "achievements": [
                {"id": a.id, "unlocked": a.unlocked}
                for a in self.achievements
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameStats:
        """Deserializar desde diccionario"""
        stats = cls(
            xp=data.get("xp", 0),
            level=data.get("level", 1),
            total_messages=data.get("total_messages", 0),
            total_tools=data.get("total_tools", 0),
        )

        # Restaurar estado de logros
        unlocked_ids = {a["id"] for a in data.get("achievements", []) if a.get("unlocked")}
        for ach in stats.achievements:
            if ach.id in unlocked_ids:
                ach.unlocked = True

        return stats


class StatsManager:
    """Gestor de estadísticas con persistencia"""

    def __init__(self, stats_dir: Path):
        self.stats_dir = stats_dir
        self.stats_file = stats_dir / "game_stats.json"
        self._stats: GameStats | None = None
        self._on_achievement: Callable[[Achievement], None] | None = None
        self._on_level_up: Callable[[int], None] | None = None

    @property
    def stats(self) -> GameStats:
        """Obtener estadísticas (cargar si es necesario)"""
        if self._stats is None:
            self._stats = self.load()
        return self._stats

    def load(self) -> GameStats:
        """Cargar estadísticas desde disco"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    return GameStats.from_dict(json.load(f))
            except Exception:
                pass
        return GameStats()

    def save(self) -> None:
        """Guardar estadísticas a disco"""
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w") as f:
            json.dump(self.stats.to_dict(), f, indent=2)

    def add_message(self) -> list[Achievement]:
        """Añadir mensaje, retornar logros desbloqueados"""
        # XP base por mensaje
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

    def add_tool_use(self) -> list[Achievement]:
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

    def add_response(self) -> None:
        """Añadir respuesta recibida (XP)"""
        self.stats.add_xp(2)
        self.save()

    def on_achievement(self, callback: Callable[[Achievement], None]) -> None:
        """Registrar callback para logros"""
        self._on_achievement = callback

    def on_level_up(self, callback: Callable[[int], None]) -> None:
        """Registrar callback para subida de nivel"""
        self._on_level_up = callback
