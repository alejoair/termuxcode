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
    ├── 3. build_prompt() con historial completo
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
| `agent.py` | Comunicación con Claude SDK |
| `sessions.py` | Multi-sesión (crear/borrar/listar) |
| `history.py` | Persistencia JSONL + rolling window |
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

## Módulo de Filtros (filters.py)

### Propósito
Preprocesamiento de mensajes del historial para controlar el tamaño del prompt reconstruido.

### Funciones principales
| Función | Descripción |
|----------|-------------|
| `FilterConfig` | Configuración de filtros (límites, estrategia de truncado) |
| `preprocess_history()` | Aplica filtros a todo el historial |
| `estimate_prompt_size()` | Estima tamaño del prompt reconstruido |
| `suggest_config()` | Sugiere configuración basada en estadísticas |
| `HistoryPreprocessor` | Clase para preprocesar con configuración persistente |

### Estrategias de truncado
- `"ellipsis"`: Corta y agrega "..." (default)
- `"cut"`: Corta directamente
- `"summary"`: Corta y agrega "[truncado de X caracteres]"

### Uso en MessageHistory
```python
from termuxcode.tui import MessageHistory, FilterConfig

# Configurar límites
config = FilterConfig(
    max_tool_result_length=500,  # Truncar tool_result a 500 caracteres
    truncate_strategy="ellipsis"
)

history = MessageHistory(
    session_id="abc123",
    filter_config=config
)

# build_prompt() aplica filtros automáticamente
prompt = history.build_prompt(history.load(), "Nuevo mensaje")
```

### Deshabilitar filtros temporalmente
```python
# Sin filtros para debug o cuando necesitas contexto completo
prompt = history.build_prompt(history, "msg", apply_filters=False)
```

### Ver `EXAMPLES_FILTERS.md`
Documentación completa de ejemplos de uso.

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

## Sistema de Validación de Fases (Phase Validation)

### Propósito
Detectar cambios de fase y validar que el avance es correcto usando otro LLM como auditor.

### Campos Persistente en ExtendedGameStats

| Campo | Descripción |
|-------|-------------|
| `current_phase` | Fase actual (planificacion, implementacion, testing, debugging, analisis, otro) |
| `current_advances_task` | Si la respuesta actual avanza la tarea |
| `current_confidence` | Confianza de la respuesta actual |
| `current_confidence_history` | Últimas 20 confianzas |
| `phase_history` | Historial de cambios de fase (últimos 50) |

### Flujo de Validación

```
Turno N: Agente responde con metadata
├── phase: "planificacion"
└── advances_current_task: true

Turno N+1: Agente responde con metadata
├── phase: "implementacion"  ← CAMBIO DE FASE
└── advances_current_task: true

ExtendedStatsManager.detecta_cambio:
├── phase_history.append({
│     "phase": "implementacion",
│     "from_phase": "planificacion",
│     "timestamp": "2025-01-15T10:30:00"
│   })
└── +15 XP por cambio de fase

Validación (automática):
├── get_phase_change_info()
├── generate_phase_validation_prompt()
└── TODO: Llamar a otro LLM para validar
    ├── ¿Se completó correctamente la fase planificacion?
    ├── ¿Es apropiado pasar a implementacion?
    └── ¿Qué se debe mejorar?
```

### Prompt de Validación

El sistema genera un prompt estructurado para el LLM validador:

```
# VALIDACIÓN DE CAMBIO DE FASE

## Cambio Detectado
- Desde: planificacion
- Hacia: implementacion
- Timestamp: 2025-01-15T10:30:00

## Contexto de la Sesión
- Confianza actual: 0.98
- Confianza promedio: 0.92
- Mensajes que avanzan la tarea: 23
- Total de mensajes: 45
- Contador por fase: {
    "planificacion": 12,
    "implementacion": 1,
    ...
}

## Instrucciones
Responde a estas 3 preguntas:

1. ¿Se completó correctamente la fase planificacion?
2. ¿Es apropiado pasar a la fase implementacion?
3. ¿Qué se debe mejorar?

## Tu Respuesta
Proporciona una respuesta clara y concisa.
```

### Métodos en ExtendedStatsManager

| Método | Descripción |
|--------|-------------|
| `get_phase_change_info()` | Retorna información del último cambio de fase |
| `generate_phase_validation_prompt()` | Genera prompt para el LLM validador |
| `get_latest_phase_change()` | Retorna el último cambio de fase |

### Métodos en GamificationMixin

| Método | Descripción |
|--------|-------------|
| `_validate_phase_change()` | Valida el cambio de fase con otro LLM |
| `_check_phase_change_after_response()` | Verifica si hubo cambio y programa validación |

### Archivos Modificados

| Archivo | Cambios |
|----------|---------|
| `src/termuxcode/tui/game/extended_stats.py` | + campos persistentes de fase, métodos de validación |
| `src/termuxcode/tui/mixins/gamification.py` | + método de validación de fases |

### TODO

Implementar la llamada al LLM validador en `_validate_phase_change()`:

```python
from claude_agent_sdk import query

response = await query(
    validation_prompt,
    model="sonnet"  # Usar modelo diferente para auditoría
)

self.chat_log.write(f"[bold]🔍 Validación:[/bold]\n{response}")
```

## Módulo Memory (memory.py)

### Propósito
Persistencia en disco simplificada con dos estructuras de datos: Fifo (cola) y Blackboard (key-value anidado).

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

### Storage (uso interno)
Clase interna para persistencia JSON/CSV. No se usa directamente en código normal, pero está disponible:
```python
from termuxcode.tui.memory import Storage

s = Storage("/path")
s.save("file.json", {"key": "value"})
s.save("file.csv", [["a", "b"], ["c", "d"]])
```

