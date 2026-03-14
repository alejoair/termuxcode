# CLAUDE.md

## Instrucciones para Claude

### USO OBLIGATORIO de Retrieval Tool
**ANTES de responder o generar código**, Claude DEBE usar la tool de retrieval (`mcp__docs-retrieve__rag_search`) para:

1. Verificar la API correcta de cualquier librería/framework usado (Textual, etc.)
2. Confirmar signatures de funciones, métodos y clases
3. Revisar patrones de uso recomendados en el código fuente oficial

**Esto es CRÍTICO para evitar errores que puedan dañar el trabajo del usuario.**

```bash
# Ejemplo de uso de retrieval:
mcp__docs-retrieve__rag_search(params={
    "query": "Textual App class methods and lifecycle",
    "folder_name": "textual",
    "k": 3
})
```

**Nunca asumas** cómo funciona una API. **Siempre verifica** con retrieval primero.

---

## Flujo de la Aplicación

### 1. Inicio
```
App → SessionManager (.sessions/sessions.json)
    ↓
_load_first_session()
    ↓
_switch_to_session()
    ├── Crea MessageHistory (messages_<id>.jsonl)
    ├── Inicializa AgentClient
    └── Carga historial en ChatLog
```

### 2. Usuario envía mensaje
```
Input → on_input_submitted → _run_query
    ↓
agent.query(prompt)
    ├── 1. Mostrar en ChatLog
    ├── 2. Guardar en historial (append)
    ├── 3. build_prompt() con historial filtrado
    ├── 4. SDK.query() → streaming
    ├── 5. Procesar mensajes (Assistant/User/Result)
    └── 6. Guardar respuesta en historial
```

### 3. Rolling Window
- **Límite**: 100 mensajes
- **Ubicación**: `.sessions/messages_<id>.jsonl`
- **save()**: solo mantiene últimos `max_messages`

### 4. Estructura de sesiones
```
.sessions/
├── sessions.json      # Índice de sesiones
├── .last_active       # Sesión activa
└── messages_*.jsonl   # Historial por sesión
```

| Módulo | Función |
|--------|---------|
| `app.py` | TUI, gestión de sesiones |
| `agent.py` | Comunicación con Claude SDK + structured response schema |
| `sessions.py` | Multi-sesión (crear/borrar/listar) |
| `history.py` | Persistencia JSONL + rolling window + filtros |
| `chat.py` | Visualización de mensajes |

### CSS por modo
| Modo | Archivo CSS |
|------|-------------|
| **TUI** (terminal local) | `src/termuxcode/tui/styles/app_css.py` |
| **Web** (Termux/Android) | `src/termuxcode/web/static/app.css` |

## Bindings
- `Ctrl+N`: Nueva sesión
- `Ctrl+W`: Cerrar sesión (no borra la última)

## SDK Config
- `max_budget_usd`: 0.10
- `permission_mode`: bypassPermissions
- `model`: opus
- `output_format`: json_schema con STRUCTURED_RESPONSE_SCHEMA

## Comandos

```bash
# Ejecutar TUI
textual run src/termuxcode/tui.py

# Ejecutar en modo web (con custom CSS/JS para Android)
python -m termuxcode --serve

# Instalar dependencias
pip install -e ".[dev]"

# Tests
pytest

# Formato
ruff format .

# Lint
ruff check .
```

---

## Sistema de Filtros (filters/)

### Propósito
Preprocesamiento de mensajes del historial para controlar el tamaño del prompt reconstruido.

### Arquitectura Modular

```
src/termuxcode/tui/filters/
├── __init__.py          # Exporta FilterManager, estimate_prompt_size
├── manager.py           # FilterManager - ejecuta todos los filtros
├── base.py              # MessageFilter - clase base abstracta
├── estimator.py         # estimate_prompt_size() - estima tokens
├── preprocessor.py      # HistoryPreprocessor - preprocesamiento avanzado
└── impl/
    ├── useful_filter.py      # UsefulFilter - elimina no útiles
    └── truncate_filter.py    # TruncateFilter - trunca contenido
```

### Filtros disponibles

| Filtro | Parámetro | Valor default | Efecto |
|--------|-----------|---------------|--------|
| **UsefulFilter** | `filter_by_useful` | `True` | Elimina mensajes con `is_useful=False` |
| **TruncateFilter** | `max_tool_result_length` | `500` | Trunca resultados de herramientas |
| **TruncateFilter** | `max_assistant_length` | `None` | No trunca mensajes del asistente |
| **Rolling window** | `max_messages` | `100` | Mantiene solo 100 mensajes en disco |

### Estrategias de truncado
- `"ellipsis"`: Corta y agrega "..." (default)
- `"cut"`: Corta directamente
- `"summary"`: Corta y agrega "[truncado de X caracteres]"

### Flujo de filtrado

```
history.load() → Carga últimos 100 mensajes
    ↓
FilterManager.apply(history)
    ├── UsefulFilter → elimina is_useful=False
    └── TruncateFilter → trunca tool_result a 500 chars
    ↓
Prompt construido → SDK → LLM
```

