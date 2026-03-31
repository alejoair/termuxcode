# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

termuxcode is a Claude Code client with two deployment modes:
1. **Termux/Android**: Python package (`pip install termuxcode`) running WebSocket + HTTP servers
2. **Desktop**: Tauri app (Windows/macOS/Linux) with embedded Python sidecar

## Architecture

### Backend (Python)
- **`termuxcode/cli.py`**: Entry point for the `termuxcode` command. Spawns two subprocesses:
  - `serve.py` - HTTP server (port 8000) serving static files from `static/`
  - `ws_server.py` - WebSocket server (port 8769) using `websockets` library
- **`termuxcode/connection/`**: Modular WebSocket connection handling:
  - `base.py` - `WebSocketConnection` orchestrator: sets up SDK client, sender, processors, and message queue
  - `sdk_client.py` - `SDKClient` wrapper for `ClaudeSDKClient` (connect, query, receive, interrupt, resume)
  - `sender.py` - `MessageSender` sends typed JSON messages to the frontend WebSocket
  - `message_processor.py` - `MessageProcessor` processes user messages from the queue, iterates SDK responses, handles stop signals
  - `ask_handler.py` - `AskUserQuestionHandler` detects `AskUserQuestion` tool use, sends questions to frontend, waits for response, sends tool_result back to SDK
  - `tool_approval_handler.py` - `ToolApprovalHandler` implements `can_use_tool` callback for tool approval flow
  - `history_manager.py` - `truncate_history()` trims SDK conversation history JSONL files before each query
- **`termuxcode/message_converter.py`**: Converts SDK messages (AssistantMessage, ResultMessage) to WebSocket JSON format. Filters out `AskUserQuestion` from normal assistant messages.
- **`termuxcode/ws_config.py`**: Configuration and logging setup (log file: `~/.termuxcode/websocket_server.log`)
- **`termuxcode/desktop_server.py`**: Entry point for PyInstaller-built sidecar on desktop. On Windows, patches `subprocess.Popen` with `CREATE_NO_WINDOW` to prevent ghost console windows.

### Frontend (static/)
- Served from localhost:8000
- Single-page WebSocket client connecting to ws://localhost:8769
- **`static/app.js`**: Entry point, initializes Framework7, starfield background, and typewriter header effect
- **`static/js/state.js`**: Global state and DOM references
- **`static/js/ui.js`**: Message rendering, loading/working state management
- **`static/js/tabs.js`**: Tab management, send/stop/disconnect commands
- **`static/js/connection.js`**: WebSocket connection lifecycle per tab
- **`static/js/modals.js`**: AskUserQuestion, tool approval, and file view modals
- **`static/js/storage.js`**: Tab persistence via localStorage

### Desktop (Tauri)
- **`src-tauri/src/lib.rs`**: On desktop only, spawns Python `termuxcode-server` sidecar via Tauri's shell plugin
- On Android, backend runs separately via Termux - app just loads http://localhost:8000

## Common Commands

### Development
```bash
# Install package in editable mode
pip install -e .

# Run both servers (HTTP + WebSocket)
termuxcode

# Run only WebSocket server
termuxcode --ws

# Run only HTTP server
termuxcode --http

# Build Python sidecar (desktop only)
pyinstaller pyinstaller.spec --distpath src-tauri/binaries
```

### Publishing (Automatic via GitHub Actions on tags)
```bash
# 1. Update version in both pyproject.toml and package.json
# 2. Create and push tag
git tag v1.0.0
git push origin v1.0.0

# This triggers:
# - .github/workflows/build-release.yml → Builds Tauri apps + APKs, creates GitHub Release
# - .github/workflows/pypi.yaml → Publishes to PyPI
```

### Testing
```bash
# Check running processes
ps aux | grep termuxcode

# Kill all termuxcode processes
pkill -f termuxcode

# View logs
cat ~/.termuxcode/websocket_server.log
```

## Key Flow: AskUserQuestion

The tool `AskUserQuestion` requires special handling:
1. SDK sends `AssistantMessage` containing `ToolUseBlock` with name "AskUserQuestion"
2. `ask_handler.py` detects this via `MessageConverter.extract_ask_user_question()`
3. Questions are sent to frontend via WebSocket message type `ask_user_question`
4. Frontend shows modal, user selects answers
5. Frontend sends `question_response` message back
6. `ask_handler.py` formats response as `tool_result` and sends to SDK via `_transport.write()`

