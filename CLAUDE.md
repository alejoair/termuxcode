# TERMUXCODE - Vue 3 Migration

## Arquitectura Frontend

- **Stack**: Vue 3 Composition API, Tailwind CDN, CodeMirror 6 (ESM via importmap, sin bundler)
- **Entry**: `static/index.html` (mount point) → `static/js/app-vue.js` (template string + componentes globales `app.component()`)
- **Patrón**: Composables independientes coordinados por `app-vue.js`
- **sharedState** (`useSharedState.js`): `reactive({ get ... })` con getters. Todo estado que pase del root a hijos debe vivir aquí.

### Componentes (`static/js/components/`)

18 componentes: AppHeader, LogSidebar, FiletreeSidebar, TodoSidebar, TasksSidebar, MessageList, InputBar, ActionToolbar, SettingsModal, McpModal, PlanModal, EditorSidebar, QuestionModal, ApprovalModal, FileViewModal, FloatingActionButton, TypingIndicator, StatsDisplay.

### Composables (`static/js/composables/`)

17 composables: useTabs, useWebSocket, useStorage, useMessages, useSharedState, useServerLogs, useTodoSidebar, useTasksSidebar, useFiletree, useEditorSidebar, useIsMobile, useModals, useUiState, useResizable, useTypewriter, useHaptics, useFileIcons + WsLspClient (adaptador LSP sobre WS) + diff-extensions.js (CM6 diff inline).

### Layout Responsive (breakpoint 768px)

- **Desktop**: Sidebars en flex-row, ActionToolbar inline horizontal
- **Mobile**: Sidebars = drawers fixed con backdrop. ActionToolbar = FAB vertical draggable con snap-to-edge. InputBar = textarea auto-resize. Tabs scrolleables.

### Patron: Sidebars Colapsables (7 capas)

1. **Composable** (`useXxxSidebar.js`): refs singleton + computeds
2. **Unwrapping** (`app-vue.js`): `computed` wrappers (no se auto-desenvuelven en template string)
3. **Template** (`app-vue.js`): flex-row sidebars izq → `flex-1 min-w-0` centro → sidebars der
4. **Componente** (`XxxSidebar.js`): `<transition name="sidebar">` + `v-if="isOpen"`
5. **Toggle** (`AppHeader.js`): emit → conectar en `app-vue.js` al composable
6. **CSS** (`index.html`): `.sidebar-enter/leave` (izq) y `.sidebar-right-enter/leave` (der)
7. **Datos WS** (si aplica): CustomEvent → `app-vue.js onMounted` → composable

| Sidebar | Lado | Composable | Datos |
|---------|------|------------|-------|
| LogSidebar | Izq | `useServerLogs.js` | `log_handler.py` → CustomEvent |
| FiletreeSidebar | Izq | `useFiletree.js` | filetree del proyecto |
| EditorSidebar | Der | `useEditorSidebar.js` | CM6 + Compartment lang/LSP, dirty tracking, diff inline |
| TasksSidebar | Der | `useTasksSidebar.js` | reutiliza `todo_update` |

### Lecciones Aprendidas (CRÍTICO)

- **Props reactivas**: `createApp({ setup() }).mount('#app')` no re-renderiza hijos con refs de `setup()`. Usar `reactive({ get prop() { return ref.value } })`.
- **Template string**: Componentes hijos se registran con `app.component()` (global), no con `components: {}`.
- **CodeMirror `setState()` destruye el editor**: Usar `Compartment` + `dispatch()` con `compartment.reconfigure()` para extensiones dinámicas. Al cambiar tab: reconfigurar compartments. `destroyEditor()` debe recrear compartments con `new Compartment()`.
- **Sin global `Vue`**: Los componentes se cargan como ES modules. Importar `ref`, `computed`, etc. directamente desde `'https://unpkg.com/vue@3/dist/vue.esm-browser.js'`. Nunca usar `Vue.xxx` (el global no existe).
- **Cleanup en `onUnmounted`**: Todo `setTimeout`/`setInterval` y `addEventListener` registrado en `onMounted` debe limpiarse en `onUnmounted`. Usar flag `_isMounted` para evitar que callbacks diferidos ejecuten `emit()` sobre un componente desmontado (causa crash `emitsOptions null`).

---

## Backend (Python)

| Servidor | Archivo | Puerto | Rol |
|----------|---------|--------|-----|
| HTTP | `serve.py` | 1988 | SPA estática + API REST |
| WebSocket | `ws_server.py` | 2025 | Bidireccional con frontend |

