"""Pydantic models for architecture agent structured output."""
from pydantic import BaseModel, Field


class ArchitectureAgentResponse(BaseModel):
    """Flat structured output of the architecture agent.
    Kept flat intentionally to avoid $defs in JSON schema, which breaks StructuredOutput tool.
    """
    modules: list[str] = Field(default_factory=list, description="Top-level module paths relative to source dir (e.g. 'core/memory', 'tui/screens').")
    module_roles: str = Field(default="", description="JSON string mapping each module to a one-line description of its responsibility.")
    entry_points: list[str] = Field(default_factory=list, description="Files where execution starts (e.g. 'cli.py', 'tui/app.py').")
    dependencies_map: str = Field(default="", description="JSON string mapping each module to a list of internal modules it imports from.")
    base_classes: list[str] = Field(default_factory=list, description="Key base classes or ABCs that other classes inherit from.")
    patterns: list[str] = Field(default_factory=list, description="Architectural patterns detected (e.g. 'observer in events', 'repository in db').")
