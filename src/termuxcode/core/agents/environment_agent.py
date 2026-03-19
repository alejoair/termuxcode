"""Agent that scans the project environment and writes results to the blackboard."""
import logging
import os

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.schemas.environment_agent_schema import EnvironmentAgentResponse
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.agents.agent_utils import get_missing_fields, build_partial_schema

logger = logging.getLogger(__name__)

# Maps blackboard paths to schema field names
FIELD_MAP = {
    "project.runtime.language": "runtime_language",
    "project.runtime.version": "runtime_version",
    "project.runtime.package_manager": "runtime_package_manager",
    "project.dependencies.main": "dependencies_main",
    "project.dependencies.dev": "dependencies_dev",
    "project.structure.entry_point": "structure_entry_point",
    "project.structure.source_dir": "structure_source_dir",
    "project.structure.test_dir": "structure_test_dir",
    "project.env.required": "env_required",
    "project.env.has_dotenv": "env_has_dotenv",
    "project.scripts.run": "scripts_run",
    "project.scripts.test": "scripts_test",
}

_BASE_PROMPT = """
You are a project environment scanner. Your only job is to inspect the project
at the current working directory and fill the structured output accurately.

Steps:
1. List the root directory (1-2 levels deep).
2. Read the dependency manifest (pyproject.toml, package.json, Cargo.toml, etc.).
3. Check for .env, .env.example, or any env reference files.
4. Detect the entry point and source/test directories.
5. Detect run/test scripts (Makefile, scripts section, etc.).

Be concise. Do not explain. Only populate the structured output.
"""


class EnvironmentAgent:
    """Scans the project environment and writes the result to the blackboard."""

    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()

    async def run(self) -> None:
        """Run the environment scan and persist results to the blackboard."""
        bb = Blackboard("app")
        missing = get_missing_fields(FIELD_MAP, bb)

        if not missing:
            logger.info("all environment fields present, skipping agent")
            return

        schema = build_partial_schema(EnvironmentAgentResponse, missing)
        field_names = list(missing.values())
        prompt = (
            _BASE_PROMPT
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
                    logger.info("persisted to blackboard")

    def _persist(self, structured: dict, missing: dict[str, str]) -> None:
        """Write only the missing fields from structured output to the blackboard."""
        bb = Blackboard("app")
        for bb_path, schema_field in missing.items():
            value = structured.get(schema_field)
            if value is not None:
                bb.set(bb_path, value)
