"""Pydantic models for main agent structured output."""
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class PromptClassification(str, Enum):
    """Classification of user prompt type."""
    UNDERSTAND = "understand"   # explain, review, audit code
    CREATE = "create"           # new feature, scaffold, integration
    FIX = "fix"                 # bug, broken behavior, error
    IMPROVE = "improve"         # refactor, optimization, cleanup
    TEST = "test"               # create or fix tests
    CONFIGURE = "configure"     # setup, env, dependencies
    DOCUMENT = "document"       # comments, README, docstrings
    OFFTOPIC = "offtopic"


class TaskPhase(str, Enum):
    """Current phase of the task."""
    EXPLORE = "explore"         # understand context and problem
    PLAN = "plan"               # decide approach
    IMPLEMENT = "implement"     # execute the plan
    VERIFY = "verify"           # check it worked


class MainAgentResponse(BaseModel):
    """Structured response from the main agent.

    Fill this alongside every response to help the system manage
    conversation history, prioritize context, and track task progress.
    """
    user_prompt_objective: str = Field(
        description="One-line summary of what the user is trying to achieve with this prompt. Be specific: 'fix TypeError in login handler' not 'fix bug'."
    )
    user_prompt_classification: PromptClassification = Field(
        description="Category that best matches the user's intent: 'understand' for explanations/reviews, 'create' for new features/scaffolding, 'fix' for bugs/errors, 'improve' for refactors/optimization, 'test' for writing/fixing tests, 'configure' for setup/env/deps, 'document' for comments/README/docstrings, 'offtopic' for non-coding chat."
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
        description="Current phase: 'explore' when understanding context or the problem, 'plan' when deciding the approach, 'implement' when writing/editing code, 'verify' when checking that the solution worked."
    )
    related_files: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list,
        description="Relative paths of files read, modified, or directly relevant in this turn. Include only files actually touched or referenced, not the entire codebase. Empty list if no files involved."
    )
    self_reflection: str | None = Field(
        default=None,
        description="Brief honest assessment of this turn's quality: what went well, what could be improved, any uncertainty or assumptions made. Null if not applicable (trivial exchange)."
    )
