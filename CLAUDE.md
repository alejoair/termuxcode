# TermuxCode

## Arquitectura

El proyecto separa la lógica general reutilizable (`core/`) de la interfaz Textual (`tui/`).

```
src/termuxcode/
├── __init__.py              # Re-exporta ClaudeChat y main
├── __main__.py
├── cli.py                   # CLI: parsea args, lanza TUI o web server
│
├── core/                    # Lógica general (sin dependencia de Textual)
│   ├── __init__.py          # Re-exporta: AgentClient, MessageHistory, SessionManager,
│   │                        #   SessionState, BackgroundTaskManager, NotificationQueue
│   ├── agent.py             # AgentClient - comunicación con Claude Agent SDK
│   ├── history.py           # MessageHistory - historial JSONL por sesión
│   ├── sessions.py          # SessionManager, Session - gestión multi-sesión
│   ├── session_state.py     # SessionState - estado individual de sesión
│   ├── background_manager.py # BackgroundTaskManager - tasks asyncio por sesión
│   ├── notification_system.py # NotificationQueue, NotificationType
│   ├── filters/             # Pipeline de filtros para historial
│   │   ├── base.py          # MessageFilter (clase base abstracta)
│   │   ├── manager.py       # FilterManager - ejecuta filtros en orden
│   │   ├── preprocessor.py  # HistoryPreprocessor - wrapper con config persistente
│   │   ├── estimator.py     # estimate_prompt_size()
│   │   └── impl/            # Implementaciones concretas
│   │       ├── useful_filter.py
│   │       ├── truncate_filter.py
│   │       └── exponential_truncate_filter.py
│   ├── memory/              # Persistencia en disco (JSON/CSV)
│   │   └── memory.py        # Storage, Fifo, Blackboard, Initializer
│   └── schemas/             # Schemas JSON
│       └── structured_response.json
│
├── tui/                     # Interfaz Textual (depende de core/)
│   ├── __init__.py          # Re-exporta ClaudeChat
│   ├── app.py               # ClaudeChat(App) - app principal
│   ├── chat.py              # ChatLog(RichLog) - widget de mensajes
│   ├── mixins/              # Mixins para ClaudeChat
│   │   ├── session_handlers.py  # SessionHandlersMixin - tabs, navegación
│   │   └── query_handlers.py   # QueryHandlersMixin - input, ejecución
│   └── styles/
│       └── app_css.py       # CSS de la app
│
├── web/                     # Assets para modo web (xterm.js)
│   ├── static/
│   └── templates/
└── web_server.py            # Servidor web (textual-serve)
```

### Imports principales

```python
# Lógica general
from termuxcode.core import AgentClient, MessageHistory, SessionManager
from termuxcode.core.filters import FilterManager
from termuxcode.core.memory import Blackboard, Fifo, Initializer

# TUI
from termuxcode.tui import ClaudeChat
```

## File Tree

```
termuxcode/
├── .claude/
│   └── settings.local.json
├── .github/
│   └── workflows/
│       └── deploy.yaml
├── .gitignore
├── docs/
│   └── claude-agent-sdk-reference.md
├── pyproject.toml
├── scripts/
│   └── copy_web_static.py
├── src/
│   └── termuxcode/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent.py
│       │   ├── background_manager.py
│       │   ├── history.py
│       │   ├── notification_system.py
│       │   ├── session_state.py
│       │   ├── sessions.py
│       │   ├── filters/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── estimator.py
│       │   │   ├── manager.py
│       │   │   ├── preprocessor.py
│       │   │   └── impl/
│       │   │       ├── exponential_truncate_filter.py
│       │   │       ├── truncate_filter.py
│       │   │       └── useful_filter.py
│       │   ├── memory/
│       │   │   ├── __init__.py
│       │   │   └── memory.py
│       │   └── schemas/
│       │       ├── __init__.py
│       │       └── structured_response.json
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── app.py
│       │   ├── chat.py
│       │   ├── mixins/
│       │   │   ├── __init__.py
│       │   │   ├── query_handlers.py
│       │   │   └── session_handlers.py
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
└── test_tag_system.py
```
