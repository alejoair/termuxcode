# TERMUXCODE - Vue 3 Migration

## Resumen de Trabajo Realizado

### Estructura Actual
- **HTML**: `static/index.html` - Solo mount point (`<div id="app"></div>`), scripts y estilos CSS
- **App Principal**: `static/js/app-vue.js` - Template string del root component, coordina composables, registra componentes globalmente
- **Componentes montados**:
  - `AppHeader.js` - Header con pestañas, recibe `state` prop, botón toggle sidebar logs
  - `LogSidebar.js` - Panel colapsable de logs del servidor con filtro por nivel
  - `MessageList.js` - Lista de mensajes con markdown y accordions
  - `InputBar.js` - Barra de input con botón enviar
- **Composables**:
  - `useTabs.js` - Gestión de pestañas (crear, cambiar, cerrar, serialización)
  - `useWebSocket.js` - Conexión WebSocket con reconexión automática
  - `useStorage.js` - Persistencia en localStorage (tabs + activeTabId)
  - `useMessages.js` - Procesamiento de mensajes (assistant, tool_use, tool_result)
  - `useSharedState.js` - Estado reactivo compartido centralizado
  - `useServerLogs.js` - Estado global de logs del servidor (no per-tab, singleton)

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

### Patron: Sidebars Colapsables

Las sidebars son paneles laterales a la izquierda del chat que se muestran/ocultan con un botón toggle en el header. Siguen un patron fijo de 4 capas: composable → unwrapping → template → componente.

#### Paso 1: Composable (`static/js/composables/useXxxSidebar.js`)

Estado global singleton (refs a nivel de modulo, no dentro de la funcion exportada):

```js
// Refs singleton (fuera de la funcion) — compartidas entre todas las instancias
const items = ref([]);
const isOpen = ref(false);

export function useXxxSidebar() {
    // Computeds dentro de la funcion — pueden leer las refs singleton
    const filteredItems = computed(() => ...);

    function toggleSidebar() { isOpen.value = !isOpen.value; }
    function clearItems() { items.value = []; }

    return { items, isOpen, filteredItems, toggleSidebar, clearItems, ... };
}
```

**Regla**: `isOpen` es una ref compartida (singleton) para que solo haya una sidebar abierta. Si se quiere exclusión mutua entre sidebars, poner la logica en `toggleSidebar()`.

#### Paso 2: Unwrapping en `app-vue.js` setup()

Los refs dentro de objetos planos retornados por `setup()` NO se auto-desenvuelven en el template string de Vue 3. Solucion: crear `computed` wrappers de nivel superior y retornarlos:

```js
// En setup():
const xxxSidebar = useXxxSidebar();

// Desenvolver para el template
const xxxSidebarOpen = computed(() => xxxSidebar.isOpen.value);
const xxxSidebarItems = computed(() => xxxSidebar.items.value);

// Retornar AMBOS: el objeto (para metodos) y los computed (para props)
return {
    xxxSidebar,              // para llamar xxxSidebar.toggleSidebar() desde @click
    xxxSidebarOpen,          // para :is-open="xxxSidebarOpen" en template
    xxxSidebarItems,         // para :items="xxxSidebarItems" en template
};
```

#### Paso 3: Template en `app-vue.js`

Layout flex-row con sidebars a la izquierda y el contenido principal con `flex-1 min-w-0`:

```html
<div class="flex h-screen overflow-hidden">
    <!-- Sidebar(s) -->
    <xxx-sidebar
        :is-open="xxxSidebarOpen"
        :items="xxxSidebarItems"
        @toggle="xxxSidebar.toggleSidebar()"
        @clear="xxxSidebar.clearItems()"
    />
    <!-- Contenido principal -->
    <div class="flex flex-col flex-1 min-w-0 p-4 safe-areas overflow-hidden">
        <!-- header, messages, toolbar, input, modals -->
    </div>
</div>
```

**Regla**: Los computed props van al componente, los metodos del composable se llaman directo en los event handlers.

#### Paso 4: Componente (`static/js/components/XxxSidebar.js`)

Template con `<transition name="sidebar">` + `v-if="isOpen"`:

