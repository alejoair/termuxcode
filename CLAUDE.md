# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TERMUXCODE is a Claude Code client with two deployment modes:
1. **Termux/Android**: Python package (`pip install termuxcode`) running WebSocket + HTTP servers
2. **Desktop**: Tauri app (Windows/macOS/Linux) with embedded Python sidecar

## Architecture

### Backend (Python)
- **`termuxcode/cli.py`**: Entry point for the `termuxcode` command. Spawns two subprocesses:
  - `serve.py` - HTTP server (port 8000) serving static files from `static/`
  - `ws_server.py` - WebSocket server (port 8769) using `websockets` library
- **`termuxcode/connection/`**: Modular WebSocket connection handling, fully isolated per-tab:
  - `session.py` - `Session` class: encapsulates ALL per-tab resources (LspManager, SDKClient, hooks, handlers, processor). Lifecycle: `create()` / `resume()` / `destroy()`. Each tab gets its own LSP servers with independent `rootUri`.
  - `session_registry.py` - Global registry: `session_id → WebSocketConnection` mapping. Used by `ws_server.py` for reconnection lookups. Session manages registration/unregistration via `_known_session_ids` set.
  - `base.py` - `WebSocketConnection` thin wrapper: connects WebSocket lifecycle to `Session`. Only handles WebSocket I/O (message loop) and delegates all logic to `Session`.
  - `sdk_client.py` - `SDKClient` wrapper for `ClaudeSDKClient` (connect, query, receive, interrupt, resume). Accepts a per-session `LspManager` instance and creates LSP hooks via closure factories.
  - `sender.py` - `MessageSender` sends typed JSON messages to the frontend WebSocket. Supports buffer/replay for reconnection.
  - `message_processor.py` - `MessageProcessor` processes user messages from the queue, iterates SDK responses, handles stop signals
  - `ask_handler.py` - `AskUserQuestionHandler` detects `AskUserQuestion` tool use, sends questions to frontend, waits for response, sends tool_result back to SDK
  - `tool_approval_handler.py` - `ToolApprovalHandler` implements `can_use_tool` callback for tool approval flow
  - `history_manager.py` - `truncate_history()` trims SDK conversation history JSONL files before each query
  - `lsp_client.py` - `LSPClient` generic LSP client over stdio (JSON-RPC). Manages lifecycle (start/shutdown), text sync (didOpen/didChange/didClose), queries (documentSymbol, hover, references), and diagnostics caching per URI.
  - `lsp_manager.py` - `LspManager` (per-session instance): registry of LSP servers by extension (`SERVERS` dict) + semantic analyzer. Auto-discovers available servers (`shutil.which`), provides `analyze_file()` (symbols + hover + references), `validate_file()` (LSP diagnostics), and baseline comparison for edit validation. Each `Session` creates its own `LspManager` with its own `rootUri`.
  - `hooks.py` - SDK hooks via LSP as **closure factories**: `make_pre_tool_use_hook(lsp_manager)`, `make_post_tool_use_read_hook(lsp_manager)`, `make_post_tool_use_edit_hook(lsp_manager)`. Each factory captures a session's `LspManager` by closure, ensuring per-session isolation.
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
- **`static/js/connection.js`**: WebSocket connection lifecycle per tab, auto-reconnect with timer cancellation
- **`static/js/modals.js`**: AskUserQuestion, tool approval, and file view modals
- **`static/js/storage.js`**: Tab persistence via localStorage
- **`static/js/haptics.js`**: Haptic feedback (vibration) for connect/disconnect/error events on mobile
- **`static/js/pipeline.js`**: Ambient pipeline background canvas animation (replaces starfield), transitions between idle/work states

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

## Key Flow: Session Lifecycle

Each browser tab maps to one `Session` with fully isolated resources:

```
ws_server.py handle_connection(websocket)
  ├─ resume_id? → session_registry.get(resume_id)
  │    ├─ found → conn.reconnect(ws, opts, cwd)
  │    │           └─ session.resume(ws, opts, cwd)
  │    │                ├─ _destroy_resources() [LSP + SDK + tasks]
  │    │                └─ create(ws) [new LspManager + SDK + hooks + processor]
  │    └─ not found → new connection (error to frontend)
  └─ new tab → WebSocketConnection(ws, resume_id, cwd, opts)
                 └─ session.create(ws)
                      ├─ LspManager() → initialize(cwd) in background
                      ├─ Hooks: make_*_hook(lsp_manager) → closures
                      ├─ SDKClient(lsp_manager, hooks) → connect()
                      ├─ Handlers: AskHandler, ToolApprovalHandler
                      ├─ MessageProcessor → start in background
                      └─ session_registry.register(session_id, connection)
```

