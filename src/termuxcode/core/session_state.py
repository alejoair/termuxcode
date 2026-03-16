"""Estado de sesión individual"""
from __future__ import annotations
import asyncio

from termuxcode.core.history import MessageHistory
from termuxcode.core.agent import AgentClient


class SessionState:
    """Estado de una sesión individual"""
    def __init__(self, history: MessageHistory, agent: AgentClient):
        self.history = history
        self.agent = agent
        self.pending_task: asyncio.Task | None = None
        self.scroll_position: int = 0  # Guardar posición de scroll
        self.scroll_x: int = 0  # Scroll horizontal si aplica