Dependencia: `claude-agent-sdk` (spawnea subproceso `claude` CLI).

### Mapa de Archivos Clave

| Archivo | Rol |
|---------|-----|
| `cli.py` | Entry point CLI, lanza HTTP+WS |
| `desktop_server.py` | Entry point Tauri, solo WS |
| `ws_server.py` | Servidor WebSocket |
| `serve.py` | HTTP + API REST (`GET/PUT /api/file`) |
| `connection/base.py` | `WebSocketConnection` - bridge WS lifecycle ↔ Session |
| `connection/session.py` | `Session` - recursos por pestaña (SDK, LSP, handlers) |
| `connection/session_registry.py` | Dict global `session_id → WebSocketConnection` |
| `connection/sdk_client.py` | Wrapper de `ClaudeSDKClient` |
| `connection/message_processor.py` | Cola de mensajes, queries al SDK, stream. Prefixa contexto dinámico (`build_message_context`) |
| `connection/sender.py` | Envío al frontend, buffer cuando desconectado |
| `connection/ask_handler.py` | AskUserQuestion bidireccional |
| `connection/tool_approval_handler.py` | Aprobación de tools |
| `connection/hooks.py` | Hooks SDK (PreToolUse Write/Edit, PostToolUse Read/Edit) |
| `connection/log_handler.py` | Captura logs, ring buffer, broadcast WS |
| `connection/lsp_manager.py` | Lifecycle LSP, registry, facade de análisis |
| `connection/claude_md_manager.py` | `update_claude_md()` + `build_message_context()` |
| `message_converter.py` | SDK → JSON. `SPECIAL_TOOLS = {"AskUserQuestion", "TodoWrite"}` |

### Comandos Frontend → Backend

| Mensaje | Efecto |
|---------|--------|
| `{command: "/destroy"}` | Destruye sesión (SDK, LSP, registry) |
| `{command: "/stop"}` | Interrumpe query actual |
| `{command: "/disconnect"}` | Cierra WS limpiamente |
| `{content: "..."}` | Query al SDK |
| `{type: "tool_approval_response"}` | Responde aprobación |
| `{type: "question_response"}` | Responde AskUserQuestion |
| `{type: "request_buffer_replay"}` | Replay del buffer |
| `{type: "request_mcp_status"}` | Estado MCP |

### Mensajes Backend → Frontend

| Tipo | Contenido |
|------|-----------|
| `session_id` | ID de sesión |
| `cwd` | Directorio de trabajo |
| `tools_list` | Tools disponibles `{name, desc, source}`. Frontend filtra `source === "builtin"` |
| `mcp_status` | Estado servidores MCP |
| `assistant`, `user`, `result`, `system` | Mensajes de chat |
| `tool_approval_request` | Solicitud aprobación |
| `question` | Pregunta del SDK |
| `server_log` | Log en tiempo real |
| `server_log_history` | Batch de logs históricos |
| `todo_update` | `{todos: [{id, content, status}]}` → TodoSidebar + TasksSidebar |
| `file_view` | Contenido para PlanModal |

### API REST (`serve.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/file?path=<rel>` | GET | Lee archivo del proyecto |
| `/api/file` | PUT `{path, content}` | Escribe archivo (crea dirs padres) |

Ambos usan `_resolve_safe_path()` contra `TERMUXCODE_CWD`, rechazan path traversal (403).

### Flujos

- **Crear tab**: WS connect → `Session.create()` (Sender, LspManager, SDKClient, handlers) → envía `tools_list` + `mcp_status`
- **Cerrar tab**: `{command: "/destroy"}` → `_destroy_resources()` + limpia registry
- **Reconectar**: mismo `session_id` → `resume()` evalúa rebuild (cambiaron cwd/model/permissions) o solo re-attach + replay buffer

---

## Custom Tools con LSP

Tools custom in-process servidas vía MCP server (`termuxcode`). Auto-registro en `registry.py` para recibir `LspManager`.

```
SDKClient → mcp_servers={"termuxcode": get_custom_mcp_server(lsp_manager)}
  → server.py → registry.py: inject_lsp_manager() → tools
```

### Patrón: Crear una Tool LSP

