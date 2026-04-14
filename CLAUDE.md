# TERMUXCODE - Vue 3 Migration

## Resumen de Trabajo Realizado

### Estructura Actual
- **HTML**: `static/index.html` - Solo mount point (`<div id="app"></div>`), scripts y estilos CSS
- **App Principal**: `static/js/app-vue.js` - Template string del root component, coordina composables, registra componentes globalmente
- **Componentes montados**:
  - `AppHeader.js` - Header con pestañas, recibe `state` + props de sidebars, botones toggle logs/filetree/todo/tasks
  - `LogSidebar.js` - Panel colapsable izquierdo de logs del servidor con filtro por nivel
  - `FiletreeSidebar.js` - Panel colapsable izquierdo de árbol de archivos del proyecto
  - `TodoSidebar.js` - Widget flotante de tareas del agente (progress bar, estados pending/in_progress/completed)
  - `TasksSidebar.js` - Panel colapsable derecho con slim/expanded modes para tasks del agente (reutiliza datos de `todo_update`)
  - `MessageList.js` - Lista de mensajes con markdown y accordions
  - `InputBar.js` - Barra de input con botón enviar
  - `ActionToolbar.js` - Toolbar con botones de acción (stop, clear, reconnect, config, MCP)
  - `SettingsModal.js` - Modal de configuración con tools del backend
  - `McpModal.js` - Modal de servidores MCP con toggles
  - `PlanModal.js` - Modal para vista de contenido (file_view)
  - `EditorSidebar.js` - Panel colapsable derecho con CodeMirror 6, tabs de archivos, dirty tracking, save (Ctrl+S)
- **Composables**:
  - `useTabs.js` - Gestión de pestañas (crear, cambiar, cerrar, serialización)
  - `useWebSocket.js` - Conexión WebSocket con reconexión automática
  - `useStorage.js` - Persistencia en localStorage (tabs + activeTabId)
  - `useMessages.js` - Procesamiento de mensajes (assistant, tool_use, tool_result)
  - `useSharedState.js` - Estado reactivo compartido centralizado
  - `useServerLogs.js` - Estado global de logs del servidor (no per-tab, singleton)
  - `useTodoSidebar.js` - Estado global de todos del agente (singleton, setTodos, toggleSidebar)
  - `useTasksSidebar.js` - Estado global de tasks con slim/expanded modes (singleton, reutiliza datos de `todo_update`)
  - `useFiletree.js` - Estado global del árbol de archivos del proyecto (singleton)
  - `useEditorSidebar.js` - Estado global del editor (singleton, openFiles con dirty, markDirty/markClean)

### Funcionalidades Implementadas

#### 1. Sistema de Pestañas
- Crear pestañas nuevas con botón +
- Cambiar entre pestañas (click en pestaña)
- Cerrar pestañas (botón ×) con destrucción de sesión en backend (`/destroy`)
- Indicador visual activa: `bg-zinc-700 text-zinc-100 border-zinc-500`
- Indicador visual inactiva: `bg-zinc-900/50 text-zinc-500 border-transparent`
- Indicador de conexión: Verde (conectado) vs Rojo (desconectado)

#### 2. Conexiones WebSocket
- Conexión automática al crear pestaña
- Reconexión con exponential backoff (hasta 30s)
- Máximo 10 intentos de reconexión
- Manejo de session_id updates (re-key de tabs)
- URL: `ws://localhost:2025`

#### 3. Persistencia LocalStorage
- Auto-save de pestañas con watch profundo
- Restauración automática al recargar página
- Reconexión de WebSocket para tabs guardados
- Sistema de versiones para migraciones futuras

