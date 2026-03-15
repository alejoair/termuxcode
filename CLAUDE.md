# TermuxCode - File Tree

```
termuxcode/
├── .claude/
│   └── settings.local.json
├── .github/
│   └── workflows/
│       └── deploy.yaml
├── .gitignore
├── .memory/
│   ├── app.json
│   ├── tags.csv
│   ├── test_board.json
│   └── test_queue.csv
├── .sessions/
│   ├── .last_active
│   ├── messages_211d2f9e.jsonl
│   ├── messages_51c47b2a.jsonl
│   ├── messages_b0514732.jsonl
│   ├── messages_cfae9d12.jsonl
│   └── sessions.json
├── EXAMPLES_FILTERS.md
├── PLAN_SESSION_PARALLEL.md
├── README.md
├── capture_console.sh
├── capture_debug.py
├── capture_logs.py
├── capture_textual_console.sh
├── debug_filtered.log
├── docs/
│   └── claude-agent-sdk-reference.md
├── memory/
├── pyproject.toml
├── scripts/
│   └── copy_web_static.py
├── src/
│   └── termuxcode/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── agent.py
│       │   ├── app.py
│       │   ├── background_manager.py
│       │   ├── chat.py
│       │   ├── filters/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── estimator.py
│       │   │   ├── impl/
│       │   │   │   ├── exponential_truncate_filter.py
│       │   │   │   ├── truncate_filter.py
│       │   │   │   └── useful_filter.py
│       │   │   ├── manager.py
│       │   │   └── preprocessor.py
│       │   ├── history.py
│       │   ├── memory/
│       │   │   ├── __init__.py
│       │   │   └── memory.py
│       │   ├── mixins/
│       │   │   ├── __init__.py
│       │   │   ├── query_handlers.py
│       │   │   ├── session_handlers.py
│       │   │   └── session_state.py
│       │   ├── notification_system.py
│       │   ├── schemas/
│       │   │   ├── README.md
│       │   │   ├── __init__.py
│       │   │   └── structured_response.json
│       │   ├── sessions.py
│       │   └── styles/
│       │       ├── __init__.py
│       │       └── app_css.py
│       ├── web/
│       │   ├── static/
│       │   │   ├── app.css
│       │   │   ├── css/
│       │   │   │   └── xterm.css
│       │   │   ├── fonts/
│       │   │   │   ├── RobotoMono-Italic-VariableFont_wght.ttf
│       │   │   │   └── RobotoMono-VariableFont_wght.ttf
│       │   │   ├── images/
│       │   │   │   └── background.png
│       │   │   └── js/
│       │   │       └── textual.js
│       │   └── templates/
│       │       └── app_index.html
│       └── web_server.py
├── termuxcode_dev.log
├── test_tag_system.py
├── textual.log
├── textual_app.log
├── textual_console.log
└── textual_dev.log
```
