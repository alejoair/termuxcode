# TermuxCode

[![PyPI version](https://img.shields.io/pypi/v/termuxcode.svg)](https://pypi.org/project/termuxcode/)
[![Python](https://img.shields.io/pypi/pyversions/termuxcode.svg)](https://pypi.org/project/termuxcode/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

**Terminal chat client for Claude Code** — A modern TUI for interacting with Claude Code on Android/Termux, desktop terminals, or via web browser.

---

## Features

- **Multi-session tabs** — Manage multiple conversations with `Ctrl+N` / `Ctrl+W`
- **Persistent history** — Each session saves its conversation automatically (JSONL format)
- **Background execution** — Switch tabs while queries continue running; get notified on completion
- **Web server mode** — Access from any browser with configurable DPI/font sizing
- **Blackboard memory** — Persist project context across sessions (`Ctrl+B` to view)
- **Structured responses** — Agent returns metadata for better context management
- **Markdown + syntax highlighting** — Rich rendering in terminal
- **Mobile-optimized** — Touch-friendly scrolling for Termux screens
- **Zero config** — Works out of the box with Claude Code CLI

---

## Requirements

- **Python 3.12+**
- **Claude Code CLI** installed first:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

---

## Installation

```bash
pip install termuxcode
```

---

## Usage

### Terminal Mode (TUI)

```bash
termuxcode                      # Launch TUI
termuxcode --dev                # TUI with debug tools
termuxcode --cwd /my/project    # Start in specific directory
```

### Web Server Mode

```bash
termuxcode --serve                          # Web server on 0.0.0.0:8001
termuxcode --serve --port 8080 --fs 24      # Custom port and font size
```

Access from any browser at `http://localhost:8001` (or your custom port).

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New session |
| `Ctrl+W` | Close current session |
| `Ctrl+S` | Toggle side panel |
| `Ctrl+H` | Stop running query |
| `Ctrl+B` | Open Blackboard viewer |

---

## Session Indicators

| Indicator | Meaning |
|-----------|---------|
| `●` (green) | Query running in this session |
| `!N` (yellow) | N unread notifications (background task completed) |

---

## Architecture

```
termuxcode/
├── core/           # Reusable logic (no Textual dependency)
│   ├── agents/     # Claude SDK client wrappers
│   ├── history/    # JSONL conversation persistence
│   ├── sessions/   # Multi-session state management
│   ├── memory/     # Blackboard + FIFO persistence
│   └── schemas/    # Pydantic response models
├── tui/            # Textual terminal UI
└── web/            # xterm.js web assets
```

---

## Links

- **PyPI**: https://pypi.org/project/termuxcode/
- **GitHub**: https://github.com/alejoair/termuxcode
- **Issues**: https://github.com/alejoair/termuxcode/issues

---

## License

MIT