#### 4. Manejo de Mensajes WebSocket
- `cwd` - Actualiza directorio de trabajo
- `session_id` - Actualiza ID del tab
- `tools_list` - Filtra solo tools con `source === "builtin"`, las guarda en `tab.builtinTools` y pone `tab.toolsReady = true`. Las tools MCP no se muestran en la modal de configuración (van en la modal MCP).
- `mcp_status` - Guarda servidores en `tab.mcpServers`, pone `tab.mcpReady = true`
- `assistant`, `user`, `result`, `system` - Mensajes de chat
- `todo_update` - Lista de tareas del agente (`data.todos`), alimenta `TodoSidebar` + `TasksSidebar`, auto-abre TasksSidebar si estaba cerrado
- `file_view` - Contenido para el modal de Plan (planContent, showPlanModal)

### Arquitectura Frontend
- **Desacoplada**: Composables independientes coordinados por app-vue.js
- **Reactiva**: Vue 3 Composition API con refs y computed
- **sharedState** (`useSharedState.js`): `reactive({ get ... })` con getters que leen de los composables. Centraliza todo el estado que se pasa como props a los componentes hijos.
- **Persistente**: Auto-save en localStorage (tabs + activeTabId)
- **Nota**: El root component usa template inline (`index.html`) — los refs devueltos por `setup()` no re-renderizan props de hijos. Solución: pasar estado vía `reactive` con getters
- **Template string**: El root component define su template como string en `app-vue.js`, no en `index.html`. Los componentes se registran globalmente con `app.component()`.

#### useSharedState — Estado Reactivo Compartido

Archivo: `static/js/composables/useSharedState.js`

Recibe `tabs` (de `useTabs`) y retorna `{ state, inputMessage }`:

| Propiedad `state.*` | Tipo | Fuente | Usado por |
|---------------------|------|--------|-----------|
| `activeTabId` | getter | `tabs.activeTabId.value` | `AppHeader` (indicador pestaña activa) |
| `tabsArray` | getter | `tabs.tabsArray.value` | `AppHeader` (renderizar pestañas) |
| `statusColor` | getter | `tabs.statusColor.value` | `AppHeader` (indicador conexión) |
| `statusText` | getter | `tabs.statusText.value` | `AppHeader` (texto estado) |
| `activeMessages` | getter | `tabs.activeTab.value.renderedMessages` | `MessageList` (mensajes del chat) |
| `mcpReady` | getter | `tab.mcpReady` | `ActionToolbar` (estado botón MCP) |
| `toolsReady` | getter | `tab.toolsReady` | `ActionToolbar` (estado botón Config) |
| `availableTools` | getter | `tab.builtinTools` | `SettingsModal` (lista tools builtin) |
| `activeMcpServers` | getter | `tab.mcpServers` | `McpModal` (lista servidores MCP) |
| `activeSettings` | getter | `tab.settings` | `SettingsModal` (configuración del tab) |
| `selectedModel` | getter | `tab.settings.model` | `ActionToolbar` (selector modelo) |
| `inputMessage` | getter/setter | ref local | `InputBar` (texto del input) |

**Regla**: Todo estado que necesite pasar del root component a un hijo debe vivir en `useSharedState`. Los refs sueltos retornados por `setup()` NO son reactivos en el template inline de `index.html`.

### Lecciones Aprendidas
- **Props reactivas en template inline**: `createApp({ setup() }).mount('#app')` con template en HTML externo no re-renderiza hijos cuando cambian refs del `setup()`. Workaround: envolver en `reactive({ get prop() { return ref.value } })` y pasar el reactive como prop.
- **Template string vs HTML inline**: Los componentes hijos registrados con `components: {}` no se resuelven desde templates inline del HTML. Solución: usar `template:` string en JS y `app.component()` para registro global.
- **Tailwind CDN + Vue templates**: Las clases dinámicas en `:class` sí funcionan con Tailwind CDN (MutationObserver detecta cambios en el DOM).
- **CodeMirror `setState()` destruye el editor**: Llamar `editorView.setState(EditorState.create({...}))` reemplaza todo el estado (syntax highlighting, cursor, scroll). Nunca llamar cuando el contenido no cambió. En el watcher `activeContent`, comparar con `editorView.state.doc.toString()` antes de actualizar.

