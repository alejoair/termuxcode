# TermuxCode

TUI chat client para Claude Code en Termux/Android. Usa `claude-agent-sdk` para comunicación con el agente y `textual` para la interfaz terminal.

## Comandos de desarrollo

```bash
pip install -e ".[dev]"       # Instalar con dependencias de desarrollo
termuxcode                    # Ejecutar TUI
termuxcode --dev              # TUI con Textual devtools
termuxcode --serve            # Modo web server (0.0.0.0:8001)
termuxcode --serve --port 8080 --fs 24  # Web con puerto/font custom
termuxcode --cwd /mi/proyecto # Directorio de trabajo específico
pytest                        # Ejecutar tests
pytest --cov=termuxcode       # Tests con coverage
mypy src/                     # Type checking (Python 3.12)
```

**Versionado**: `setuptools_scm` con tags git (`v*`). Deploy automático a PyPI via GitHub Actions al crear tag.

## Arquitectura

El proyecto separa la lógica general reutilizable (`core/`) de la interfaz Textual (`tui/`).

### Flujo de datos principal

```
User Input (on_input_submitted)
  → QueryHandlersMixin._handle_query()
    → history.append("user", prompt)
    → asyncio.create_task(_run_query_safe())
      → BackgroundTaskManager.start_task(coro, callback)
        → AgentClient.query() streams desde claude_agent_sdk
          → TextBlock → write_assistant() + append "assistant"
          → ToolUseBlock → write_tool() + append "tool_use"
          → ToolResultBlock → write_result() + append "tool_result"
        → on_complete callback → update UI / notificación si background
```

### Modelo de sesiones

- `SessionManager` persiste índice en `.sessions/sessions.json`, último activo en `.sessions/.last_active`
- Cada sesión tiene `SessionState`: `MessageHistory` + `AgentClient` + `asyncio.Task` + scroll position
- Historial JSONL por sesión: `.sessions/messages_{session_id}.jsonl`
- **Ejecución paralela**: las queries NO se cancelan al cambiar de tab. `BackgroundTaskManager` mantiene un `asyncio.Task` por sesión
- `NotificationQueue` almacena resultados de sesiones en background (SUCCESS/ERROR/INFO), mostradas al volver al tab

### Formato de mensajes (JSONL)

```json
{"role": "user|assistant|tool_use|tool_result", "content": "str|dict", "is_useful": true}
```
- `tool_use` content: `{"name": "...", "input": "..."}`
- `is_useful`: controla si el mensaje pasa el filtro de historial

### AgentClient config

```python
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    model="opus",
    output_format={"type": "json_schema", "schema": MainAgentResponse.model_json_schema()},
    setting_sources=["project", "user"],
)
```
- **Stop tools**: se detiene automáticamente en `AskUserQuestion` o `StructuredOutput`
- Mensajes de herramientas se guardan incrementalmente (no en batch)

### Schema de respuesta estructurada

`MainAgentResponse` (Pydantic) incluye campos como:
- `user_prompt_classification`: single_task, research, plan, implementation, debugging, etc.
- `is_useful_to_record_in_history`: controla persistencia del turno
- `task_phase`: planificacion, implementacion, testing, debugging, analisis, otro
- `related_files`, `tag` (WARNING/ERROR/INFO/SUCCESS), `self_reflection`

### Pipeline de filtros (`core/filters/`)

Cadena de `MessageFilter` ejecutada por `FilterManager` antes de enviar al agente:
1. **UsefulFilter** — filtra mensajes con `is_useful=False`
2. **TruncateFilter** — truncación fija (`max_tool_result_length`, `max_assistant_length`, estrategia: cut/ellipsis/summary)
3. **ExponentialTruncateFilter** — mensajes recientes se conservan más completos (`length = base * (1.0 - distance * decay)`)

`HistoryPreprocessor` wrappea FilterManager con config persistente.

### TUI (`tui/`)

- `ClaudeChat` hereda de `SessionHandlersMixin`, `QueryHandlersMixin`, `App`
- `ChatLog(RichLog)`: métodos `write_user()`, `write_assistant()`, `write_tool()`, `write_result()`, `write_error()`, `write_thinking()`
- **Keybindings**: Ctrl+N (nueva sesión), Ctrl+W (cerrar), Ctrl+S (toggle panel), Ctrl+H (stop query)
- **Indicadores en tabs**: `●` verde = query corriendo, `!N` amarillo = notificaciones sin leer
- Al cambiar tab: guarda scroll → limpia chat → carga historial → muestra notificaciones → restaura scroll

## Memory System

Persistencia simple en `.claude/memory/`:

- **Storage**: Base para leer/escribir JSON y CSV
- **Fifo**: Cola persistente (`push`/`pop`, archivo CSV)
- **Blackboard**: Dict anidado con rutas tipo Firebase (`bb.get("user.name")`, archivo JSON)
- **Initializer**: Carga archivos iniciales (CLAUDE.md, config.json) al Blackboard

## File Tree

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
│   └── schemas/             # Schemas JSON + Pydantic
│       ├── main_agent_schema.json
│       └── main_agent_schema.py  # MainAgentResponse (Pydantic model)
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
└── web_server.py            # Servidor web (textual-serve + aiohttp)
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

## Datos en disco (gitignored)

- `.sessions/` — índice de sesiones, historial JSONL, último activo
- `.claude/memory/` — Fifo (CSV) y Blackboard (JSON)
