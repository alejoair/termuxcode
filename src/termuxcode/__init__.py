"""TermuxCode - Python project for Termux development."""

__version__ = "0.2.0"

from .tui import ClaudeChat
from .cli import main

__all__ = ['ClaudeChat', 'main']