### Patron: Sidebars Colapsables

Patron fijo de 7 capas para sidebars (paneles laterales izq/der con toggle en header):

1. **Composable** (`useXxxSidebar.js`): refs singleton a nivel de módulo (`items`, `isOpen`), computeds dentro de la función
2. **Unwrapping** (`app-vue.js` setup): crear `computed` wrappers de nivel superior para cada ref (no se auto-desenvuelven en template string). Retornar ambos: objeto composable (para métodos) + computed (para props)
3. **Template** (`app-vue.js`): layout flex-row: sidebars izq → `flex-1 min-w-0` contenido principal → sidebars der
4. **Componente** (`XxxSidebar.js`): `<transition name="sidebar">` + `v-if="isOpen"`, props: `isOpen` + datos, emits: `toggle`
5. **Toggle button** (`AppHeader.js`): emit `'toggle-xxx-sidebar'` → conectar en `app-vue.js` al composable
6. **CSS** (`index.html`): `.sidebar-enter/leave` (izq, `margin-left`) y `.sidebar-right-enter/leave` (der, `margin-right`)
7. **Datos WS** (si aplica): backend handler → `useWebSocket.js` intercepta con `CustomEvent` → `app-vue.js onMounted` escucha y llama al composable

**Sidebars implementadas**:

| Sidebar | Lado | Composable | Componente | Datos |
|---------|------|------------|------------|-------|
| LogSidebar | Izq | `useServerLogs.js` | `LogSidebar.js` | `log_handler.py` → CustomEvent `server-log` |
| FiletreeSidebar | Izq | `useFiletree.js` | `FiletreeSidebar.js` | filetree del proyecto |
| EditorSidebar | Der | `useEditorSidebar.js` | `EditorSidebar.js` | archivos del proyecto; slim (48px) / expanded (500px); dirty tracking + save |
| TasksSidebar | Der | `useTasksSidebar.js` | `TasksSidebar.js` | reutiliza `todo_update`; slim (48px) / expanded (320px) |

### Pendientes
- Conectar handlers faltantes: `question`, `tool_approval_request`
- Montar `FloatingActionButton`
- Importar `useTypewriter`, `useHaptics`
- Implementar modales faltantes: `question`, `approval`