```html
<transition name="sidebar">
    <div v-if="isOpen" class="flex flex-col h-full bg-base border-r border-border w-96 flex-shrink-0">
        <!-- Header: titulo + controles + boton cerrar -->
        <!-- Body: contenido scrollable -->
    </div>
</transition>
```

Props: `isOpen`, datos especificos. Emits: `toggle`, acciones.

#### Paso 5: Botón toggle en `AppHeader.js`

Agregar un emit `'toggle-xxx-sidebar'` y un boton SVG en el header:

```html
<button @click="$emit('toggle-xxx-sidebar')" title="XXX" class="...">
    <svg ...></svg>
</button>
```

En `app-vue.js`, conectar el emit del header al composable:

```html
<app-header ... @toggle-xxx-sidebar="xxxSidebar.toggleSidebar()" />
```

#### Paso 6: CSS de transición en `index.html`

Ya existe la clase `.sidebar-enter/leave` para todas las sidebars (definida una sola vez):

```css
.sidebar-enter-active, .sidebar-leave-active { transition: margin-left 0.25s ease, opacity 0.2s ease; }
.sidebar-enter-from, .sidebar-leave-to { margin-left: -24rem; opacity: 0; }
```

#### Paso 7: Datos via WebSocket (si aplica)

Si la sidebar consume datos del backend:

1. **Backend**: Crear un handler/message type nuevo (ej: `log_handler.py`)
2. **useWebSocket.js**: Intercepta el message type con `window.dispatchEvent(new CustomEvent(...))` antes del dispatch per-tab, hace `return` para evitar duplicacion
3. **app-vue.js onMounted()**: Escuchar el CustomEvent y llamar al composable: `window.addEventListener('xxx-data', (e) => xxxSidebar.addData(e.detail))`

#### Ejemplo: LogSidebar (implementado)

| Capa | Archivo |
|------|---------|
| Composable | `static/js/composables/useServerLogs.js` |
| Componente | `static/js/components/LogSidebar.js` |
| Datos backend | `termuxcode/connection/log_handler.py` (`WebSocketLogHandler`) |
| Intercept WS | `useWebSocket.js` → CustomEvent `server-log` / `server-log-history` |
| Toggle button | `AppHeader.js` (icono terminal, emit `toggle-sidebar`) |
| Unwrapping | `app-vue.js` lineas ~98-103 (`logSidebarOpen`, `logSidebarFilteredLogs`, etc.) |

### Pendientes
- Conectar handlers faltantes: `question`, `tool_approval_request`, `file_view`
- Montar `FloatingActionButton`, `TypingIndicator`
- Importar `useTypewriter`, `useHaptics`
- Implementar modales faltantes: `question`, `approval`, `fileView`, `plan`
- `handleSaveSettings` solo actualiza estado local — no reconecta WebSocket para aplicar cambios en backend (model, tools, permission_mode). Comparar con `handleApplyMcp` que sí hace disconnect/reconnect.

### Archivos Modificados
- `static/index.html` - Solo mount point + CSS + scripts
- `static/js/app-vue.js` - Template string del root, componentes globales, coordina composables y handlers de mensajes
- `static/js/components/AppHeader.js` - Header con tabs, recibe `state` prop, botón toggle sidebar logs
- `static/js/components/LogSidebar.js` - Panel colapsable de logs del servidor (filtro por nivel, auto-scroll, badges de errores/warnings)
- `static/js/components/MessageList.js` - Lista de mensajes con markdown y accordions
- `static/js/components/InputBar.js` - Barra de input con botón enviar
- `static/js/components/ActionToolbar.js` - Toolbar con botones de acción (stop, clear, reconnect, config, MCP). Botones Config y MCP tienen estado loading con spinner hasta que llega `toolsReady`/`mcpReady` del backend.
- `static/js/components/SettingsModal.js` - Modal de configuración. La lista de tools viene del backend vía `tools_list` (solo builtins), no hardcodeada. Cada tool muestra `name` y tooltip con `desc`.
- `static/js/components/McpModal.js` - Modal de servidores MCP con toggles enable/disable
- `static/js/composables/useSharedState.js` - Estado reactivo compartido centralizado
- `static/js/composables/useServerLogs.js` - Estado global de logs del servidor (singleton, filteredLogs computed, levelFilter)
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
| `termuxcode/serve.py` | Servidor HTTP para archivos estáticos |
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
| `termuxcode/message_converter.py` | Convierte mensajes del SDK (AssistantMessage, ResultMessage, etc.) a JSON |
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

