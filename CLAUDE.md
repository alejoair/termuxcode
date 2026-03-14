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
