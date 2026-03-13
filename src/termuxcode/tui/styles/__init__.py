"""Estilos modulares para la TUI"""
from .base import BASE_CSS
from .chat import CHAT_CSS
from .tabs import TABS_CSS
from .input import INPUT_CSS
from .gamification import GAMIFICATION_CSS

CSS = BASE_CSS + CHAT_CSS + TABS_CSS + INPUT_CSS + GAMIFICATION_CSS

__all__ = ["CSS"]
