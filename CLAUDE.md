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