### Ejemplo de prompt enviado al LLM

```
User: Hola, ayúdame con este código

Assistant: Claro, déjame leer el archivo...

[Used tool: Read, input: {'file_path': '/path/to/file.py'}]

[Tool result: #!/usr/bin/env python3
import sys
from pathlib import Path
...
]

User: Ahora explícame la función main()

Assistant:
```

### Uso en MessageHistory

```python
from termuxcode.tui import MessageHistory

# Configurar límites (opcional, ya están por default)
history = MessageHistory(
    session_id="abc123",
    max_messages=100,
    max_tool_result_length=500,
    truncate_strategy="ellipsis"
)

# build_prompt() aplica filtros automáticamente
prompt = history.build_prompt(history.load(), "Nuevo mensaje")
```

### Deshabilitar filtros temporalmente
```python
# Sin filtros para debug o cuando necesitas contexto completo
prompt = history.build_prompt(history, "msg", apply_filters=False)
```

---

## Sistema de Respuestas Estructuradas

### Propósito
El SDK devuelve un structured output con metadata que la aplicación usa para controlar el flujo y mostrar información al usuario.

### Schema (definido en agent.py)

```python
STRUCTURED_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "user_prompt_objective": {"type": "string"},
                "user_prompt_classification": {
                    "type": "string",
                    "enum": ["single_task", "research", "plan", "implementation",
                            "debugging", "testing", "code_review", "documentation",
                            "refactoring", "explanation", "offtopic", "meta"]
                },
                "next_suggested_immediate_action": {"type": "string"},
                "is_useful_to_record_in_history": {"type": "boolean"},
                "advances_current_task": {"type": "boolean"},
                "task_phase": {
                    "type": "string",
                    "enum": ["planificacion", "implementacion", "testing", "debugging",
                            "analisis", "otro"]
                },
                "related_files": {"type": "array", "items": {"type": "string"}},
                "tag": {
                    "type": "string",
                    "enum": ["WARNING", "ERROR", "INFO", "SUCCESS"],
                    "default": "INFO"
                },
                "self_reflection": {"type": "string"},
                "personal_goal": {"type": "string"},
            },
            "required": [
                "user_prompt_objective",
                "user_prompt_classification",
                "next_suggested_immediate_action",
                "is_useful_to_record_in_history",
                "advances_current_task",
                "task_phase",
            ]
        }
    },
    "required": ["response", "metadata"]
}
```

### Uso en agent.py

```python
# Función helper para acceder a campos con defaults
def _get_metadata(structured: dict | None, key: str, default=None):
    if not structured or "metadata" not in structured:
        return default
    return structured["metadata"].get(key, default)

# En _process_result
structured = message.structured_output  # dict del SDK
tag = _get_metadata(structured, "tag", "INFO")

# Si is_useful_to_record_in_history = False,
# marca todos los mensajes del turno como no útiles
is_useful = _get_metadata(structured, "is_useful_to_record_in_history", True)
if not is_useful:
    _mark_turn_as_not_useful(initial_count)
```

---

## Módulo Memory (memory/)

### Propósito
Persistencia en disco simplificada con dos estructuras de datos: Fifo (cola) y Blackboard (key-value anidado).

### Estructura
```
src/termuxcode/tui/memory/
├── __init__.py       # Exporta Fifo, Blackboard, Storage, Initializer
└── memory.py         # Implementación completa
```

### Uso básico
```python
from termuxcode.tui.memory import Fifo, Blackboard

# Fifo - Cola FIFO (CSV)
fifo = Fifo("queue_name")
fifo.push("item")
item = fifo.pop()  # FIFO

# Blackboard - Key-value anidado (JSON)
bb = Blackboard("board_name")
bb.set("path.to.value", "data")
value = bb.get("path.to.value")
```

### Fifo - Métodos avanzados
| Método | Descripción |
|--------|-------------|
| `push(data)` | Enqueue - agregar al final |
| `pop() → Any` | Dequeue - remover y retornar primero (None si vacío) |
| `peek() → Any` | Retornar primero sin remover |
| `size() → int` | Cantidad de elementos |
| `is_empty() → bool` | ¿Está vacía? |
| `to_list() → list` | Copia como lista |
| `clear()` | Vaciar cola |
| `memory_dir` | Customizar dir: `Fifo("name", memory_dir="/path")` |

### Blackboard - Métodos avanzados
| Método | Descripción |
|--------|-------------|
| `set(path, value)` | Guardar valor en ruta anidada ("a.b.c") |
| `get(path, default=None) → Any` | Obtener valor (default si no existe) |
| `get_all() → dict` | Copia completa del documento |
| `update(new_data: dict)` | Merge recursivo (deep) con datos existentes |
| `delete(path) → bool` | Eliminar ruta (True si existía) |
| `exists(path) → bool` | Verificar si existe ruta |
| `keys() → list` | Claves de nivel superior |
| `clear()` | Vaciar todo |
| `memory_dir` | Customizar dir: `Blackboard("name", memory_dir="/path")` |