---

## Custom Tools con LSP

### Arquitectura

Las tools custom se sirven vía un servidor MCP in-process (`termuxcode`) que se inyecta en el SDK client. Las tools que necesitan acceso al LSP de la sesión pueden usar un sistema de **auto-registro** para recibir el `LspManager`.

```
SDKClient
  └─> mcp_servers={"termuxcode": get_custom_mcp_server(lsp_manager)}
       └─> server.py → registry.py: inject_lsp_manager(lsp_manager)
            └─> type_check.py: _lsp_manager.validate_file()
```

### Patrón: Crear una Tool LSP

Para agregar una nueva tool que use el LSP, sigue estos 4 pasos:

#### Paso 1: Crear archivo de la tool

`termuxcode/custom_tools/tools/my_tool.py`:

```python
#!/usr/bin/env python3
"""Tool: my_feature — descripción de lo que hace."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import tool
from termuxcode.connection.lsp.uri import normalize_path

if TYPE_CHECKING:
    from termuxcode.connection.lsp_manager import LspManager

# ── Paso 1: Variable global + setter ───────────────────────────────

_lsp_manager: "LspManager | None" = None


def set_lsp_manager(lsp_manager: "LspManager | None") -> None:
    """Inyecta el LspManager para ser usado por la tool."""
    global _lsp_manager
    _lsp_manager = lsp_manager


# ── Paso 2: Auto-registro (OBLIGATORIO) ─────────────────────────────

from termuxcode.custom_tools.registry import register_lsp_tool

register_lsp_tool(set_lsp_manager)


# ── Paso 3: Definir la tool ───────────────────────────────────────────

@tool(
    "my_tool_name",
    "Human-readable description of what this tool does.",
    {"file_path": str, "optional_param": int},
)
async def my_tool_name(args: dict[str, Any]) -> dict[str, Any]:
    """Implementación de la tool usando el LspManager."""
    # IMPORTANTE: Normalizar el file_path (como hacen los hooks)
    file_path = normalize_path(args.get("file_path", "").strip())

    if not file_path:
        return {"content": [{"type": "text", "text": "Error: file_path is required"}]}

    if not os.path.isfile(file_path):
        return {"content": [{"type": "text", "text": f"Error: file not found: {file_path}"}]}

    # Verificar si hay LSP disponible
    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP not available for this session"}]}

    try:
        # Usar el LspManager según lo que necesites
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")

        # Opción 1: Validación (diagnósticos)
        diagnostics = await _lsp_manager.validate_file(file_path, content)

        # Opción 2: Análisis semántico (contexto completo)
        analysis = await _lsp_manager.analyze_file(file_path)

        # Opción 3: Cliente directo
        client = _lsp_manager.get_client(file_path)
        if client:
            symbols = await client.get_symbols(file_path)
            hover = await client.get_hover(file_path, line, col)
            references = await client.get_references(file_path, line, col)
            inlay_hints = await client.get_inlay_hints(file_path)

        return {"content": [{"type": "text", "text": "Result..."}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}]}
```

#### Paso 4: Registrar en `__init__.py`

`termuxcode/custom_tools/tools/__init__.py`:

```python
from termuxcode.custom_tools.tools.type_check import type_check
from termuxcode.custom_tools.tools.my_tool import my_tool_name  # <-- Importar

TOOLS = [
    type_check,
    my_tool_name,  # <-- Agregar a la lista
]
```

### API del LspManager

El `LspManager` expone las siguientes operaciones:

#### Métodos de alto nivel (recomendados)

| Método | Retorna | Descripción |
|--------|---------|-------------|
| `validate_file(file_path, content)` | `list[dict]` | Diagnósticos de todos los LSPs (ty, ruff, etc.) |
| `analyze_file(file_path)` | `str` | Contexto semántico completo (símbolos, tipos, referencias) |
| `is_supported_file(file_path)` | `bool` | True si hay servidor LSP para esa extensión |
| `get_client(file_path)` | `LSPClient \| None` | Cliente LSP principal para la extensión |
| `get_all_clients(file_path)` | `list[LSPClient]` | TODOS los clientes LSP para la extensión |

