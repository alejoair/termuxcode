"""Agent that builds a high-level overview of the project and writes it to the blackboard."""
import logging
import os

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.schemas.overview_agent_schema import OverviewAgentResponse
from termuxcode.core.memory.blackboard import Blackboard
from termuxcode.core.agents.agent_utils import get_missing_fields, build_partial_schema

logger = logging.getLogger(__name__)

FIELD_MAP = {
    "project.overview.name": "name",
    "project.overview.description": "description",
    "project.overview.purpose": "purpose",
    "project.overview.target_platform": "target_platform",
    "project.overview.tech_stack": "tech_stack",
    "project.overview.how_to_install": "how_to_install",
    "project.overview.how_to_run": "how_to_run",
    "project.overview.how_to_test": "how_to_test",
    "project.overview.key_concepts": "key_concepts",
    "project.overview.user_facing_features": "user_facing_features",
    "project.overview.developer_notes": "developer_notes",
}

_BASE_PROMPT = """
You are a project analyst. Your job is to understand the project at the current
working directory and produce a comprehensive, detailed overview.

Steps:
1. Read the README.md and/or CLAUDE.md if they exist.
2. Read the main manifest (pyproject.toml, package.json, Cargo.toml, etc.).
3. Explore the source directory structure 2-3 levels deep.
4. Read 2-3 key files (entry point, main module, config) to understand the project.
5. If there are scripts or Makefile, read them to understand install/run/test commands.
6. Synthesize everything into the structured output.

Guidelines for each field:
- name: The project name from the manifest, not the directory name.
- description: Write a clear, detailed paragraph. Assume the reader is a developer
  who has never seen this project. Explain what it does, how it works at a high level,
  and what makes it different from similar tools.
- purpose: Why does this project exist? What problem does it solve? Who is it for?
- target_platform: Be specific. Include OS, runtime environment, device types.
- tech_stack: List every significant technology, framework, and library. Include versions
  if visible in the manifest.
- how_to_install: Exact shell commands, from cloning to ready-to-run. Include prerequisites.
- how_to_run: The exact command(s) to start the project after installation.
- how_to_test: The exact command(s) to run tests. If no tests exist, say "No test suite found."
- key_concepts: List the 5-10 most important concepts. Each item should be a phrase
  followed by a colon and a one-sentence explanation. Example:
  "Blackboard memory: key-value store that persists project context across sessions"
  These should be things a new developer MUST understand to contribute effectively.
- user_facing_features: List the main features that an end user would see and use.
  Be specific. "Session management with tabs" is better than "sessions".
- developer_notes: Include gotchas, non-obvious conventions, known limitations,
  things that break easily, and anything a developer would wish they knew before
  their first PR. Be thorough — this is the most valuable field for onboarding.

Be thorough and detailed. Do not abbreviate. Do not summarize. Fill every field completely.
"""


class OverviewAgent:
    """Builds a high-level project overview and writes it to the blackboard."""

    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()

    async def run(self) -> None:
        """Run the overview scan and persist results to the blackboard."""
        bb = Blackboard("app")
        missing = get_missing_fields(FIELD_MAP, bb)

        if not missing:
            logger.info("all overview fields present, skipping agent")
            return

        # Inject context from previous agents
        context_keys = {
            "project.runtime.language": "Language",
            "project.runtime.version": "Version",
            "project.runtime.package_manager": "Package manager",
            "project.structure.source_dir": "Source directory",
            "project.structure.entry_point": "Entry point",
            "project.scripts.run": "Run command",
            "project.scripts.test": "Test command",
            "project.architecture.modules": "Modules",
            "project.architecture.module_roles": "Module roles",
            "project.architecture.patterns": "Patterns",
        }
        context_lines = []
        for bb_path, label in context_keys.items():
            val = bb.get(bb_path)
            if val is not None:
                context_lines.append(f"- {label}: {val}")

        all_missing = len(missing) == len(FIELD_MAP)
        schema = build_partial_schema(OverviewAgentResponse, missing)
        field_names = list(missing.values())

        context_block = ""
        if context_lines:
            context_block = (
                "\n\nAlready known about this project:\n"
                + "\n".join(context_lines)
                + "\nUse this info — do not re-discover it. Focus on understanding the big picture.\n"
            )

        if all_missing:
            prompt = _BASE_PROMPT + context_block
            final_schema = OverviewAgentResponse.model_json_schema()
        else:
            prompt = (
                _BASE_PROMPT
                + context_block
                + f"\nOnly fill these fields: {', '.join(field_names)}. "
                + "Leave no field empty."
            )
            final_schema = schema

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            model="opus",
            setting_sources=["project", "user"],
            tools=["Read", "LS", "Bash", "StructuredOutput"],
            output_format={
                "type": "json_schema",
                "schema": final_schema,
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
                    await self._persist(structured, missing)
                    logger.info("persisted overview to blackboard")

    async def _persist(self, structured: dict, missing: dict[str, str]) -> None:
        """Write only the missing fields from structured output to the blackboard."""
        bb = Blackboard("app")
        for bb_path, schema_field in missing.items():
            value = structured.get(schema_field)
            if value is not None:
                await bb.set(bb_path, value)