## Key Flow: Session ID

The session_id enables session resumption and history management:

1. **Frontend sends session_id** via WebSocket query string (`?session_id=xxx&cwd=/path`)
2. **Backend receives as `resume_id`** in `ws_server.py`, passes to `WebSocketConnection` and `SDKClient`
3. **SDK uses it for resume** via `ClaudeAgentOptions.resume = resume_id`
4. **ResultMessage contains session_id** from SDK, which is:
   - Saved in `MessageProcessor._session_id` for `truncate_history()`
   - Sent back to frontend to persist for reconnection
5. **History truncation** uses `session_id` to find `~/.claude/projects/{project}/{session_id}.jsonl`

Note: The SDK client does NOT expose `session_id` directly after `connect()`. It only arrives in `ResultMessage` during streaming.

## Key Flow: Reconnection Buffer

When WebSocket disconnects, messages are preserved for reconnection:

1. **Session Registry**: `_active_sessions` dict in `ws_server.py` maps session_id → WebSocketConnection
2. **On WebSocket close**: `_cleanup()` detaches WebSocket and calls `cancel()` on handlers to unblock any pending waits. SDK continues running.
3. **MessageSender buffer**: `_send_or_buffer()` accumulates messages in `_buffer` list when no WebSocket. Buffer has `MAX_BUFFER_SIZE = 1000` with FIFO eviction.
4. **On reconnect**: `base.py.reconnect()` calls `replay_buffer()` which sends all accumulated messages with partial-failure protection (unsent messages stay in buffer).
5. **Session update**: When SDK generates new session_id, registry keeps ALL previous IDs mapping to the same connection (`_known_session_ids` set). This ensures reconnection works even with stale session_ids.
6. **Timeouts**: All `Event.wait()` calls use `asyncio.wait()` with a timeout (30s for tool approval, 60s for AskUserQuestion) and a `_cancel_event` for immediate unblock on disconnect. On timeout/cancel, tools are denied and questions are cancelled so the SDK can continue.
7. **Frontend**: `connection.js` cancels old reconnect timers before creating new connections. UI calls `hideLoading()` on disconnect to prevent stuck loading states.

## Agent Options

Frontend can pass options via query string `?options=<json>`:

- `permission_mode`: Tool approval mode (e.g., "auto", "interactive")
- `model`: Model override (e.g., "claude-sonnet-4-6")
- `system_prompt` / `append_system_prompt`: Custom system prompts
- `max_turns`: Maximum agent turns
- `rolling_window`: History truncation window (default: 100)
- `allowed_tools` / `disallowed_tools`: Comma-separated tool names

## Key Flow: Working State Animations

When the agent is processing, visual feedback is provided:
1. `showLoading()` in `ui.js` activates starfield acceleration + header typewriter via `setWorking(true)`
2. `assistant` messages with `tool_use` blocks re-trigger `showLoading()` (agent still working)
3. `assistant` messages without tools only hide the typing indicator (animations continue)
4. `result` message calls `hideLoading()` which stops all animations
5. User interactions (AskUserQuestion response, tool approval) re-activate animations

## Ports

- HTTP: 8000 (static files)
- WebSocket: 8769 (SDK communication)

## WebSocket Message Types

**Frontend → Backend:**
- `{content, attachments}`: User chat message
- `{command: "/stop"}`: Stop current operation
- `{type: "tool_approval_response", ...}`: Tool approval decision
- `{type: "question_response", responses, cancelled}`: AskUserQuestion response
- `{type: "request_buffer_replay"}`: Request buffered messages on reconnect

**Backend → Frontend:**
- `{type: "assistant", blocks}`: Assistant message with content blocks
- `{type: "result", ...}`: SDK result message
- `{type: "session_id", session_id}`: New session ID from SDK
- `{type: "system", message}`: System status message
- `{type: "ask_user_question", questions}`: AskUserQuestion modal
- `{type: "tool_approval_request", tool_name, input}`: Tool approval modal
- `{type: "file_view", file_path, content}`: File content for viewing

## Version Sync

When releasing, update version in:
- `pyproject.toml` (project.version)
- `package.json` (version)
- `termuxcode/__init__.py` (__version__)
