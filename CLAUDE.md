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
- **`termuxcode/ws_connection.py`**: Handles individual WebSocket connections
  - Creates a `ClaudeSDKClient` from `claude-agent-sdk`
  - Manages session resumption via `resume_id` query parameter
  - Handles `AskUserQuestion` tool specially - extracts questions, sends to frontend, waits for response, sends back to SDK via `_transport.write()`
- **`termuxcode/message_converter.py`**: Converts SDK messages (AssistantMessage, ResultMessage) to WebSocket JSON format. Filters out `AskUserQuestion` from normal assistant messages.
- **`termuxcode/ws_config.py`**: Configuration and logging setup (log file: `~/.termuxcode/websocket_server.log`)
- **`termuxcode/desktop_server.py`**: Entry point for PyInstaller-built sidecar on desktop

### Frontend (static/)
- Served from localhost:8000
- Single-page WebSocket client connecting to ws://localhost:8769
- Handles `ask_user_question` messages as modal prompts

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
2. `ws_connection.py` detects this via `MessageConverter.extract_ask_user_question()`
3. Questions are sent to frontend via WebSocket message type `ask_user_question`
4. Frontend shows modal, user selects answers
5. Frontend sends `question_response` message back
6. `ws_connection.py` formats response as `tool_result` and sends to SDK via `_transport.write()`

## Ports

- HTTP: 8000 (static files)
- WebSocket: 8769 (SDK communication)

## Version Sync

When releasing, update version in:
- `pyproject.toml` (project.version)
- `package.json` (version)
- `termuxcode/__init__.py` (__version__)