**Per-session resources** (no sharing between tabs):
- `LspManager` — own LSP servers with own `rootUri` (different CWDs)
- `SDKClient` — own Claude SDK process with own hooks
- `MessageSender` — own WebSocket + buffer
- `AskUserQuestionHandler` / `ToolApprovalHandler` — own cancel events
- `MessageProcessor` — own asyncio.Queue and asyncio.Task

**Cleanup flow**: `Session.destroy()` cancels processor task → disconnects SDK → shuts down LSP → resets handlers → unregisters all session_ids from `session_registry`.

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
2. **Backend receives as `resume_id`** in `ws_server.py`, looks up `session_registry.get(resume_id)` for reconnection or creates a new `WebSocketConnection` → `Session`
3. **Session registers** the session_id in `session_registry` via `register(session_id, connection)`, tracked in `_known_session_ids` for multi-ID mapping (re-key)
4. **SDK uses it for resume** via `ClaudeAgentOptions.resume = resume_id`
5. **ResultMessage contains session_id** from SDK, which is:
   - Saved in `MessageProcessor._session_id` for `truncate_history()`
   - Registered in `session_registry` via `on_session_id_update` callback
   - Sent back to frontend via `send_session_id()` to persist for reconnection
6. **History truncation** uses `session_id` to find `~/.claude/projects/{project}/{session_id}.jsonl`

### Tab Re-Key

When the SDK sends a `session_id`, the frontend migrates the tab's temporary ID (`tab_xxx`) to the real session_id:

1. Backend sends `{"type": "session_id", "session_id": "abc123"}`
2. Frontend deletes old key from `state.tabs` Map, updates `tab.id` to `abc123`, re-inserts
3. DOM attribute `data-tab-id` is updated on the tab element
4. `state.activeTabId` is updated if the active tab was re-keyed
5. `tab.sessionId` is set for future reconnection
6. WebSocket handlers in `connection.js` resolve `tab.id` dynamically (not via captured closure) so they work correctly after re-key

Note: The SDK client does NOT expose `session_id` directly after `connect()`. It only arrives in `ResultMessage` during streaming.

## Key Flow: Reconnection Buffer

When WebSocket disconnects, messages are preserved for reconnection:

1. **Session Registry**: `session_registry` module maps `session_id → WebSocketConnection`. Each `Session` registers all known IDs via `_known_session_ids` set.
2. **On WebSocket close**: `Session.detach_websocket()` detaches WebSocket and calls `cancel()` on handlers (AskHandler, ToolApprovalHandler) to unblock any pending waits. SDK continues running.
3. **MessageSender buffer**: `_send_or_buffer()` accumulates messages in `_buffer` list when no WebSocket. Buffer has `MAX_BUFFER_SIZE = 1000` with FIFO eviction.
4. **On reconnect**: `ws_server.py` looks up `session_registry.get(resume_id)` → finds the existing `WebSocketConnection` → calls `conn.reconnect()` → `session.resume()` destroys old SDK/LSP and creates fresh ones → `replay_buffer()` sends accumulated messages.
5. **Session update**: When SDK generates new session_id, `on_session_id_update` callback registers the new ID in `session_registry`. Registry keeps ALL previous IDs mapping to the same connection (`_known_session_ids` set). This ensures reconnection works even with stale session_ids.
6. **Timeouts**: No timeouts on `Event.wait()` calls — only `_cancel_event` for immediate unblock on disconnect. Waits block indefinitely until the frontend responds or the WebSocket disconnects (which triggers `cancel()`). Sessions live forever until explicitly cleaned up via `Session.destroy()`.
7. **Frontend**: `connection.js` cancels old reconnect timers before creating new connections. UI calls `hideLoading()` on disconnect to prevent stuck loading states.

## Agent Options

Frontend can pass options via query string `?options=<json>`:

- `permission_mode`: Tool approval mode (e.g., "auto", "interactive")
- `model`: Model override (e.g., "claude-sonnet-4-6")
- `system_prompt` / `append_system_prompt`: Custom system prompts
- `max_turns`: Maximum agent turns
- `rolling_window`: History truncation window (default: 100)
- `allowed_tools` / `disallowed_tools`: Comma-separated tool names

## Key Flow: Per-Tab CWD

Each tab has its own CWD (working directory) independent of the backend's `os.getcwd()`:

