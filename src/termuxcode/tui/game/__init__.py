"""Sistema de gamificación modular"""
from .stats import GameStats, StatsManager, Achievement
from .widgets import XPBar, AchievementPopup, LevelUpBanner, GameStatsDisplay
from .extended_stats import ExtendedGameStats, ExtendedStatsManager
from .metadata_achievements import METADATA_ACHIEVEMENTS, get_all_metadata_achievements, merge_achievements
from .metadata_widgets import (
    PhaseBadge,
    AdvancesBadge,
    SuggestionBox,
    ProductivityIndicator,
    PhaseDistribution,
    SuggestionTracker,
    MetadataPanel,
    MessageMetadata,
)

__all__ = [
    # Stats básicos
    "GameStats",
    "StatsManager",
    "Achievement",
    # Stats extendidos con metadata
    "ExtendedGameStats",
    "ExtendedStatsManager",
    # Logros de metadata
    "METADATA_ACHIEVEMENTS",
    "get_all_metadata_achievements",
    "merge_achievements",
    # Widgets básicos
    "XPBar",
    "AchievementPopup",
    "LevelUpBanner",
    "GameStatsDisplay",
    # Widgets de metadata
    "PhaseBadge",
    "AdvancesBadge",
    "SuggestionBox",
    "ProductivityIndicator",
    "PhaseDistribution",
    "SuggestionTracker",
    "MetadataPanel",
    "MessageMetadata",
]