### Deep merge en update()
```python
bb.set("a.x", 1)
bb.set("b.y", 2)
bb.update({"a": {"z": 3}, "c": 4})

# Resultado:
# {"a": {"x": 1, "z": 3}, "b": {"y": 2}, "c": 4}
# "a.x" se preserva, "a.z" se agrega, "b.y" se preserva
```

### Estructura de archivos
```
.memory/              # Por defecto en cwd
├── queue_name.csv    # Fifo: una fila por elemento
└── board_name.json   # Blackboard: JSON anidado
```

### Initializer - Carga inicial de datos
Inicializa Fifo y Blackboard desde archivos al iniciar la app.

**Métodos:**
| Método | Descripción |
|--------|-------------|
| `load_claude_md(board="app", path=None)` | Lee CLAUDE.md → blackboard |
| `load_config_json(board="app", path=None, path="config")` | Lee config.json → blackboard |
| `initialize_fifo(name, items)` | Inicializa Fifo con lista |
| `initialize_fifo_from_file(name, path, format)` | Desde archivo (json/txt) |
| `initialize_all()` | Ejecuta todas por defecto |

**Uso:**
```python
from termuxcode.tui.memory import Initializer

init = Initializer()
init.initialize_all()  # Carga CLAUDE.md y config.json

# Acceder a datos cargados
from termuxcode.tui.memory import Blackboard
bb = Blackboard("app")
claude_md = bb.get("docs.claude_md")
config = bb.get("config")
```

**Integración:** Se llama automáticamente en `ClaudeChat.on_mount()` via `_initialize_memory()`.

---

## Modo Web (Template Custom)

### Archivos
- `src/termuxcode/web/templates/app_index.html` - Template HTML
- `src/termuxcode/web/static/app.css` - Estilos splash/diálogos (viewport, body, dialogs, terminal fade-in)
- `src/termuxcode/web/static/css/xterm.css` - Estilos de xterm.js (terminal emulado)

### Flujo de carga
1. **Splash screen** visible con botón "Start"
2. Click → Conexión WebSocket → `textual.js` inicializa xterm
3. Primer byte recibido → Body obtiene clase `-first-byte`
4. Splash oculto (`display: none`), terminal visible (`opacity: 1`)

### Estructura HTML
```
body
├── .dialog-container.intro-dialog (splash)
│   └── .intro (caja con logo + botón)
├── .dialog-container.closed-dialog (sesión terminada)
└── #terminal (donde xterm.js se monta)
    └── .xterm (terminal xterm.js)
        ├── .xterm-viewport (scrollable)
        ├── .xterm-screen (canvas)
        └── .xterm-helpers
            └── .xterm-helper-textarea (input oculto en left: -9999em)
```

### Problema teclado Android
El input real `.xterm-helper-textarea` está oculto fuera de pantalla (`left: -9999em`).
Cuando el teclado sale, el browser no sabe hacia dónde hacer scroll.

### Comandos
```bash
# Ejecutar modo web
python -m termuxcode --serve
```

---

## Arquitectura Simplificada (cambios recientes)

### Archivos eliminados en refactorización
- `src/termuxcode/tui/structured_response.py` - Schema movido a `agent.py`, usa dict directamente
- `src/termuxcode/tui/filters.py` - Refactorizado a paquete modular `filters/`
- `src/termuxcode/tui/game/change_detector.py` - Sistema de gamificación simplificado
- `src/termuxcode/tui/simple_agent.py` - Removido, trigger system simplificado
- `src/termuxcode/tui/styles/` - Módulo de estilos simplificado

### Principios actuales
1. **Simplicidad**: Usar `dict` directo del SDK sin capas de abstracción innecesarias
2. **Modularidad**: Filtros como paquete separado con clases base
3. **Configuración por default**: Valores sensibles en código, no en archivos
4. **Estado mínimo**: Solo persistir lo necesario (historial, sesiones)

---

## Historial de Cambios Recientes

| Commit | Fecha | Cambio principal |
|--------|-------|------------------|
| 5e55818 | 2026-03-14 | feat: Add memory module and refactor filters system |
| 84e9fdf | - | refactor: Clean up feedback_filter and extended_stats after schema simplification |
| e427223 | - | refactor: Simplify structured response schema |
| 1fa2052 | - | refactor: Simplify gamification system - remove overengineered phase validation |
| 8568934 | - | refactor: Replace specific SimpleAgent methods with generic trigger system |
| 90c165e | - | feat: Add user prompt classification and phase validation schema |
| 532ac1f | - | fix: Fix phase validation system and remove structured output prompt template |
| d8338d4 | - | feat: Add persistent metadata storage and phase change validation system |
| 42a26fe | - | feat: Add agent self-reflection and personal goals with feedback system |
| b07c4fa | - | feat: Add structured responses with metadata for gamification |
| c812d3e | - | feat: Add preprocesamiento module for conversation history filters |