### Archivos Modificados
- `static/index.html` - Solo mount point + CSS + scripts. CSS transitions para `.sidebar` (izquierda) y `.sidebar-right` (derecha).
- `static/js/app-vue.js` - Template string del root, componentes globales, coordina composables y handlers de mensajes. Handlers de editor: `handleFileDirty`, `handleSaveFile` (PUT /api/file), `handleEditorContentUpdate`
- `static/js/components/AppHeader.js` - Header con tabs, recibe `state` + props de sidebars (log, filetree, todo, tasks), botones toggle
- `static/js/components/LogSidebar.js` - Panel colapsable izquierdo de logs del servidor (filtro por nivel, auto-scroll, badges de errores/warnings)
- `static/js/components/FiletreeSidebar.js` - Panel colapsable izquierdo de árbol de archivos del proyecto
- `static/js/components/TodoSidebar.js` - Widget flotante de tareas (emits: `toggle`, no `clear`). Se muestra solo si `isOpen && todos.length > 0`
- `static/js/components/TasksSidebar.js` - Panel colapsable derecho con slim (48px) / expanded (320px) modes. Progress bar, status icons, activeForm spinner.
- `static/js/components/MessageList.js` - Lista de mensajes con markdown y accordions
- `static/js/components/InputBar.js` - Barra de input con botón enviar
- `static/js/components/ActionToolbar.js` - Toolbar con botones de acción (stop, clear, reconnect, config, MCP). Botones Config y MCP tienen estado loading con spinner hasta que llega `toolsReady`/`mcpReady` del backend.
- `static/js/components/SettingsModal.js` - Modal de configuración. La lista de tools viene del backend vía `tools_list` (solo builtins), no hardcodeada. Cada tool muestra `name` y tooltip con `desc`.
- `static/js/components/McpModal.js` - Modal de servidores MCP con toggles enable/disable
- `static/js/components/PlanModal.js` - Modal de vista de contenido (file_view)
- `static/js/components/EditorSidebar.js` - Panel colapsable derecho con CodeMirror 6. Tabs de archivos, dirty tracking (punto amarillo ●), botón save, Ctrl+S/Cmd+S, `updateListener` detecta edits, preservación de contenido al cambiar tab. Emits: `file-dirty`, `save-file`, `update-content`.
- `static/js/composables/useSharedState.js` - Estado reactivo compartido centralizado
- `static/js/composables/useServerLogs.js` - Estado global de logs del servidor (singleton, filteredLogs computed, levelFilter)
- `static/js/composables/useTodoSidebar.js` - Estado global de todos (singleton, `todos`, `isOpen`, `setTodos`, `toggleSidebar`)
- `static/js/composables/useTasksSidebar.js` - Estado global de tasks con slim/expanded (singleton, `tasks`, `isOpen`, `expanded`, computed counts/progress)
- `static/js/composables/useFiletree.js` - Estado global del árbol de archivos (singleton)
- `static/js/composables/useEditorSidebar.js` - Estado global del editor (singleton). `openFiles` con campo `dirty`, métodos `markDirty(path)` / `markClean(path)`. Archivo default `welcome.py` precargado.
- `static/js/composables/useMessages.js` - Procesamiento de mensajes (assistant, tool_use, tool_result)
- `static/js/composables/useTabs.js` - Gestión de pestañas. Cada tab tiene `builtinTools`, `toolsReady` (análogo a `mcpServers`, `mcpReady`) que se llenan al recibir `tools_list` del backend y se resetean al deserializar de localStorage.

---

## Backend (Python)

### Arquitectura General

Dos servidores corren como subprocesos desde `cli.py`:

| Servidor | Archivo | Puerto | Rol |
|----------|---------|--------|-----|
| HTTP | `serve.py` | 1988 | Sirve archivos estáticos (SPA) |
| WebSocket | `ws_server.py` | 2025 | Comunicación bidireccional con el frontend |

Dependencia clave: `claude-agent-sdk` - SDK de Python que spawnea un subproceso `claude` CLI.

### Mapa de Archivos

| Archivo | Rol |
|---------|-----|
| `termuxcode/cli.py` | Entry point CLI, lanza HTTP+WS como subprocesos |
| `termuxcode/desktop_server.py` | Entry point Tauri, solo WS server |
| `termuxcode/ws_server.py` | Servidor WebSocket, despacha conexiones |
| `termuxcode/serve.py` | Servidor HTTP para archivos estáticos + API REST (`GET/PUT /api/file`) |
| `termuxcode/ws_config.py` | Config del WS (host, port, logging) |
| `termuxcode/connection/base.py` | `WebSocketConnection` - bridge entre WS lifecycle y Session |
| `termuxcode/connection/session.py` | `Session` - posee todos los recursos por pestaña (SDK, LSP, handlers) |
| `termuxcode/connection/session_registry.py` | Dict global `session_id -> WebSocketConnection` para reconexión |
| `termuxcode/connection/sdk_client.py` | `SDKClient` - wrapper de `claude-agent-sdk.ClaudeSDKClient` |
| `termuxcode/connection/message_processor.py` | Consume cola de mensajes, envía queries al SDK, streamea respuestas |
| `termuxcode/connection/sender.py` | `MessageSender` - envía mensajes al frontend, buffer cuando desconectado |
| `termuxcode/connection/ask_handler.py` | Flujo bidireccional de AskUserQuestion |
| `termuxcode/connection/tool_approval_handler.py` | Flujo de aprobación de tools |
| `termuxcode/connection/hooks.py` | Hooks del SDK (PreToolUse para Write/Edit, PostToolUse para Read/Edit) |
| `termuxcode/connection/history_manager.py` | Truncado de historial JSONL (rolling window) |
| `termuxcode/connection/log_handler.py` | `WebSocketLogHandler` - captura logs, ring buffer, broadcast via WebSocket |
| `termuxcode/connection/lsp_manager.py` | Lifecycle de servidores LSP, registry, facade de análisis |
| `termuxcode/message_converter.py` | Convierte mensajes del SDK (AssistantMessage, ResultMessage, etc.) a JSON. `SPECIAL_TOOLS = {"AskUserQuestion", "TodoWrite"}` excluye estas tools del flujo normal y las procesa por separado. |
| `termuxcode/custom_tools/` | Tools custom in-process servidas vía MCP |
| `termuxcode/custom_tools/registry.py` | Registry de auto-registro para tools LSP (evita imports circulares) |
| `termuxcode/custom_tools/server.py` | MCP server que agrupa custom tools + inyecta LspManager |
| `termuxcode/custom_tools/tools/` | Implementación de tools custom |
| `termuxcode/custom_tools/tools/type_check.py` | Tool de type checking usando LSP (ty, ruff, etc.) |

