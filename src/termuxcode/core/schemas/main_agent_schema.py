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

    This model captures the agent's analysis of user prompts and
    its self-reflection on the current task state.
    """
    user_prompt_objective: str = Field(
        description="Extracted objective from the user's prompt"
    )
    user_prompt_classification: PromptClassification = Field(
        description="Classification of the prompt type"
    )
    next_suggested_immediate_action: str = Field(
        description="Suggested next action to take"
    )
    is_useful_to_record_in_history: bool = Field(
        description="Whether this interaction should be saved to history"
    )
    advances_current_task: bool = Field(
        description="Whether this response advances the current task"
    )
    task_phase: TaskPhase = Field(
        description="Current phase of the task"
    )
    related_files: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list,
        description="List of files related to this interaction"
    )
    tag: Tag = Field(
        default=Tag.INFO,
        description="Severity/importance tag for this response"
    )
    self_reflection: str | None = Field(
        default=None,
        description="Agent's self-reflection on its performance"
    )
    personal_goal: str | None = Field(
        default=None,
        description="Current personal goal the agent is working towards"
    )