1. Crear `termuxcode/custom_tools/tools/my_tool.py`:
```python
from typing import TYPE_CHECKING, Any
from claude_agent_sdk import tool
from termuxcode.connection.lsp.uri import normalize_path
if TYPE_CHECKING:
    from termuxcode.connection.lsp_manager import LspManager

_lsp_manager: "LspManager | None" = None
def set_lsp_manager(mgr): global _lsp_manager; _lsp_manager = mgr

from termuxcode.custom_tools.registry import register_lsp_tool
register_lsp_tool(set_lsp_manager)

@tool("my_tool", "Descripción.", {"file_path": str})
async def my_tool(args: dict[str, Any]) -> dict[str, Any]:
    file_path = normalize_path(args.get("file_path", "").strip())  # CRÍTICO: siempre normalizar
    if not _lsp_manager: return {"content": [{"type": "text", "text": "Error: LSP not available"}]}
    diagnostics = await _lsp_manager.validate_file(file_path, content)
    return {"content": [{"type": "text", "text": "Result..."}]}
```

2. Registrar en `tools/__init__.py`: agregar import + entrada en `TOOLS` list

### LspManager API

| Método | Retorna | Descripción |
|--------|---------|-------------|
| `validate_file(path, content)` | `list[dict]` | Diagnósticos de todos los LSPs |
| `analyze_file(path)` | `str` | Contexto semántico completo |
| `is_supported_file(path)` | `bool` | True si hay LSP para la extensión |
| `get_client(path)` | `LSPClient \| None` | Cliente LSP principal |

**LSPClient**: `get_symbols`, `get_hover`, `get_references`, `get_type_definition`, `get_type_hierarchy`, `get_inlay_hints`, `format_file`, `get_cached_diagnostics`

### Reglas Custom Tools

- **Imports absolutos** en `custom_tools/` — los relativos causan import circular
- **`normalize_path()`** de `lsp.uri` es **CRÍTICO** — convierte relativas a absolutas, maneja MSYS en Windows
- **`TYPE_CHECKING`**: import de `LspManager` solo para type hints
- **Fallback**: manejar `_lsp_manager is None`
- **Auto-registro**: `register_lsp_tool(setter)` al importar. Si una falla, no rompe las demás

---

## Context Providers

Dos mecanismos orquestados desde `claude_md_manager.py`:

1. **CLAUDE.md** (`update_claude_md`): REEMPLAZA sección `## Project Context (Auto-generated)` antes de cada query
2. **Prefijo de mensaje** (`build_message_context`): prefixa `<context>...</context>` al inicio de cada mensaje del usuario

```python
# build_message_context() - agregar provider al prefijo:
MESSAGE_CONTEXT_PROVIDERS = [
    ("system",     False, generate_system_context),
    ("git_status", True,  generate_git_status_context),
]
# Formato: (nombre, requires_git, callable(cwd) -> str)
```

### Providers

| Provider | Prioridad | Req. Git | En mensaje |
|----------|-----------|----------|------------|
| `generate_system_context` | 5 | No | ✅ |
| `generate_extended_system_context` | 6 | No | — |
| `generate_filetree_context` | 10 | No | — |
| `generate_stats_context` | 20 | No | — |
| `generate_git_context` | 30 | Sí | — |
| `generate_git_status_context` | 31 | Sí | ✅ |

### Patrón: Crear Context Provider

1. Crear `termuxcode/connection/context/mi_provider.py`:
```python
from termuxcode.connection.context import register_context_provider

@register_context_provider(name="mi_provider", priority=50, requires_git=False)
def generate_mi_context(cwd: str) -> str:
    return "### Mi Sección\n\n- **Dato**: valor"
```
2. Para CLAUDE.md: importar en `claude_md_manager.py`
3. Para prefijo: añadir a `MESSAGE_CONTEXT_PROVIDERS`

**Reglas**: Prioridades 1-10 crítica, 10-30 estructura, 30-50 git, 50-100 custom. Si un provider falla, no rompe los demás.

---

## Editor LSP (CodeMirror 6)

Editor standalone con LSP vía WebSocket. Archivos en `static/js/editor/` (lsp-client.js, lsp-extensions.js) + `static/editor-tests.html`.

```
Browser (CM6) → WebSocket → lsp_proxy.py (puerto 2087) → ty/ruff (stdio)
```

**LSP Proxy**: `python -m termuxcode.lsp_proxy --port 2087 --log-level DEBUG`

| Lenguaje | Comando |
|----------|---------|
| Python | `ty server`, `ruff server` |
| TS/JS | `typescript-language-server --stdio` |
| Go | `gopls` |

**Features implementadas**: Diagnostics (push), Completion, Hover, Document sync.

---

## Pendientes
- Montar `FloatingActionButton`
- Importar `useTypewriter`, `useHaptics`

---
