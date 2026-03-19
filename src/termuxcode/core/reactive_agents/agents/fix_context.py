"""Reactive agent that gathers extra context when the user is fixing a bug.

Trigger: pre_query — runs BEFORE the main agent so context is ready.
"""
from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.reactive_agents.base import ReactiveAgent

logger = logging.getLogger(__name__)

_PROMPT = """You are a context-gathering assistant. The user is about to work on a bug fix.

Objective: {objective}
Related files: {related_files}

Your job is to gather relevant context BEFORE the main agent starts. Focus on:

1. Read the related files listed above (if any).
2. Run `git log --oneline -5` and `git diff --stat` to see recent changes.
3. Look for test files related to the affected code.
4. If there are error patterns or stack traces mentioned in the objective, search for them.

Write a concise context summary (max ~500 words) with:
- Key code snippets from the affected files
- Recent changes that might be related
- Relevant test files or error patterns found

Be factual and specific — the main agent will use this to start working immediately.
"""


class FixContextAgent(ReactiveAgent):
    """Gathers debugging context when the classifier tags a prompt as 'fix'.

    Triggers: pre_query, when classification == "fix"
    Reads from BB: session.{id}.pre_query.{objective, related_files}
    Writes to BB: session.{id}.reactive.fix_context
    """

    pattern = "session.*.pre_query.classification"
    trigger = "pre_query"

    def condition(self, path: str, value: Any, bb: Blackboard) -> bool:
        """Only trigger when classification is 'fix'."""
        return value == "fix"

    async def run(self, path: str, value: Any, bb: Blackboard) -> None:
        """Gather context for the bug fix and write it to the Blackboard."""
        # Extract session_id from path: "session.{id}.pre_query.classification"
        parts = path.split(".")
        if len(parts) < 4:
            logger.warning(f"unexpected path format: {path}")
            return
        session_id = parts[1]

        # Read classifier results from BB
        objective = bb.get(f"session.{session_id}.pre_query.objective") or "unknown"
        related_files = bb.get(f"session.{session_id}.pre_query.related_files") or []

        prompt = _PROMPT.format(
            objective=objective,
            related_files=", ".join(related_files) if related_files else "none specified",
        )

        logger.info(f"FixContextAgent running for session {session_id}: {objective}")

        context_parts = []

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            model="haiku",
            tools=["Read", "Bash", "Glob", "Grep"],
        )

        try:
            async for message in query(prompt=prompt, options=options):
                msg_type = message.__class__.__name__

                if msg_type == "AssistantMessage":
                    for block in getattr(message, "content", []):
                        if block.__class__.__name__ == "TextBlock":
                            context_parts.append(block.text)

                elif msg_type == "ResultMessage":
                    if hasattr(message, "text") and message.text:
                        context_parts.append(message.text)
        except Exception as e:
            logger.error(f"FixContextAgent query failed: {e}", exc_info=True)
            return

        # Write gathered context to the BB
        if context_parts:
            context = "\n".join(context_parts)
            await bb.set(f"session.{session_id}.reactive.fix_context", context)
            logger.info(
                f"FixContextAgent wrote {len(context)} chars of context for session {session_id}"
            )
        else:
            logger.warning(f"FixContextAgent gathered no context for session {session_id}")