#### Métodos del LSPClient (uso avanzado)

```python
client = _lsp_manager.get_client(file_path)

# Información semántica
symbols = await client.get_symbols(file_path)  # DocumentSymbol[]
hover = await client.get_hover(file_path, line, col)  # str | None
references = await client.get_references(file_path, line, col)  # Location[]
type_def = await client.get_type_definition(file_path, line, col)  # Location[]
type_hierarchy = await client.get_type_hierarchy(file_path, line, col)  # dict | None

# Hints de tipos
inlay_hints = await client.get_inlay_hints(file_path)  # InlayHint[]

# Formateo
edits = await client.format_file(file_path)  # TextEdit[] | None

# Cache de diagnósticos (no bloquea)
diagnostics = client.get_cached_diagnostics(file_path)  # list[dict]
```

### Ejemplo: Tool `type_check` (implementado)

Ubicación: `termuxcode/custom_tools/tools/type_check.py`

Esta tool valida archivos Python usando el servidor LSP:

1. Lee el contenido del archivo
2. Llama a `LspManager.validate_file(file_path, content)`
3. Combina diagnósticos de todos los LSPs configurados (ty, ruff, etc.)
4. Retorna errores formateados con formato `file:line:col: [source] severity: message`
5. Retorna error si no hay LSP disponible (requiere LSP para funcionar)

**Ventajas sobre el CLI:**
- ✅ Usa el servidor LSP que ya está corriendo (más eficiente)
- ✅ Combina múltiples servidores LSP simultáneamente
- ✅ No requiere subprocess separado
- ✅ Diagnósticos cacheados disponibles
- ✅ Requisito explícito: falla claro si no hay LSP configurado

### Registry de Auto-registro

El sistema de auto-registro (`register_lsp_tool`) permite que cada tool se registre automáticamente sin modificar `server.py`. Para evitar imports circulares, el registry vive en un módulo separado (`registry.py`).

**Arquitectura:**
```
server.py → tools/__init__.py → type_check.py → registry.py ✅ (sin ciclo)
```

**El proceso:**
1. Al importar la tool (via `from termuxcode.custom_tools.tools import TOOLS`), se ejecuta `register_lsp_tool(set_lsp_manager)` en `type_check.py`
2. `registry.py` mantiene una lista `_LSP_TOOLS` con todas las funciones setter
3. `server.py:get_custom_mcp_server()` llama a `inject_lsp_manager()` desde `registry.py`
4. `inject_lsp_manager()` itera sobre `_LSP_TOOLS` e inyecta el manager en cada tool
5. Si una tool falla al inyectar, no rompe las demás (fail-safe)

### Notas

- **TYPE_CHECKING**: El import de `LspManager` está dentro de `if TYPE_CHECKING:` para evitar imports circulares. El tipo se usa solo para type hints, no en runtime.
- **Imports absolutos**: **REQUERIDO** — Todos los imports en `custom_tools/` deben ser absolutos (ej: `from termuxcode.custom_tools.registry import ...`). Los imports relativos (`from . import`) causan errores de import circular.
- **Fallback**: Las tools LSP deben manejar el caso donde `_lsp_manager` es `None` (sesiones sin LSP configurado).
- **MCP server**: El servidor MCP se crea en `sdk_client.py` con el `lsp_manager` inyectado: `get_custom_mcp_server(lsp_manager=self._lsp_manager)`.
- **Estado global**: `_lsp_manager` es una variable a nivel de módulo. Se resetea en cada sesión al crear un nuevo MCP server.
- **normalize_path()**: **CRÍTICO** — Siempre usar `normalize_path()` del módulo `lsp.uri` en el file_path recibido en los args. Esto convierte rutas relativas a absolutas y maneja rutas MSYS en Windows. Sin esto, ty recibirá URIs `file:///` inválidas (ej: `file:///src/file.py` en lugar de `file:///C:/project/src/file.py`).
- **Consistencia con hooks**: Los hooks LSP (`PreToolUse`, `PostToolUse`) también usan `normalize_path()` antes de pasar el file_path al `LspManager`. Las tools custom deben seguir el mismo patrón.