### Flujo: Crear Pestaña

1. Frontend abre WebSocket a `ws://localhost:2025?session_id=XXX&cwd=/path&options={...}`
2. `ws_server.py:handle_connection()` parsea query params
3. Si hay `session_id` y existe en `session_registry` → `reconnect()` (reattach o rebuild)
4. Si no → crea `WebSocketConnection` + `Session`
5. `Session.create()` inicializa: MessageSender, LspManager (background), SDKClient (spawnea subproceso `claude`), ToolApprovalHandler, AskUserQuestionHandler, MessageProcessor
6. Sincroniza estado de MCP servers (habilitar/deshabilitar según `disabledMcpServers`)
7. Envía `tools_list` y `mcp_status` al frontend

### Flujo: Cerrar Pestaña (implementado)

1. Frontend envía `{command: "/destroy"}` antes de cerrar el WebSocket
2. `base.py:_message_loop()` intercepta `/destroy` y llama `destroy_session()`
3. `Session.destroy()` ejecuta `_destroy_resources()` (cancela processor, desconecta SDK, apaga LSP) + limpia `session_registry`
4. El message loop termina con `return`, `handle()` sale del `finally` (chequea `self._session` no es None antes de detach)

### Flujo: Reconexión

1. Frontend reconecta con mismo `session_id` en query params
2. `session_registry` encuentra la `WebSocketConnection` existente
3. `resume()` evalúa si necesita rebuild (cambiaron cwd, model, permission_mode, etc.)
4. Sin cambios: solo re-attach del WebSocket + replay del buffer
5. Con cambios: `_destroy_resources()` + `create()` desde cero

### Comandos del Frontend al Backend

| Mensaje | Tipo | Efecto |
|---------|------|--------|
| `{command: "/destroy"}` | Comando | Destruye la sesión completamente (SDK, LSP, tasks, registry) |
| `{command: "/stop"}` | Comando | Interrumpe la query actual del SDK (no destruye sesión) |
| `{command: "/disconnect"}` | Comando | Cierra el WebSocket limpiamente (detach only) |
| `{content: "..."}` | Query | Envía texto al SDK como query del usuario |
| `{type: "tool_approval_response"}` | Respuesta | Responde a una solicitud de aprobación de tool |
| `{type: "question_response"}` | Respuesta | Responde a un AskUserQuestion del SDK |
| `{type: "request_buffer_replay"}` | Request | Pide replay del buffer de mensajes |
| `{type: "request_mcp_status"}` | Request | Pide estado actual de MCP servers |

### Mensajes del Backend al Frontend

