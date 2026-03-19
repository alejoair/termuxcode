"""Base class for reactive agents."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from termuxcode.core.memory.blackboard import Blackboard

logger = logging.getLogger(__name__)


class ReactiveAgent(ABC):
    """Base class for agents that react to Blackboard changes.

    Subclasses define:
    - `pattern`: the Blackboard path pattern that triggers this agent (e.g. "session.*.task.*")
    - `trigger`: when this agent runs — "pre_query" (before main agent) or "post_query" (after)
    - `condition()`: optional filter — return True to run, False to skip
    - `run()`: the actual agent logic (call Claude SDK, read files, write to BB)
    """

    # Blackboard pattern that triggers this agent (set in subclass)
    pattern: str = ""
    # When to trigger: "pre_query" runs before main agent (awaited),
    # "post_query" runs after main agent finishes (fire-and-forget)
    trigger: str = "pre_query"

    def __init__(self, cwd: str | None = None):
        import os
        self.cwd = cwd or os.getcwd()

    def condition(self, path: str, value: Any, bb: Blackboard) -> bool:
        """Optional guard. Return True to proceed with run(), False to skip.

        Override in subclasses for fine-grained control.
        Default: always run.
        """
        return True

    @abstractmethod
    async def run(self, path: str, value: Any, bb: Blackboard) -> None:
        """Execute the reactive agent logic.

        Args:
            path: The exact Blackboard path that changed.
            value: The new value that was set.
            bb: The Blackboard instance for reading/writing context.
        """
        ...