---

## Sistema de Context Providers para CLAUDE.md

### Propósito

El sistema de **Context Providers** inyecta información actualizada del proyecto en el archivo `CLAUDE.md` antes de cada query del SDK. Esto permite que el agente tenga contexto fresco sobre el estado actual del código (filetree, git status, estadísticas, etc.) sin que el usuario tenga que mantener esta información manualmente.

### Arquitectura

```
termuxcode/connection/
├── claude_md_manager.py       # Orquesta providers y actualiza CLAUDE.md
└── context/
    ├── __init__.py            # Registry de providers con decorador
    ├── filetree_provider.py   # File tree + estadísticas del proyecto
    ├── git_provider.py        # Git info (branch, commits, status)
    └── example_custom_provider.py  # Ejemplo para crear nuevos
```

### Flujo de Actualización

```
1. Usuario envía mensaje
   ↓
2. message_processor._handle_query()
   ↓
3. claude_md_manager.update_claude_md(cwd, session_id)
   ↓
4. Ejecuta todos los providers registrados (en orden de prioridad)
   ↓
5. Genera sección "## Project Context (Auto-generated)"
   ↓
6. REEMPLAZA la sección existente en CLAUDE.md (no duplica)
   ↓
7. SDK lee CLAUDE.md con la info actualizada
   ↓
8. SDK procesa la query con el contexto fresco
```

**Importante**: La sección se **REEMPLAZA** en cada mensaje, no se acumula. Si existe el marcador `## Project Context (Auto-generated)`, se busca desde ahí hasta el próximo `##` de nivel 2 y se reemplaza todo ese bloque.

### Providers Implementados

| Provider | Prioridad | Requiere Git | Descripción |
|----------|-----------|--------------|-------------|
| `generate_system_context` | 5 | No | Información del sistema (OS, usuario, fecha, Python, shell) |
| `generate_extended_system_context` | 6 | No | Variables de entorno (PATH, LANG, TERM) |
| `generate_filetree_context` | 10 | No | Árbol de archivos (profundidad 3, excluye node_modules, .git, etc.) |
| `generate_stats_context` | 20 | No | Estadísticas (cantidad de archivos Python/JS/TS) |
| `generate_git_context` | 30 | Sí | Branch actual + últimos 3 commits |
| `generate_git_status_context` | 31 | Sí | Archivos modificados (git status --short) |

### Patrón: Crear un Context Provider

Los context providers usan un sistema de **auto-registro** similar a las tools LSP. Solo necesitas 2 pasos:

#### Paso 1: Crear el archivo del provider

`termuxcode/connection/context/mi_provider.py`:

```python
from termuxcode.connection.context import register_context_provider

@register_context_provider(
    name="mi_provider",
    priority=50,              # Menor = se ejecuta primero
    requires_git=False,       # True si necesita repo git
)
def generate_mi_context(cwd: str) -> str:
    """Genera información personalizada para CLAUDE.md.

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con el contexto en formato markdown (con encabezado ###)
    """
    # Tu lógica aquí
    return """### Mi Contexto Personalizado

- **Dato importante**: valor
- **Otro dato**: valor
"""
```

#### Paso 2: Importar en el manager

`termuxcode/connection/claude_md_manager.py` (agregar una línea al inicio):

```python
# Importar todos los providers para que se registren automáticamente
from termuxcode.connection.context import filetree_provider  # noqa: F401
from termuxcode.connection.context import git_provider  # noqa: F401
from termuxcode.connection.context import mi_provider  # noqa: F401  ← AGREGAR
```

**No necesitas modificar nada más**. El sistema es auto-descubrible: cualquier módulo importado que use el decorador `@register_context_provider()` se incluye automáticamente.

### Decorador `@register_context_provider`

```python
@register_context_provider(
    name="nombre",           # Identificador para logs/debugging
    priority=100,            # Orden de ejecución (menor = antes)
    requires_git=False,      # True solo se ejecuta si hay repo git
)
def mi_funcion(cwd: str) -> str:
    return "### Mi Sección\n\nContenido"
```