| Tipo | Contenido |
|------|-----------|
| `session_id` | ID de sesión (nuevo o existente) |
| `cwd` | Directorio de trabajo actual |
| `tools_list` | Lista de tools disponibles (builtins + MCP). Cada tool tiene `{name, desc, source}`. Frontend filtra `source === "builtin"` para la modal de configuración. |
| `mcp_status` | Estado detallado de servidores MCP |
| `assistant` | Bloques del mensaje del asistente |
| `user` | Bloques del mensaje del usuario |
| `result` | Resultado de la query |
| `system` | Mensajes del sistema (errores, estado) |
| `tool_approval_request` | Solicitud de aprobación de tool |
| `question` | Pregunta del SDK al usuario |
| `server_log` | Log individual del servidor en tiempo real (`{type, level, timestamp, logger, message}`) |
| `server_log_history` | Batch de logs históricos al conectar (`{type, entries: [...]}`) |
| `todo_update` | Lista de tareas del agente (`{type, todos: [{id, content, status}]}`). Backend intercepta `TodoWrite` del SDK y extrae los todos. Frontend muestra `TodoSidebar` (widget flotante) + `TasksSidebar` (panel derecho con slim/expanded). |

### API REST (`serve.py`)

| Endpoint | Método | Body/Params | Response | Descripción |
|----------|--------|-------------|----------|-------------|
| `/api/file` | GET | `?path=<rel>` | `{content, path, name, size}` | Lee archivo del proyecto |
| `/api/file` | PUT | `{path, content}` | `{ok, path, size}` | Escribe archivo al disco |

Ambos endpoints usan `_resolve_safe_path(rel_path)` que resuelve contra `TERMUXCODE_CWD` y rechaza path traversal (403). PUT crea directorios padres si no existen.

---

## Custom Tools con LSP

Tools custom servidas vía MCP server in-process (`termuxcode`) inyectado en el SDK client. Las tools que necesitan LSP usan auto-registro (`registry.py`) para recibir el `LspManager`.

```
SDKClient → mcp_servers={"termuxcode": get_custom_mcp_server(lsp_manager)}
  → server.py → registry.py: inject_lsp_manager() → type_check.py: _lsp_manager.validate_file()
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

### API del LspManager

| Método | Retorna | Descripción |
|--------|---------|-------------|
| `validate_file(path, content)` | `list[dict]` | Diagnósticos de todos los LSPs |
| `analyze_file(path)` | `str` | Contexto semántico completo |
| `is_supported_file(path)` | `bool` | True si hay LSP para la extensión |
| `get_client(path)` | `LSPClient \| None` | Cliente LSP principal |

**LSPClient** (uso avanzado): `get_symbols`, `get_hover(path, line, col)`, `get_references`, `get_type_definition`, `get_type_hierarchy`, `get_inlay_hints`, `format_file`, `get_cached_diagnostics`

### Tool `type_check` (implementado)

`custom_tools/tools/type_check.py` — Valida archivos Python vía `LspManager.validate_file()`, combina diagnósticos de ty+ruff, retorna errores en formato `file:line:col: [source] severity: message`.

### Reglas

- **Imports absolutos requeridos** en `custom_tools/` — los relativos causan import circular
- **`normalize_path()`** de `lsp.uri` es **CRÍTICO** — convierte rutas relativas a absolutas y maneja MSYS en Windows. Sin esto, URIs `file:///` inválidas
- **`TYPE_CHECKING`**: import de `LspManager` solo para type hints, no runtime
- **Fallback**: manejar `_lsp_manager is None` (sesiones sin LSP)
- **Auto-registro**: al importar la tool se ejecuta `register_lsp_tool(setter)`, `server.py` llama `inject_lsp_manager()` que inyecta en todas las tools. Si una falla, no rompe las demás

---

## Sistema de Context Providers para CLAUDE.md

Inyecta info actualizada del proyecto en `CLAUDE.md` antes de cada query del SDK. `message_processor._handle_query()` llama `update_claude_md(cwd, session_id)`, que ejecuta todos los providers registrados y **REEMPLAZA** la sección `## Project Context (Auto-generated)` (no duplica).

### Arquitectura

