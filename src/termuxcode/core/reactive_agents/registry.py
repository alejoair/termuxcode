"""Registry that connects ReactiveAgents to Blackboard events."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from termuxcode.core.memory.blackboard import Blackboard
from .base import ReactiveAgent
from .agents.classifier import ClassifierAgent

logger = logging.getLogger(__name__)


class ReactiveRegistry:
    """Manages reactive agent registration and dispatching.

    Two modes of operation:

    1. **pre_query** agents: Run BEFORE the main agent via `run_pre_query()`.
       The classifier runs first (Haiku, fast), then matching pre_query agents
       execute concurrently. All are awaited so the main agent gets their context.

    2. **post_query** agents: Run AFTER the main agent via Blackboard events.
       These are fire-and-forget (asyncio.create_task).

    Usage:
        registry = ReactiveRegistry(cwd="/path/to/project")
        registry.register(FixContextAgent)
        registry.activate()   # starts post_query BB listeners

        # Before each query:
        await registry.run_pre_query(prompt, session_id)
        # ... then run main agent ...
    """

    def __init__(self, cwd: str | None = None):
        import os
        self.cwd = cwd or os.getcwd()
        self._agents: list[ReactiveAgent] = []
        self._active = False
        self._callbacks: list[tuple[str, Any]] = []
        self._classifier = ClassifierAgent(cwd=self.cwd)

    def register(self, agent_cls: type[ReactiveAgent]) -> None:
        """Register a reactive agent class."""
        agent = agent_cls(cwd=self.cwd)
        if not agent.pattern:
            raise ValueError(f"{agent_cls.__name__} must define a 'pattern' attribute")
        self._agents.append(agent)
        logger.info(f"registered reactive agent: {agent_cls.__name__} "
                     f"(trigger={agent.trigger}, pattern='{agent.pattern}')")

    # ── Pre-query pipeline ──────────────────────────────────────

    async def run_pre_query(self, prompt: str, session_id: str) -> None:
        """Run the pre-query pipeline: classify → run matching agents (awaited).

        This is called BEFORE the main agent query. All pre_query agents that
        match are awaited so their results are available in the Blackboard
        when the main agent starts.
        """
        bb = Blackboard("app")

        # Step 1: Classify the prompt
        classification = await self._classifier.classify(prompt, session_id, bb)
        if not classification:
            logger.warning("pre-query: classifier returned nothing, skipping reactive agents")
            return

        # Step 2: Run pre_query agents whose condition matches
        prefix = f"session.{session_id}.pre_query"
        tasks: list[asyncio.Task] = []

        for agent in self._agents:
            if agent.trigger != "pre_query":
                continue

            # Check condition against the classification path
            path = f"{prefix}.classification"
            value = classification.classification

            try:
                if not agent.condition(path, value, bb):
                    logger.debug(f"pre_query: {agent.__class__.__name__} skipped (condition=False)")
                    continue
            except Exception as e:
                logger.error(f"pre_query: condition error in {agent.__class__.__name__}: {e}")
                continue

            logger.info(f"pre_query: triggering {agent.__class__.__name__}")
            tasks.append(
                asyncio.create_task(
                    self._run_safe(agent, path, value, bb),
                    name=f"pre-query-{agent.__class__.__name__}",
                )
            )

        if tasks:
            # Await all pre_query agents — the main agent needs their results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"pre_query agent failed: {result}")

    # ── Post-query (Blackboard event listeners) ─────────────────

    def activate(self) -> None:
        """Start listening to Blackboard events for post_query agents."""
        if self._active:
            return

        for agent in self._agents:
            if agent.trigger != "post_query":
                continue
            callback = self._make_post_callback(agent)
            Blackboard.on(agent.pattern, callback)
            self._callbacks.append((agent.pattern, callback))
            logger.debug(f"activated post_query listener for {agent.__class__.__name__}")

        self._active = True
        logger.info(f"reactive registry activated with {len(self._agents)} agent(s)")

    def deactivate(self) -> None:
        """Stop listening to all Blackboard events."""
        for pattern, callback in self._callbacks:
            Blackboard.off(pattern, callback)
        self._callbacks.clear()
        self._active = False
        logger.info("reactive registry deactivated")

    def _make_post_callback(self, agent: ReactiveAgent):
        """Create an async callback for post_query agents (fire-and-forget)."""

        async def _on_change(path: str, value: Any, bb: Blackboard) -> None:
            try:
                if not agent.condition(path, value, bb):
                    return
                logger.info(f"post_query: triggering {agent.__class__.__name__} for {path}")
                asyncio.create_task(
                    self._run_safe(agent, path, value, bb),
                    name=f"reactive-{agent.__class__.__name__}",
                )
            except Exception as e:
                logger.error(f"post_query callback error: {e}")

        return _on_change

    # ── Shared ──────────────────────────────────────────────────

    async def _run_safe(self, agent: ReactiveAgent, path: str, value: Any, bb: Blackboard) -> None:
        """Run agent with error handling."""
        try:
            await agent.run(path, value, bb)
        except Exception as e:
            logger.error(f"reactive agent {agent.__class__.__name__} failed: {e}", exc_info=True)
