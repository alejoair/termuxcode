"""Pydantic models for overview agent structured output."""
from pydantic import BaseModel, Field


class OverviewAgentResponse(BaseModel):
    """Flat structured output of the overview agent.
    Kept flat intentionally to avoid $defs in JSON schema, which breaks StructuredOutput tool.
    """
    name: str | None = Field(default=None, description="Project name as defined in manifest or root directory name.")
    description: str | None = Field(default=None, description="One-paragraph description of what the project does, written for a developer seeing it for the first time.")
    purpose: str | None = Field(default=None, description="The core problem this project solves and why it exists.")
    target_platform: str | None = Field(default=None, description="Target platforms or environments (e.g. 'Android/Termux, Windows, Linux').")
    tech_stack: str | None = Field(default=None, description="Comma-separated list of main technologies, frameworks and libraries.")
    how_to_install: str | None = Field(default=None, description="Exact commands to install the project from scratch.")
    how_to_run: str | None = Field(default=None, description="Exact commands to run the project after installation.")
    how_to_test: str | None = Field(default=None, description="Exact commands to run the test suite.")
    key_concepts: list[str] = Field(default_factory=list, description="Core concepts a developer must understand to work on this project. Each item is a short phrase with a one-sentence explanation.")
    user_facing_features: list[str] = Field(default_factory=list, description="Main features visible to end users. Each item is a short description.")
    developer_notes: str | None = Field(default=None, description="Anything unusual, non-obvious, or important that a developer should know before making changes. Gotchas, conventions, known limitations.")