```
termuxcode/connection/
├── claude_md_manager.py       # Orquesta providers, actualiza CLAUDE.md
└── context/
    ├── __init__.py            # Registry con decorador @register_context_provider
    ├── filetree_provider.py   # File tree + estadísticas
    └── git_provider.py        # Git info (branch, commits, status)
```

### Providers Implementados

| Provider | Prioridad | Req. Git | Descripción |
|----------|-----------|----------|-------------|
| `generate_system_context` | 5 | No | OS, usuario, fecha, Python, shell |
| `generate_extended_system_context` | 6 | No | Variables de entorno (PATH, LANG, TERM) |
| `generate_filetree_context` | 10 | No | Árbol de archivos (profundidad 3) |
| `generate_stats_context` | 20 | No | Estadísticas (Python/JS/TS files) |
| `generate_git_context` | 30 | Sí | Branch actual + últimos 3 commits |
| `generate_git_status_context` | 31 | Sí | Archivos modificados |

### Patrón: Crear un Context Provider

1. Crear `termuxcode/connection/context/mi_provider.py`:
```python
from termuxcode.connection.context import register_context_provider

@register_context_provider(name="mi_provider", priority=50, requires_git=False)
def generate_mi_context(cwd: str) -> str:
    return "### Mi Sección\n\n- **Dato**: valor"
```

2. Importar en `claude_md_manager.py`: `from termuxcode.connection.context import mi_provider  # noqa: F401`

**Reglas**:
- Prioridades: 1-10 crítica, 10-30 estructura, 30-50 git, 50-100 custom
- `requires_git=True` → se saltea automáticamente si no hay repo
- Si un provider falla (excepción), no rompe los demás (debug log, no crítico)
- Retornar `""` si no hay contenido
- Debug: `list_active_providers()` desde `claude_md_manager`

---

## Editor LSP (CodeMirror 6)

### Propósito

Editor de código standalone con integración LSP vía WebSocket para pruebas y desarrollo. Permite editar código con autocompletado, diagnósticos y hover en tiempo real conectado a servidores LSP reales (ty, ruff, etc.).

### Arquitectura

```
Browser (CodeMirror 6)
  │
  ├── editor-tests.html          ← HTML + UI logic (DOM events, samples, createEditor)
  ├── css/editor-tests.css       ← Estilos (Catppuccin Mocha theme)
  ├── js/editor/
  │   ├── lsp-client.js          ← LspClient (JSON-RPC over WebSocket)
  │   └── lsp-extensions.js      ← Extensiones CM6 (diagnostics, completion, hover, sync)
  │
  └── WebSocket ──→ lsp_proxy.py (puerto 2087) ──→ ty/ruff (stdio)
```

### Servidor LSP Proxy

**Archivo**: `termuxcode/lsp_proxy.py` — Proxy WebSocket-to-Stdio que traduce JSON-RPC plano del browser al protocolo LSP stdio (`Content-Length` headers).

**Uso**:
```bash
python -m termuxcode.lsp_proxy --port 2087 --log-level DEBUG
```

**URL**: `ws://localhost:2087/?language=python&cwd=/path/to/project`

**Servidores soportados**:

| Lenguaje | Comando | Estado |
|----------|---------|--------|
| Python | `ty server`, `ruff server` | OK (los dos) |
| TypeScript/JS/TSX/JSX | `typescript-language-server --stdio` | Requiere instalación |
| Go | `gopls` | Requiere instalación |

### Archivos del Editor

| Archivo | Rol |
|---------|-----|
| `static/editor-tests.html` | HTML structure + UI logic (DOM events, `createEditor`, samples) |
| `static/css/editor-tests.css` | Todos los estilos: header, editor, lint underlines, autocomplete dropdown, hover tooltips |
| `static/js/editor/lsp-client.js` | `LspClient` — Cliente JSON-RPC over WebSocket. Maneja `request()`, `notify()`, `onNotification()`, `initialize()`, `sendChange()` |
| `static/js/editor/lsp-extensions.js` | Extensiones CodeMirror 6: `lspDiagnostics`, `lspCompletion`, `lspHover`, `lspSync`, helpers (`offsetToPos`, `posToOffset`) |

