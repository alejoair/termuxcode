"""Estado de sesión individual"""
from __future__ import annotations
import asyncio

from termuxcode.core.history_manager import MessageHistory
from termuxcode.core.agents import MainAgentClient


class SessionState:
    """Estado de una sesión individual"""
    def __init__(self, history: MessageHistory, agent: MainAgentClient):
        self.history = history
        self.agent = agent
        self.pending_task: asyncio.Task | None = None
        self.scroll_position: int = 0  # Guardar posición de scroll
        self.scroll_x: int = 0  # Scroll horizontal si aplica
