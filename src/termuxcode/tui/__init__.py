"""TUI para Claude Agent SDK - Chat Interface"""

from .app import ClaudeChat
from .history import MessageHistory
from .filters import FilterConfig, HistoryPreprocessor, preprocess_history
from .structured_response import (
    StructuredResponse,
    ResponseMetadata,
    parse_structured_output,
    STRUCTURED_RESPONSE_SCHEMA,
    STRUCTURED_RESPONSE_PROMPT_TEMPLATE,
    format_phase_badge,
    format_advances_badge,
    format_suggestion_box,
)

__all__ = [
    'ClaudeChat',
    'MessageHistory',
    'FilterConfig',
    'HistoryPreprocessor',
    'preprocess_history',
    # Structured response
    'StructuredResponse',
    'ResponseMetadata',
    'parse_structured_output',
    'STRUCTURED_RESPONSE_SCHEMA',
    'STRUCTURED_RESPONSE_PROMPT_TEMPLATE',
    'format_phase_badge',
    'format_advances_badge',
    'format_suggestion_box',
]