### Features LSP Implementadas

| Feature | ty soporta | Editor | LSP method |
|---------|------------|--------|------------|
| Diagnostics (push) | ✅ | ✅ | `textDocument/publishDiagnostics` |
| Completion | ✅ | ✅ | `textDocument/completion` + `completionItem/resolve` |
| Hover | ✅ | ✅ | `textDocument/hover` |
| Document sync | — | ✅ | `textDocument/didOpen` + `textDocument/didChange` |

### Features LSP Disponibles (no implementadas)

| Feature | LSP method | Qué haría |
|---------|------------|-----------|
| Go to Definition | `textDocument/definition` | Click → saltar a la definición |
| Go to Declaration | `textDocument/declaration` | Click → saltar a la declaración |
| Go to Type Definition | `textDocument/typeDefinition` | Click → saltar al tipo |
| Find References | `textDocument/references` | Encontrar todos los usos |
| Document Highlight | `textDocument/documentHighlight` | Resaltar ocurrencias del símbolo |
| Document Symbols | `textDocument/documentSymbol` | Outline del archivo |
| Inlay Hints | `textDocument/inlayHint` | Types inline grises |
| Signature Help | `textDocument/signatureHelp` | Parámetros al escribir `(` |
| Semantic Tokens | `textDocument/semanticTokens` | Coloreado semántico |
| Folding Range | `textDocument/foldingRange` | Colapsar bloques |
| Code Actions | `textDocument/codeAction` | Quick fixes, auto-import |
| Rename | `textDocument/rename` | Renombrar símbolo global |
| Workspace Symbols | `workspace/symbol` | Buscar símbolos en el proyecto |

### Flujo de Conexión

```
1. Usuario click "Connect LSP"
   ↓
2. createEditor(true) — destruye editor anterior, crea nuevo
   ↓
3. new LspClient(wsUrl) — abre WebSocket al proxy
   ↓
4. client.initialize(rootUri, lang, documentUri, doc)
   ↓
5. Proxy spawnea proceso LSP (ty/ruff), traduce initialize
   ↓
6. LSP responde con capabilities → client.ready = true
   ↓
7. Se añaden extensiones CM6: diagnostics, completion, hover, sync
   ↓
8. Editor creado con las extensiones activas
```

### Dependencias (ESM via importmap)

Todas las dependencias se cargan desde esm.sh sin bundler:

| Paquete | Versión | Uso |
|---------|---------|-----|
| `codemirror` | 6.0.2 | `EditorView`, `basicSetup` |
| `@codemirror/lang-python` | 6 | Syntax highlighting Python |
| `@codemirror/lang-javascript` | 6 | Syntax highlighting JS/TS |
| `@codemirror/lang-html` | 6 | Syntax highlighting HTML |
| `@codemirror/lang-css` | 6 | Syntax highlighting CSS |
| `@codemirror/lang-json` | 6 | Syntax highlighting JSON |
| `@codemirror/lang-markdown` | 6 | Syntax highlighting Markdown |
| `@codemirror/lint` | 6 | `setDiagnostics` para errores |
| `@codemirror/theme-one-dark` | 6 | Tema oscuro |
| `@codemirror/autocomplete` | 6 | `autocompletion` (lazy import) |
| `@codemirror/view` | 6 | `hoverTooltip` (lazy import) |

### Testing

1. Lanzar LSP proxy: `python -m termuxcode.lsp_proxy --log-level DEBUG`
2. Lanzar HTTP server: `python -m termuxcode.serve` (puerto 1988)
3. Abrir `http://localhost:1988/editor-tests.html`
4. Click "Connect LSP"
5. Verificar:
   - Diagnostics: línea ondulada roja en `show_peding` (error intencional)
   - Completion: escribir `tasks[0].` → dropdown con propiedades
   - Hover: posicionar cursor sobre `add_task` → tooltip con firma
