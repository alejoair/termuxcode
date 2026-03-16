"""TermuxCode - Python project for Termux development."""

__version__ = "0.2.0"

from termuxcode.tui import ClaudeChat
from termuxcode.cli import main

__all__ = ['ClaudeChat', 'main']