### Prioridades Recomendadas

| Rango | Uso típico |
|-------|------------|
| 1-10 | Información crítica (debe ir primero) |
| 10-30 | Estructura del proyecto (filetree, stats) |
| 30-50 | Info de git/SCM |
| 50-100 | Contexto secundario o custom |
| 100+ | Información opcional |

### Comportamiento con Git

- Si el proyecto **NO tiene git**, los providers con `requires_git=True` se **saltean automáticamente**
- Esto evita errores de subprocess y mejora performance
- `claude_md_manager._is_git_repo()` detecta si hay repo con `git rev-parse --git-dir`

### Output en CLAUDE.md

La sección generada tiene este formato:

```markdown
## Project Context (Auto-generated)

> **Nota**: Esta sección se genera automáticamente antes de cada query.
> No la edites manualmente ya que se sobrescribirá.
>
> Providers activos: generate_system_context, generate_extended_system_context, generate_filetree_context, generate_stats_context, generate_git_context, generate_git_status_context

### System Info

- **OS**: 🪟 Windows 10 (x86_64)
- **User**: `alejandro@DESKTOP-ABC123`
- **Home**: `C:\Users\alejandro`
- **Shell**: `C:\Windows\System32\cmd.exe`
- **Python**: `3.11.0` → `C:\Python311\python.exe`
- **Date/Time**: 2025-01-15 14:30:25 (UTC-5)
- **Unix Timestamp**: `1736954625`

### Extended System Info

- **LANG**: `en_US.UTF-8`
- **TERM**: `xterm-256color`
- **PATH**:
  ```
  /usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
  ```

### File Tree

```
termuxcode/
├── connection/
│   ├── context/
│   │   ├── __init__.py
│   │   ├── filetree_provider.py
│   │   ├── git_provider.py
│   │   └── system_provider.py
│   └── ...
└── ...
```

### Project Stats

- **Python files**: 42
- **JS/TS files**: 15
- **Total tracked files**: 57

### Git Info

- **Branch**: `main`
  - 9fe6877 feat: migración Vue 3 completa
  - 2c7d8f1 feat: MCP per-tab state
  - 7dd1b03 feat: wake lock + reconexión

### Git Status

```
M static/js/app-vue.js
A termuxcode/connection/context/mi_provider.py
```

---
```

### Manejo de Errores

- Si un provider falla (excepción), se loguea como debug y **no rompe** los demás
- Si todos los providers fallan o no generan contenido, `update_claude_md()` retorna `False` y no modifica el archivo
- Los providers deben retornar string vacío (`""`) si no tienen contenido que aportar

### Debugging

Para ver qué providers están registrados:

```python
from termuxcode.connection.claude_md_manager import list_active_providers

providers = list_active_providers()
for p in providers:
    print(f"{p['name']} (priority={p['priority']}, git={p['requires_git']})")
```

### Integración con Message Processor

`termuxcode/connection/message_processor.py` (líneas ~125-132):

```python
# Actualizar CLAUDE.md con información actualizada del proyecto
# El SDK lo leerá antes de procesar la query
if self._cwd:
    try:
        from termuxcode.connection.claude_md_manager import update_claude_md
        update_claude_md(self._cwd, self._session_id)
    except Exception as e:
        logger.debug(f"Error actualizando CLAUDE.md (no crítico): {e}")
```

El error se maneja como **no crítico** porque si falla la actualización del contexto, la query puede proseguir de todas formas (solo que con información posiblemente desactualizada).

### Diferencias con Custom Tools

| Aspecto | Context Providers | Custom Tools |
|---------|-------------------|--------------|
| **Propósito** | Inyectar contexto en CLAUDE.md | Ejecutar acciones del SDK |
| **Momento** | Antes de cada query | Durante la conversación |
| **Output** | Markdown (texto) | JSON (tool result) |
| **Registro** | `@register_context_provider()` | `@tool()` + `TOOLS` list |
| **Aislamiento** | Global (mismo para todas las sesiones) | Per-session (cada sesión tiene su LspManager) |
