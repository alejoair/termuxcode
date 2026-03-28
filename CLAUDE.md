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
  - `ask_handler.py` - `AskHandler` detects `AskUserQuestion` tool use, sends questions to frontend, waits for response, sends tool_result back to SDK
  - `tool_approval_handler.py` - `ToolApprovalHandler` implements `can_use_tool` callback for tool approval flow
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

## Version Sync

When releasing, update version in:
- `pyproject.toml` (project.version)
- `package.json` (version)
- `termuxcode/__init__.py` (__version__)
