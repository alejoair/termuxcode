"""Pydantic model for the pre-query classifier agent."""
from typing import Annotated

from pydantic import BaseModel, Field


class ClassifierResponse(BaseModel):
    """Quick classification of the user's prompt before the main agent runs."""

    classification: Annotated[
        str,
        Field(description=(
            "Category: 'fix' for bugs/errors, 'create' for new features, "
            "'improve' for refactors, 'understand' for explanations, "
            "'test' for tests, 'configure' for setup/deps, "
            "'document' for docs, 'offtopic' for non-coding."
        )),
    ]

    objective: Annotated[
        str,
        Field(description="One-line summary of what the user wants to achieve."),
    ]

    related_files: Annotated[
        list[str],
        Field(
            default_factory=list,
            description=(
                "File paths likely relevant to this task, inferred from the prompt "
                "and project structure. Use relative paths."
            ),
        ),
    ]

    urgency: Annotated[
        str,
        Field(
            default="normal",
            description="'high' if the user seems blocked or frustrated, else 'normal'.",
        ),
    ]
