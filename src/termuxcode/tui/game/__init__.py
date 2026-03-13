"""Sistema de gamificación modular"""
from .stats import GameStats, StatsManager, Achievement
from .widgets import XPBar, AchievementPopup, LevelUpBanner, GameStatsDisplay

__all__ = [
    "GameStats",
    "StatsManager",
    "Achievement",
    "XPBar",
    "AchievementPopup",
    "LevelUpBanner",
    "GameStatsDisplay",
]
