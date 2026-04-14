// ===== TERMUXCODE - Vue 3 App =====

import { createApp, ref, computed, onMounted } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Importar componentes
import AppHeader from './components/AppHeader.js';
import MessageList from './components/MessageList.js';
import InputBar from './components/InputBar.js';
import ActionToolbar from './components/ActionToolbar.js';
import McpModal from './components/McpModal.js';
import SettingsModal from './components/SettingsModal.js';
import LogSidebar from './components/LogSidebar.js';
import FiletreeSidebar, { FiletreeNode } from './components/FiletreeSidebar.js';
import TodoSidebar from './components/TodoSidebar.js';
import TasksSidebar from './components/TasksSidebar.js';
import PlanModal from './components/PlanModal.js';

// Importar composables
import { useTabs } from './composables/useTabs.js';
import { useWebSocket } from './composables/useWebSocket.js';
import { useStorage } from './composables/useStorage.js';
import { useMessages } from './composables/useMessages.js';
import { useSharedState } from './composables/useSharedState.js';
import { useServerLogs } from './composables/useServerLogs.js';
import { useTodoSidebar } from './composables/useTodoSidebar.js';
import { useTasksSidebar } from './composables/useTasksSidebar.js';
import { useFiletree } from './composables/useFiletree.js';

// ===== Componente Principal =====
const app = createApp({
    template: `
        <div class="flex h-screen overflow-hidden">
            <filetree-sidebar
                :tree="filetreeTree"
                :expanded="filetreeExpanded"
                :expanded-paths="filetreeExpandedPaths"
                :file-count="filetreeFileCount"
                @toggle-expanded="filetree.toggleExpanded()"
                @toggle-path="filetree.togglePath($event)"
                @expand-all="filetree.expandAll()"
                @collapse-all="filetree.collapseAll()"
            />
            <log-sidebar
                :is-open="logSidebarOpen"
                :logs="logSidebarFilteredLogs"
                :error-count="logSidebarErrorCount"
                :warn-count="logSidebarWarnCount"
                :current-filter="logSidebarFilter"
                @toggle="serverLogs.toggleSidebar()"
                @clear="serverLogs.clearLogs()"
                @set-filter="serverLogs.setLevelFilter($event)"
            />
            <div class="flex flex-col flex-1 min-w-0 p-4 safe-areas overflow-hidden">
                <app-header
                    :state="sharedState"
                    :todo-count="todoSidebarItems.length"
                    :todo-open="todoSidebarOpen"
                    :log-open="logSidebarOpen"
                    @switch-tab="handleSwitchTab"
                    @close-tab="handleCloseTab"
                    @new-tab="handleNewTab"
                    @toggle-sidebar="serverLogs.toggleSidebar()"
                    @toggle-todo-sidebar="todoSidebar.toggleSidebar()"
                />

                <message-list
                    :messages="sharedState.activeMessages"
                    :is-processing="sharedState.isProcessing"
                    class="flex-1 overflow-y-auto min-h-0"
                />

                <action-toolbar
                    :selected-model="sharedState.selectedModel"
                    :mcp-ready="sharedState.mcpReady"
                    :tools-ready="sharedState.toolsReady"
                    @change-model="handleChangeModel"
                    @stop="handleStop"
                    @clear="handleClear"
                    @disconnect="handleDisconnect"
                    @open-mcp="handleOpenMcp"
                    @open-settings="handleOpenSettings"
                    class="pb-2"
                />

                <input-bar
                    :message="sharedState.inputMessage"
                    :no-tab="!sharedState.hasActiveTab"
                    :disabled="!sharedState.toolsReady || !sharedState.isConnected"
                    :failed="sharedState.reconnectFailed"
                    loading-text="Reconectando..."
                    @update:message="sharedState.inputMessage = $event"
                    @send="handleSend"
                />

                <!-- Modals -->
                <mcp-modal
                    v-if="showMcpModal"
                    :tab-id="sharedState.activeTabId"
                    :servers="sharedState.activeMcpServers"
                    :disabled-mcp-servers="sharedState.activeSettings.disabledMcpServers || []"
                    @close="showMcpModal = false"
                    @apply="handleApplyMcp"
                />

                <settings-modal
                    v-if="showSettingsModal"
                    :tab-id="sharedState.activeTabId"
                    :settings="sharedState.activeSettings"
                    :available-tools="sharedState.availableTools"
                    @close="showSettingsModal = false"
                    @save="handleSaveSettings"
                />

                <plan-modal
                    v-if="showPlanModal"
                    :plan="planContent"
                    @close="showPlanModal = false"
                />
            </div>

            <!-- Tasks sidebar derecha (siempre visible) -->
            <tasks-sidebar
                :tasks="tasksSidebarItems"
                :expanded="tasksSidebarExpanded"
                :total-count="tasksSidebarTotalCount"
                :progress-percent="tasksSidebarProgressPercent"
                :pending-count="tasksSidebarPendingCount"
                :in-progress-count="tasksSidebarInProgressCount"
                :completed-count="tasksSidebarCompletedCount"
                @toggle-expanded="tasksSidebar.toggleExpanded()"
            />
        </div>
    `,
    setup() {
        const tabs = useTabs();
        const ws = useWebSocket();
        const storage = useStorage(tabs.tabs, tabs.activeTabId);
        const msg = useMessages();
        const { state: sharedState, inputMessage } = useSharedState(tabs);
        const serverLogs = useServerLogs();
        const todoSidebar = useTodoSidebar();
        const tasksSidebar = useTasksSidebar();
        const filetree = useFiletree();

        // Desenvolver serverLogs para el template (refs dentro de objetos planos no se auto-desenvuelven)
        const logSidebarOpen = computed(() => serverLogs.isOpen.value);
        const logSidebarFilteredLogs = computed(() => serverLogs.filteredLogs.value);
        const logSidebarErrorCount = computed(() => serverLogs.errorCount.value);
        const logSidebarWarnCount = computed(() => serverLogs.warnCount.value);
        const logSidebarFilter = computed(() => serverLogs.levelFilter.value);

        // Desenvolver todoSidebar para el template
        const todoSidebarOpen = computed(() => todoSidebar.isOpen.value);
        const todoSidebarItems = computed(() => todoSidebar.todos.value);
        const todoSidebarCompletedCount = computed(() => todoSidebar.completedCount.value);

        // Desenvolver tasksSidebar para el template
        const tasksSidebarItems = computed(() => tasksSidebar.tasks.value);
        const tasksSidebarExpanded = computed(() => tasksSidebar.expanded.value);
        const tasksSidebarTotalCount = computed(() => tasksSidebar.totalCount.value);
        const tasksSidebarProgressPercent = computed(() => tasksSidebar.progressPercent.value);
        const tasksSidebarPendingCount = computed(() => tasksSidebar.pendingCount.value);
        const tasksSidebarInProgressCount = computed(() => tasksSidebar.inProgressCount.value);
        const tasksSidebarCompletedCount = computed(() => tasksSidebar.completedCount.value);

        // Desenvolver filetree para el template
        const filetreeExpanded = computed(() => filetree.expanded.value);
        const filetreeTree = computed(() => filetree.tree.value);
        const filetreeExpandedPaths = computed(() => filetree.expandedPaths.value);
        const filetreeFileCount = computed(() => filetree.fileCount.value);

        // Modal state
        const showMcpModal = ref(false);
        const showSettingsModal = ref(false);
        const showPlanModal = ref(false);
        const planContent = ref('');

        // ===== WebSocket Message Handler =====
        function handleMessage(data, tabId) {
            console.log('[WebSocket] Mensaje recibido:', data.type, 'para tab:', tabId);

            const tab = tabs.getTab(tabId);
            if (!tab) {
                console.warn('[WebSocket] Tab not found:', tabId);
                return;
            }

            const handlers = {
                cwd: () => {
                    tabs.updateTabCwd(tabId, data.cwd);
                },
                session_id: () => {},
                tools_list: () => {
                    const builtinTools = (data.tools || []).filter(t => t.source === 'builtin');
                    tabs.updateTabBuiltinTools(tabId, builtinTools);
                },
                mcp_status: () => {
                    tabs.updateTabMcpServers(tabId, data.servers);
                    tab.mcpReady = true;
                },
                assistant: () => {
                    const blocks = msg.processAssistantBlocks(data.blocks);
                    blocks.forEach(block => msg.addMessageToTab(tab, block));
                },
                user: () => {
                    if (data.blocks) {
                        const results = msg.processToolResultBlocks(data.blocks);
                        results.forEach(r => msg.addMessageToTab(tab, r));
                    }
                },
                result: () => {
                    if (data.blocks) {
                        const results = msg.processToolResultBlocks(data.blocks);
                        results.forEach(r => msg.addMessageToTab(tab, r));
                    }
                    msg.addMessageToTab(tab, { type: 'result', subtype: data.subtype, cost: data.cost });
                    tab.isProcessing = false;
                },
                system: () => {
                    msg.addMessageToTab(tab, { type: 'system', message: data.message });
                },
                file_view: () => {
                    planContent.value = data.content || '';
                    showPlanModal.value = true;
                },
                todo_update: () => {
                    todoSidebar.setTodos(data.todos || []);
                    tasksSidebar.setTasks(data.todos || []);
                },
            };

            handlers[data.type]?.();
        }

        // ===== Tabs Handlers =====
        function handleNewTab() {
            const tabId = tabs.createTab();
            const tab = tabs.getTab(tabId);
            if (tab) {
                ws.connectTab(tab, handleMessage);
            }
        }

        function handleSwitchTab(tabId) {
            tabs.switchTab(tabId);
        }

        function handleCloseTab(tabId) {
            const tab = tabs.getTab(tabId);
            if (tab) {
                ws.sendCommand(tab, '/destroy');
                ws.disconnectTab(tab);
            }
            tabs.closeTab(tabId);
        }

        // ===== Input =====
        function handleSend() {
            const text = inputMessage.value.trim();
            if (!text) return;

            const tab = tabs.activeTab.value;
            if (!tab) return;

            msg.addMessageToTab(tab, { type: 'user', content: text });
            tab.isProcessing = true;

            // Si el tab ya tiene WebSocket conectado, enviar directamente
            if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
                ws.sendUserMessage(tab, text);
            } else {
                // Conectar y enviar cuando esté listo
                ws.connectTab(tab, handleMessage);
                const socket = tab.ws;
                const sendOnOpen = () => {
                    ws.sendUserMessage(tab, text);
                    socket.removeEventListener('open', sendOnOpen);
                };
                socket.addEventListener('open', sendOnOpen);
            }

            inputMessage.value = '';
        }

        // ===== Action Toolbar Handlers =====
        function handleChangeModel(model) {
            const tab = tabs.activeTab.value;
            if (!tab) return;

            tabs.updateTabSettings(tab.id, { model });
            tabs.resetTabReadyFlags(tab.id);
            ws.disconnectTab(tab);
            ws.connectTab(tab, handleMessage);
        }

        function handleStop() {
            const tab = tabs.activeTab.value;
            if (tab) {
                ws.sendCommand(tab, '/stop');
                tab.isProcessing = false;
                msg.addMessageToTab(tab, { type: 'system', message: '⏹ Deteniendo...' });
            }
        }

        function handleClear() {
            const tabId = tabs.activeTabId.value;
            if (tabId) tabs.clearTabMessages(tabId);
        }

        function handleDisconnect() {
            const tab = tabs.activeTab.value;
            if (tab) {
                ws.sendCommand(tab, '/disconnect');
                msg.addMessageToTab(tab, { type: 'system', message: '🔄 Reconectando...' });
            }
        }

        function handleOpenMcp() {
            showMcpModal.value = true;
        }

        function handleOpenSettings() {
            showSettingsModal.value = true;
        }

        function handleApplyMcp(disabledServers) {
            const tab = tabs.activeTab.value;
            if (!tab) return;

            // Actualizar settings localmente
            tabs.updateTabSettings(tab.id, { disabledMcpServers: disabledServers });

            // Resetear flags de ready para que los botones muestren spinner
            tabs.resetTabReadyFlags(tab.id);

            // Reconectar para que el backend rebuild el SDK con los nuevos MCP settings
            ws.disconnectTab(tab);
            ws.connectTab(tab, handleMessage);

            showMcpModal.value = false;
        }

        function handleSaveSettings(settings) {
            const tab = tabs.activeTab.value;
            if (!tab) return;

            // Actualizar settings localmente
            tabs.updateTabSettings(tab.id, settings);

            // Resetear flags de ready para que los botones muestren spinner
            tabs.resetTabReadyFlags(tab.id);

            // Reconectar para que el backend aplique los nuevos settings (model, tools, permission_mode, etc.)
            ws.disconnectTab(tab);
            ws.connectTab(tab, handleMessage);

            showSettingsModal.value = false;
        }

        // ===== Lifecycle =====
        onMounted(() => {
            console.log('[Vue] App montada');

            // Escuchar logs del servidor
            window.addEventListener('server-log', (event) => {
                serverLogs.addLog(event.detail);
            });
            window.addEventListener('server-log-history', (event) => {
                serverLogs.addLogBatch(event.detail.entries);
            });

            // Escuchar filetree snapshots
            window.addEventListener('filetree-snapshot', (event) => {
                filetree.setTree(event.detail.entries, event.detail.cwd);
            });

            // Escuchar cambios de session_id del WebSocket
            window.addEventListener('tab-session-id-update', (event) => {
                const { oldId, newId } = event.detail;
                console.log('[Vue] Session ID update:', oldId, '->', newId);
                tabs.updateTabSessionId(oldId, newId);
                storage.saveTabs(tabs.serializeTabs());
            });

            // Conexion: reset reconnectFailed al reconectar
            window.addEventListener('tab-connected', (event) => {
                const tab = tabs.getTab(event.detail.tabId);
                if (tab) tab.reconnectFailed = false;
            });

            // Conexion: marcar tab como fallido
            window.addEventListener('tab-reconnect-failed', (event) => {
                const tab = tabs.getTab(event.detail.tabId);
                if (tab) tab.reconnectFailed = true;
            });

            // Reconexion inmediata al volver a la pestaña del navegador
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) return;
                for (const [, tab] of tabs.tabs) {
                    if (!tab.isConnected) {
                        if (tab.reconnectTimeout) clearTimeout(tab.reconnectTimeout);
                        tab.reconnectTimeout = null;
                        tab.reconnectAttempts = 0;
                        tab.reconnectFailed = false;
                        ws.connectTab(tab, handleMessage);
                    }
                }
            });

            // Reconexion cuando vuelve la red
            window.addEventListener('online', () => {
                for (const [, tab] of tabs.tabs) {
                    if (!tab.isConnected) {
                        if (tab.reconnectTimeout) clearTimeout(tab.reconnectTimeout);
                        tab.reconnectTimeout = null;
                        tab.reconnectAttempts = 0;
                        tab.reconnectFailed = false;
                        ws.connectTab(tab, handleMessage);
                    }
                }
            });

            // Cargar tabs guardados
            const { tabs: savedTabs, activeTabId: savedActiveTabId } = storage.loadTabs();

            if (savedTabs.length > 0) {
                tabs.deserializeTabs(savedTabs);

                // Filtrar tabs sin sesión real (temporal) — no se pueden reconectar
                const reconnectable = [];
                const discarded = [];
                tabs.tabsArray.value.forEach(tab => {
                    if (tab.sessionId && tab.id === tab.sessionId) {
                        reconnectable.push(tab);
                    } else {
                        discarded.push(tab);
                    }
                });

                // Descartar tabs temporales del mapa
                discarded.forEach(tab => {
                    tabs.closeTab(tab.id);
                });

                if (reconnectable.length > 0) {
                    if (savedActiveTabId && tabs.getTab(savedActiveTabId)) {
                        tabs.switchTab(savedActiveTabId);
                    } else {
                        tabs.switchTab(reconnectable[0].id);
                    }

                    // Reconectar WebSocket solo para tabs con sesión real
                    reconnectable.forEach(tab => {
                        ws.connectTab(tab, handleMessage);
                    });
                }
            }

            // Configurar auto-save
            storage.setupAutoSave(() => tabs.serializeTabs());

            // Guardar estado síncrono antes de recargar/cerrar
            // Previene que el auto-save asíncrono de Vue no llegue a ejecutarse
            window.addEventListener('beforeunload', () => {
                storage.saveTabs(tabs.serializeTabs());
            });
        });

        return {
            sharedState,
            showMcpModal,
            showSettingsModal,
            showPlanModal,
            planContent,
            serverLogs,
            logSidebarOpen,
            todoSidebar,
            todoSidebarOpen,
            todoSidebarItems,
            todoSidebarCompletedCount,
            tasksSidebar,
            tasksSidebarItems,
            tasksSidebarExpanded,
            tasksSidebarTotalCount,
            tasksSidebarProgressPercent,
            tasksSidebarPendingCount,
            tasksSidebarInProgressCount,
            tasksSidebarCompletedCount,
            filetree,
            filetreeExpanded,
            filetreeTree,
            filetreeExpandedPaths,
            filetreeFileCount,
            logSidebarFilteredLogs,
            logSidebarErrorCount,
            logSidebarWarnCount,
            logSidebarFilter,
            handleNewTab,
            handleSwitchTab,
            handleCloseTab,
            handleSend,
            handleChangeModel,
            handleStop,
            handleClear,
            handleDisconnect,
            handleOpenMcp,
            handleOpenSettings,
            handleApplyMcp,
            handleSaveSettings,
        };
    },
});

app.component('AppHeader', AppHeader);
app.component('MessageList', MessageList);
app.component('InputBar', InputBar);
app.component('ActionToolbar', ActionToolbar);
app.component('McpModal', McpModal);
app.component('SettingsModal', SettingsModal);
app.component('LogSidebar', LogSidebar);
app.component('FiletreeSidebar', FiletreeSidebar);
app.component('filetree-node', FiletreeNode);
app.component('TodoSidebar', TodoSidebar);
app.component('TasksSidebar', TasksSidebar);
app.component('PlanModal', PlanModal);

app.mount('#app');
