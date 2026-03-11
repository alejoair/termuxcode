# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Run the TUI
textual run src/termuxcode/tui.py
# or
python -m termuxcode.tui

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/
```

## Architecture

### Project Structure

```
termuxcode/
├── src/termuxcode/
│   ├── tui/                    # TUI module
│   │   ├── app.py             # Main Textual app (ClaudeChat)
│   │   ├── agent.py           # Claude Agent SDK client
│   │   ├── chat.py            # Chat widget (RichLog subclass)
│   │   └── styles.py          # Responsive CSS
```

### Core Components

**`app.py` - Main TUI App**
- `ClaudeChat(App)`: Main Textual application
- Composes: Header, ChatLog, Input
- Uses responsive breakpoints: `-small` (<60 chars), `-medium` (60-100), `-large` (>100)
- Header hidden on small screens

**`agent.py` - SDK Client**
- `AgentClient`: Communicates with Claude Agent SDK using stateless `query()`
- Processes: `AssistantMessage`, `UserMessage`, `ResultMessage`
- Uses `ClaudeAgentOptions` with `bypassPermissions`, `max_budget_usd=0.10`
- Note: Current implementation is incomplete - rolling window system not yet implemented

**`chat.py` - Chat Widget**
- `ChatLog(RichLog)`: Displays messages with markup
- Methods: `write_user()`, `write_assistant()`, `write_tool()`, `write_result()`, `write_error()`
- Tool/result previews limited to 2 lines

### Data Flow

1. User input → `Input.Submitted` → `_run_query(prompt)`
2. Agent receives prompt → `query()` calls SDK
3. SDK streams messages → `_process_message()` → updates ChatLog
4. ChatLog auto-scrolls to latest message

### Important Implementation Notes

- **SDK is stateless**: Each `query()` call is independent. No native session management in current implementation.
- **Textual responsive**: Uses CSS classes `Screen.-small/medium/large` for breakpoints
- **Async everywhere**: All SDK/UI interactions use `async/await`
- **CLAUDECODE environment**: SDK pops `CLAUDECODE` env var during queries

### Dependencies

- `claude-agent-sdk==0.1.48` - Claude Agent SDK
- `textual==8.0.0` - TUI framework

Python 3.12+ required.
