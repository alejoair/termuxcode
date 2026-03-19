"""Pre-query classifier agent: quickly categorises the user prompt with Haiku."""
from __future__ import annotations

import logging
import os

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.schemas.classifier_schema import ClassifierResponse

logger = logging.getLogger(__name__)

_PROMPT = """You are a prompt classifier. Given the user's message and the project
context below, classify the prompt and identify relevant files.

<project_context>
{project_context}
</project_context>

<user_prompt>
{user_prompt}
</user_prompt>

Rules:
- classification must be one of: fix, create, improve, understand, test, configure, document, offtopic
- objective: one concise sentence describing what the user wants
- related_files: list file paths (relative) that are likely relevant — infer from
  the prompt text, project structure, and module names. Empty list if unclear.
- urgency: 'high' only if the user mentions errors, crashes, blocking issues, or
  uses urgent language; otherwise 'normal'

Respond ONLY with the structured output.
"""


class ClassifierAgent:
    """Runs a fast Haiku call to classify the user prompt before the main agent."""

    def __init__(self, cwd: str | None = None):
        self.cwd = cwd or os.getcwd()

    async def classify(
        self, prompt: str, session_id: str, bb: Blackboard
    ) -> ClassifierResponse | None:
        """Classify the user prompt and write results to the Blackboard.

        Writes to:
            session.{session_id}.pre_query.classification
            session.{session_id}.pre_query.objective
            session.{session_id}.pre_query.related_files
            session.{session_id}.pre_query.urgency

        Returns:
            The ClassifierResponse or None if classification failed.
        """
        # Build minimal project context from BB
        project_data = bb.get("project")
        if project_data:
            context_lines = []
            self._flatten(project_data, context_lines, "")
            project_context = "\n".join(context_lines)
        else:
            project_context = "(no project context available yet)"

        full_prompt = _PROMPT.format(
            project_context=project_context,
            user_prompt=prompt,
        )

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            model="haiku",
            output_format={
                "type": "json_schema",
                "schema": ClassifierResponse.model_json_schema(),
            },
        )

        result: ClassifierResponse | None = None

        try:
            async for message in query(prompt=full_prompt, options=options):
                msg_type = message.__class__.__name__

                if msg_type == "ResultMessage" and hasattr(message, "structured_output"):
                    structured = message.structured_output
                    if structured:
                        try:
                            result = ClassifierResponse(**structured)
                        except Exception as e:
                            logger.warning(f"classifier parse error: {e}")
                            result = None
        except Exception as e:
            logger.error(f"classifier agent failed: {e}", exc_info=True)
            return None

        if result:
            prefix = f"session.{session_id}.pre_query"
            await bb.set(f"{prefix}.classification", result.classification)
            await bb.set(f"{prefix}.objective", result.objective)
            await bb.set(f"{prefix}.related_files", result.related_files)
            await bb.set(f"{prefix}.urgency", result.urgency)
            logger.info(
                f"classified prompt as '{result.classification}' "
                f"objective='{result.objective}' files={result.related_files}"
            )
        else:
            logger.warning("classifier returned no result")

        return result

    @staticmethod
    def _flatten(data: dict, lines: list, prefix: str) -> None:
        """Flatten dict to readable lines for context."""
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                ClassifierAgent._flatten(value, lines, path)
            elif isinstance(value, list):
                if value and len(value) <= 10:
                    lines.append(f"{path}: {', '.join(str(v) for v in value)}")
                elif value:
                    lines.append(f"{path}: ({len(value)} items)")
                else:
                    lines.append(f"{path}: []")
            else:
                lines.append(f"{path}: {value}")
