"""Agent that scans the project architecture and writes results to the blackboard."""
import json
import logging
import os

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.schemas.architecture_agent_schema import ArchitectureAgentResponse
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.agents.agent_utils import get_missing_fields, build_partial_schema

logger = logging.getLogger(__name__)

# Maps blackboard paths to schema field names
FIELD_MAP = {
    "project.architecture.modules": "modules",
    "project.architecture.module_roles": "module_roles",
    "project.architecture.entry_points": "entry_points",
    "project.architecture.dependencies_map": "dependencies_map",
    "project.architecture.base_classes": "base_classes",
    "project.architecture.patterns": "patterns",
}

# Fields whose structured output is a JSON string that should be parsed to dict
_JSON_STRING_FIELDS = {"module_roles", "dependencies_map"}

_BASE_PROMPT = """
You are a project architecture scanner. Your only job is to inspect the project
at the current working directory and fill the structured output accurately.

Steps:
1. List the source directory 2-3 levels deep to identify all modules.
2. For each module directory, read 1-2 representative files to understand its role.
3. Trace import statements to build the internal dependency map between modules.
4. Identify entry point files (where execution starts: main, cli, app).
5. Identify base classes or ABCs that other classes inherit from.
6. Note any recurring architectural patterns (observer, repository, strategy, etc.).

For module_roles and dependencies_map, return valid JSON strings, not Python dicts.
Example module_roles: '{"core/memory": "key-value persistence and queues", "tui": "terminal UI screens"}'
Example dependencies_map: '{"tui": ["core/agents", "core/memory"], "core/agents": ["core/memory"]}'

Be concise. Do not explain. Only populate the structured output.
"""


class ArchitectureAgent:
    """Scans the project architecture and writes the result to the blackboard."""

    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()

    async def run(self) -> None:
        """Run the architecture scan and persist results to the blackboard."""
        bb = Blackboard("app")
        missing = get_missing_fields(FIELD_MAP, bb)

        if not missing:
            logger.info("all architecture fields present, skipping agent")
            return

        # Inject environment context if available
        context_keys = {
            "project.runtime.language": "Language",
            "project.structure.source_dir": "Source directory",
            "project.structure.entry_point": "Entry point",
        }
        context_lines = []
        for bb_path, label in context_keys.items():
            val = bb.get(bb_path)
            if val is not None:
                context_lines.append(f"- {label}: {val}")

        schema = build_partial_schema(ArchitectureAgentResponse, missing)
        field_names = list(missing.values())

        context_block = ""
        if context_lines:
            context_block = (
                "\n\nAlready known about this project:\n"
                + "\n".join(context_lines)
                + "\nUse this to guide your exploration.\n"
            )

        prompt = (
            _BASE_PROMPT
            + context_block
            + f"\nOnly fill these fields: {', '.join(field_names)}. "
            + "Leave no field empty."
        )

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            model="opus",
            setting_sources=["project", "user"],
            tools=["Read", "LS", "Bash", "StructuredOutput"],
            output_format={
                "type": "json_schema",
                "schema": schema,
            },
        )

        async for message in query(prompt=prompt, options=options):
            msg_type = message.__class__.__name__
            logger.debug(f"message: {msg_type}")

            if msg_type == "AssistantMessage":
                for block in getattr(message, "content", []):
                    block_type = block.__class__.__name__
                    if block_type == "ToolUseBlock":
                        logger.debug(f"tool_use: {block.name}")
                    elif block_type == "TextBlock":
                        logger.debug(f"text: {block.text[:80]}")

            elif msg_type == "UserMessage":
                for block in getattr(message, "content", []):
                    block_type = block.__class__.__name__
                    content = str(getattr(block, "content", vars(block)))[:300]
                    is_error = getattr(block, "is_error", None)
                    logger.debug(f"user_block type={block_type} is_error={is_error}: {content}")

            elif msg_type == "ResultMessage":
                structured = getattr(message, "structured_output", None)
                logger.info(f"structured_output raw: {structured}")
                logger.info(f"structured={bool(structured)}")
                if structured:
                    self._persist(structured, missing)
                    logger.info("persisted architecture to blackboard")

    def _persist(self, structured: dict, missing: dict[str, str]) -> None:
        """Write only the missing fields from structured output to the blackboard."""
        bb = Blackboard("app")
        for bb_path, schema_field in missing.items():
            value = structured.get(schema_field)
            if value is None:
                continue
            # Parse JSON string fields back to dicts
            if schema_field in _JSON_STRING_FIELDS and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            bb.set(bb_path, value)
