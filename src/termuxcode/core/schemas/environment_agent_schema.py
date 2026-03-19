"""Pydantic models for environment recognition agent structured output."""
from pydantic import BaseModel, Field


class EnvironmentAgentResponse(BaseModel):
    """Flat structured output of the environment recognition agent.
    Kept flat intentionally to avoid $defs in JSON schema, which breaks StructuredOutput tool.
    """
    runtime_language: str | None = Field(default=None, description="Primary language detected (e.g. 'python', 'javascript', 'rust').")
    runtime_version: str | None = Field(default=None, description="Runtime version (e.g. '3.14', '20.11').")
    runtime_package_manager: str | None = Field(default=None, description="Package manager detected (e.g. 'pip', 'npm', 'cargo').")
    dependencies_main: list[str] = Field(default_factory=list, description="Production dependencies.")
    dependencies_dev: list[str] = Field(default_factory=list, description="Development/test dependencies.")
    structure_entry_point: str | None = Field(default=None, description="Main entry point relative path (e.g. 'src/cli.py').")
    structure_source_dir: str | None = Field(default=None, description="Source directory relative path (e.g. 'src/').")
    structure_test_dir: str | None = Field(default=None, description="Test directory relative path (e.g. 'tests/').")
    env_required: list[str] = Field(default_factory=list, description="Required environment variable names.")
    env_has_dotenv: bool = Field(default=False, description="True if .env or .env.example exists.")
    scripts_run: str | None = Field(default=None, description="Command to run the project (e.g. 'python -m termuxcode').")
    scripts_test: str | None = Field(default=None, description="Command to run tests (e.g. 'pytest').")
