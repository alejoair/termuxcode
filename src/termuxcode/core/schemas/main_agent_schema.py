"""Pydantic models for main agent structured output."""
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class PromptClassification(str, Enum):
    """Classification of user prompt type."""
    SINGLE_TASK = "single_task"
    RESEARCH = "research"
    PLAN = "plan"
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    EXPLANATION = "explanation"
    OFFTOPIC = "offtopic"
    META = "meta"


class TaskPhase(str, Enum):
    """Current phase of the task."""
    PLANIFICACION = "planificacion"
    IMPLEMENTACION = "implementacion"
    TESTING = "testing"
    DEBUGGING = "debugging"
    ANALISIS = "analisis"
    OTRO = "otro"


class Tag(str, Enum):
    """Message severity tag."""
    WARNING = "WARNING"
    ERROR = "ERROR"
    INFO = "INFO"
    SUCCESS = "SUCCESS"


class MainAgentResponse(BaseModel):
    """Structured response from the main agent.

    Fill this alongside every response to help the system manage
    conversation history, prioritize context, and track task progress.
    """
    user_prompt_objective: str = Field(
        description="One-line summary of what the user is trying to achieve with this prompt. Be specific: 'fix TypeError in login handler' not 'fix bug'."
    )
    user_prompt_classification: PromptClassification = Field(
        description="Category that best matches the user's intent. Use 'single_task' for quick one-off requests, 'meta' for questions about the agent itself, 'offtopic' for non-coding chat."
    )
    next_suggested_immediate_action: str = Field(
        description="Concrete next step the agent should take after this turn. Example: 'run pytest to verify the fix', 'read auth.py to understand the middleware chain'. Should be actionable, not vague."
    )
    is_useful_to_record_in_history: bool = Field(
        description="False for trivial exchanges that add no context for future turns: greetings, confirmations ('ok', 'thanks'), offtopic chat, or repeated information. True for anything that contains code changes, decisions, error analysis, or context the agent may need later."
    )
    advances_current_task: bool = Field(
        description="True if this turn made concrete progress: wrote/modified code, identified root cause, produced a plan, or gathered needed information. False for clarifying questions, failed attempts that yielded no insight, or unrelated tangents."
    )
    task_phase: TaskPhase = Field(
        description="Current phase: 'planificacion' when designing approach or gathering requirements, 'implementacion' when writing/editing code, 'testing' when running or writing tests, 'debugging' when diagnosing failures, 'analisis' when reading/understanding code without modifying it, 'otro' for everything else."
    )
    related_files: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list,
        description="Relative paths of files read, modified, or directly relevant in this turn. Include only files actually touched or referenced, not the entire codebase. Empty list if no files involved."
    )
    tag: Tag = Field(
        default=Tag.INFO,
        description="WARNING: agent encountered something unexpected that may need user attention. ERROR: the turn failed or produced an error. SUCCESS: a milestone was completed (tests pass, feature done, bug fixed). INFO: normal informational response (default)."
    )
    self_reflection: str | None = Field(
        default=None,
        description="Brief honest assessment of this turn's quality: what went well, what could be improved, any uncertainty or assumptions made. Null if not applicable (trivial exchange)."
    )
    personal_goal: str | None = Field(
        default=None,
        description="Short-term goal the agent is working towards across multiple turns, e.g. 'complete auth refactor' or 'get all tests passing'. Null if there is no ongoing multi-turn goal."
    )