1. **New tab**: Frontend passes `cwd` via WebSocket query string (Tauri uses folder picker, browser uses backend default)
2. **Backend sends CWD** after SDK connects via `sender.send_cwd()` → `{"type": "cwd", "cwd": "/path"}`
3. **Frontend stores** `tab.cwd` and persists to localStorage via `saveTabs()`
4. **Reconnection**: Frontend sends stored `tab.cwd` in query string, backend passes to `conn.reconnect(cwd=cwd)` which updates `self.cwd`
5. **Session rebuild**: When SDK is rebuilt on reconnect, it uses the updated `self.cwd` for `ClaudeAgentOptions.cwd`

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
- `{type: "session_id", session_id}`: New session ID from SDK (triggers tab re-key)
- `{type: "cwd", cwd}`: Working directory for the session
- `{type: "system", message}`: System status message
- `{type: "ask_user_question", questions}`: AskUserQuestion modal
- `{type: "tool_approval_request", tool_name, input}`: Tool approval modal
- `{type: "file_view", file_path, content}`: File content for viewing

## Design: OLED Dark Theme

The UI is optimized for OLED screens (Android/Termux nighttime use):
- **Pure black `#000000`** backgrounds — pixels off, zero battery drain
- **Text `#e4e4e7`** instead of pure white — less eye strain at night
- **Low-opacity surfaces** (4-7%) for subtle depth without pixel illumination
- **Muted accents** — primary blues/purples slightly desaturated to reduce glare
- **Reduced glow intensity** — working state animations use dimmer text-shadows
- **Pipeline canvas** — pure black fill, pipe strokes at 40% opacity/45% lightness

All colors flow through `static/css/variables.css`. The only hardcoded exceptions are the pipeline canvas in `pipeline.js` and a few `base.css` glow colors. The `manifest.json` also uses `background_color: #000000`.

## Key Flow: LSP Hooks

SDK hooks enrich Claude's understanding of code and prevent errors via Language Server Protocol:

**Architecture**: Each `Session` creates its own `LspManager` instance (in `lsp_manager.py`), which manages a registry of LSP clients (`LSPClient` in `lsp_client.py`), one per file extension. Servers are auto-discovered per-session via `shutil.which`. Supported extensions: `.py` (pylsp), `.ts/.js/.tsx/.jsx` (typescript-language-server), `.go` (gopls).

**Per-Session Isolation**: Hooks are created via closure factories in `hooks.py` (`make_pre_tool_use_hook(lsp_manager)`, `make_post_tool_use_read_hook(lsp_manager)`, `make_post_tool_use_edit_hook(lsp_manager)`). Each factory captures a session's `LspManager` by closure, ensuring that each tab's hooks operate on its own LSP servers with its own `rootUri`. LSP initialization is non-blocking — `session.create()` launches `lsp_manager.initialize(cwd)` in background via `asyncio.create_task`. Hooks check `lsp_manager._initialized` and passthrough if not ready.

1. **PostToolUse Read** (`matcher="Read"`): When Claude reads a supported file, `LspManager.analyze_file()` injects semantic context via `additionalContext`:
   - **Signatures**: Top-level symbols with hover info (full type signatures via `textDocument/hover`)
   - **Methods**: Class methods with hover signatures
   - **References**: Cross-file usages of classes/functions via `textDocument/references` — shows which files and lines reference each symbol. Limited to 10 symbols × 8 refs each.
   - Uses `textDocument/documentSymbol` for hierarchical symbol discovery
2. **PreToolUse Write|Edit** (`matcher="Write|Edit"`): Before writing/editing, validates the resulting code via LSP diagnostics (`textDocument/publishDiagnostics`). For **Edit**, reads the current file, applies `old_string → new_string` replacement in memory, and validates the complete result. On new errors → returns `{"decision": "block", "reason": "..."}` and Claude auto-corrects.

   **Baseline Check**: The hook takes a snapshot of current diagnostics before the edit. If the file already had errors → allows the edit (Claude is fixing something broken). If the file was clean and the edit introduces errors → blocks with an educational reason.
3. **PostToolUse Write|Edit** (`matcher="Write|Edit"`): After writing, reports all LSP diagnostics (errors, warnings, info) from the cached diagnostics as `additionalContext`.
4. Unsupported files pass through untouched (only extensions with a running LSP server trigger analysis).
5. The `_dummy_hook` with `matcher=None` remains for `can_use_tool` compatibility.

### LSP Protocol Notes

- `LSPClient` communicates over stdio via JSON-RPC with Content-Length headers
- File sync uses full-content mode (`didOpen`/`didChange` with full text)
- Diagnostics are cached per URI and signaled via `asyncio.Event` for `wait_diagnostics()`
- All LSP positions are 0-based (line and character)
- Server startup is non-blocking — `Session.create()` initializes LSP in background via `asyncio.create_task`
- On `Session.destroy()`, LSP servers are shut down (`lsp_manager.shutdown()`), releasing all resources

Dependencies: LSP servers must be installed separately (`pylsp`, `typescript-language-server`, `gopls`). Servers not found are silently skipped.

## Version Sync

When releasing, update version in:
- `pyproject.toml` (project.version)
- `package.json` (version)
- `termuxcode/__init__.py` (__version__)
