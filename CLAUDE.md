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
│   ├── memory/              # Persistencia en disco (.claude/memory/)
│   │   ├── storage.py       # Storage - base JSON/CSV
│   │   ├── fifo.py          # Fifo - cola persistente CSV
│   │   ├── blackboard.py    # Blackboard - key-value JSON con rutas "a.b.c"
│   │   └── initializer.py   # Initializer - carga CLAUDE.md, config.json
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

## Memory System

Persistencia simple en `.claude/memory/`:

- **Storage**: Base para leer/escribir JSON y CSV
- **Fifo**: Cola persistente (`push`/`pop`, archivo CSV)
- **Blackboard**: Dict anidado con rutas tipo Firebase (`bb.get("user.name")`, archivo JSON)
- **Initializer**: Carga archivos iniciales (CLAUDE.md, config.json) al Blackboard

