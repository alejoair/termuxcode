"""TUI para Claude Agent SDK - Chat Interface"""

from .app import ClaudeChat
from .history import MessageHistory
from .filters import HistoryPreprocessor
from .structured_response import (
    StructuredResponse,
    ResponseMetadata,
    parse_structured_output,
    STRUCTURED_RESPONSE_SCHEMA,
    format_phase_badge,
    format_advances_badge,
    format_classification_badge,
    format_suggestion_box,
    format_agent_feedback,
)
from .feedback_filter import (
    FeedbackFilter,
    FeedbackFilterConfig,
    FeedbackHistory,
    FilteredAgentFeedback,
    format_filtered_feedback,
)
