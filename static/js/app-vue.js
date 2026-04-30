// ===== TERMUXCODE - Vue 3 App =====

import { createApp, ref, computed, onMounted, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// API base: in Tauri mode (tauri:// protocol) relative URLs don't work, use localhost
const API_BASE = window.location.protocol === 'tauri:' ? 'http://localhost:1988' : '';

// Importar componentes
import AppHeader from './components/AppHeader.js';
import MessageList from './components/MessageList.js';
import InputBar from './components/InputBar.js';
import ActionToolbar from './components/ActionToolbar.js';
import McpModal from './components/McpModal.js';
import SettingsModal from './components/SettingsModal.js';
import TerminalSidebar from './components/TerminalSidebar.js';
import FiletreeSidebar, { FiletreeNode } from './components/FiletreeSidebar.js';
import TodoSidebar from './components/TodoSidebar.js';
import TasksSidebar from './components/TasksSidebar.js';
import EditorSidebar from './components/EditorSidebar.js';
import PlanModal from './components/PlanModal.js';


// Importar composables
import { useTabs } from './composables/useTabs.js';
import { useWebSocket } from './composables/useWebSocket.js';
import { useStorage } from './composables/useStorage.js';
import { useMessages, computeLineDiff } from './composables/useMessages.js';
import { useSharedState } from './composables/useSharedState.js';
import { useServerLogs } from './composables/useServerLogs.js';
import { useTerminal } from './composables/useTerminal.js';
import { useTodoSidebar } from './composables/useTodoSidebar.js';
import { useTasksSidebar } from './composables/useTasksSidebar.js';
import { useFiletree } from './composables/useFiletree.js';
import { useEditorSidebar } from './composables/useEditorSidebar.js';
import { useIsMobile } from './composables/useIsMobile.js';
import { useUiState } from './composables/useUiState.js';

// ===== Componente Principal =====
const app = createApp({
    template: `
        <div class="flex overflow-hidden" style="height: 100dvh">
            <!-- ===== DESKTOP LAYOUT ===== -->
            <template v-if="!isMobileValue">
                <filetree-sidebar
                    :tree="filetreeTree"
                    :expanded="filetreeExpanded"
                    :expanded-paths="filetreeExpandedPaths"
                    :file-count="filetreeFileCount"
                    :expanded-width="filetreeWidthValue"
                    @toggle-expanded="filetree.toggleExpanded()"
                    @toggle-path="filetree.togglePath($event)"
                    @expand-all="filetree.expandAll()"
                    @collapse-all="filetree.collapseAll()"
                    @open-file="handleOpenFile"
                />
                <terminal-sidebar
                    :is-open="terminalOpen"
                    :is-mobile="false"
                    :sidebar-width="500"
                    @toggle="terminal.toggleSidebar()"
                />
                <div class="flex flex-col flex-1 min-w-0 p-4 safe-areas overflow-hidden">
                    <app-header
                        :state="sharedState"
                        :todo-count="todoSidebarItems.length"
                        :todo-open="todoSidebarOpen"
                        :log-open="terminalOpen"
                        @switch-tab="handleSwitchTab"
                        @close-tab="handleCloseTab"
                        @new-tab="handleNewTab"
                        @rename-tab="handleRenameTab"
                        @set-tab-color="handleSetTabColor"
                        @toggle-sidebar="terminal.toggleSidebar()"
                        @toggle-todo-sidebar="todoSidebar.toggleSidebar()"
                    />

                    <message-list
                        :messages="sharedState.activeMessages"
                        :is-processing="sharedState.isProcessing"
                        :scroll-ratio="activeScrollRatio"
                        class="flex-1 overflow-y-auto min-h-0"
                        @scroll-change="handleScrollChange"
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
                        @approve="handlePlanApprove"
                        @reject="handlePlanReject"
                    />
                </div>

                <!-- Editor sidebar derecha -->
                <editor-sidebar
                    ref="editorSidebarRef"
                    :open-files="editorSidebarOpenFiles"
                    :active-file-path="editorSidebarActiveFilePath"
                    :expanded="editorSidebarExpanded"
                    :lsp-client="editorSidebarLspClient"
                    :expanded-width="editorWidthValue"
                    :diff-ranges="editorSidebarDiffRanges"
                    @toggle-expanded="editorSidebar.toggleExpanded()"
                    @close-file="editorSidebar.closeFile($event)"
                    @set-active="editorSidebar.setActiveFile($event)"
                    @file-dirty="handleFileDirty"
                    @save-file="handleSaveFile"
                    @update-content="handleEditorContentUpdate"
                    @clear-diff="handleClearDiff"
                />

                <!-- Tasks sidebar derecha (siempre visible) -->
                <tasks-sidebar
                    :tasks="tasksSidebarItems"
                    :expanded="tasksSidebarExpanded"
                    :total-count="tasksSidebarTotalCount"
                    :progress-percent="tasksSidebarProgressPercent"
                    :pending-count="tasksSidebarPendingCount"
                    :in-progress-count="tasksSidebarInProgressCount"
                    :completed-count="tasksSidebarCompletedCount"
                    :stats="sharedState.activeStats"
                    :expanded-width="tasksWidthValue"
                    @toggle-expanded="tasksSidebar.toggleExpanded()"
                />
            </template>

            <!-- ===== MOBILE LAYOUT ===== -->
            <template v-else>
                <div class="flex flex-col w-full h-full safe-areas overflow-hidden">
                    <app-header
                        :state="sharedState"
                        :is-mobile="true"
                        :todo-count="todoSidebarItems.length"
                        :todo-open="todoSidebarOpen"
                        :log-open="terminalOpen"
                        @switch-tab="handleSwitchTab"
                        @close-tab="handleCloseTab"
                        @new-tab="handleNewTab"
                        @rename-tab="handleRenameTab"
                        @set-tab-color="handleSetTabColor"
                        @toggle-sidebar="toggleMobileDrawer('terminal')"
                        @toggle-todo-sidebar="todoSidebar.toggleSidebar()"
                        @toggle-filetree="toggleMobileDrawer('filetree')"
                        @toggle-editor="toggleMobileDrawer('editor')"
                        @toggle-tasks="toggleMobileDrawer('tasks')"
                    />

                    <message-list
                        :messages="sharedState.activeMessages"
                        :is-processing="sharedState.isProcessing"
                        :scroll-ratio="activeScrollRatio"
                        class="flex-1 overflow-y-auto min-h-0 px-2"
                        @scroll-change="handleScrollChange"
                    />

                    <!-- InputBar -->
                    <input-bar
                        :message="sharedState.inputMessage"
                        :no-tab="!sharedState.hasActiveTab"
                        :disabled="!sharedState.toolsReady || !sharedState.isConnected"
                        :failed="sharedState.reconnectFailed"
                        :is-mobile="true"
                        loading-text="Reconectando..."
                        @update:message="sharedState.inputMessage = $event"
                        @send="handleSend"
                    />

                    <!-- Mobile: bottom bar — drawer toggles + action icons -->
                    <div class="mobile-bottom-bar">
                        <!-- Drawer toggles -->
                        <button @click="toggleMobileDrawer('filetree')" title="Archivos"
                            class="mobile-action-icon"
                            :class="{ active: mobileDrawer === 'filetree' }">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                            </svg>
                        </button>
                        <button @click="toggleMobileDrawer('terminal')" title="Terminal"
                            class="mobile-action-icon"
                            :class="{ active: mobileDrawer === 'terminal' }">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
                            </svg>
                        </button>
                        <button @click="toggleMobileDrawer('editor')" title="Editor"
                            class="mobile-action-icon"
                            :class="{ active: mobileDrawer === 'editor' }">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                        </button>
                        <button @click="toggleMobileDrawer('tasks')" title="Tasks"
                            class="mobile-action-icon"
                            :class="{ active: mobileDrawer === 'tasks' }">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </button>

                        <div class="mobile-bottom-sep"></div>

                        <!-- Action toolbar inline -->
                        <action-toolbar
                            :selected-model="sharedState.selectedModel"
                            :mcp-ready="sharedState.mcpReady"
                            :tools-ready="sharedState.toolsReady"
                            :is-mobile="true"
                            @change-model="handleChangeModel"
                            @stop="handleStop"
                            @clear="handleClear"
                            @disconnect="handleDisconnect"
                            @open-mcp="handleOpenMcp"
                            @open-settings="handleOpenSettings"
                        />
                    </div>

                    <!-- Modals (fixed overlays, funcionan igual) -->
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
                        @approve="handlePlanApprove"
                        @reject="handlePlanReject"
                    />
                </div>

                <!-- ===== Mobile Drawers (position: fixed) ===== -->

                <!-- Filetree Drawer (izquierda) -->
                <div v-if="mobileDrawer === 'filetree'" class="drawer-overlay" @click="closeMobileDrawer"></div>
                <div v-if="mobileDrawer === 'filetree'" class="drawer-left drawer-open bg-base border-r border-border">
                    <filetree-sidebar
                        :tree="filetreeTree"
                        :expanded="true"
                        :is-mobile="true"
                        :expanded-paths="filetreeExpandedPaths"
                        :file-count="filetreeFileCount"
                        @toggle-expanded="closeMobileDrawer"
                        @toggle-path="filetree.togglePath($event)"
                        @expand-all="filetree.expandAll()"
                        @collapse-all="filetree.collapseAll()"
                        @open-file="handleOpenFile"
                    />
                </div>

                <!-- Terminal Drawer (izquierda) -->
                <div v-if="mobileDrawer === 'terminal'" class="drawer-overlay" @click="closeMobileDrawer"></div>
                <div v-if="mobileDrawer === 'terminal'" class="drawer-left drawer-open bg-base border-r border-border">
                    <terminal-sidebar
                        :is-open="true"
                        :is-mobile="true"
                        @toggle="closeMobileDrawer"
                    />
                </div>

                <!-- Editor Drawer (derecha) -->
                <div v-if="mobileDrawer === 'editor'" class="drawer-overlay" @click="closeMobileDrawer"></div>
                <div v-if="mobileDrawer === 'editor'" class="drawer-right drawer-open bg-base border-l border-border">
                    <editor-sidebar
                        ref="editorSidebarRef"
                        :open-files="editorSidebarOpenFiles"
                        :active-file-path="editorSidebarActiveFilePath"
                        :expanded="true"
                        :is-mobile="true"
                        :lsp-client="editorSidebarLspClient"
                        :diff-ranges="editorSidebarDiffRanges"
                        @toggle-expanded="closeMobileDrawer"
                        @close-file="editorSidebar.closeFile($event)"
                        @set-active="editorSidebar.setActiveFile($event)"
                        @file-dirty="handleFileDirty"
                        @save-file="handleSaveFile"
                        @update-content="handleEditorContentUpdate"
                        @clear-diff="handleClearDiff"
                    />
                </div>

                <!-- Tasks Drawer (derecha) -->
                <div v-if="mobileDrawer === 'tasks'" class="drawer-overlay" @click="closeMobileDrawer"></div>
                <div v-if="mobileDrawer === 'tasks'" class="drawer-right drawer-open bg-base border-l border-border">
                    <tasks-sidebar
                        :tasks="tasksSidebarItems"
                        :expanded="true"
                        :is-mobile="true"
                        :total-count="tasksSidebarTotalCount"
                        :progress-percent="tasksSidebarProgressPercent"
                        :pending-count="tasksSidebarPendingCount"
                        :in-progress-count="tasksSidebarInProgressCount"
                        :completed-count="tasksSidebarCompletedCount"
                        :stats="sharedState.activeStats"
                        @toggle-expanded="closeMobileDrawer"
                    />
                </div>
            </template>
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
        const editorSidebar = useEditorSidebar();
        const { isMobile } = useIsMobile();
        const isMobileValue = computed(() => isMobile.value);

        // UI State persistence
        const uiState = useUiState();

        // Computed wrappers de width defaults para pasar como props a componentes
        // Los componentes usan useResizable internamente para manejar sus propios anchos
        const filetreeWidthValue = computed(() => 320);
        const editorWidthValue = computed(() => 500);
        const tasksWidthValue = computed(() => 320);

        // Pending diffs: toolUseId → { filePath, oldContent, block }
        const pendingDiffs = new Map();

        // Scroll ratio por tab
        const activeScrollRatio = computed(() => {
            const tabId = tabs.activeTabId.value;
            return tabId ? uiState.getScrollRatio(tabId) : null;
        });

        function handleScrollChange(ratio) {
            const tabId = tabs.activeTabId.value;
            if (tabId) uiState.setScrollRatio(tabId, ratio);
        }

        // Mobile drawer state
        const mobileDrawer = ref(null); // 'filetree' | 'logs' | 'editor' | 'tasks' | null
        function toggleMobileDrawer(name) {
            mobileDrawer.value = mobileDrawer.value === name ? null : name;
        }
        function closeMobileDrawer() {
            mobileDrawer.value = null;
        }

        // Terminal (reemplaza log sidebar)
        const terminal = useTerminal();
        const terminalOpen = computed(() => terminal.isOpen.value);

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

        // Desenvolver editorSidebar para el template
        const editorSidebarOpenFiles = computed(() => editorSidebar.openFiles.value);
        const editorSidebarActiveFilePath = computed(() => editorSidebar.activeFilePath.value);
        const editorSidebarExpanded = computed(() => editorSidebar.expanded.value);
        const editorSidebarLspClient = computed(() => editorSidebar.getLspClient());
        const editorSidebarRef = ref(null); // template ref para acceder al componente
        const editorSidebarDiffRanges = computed(() => {
            const path = editorSidebar.activeFilePath.value;
            return path ? editorSidebar.getDiffRanges(path) : null;
        });

        // Modal state
        const showMcpModal = ref(false);
        const showSettingsModal = ref(false);
        const showPlanModal = ref(false);
        const planContent = ref('');
        const planTab = ref(null); // tab activo cuando se recibió el plan

        function handlePlanApprove() {
            showPlanModal.value = false;
            const tab = planTab.value;
            if (tab?.ws?.readyState === WebSocket.OPEN) {
                tab.ws.send(JSON.stringify({ type: 'tool_approval_response', allow: true }));
            }
            planTab.value = null;
        }

        function handlePlanReject() {
            showPlanModal.value = false;
            const tab = planTab.value;
            if (tab?.ws?.readyState === WebSocket.OPEN) {
                tab.ws.send(JSON.stringify({ type: 'tool_approval_response', allow: false }));
            }
            planTab.value = null;
        }

        // ===== Diff Capture for Agent Edits =====
        async function captureBeforeContent(block) {
            const filePath = block.input?.file_path;
            if (!filePath) return;
            const toolUseId = block.id;
            let oldContent = '';

            try {
                // Check if file is open in editor and not dirty — use its content
                const existing = editorSidebar.openFiles.value.find(f => f.path === filePath);
                if (existing && !existing.dirty) {
                    oldContent = existing.content;
                } else {
                    // Fetch current content from disk (before SDK executes the tool)
                    const res = await fetch(API_BASE + '/api/file?path=' + encodeURIComponent(filePath));
                    if (res.ok) {
                        const data = await res.json();
                        oldContent = data.content || '';
                    } else {
                        // File doesn't exist yet (new file) — old content is empty
                        oldContent = '';
                    }
                }
            } catch {
                oldContent = '';
            }

            console.log('[diff] captureBeforeContent stored — toolUseId:', toolUseId, 'filePath:', filePath, 'oldContent len:', oldContent.length);
            pendingDiffs.set(toolUseId, { filePath, oldContent, block });
        }

        async function handleFileEditComplete(toolUseId) {
            const pending = pendingDiffs.get(toolUseId);
            if (!pending) return;
            pendingDiffs.delete(toolUseId);

            const { filePath, oldContent, block } = pending;

            try {
                // Determine new content
                let newContent;
                if (block.name === 'Write' && block.input?.content !== undefined) {
                    // Write tool has the full content in the input
                    newContent = block.input.content;
                } else {
                    // Edit tool or fallback — fetch the file from disk
                    const res = await fetch(API_BASE + '/api/file?path=' + encodeURIComponent(filePath));
                    if (res.ok) {
                        const data = await res.json();
                        newContent = data.content || '';
                    } else {
                        return; // Can't get new content
                    }
                }

                // Compute diff
                const diffLines = computeLineDiff(oldContent, newContent);

                // Build ranges for diff decorations
                const addRanges = [];
                const removeRanges = [];

                // Track current line in new content (1-based)
                let newLineNum = 0;
                for (const line of diffLines) {
                    if (line.type === 'equal') {
                        newLineNum = line.newLine + 1;
                    } else if (line.type === 'add') {
                        newLineNum = line.newLine + 1;
                        addRanges.push({ line: newLineNum });
                    } else if (line.type === 'remove') {
                        // Insert remove widget before the next new-line or at position
                        const insertLine = newLineNum > 0 ? newLineNum + 1 : 1;
                        removeRanges.push({ line: insertLine, content: line.content });
                    }
                }

                const ranges = { addRanges, removeRanges };

                // If no diff, skip
                if (addRanges.length === 0 && removeRanges.length === 0) return;

                // Save diff state
                editorSidebar.setDiffRanges(filePath, ranges);

                // Check if file is dirty in editor — don't overwrite
                const existing = editorSidebar.openFiles.value.find(f => f.path === filePath);
                if (existing && existing.dirty) {
                    // Just activate the tab, don't overwrite content
                    editorSidebar.setActiveFile(filePath);
                    editorSidebar.setExpanded(true);
                    return;
                }

                // Open/update file in editor with new content
                const name = filePath.split(/[\\/]/).pop();
                const ext = name.split('.').pop().toLowerCase();
                const langMap = {
                    py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript',
                    tsx: 'typescript', html: 'html', css: 'css', json: 'json',
                    md: 'markdown', txt: 'text',
                };

                if (existing) {
                    editorSidebar.updateFileContent(filePath, newContent);
                    editorSidebar.setActiveFile(filePath);
                    editorSidebar.setExpanded(true);
                } else {
                    editorSidebar.openFile(filePath, name, newContent, langMap[ext] || 'text');
                }

                // Esperar dos ticks: el watcher de activeContent llama $nextTick internamente,
                // necesitamos que updateEditor() termine antes de aplicar el diff.
                await nextTick();
                await nextTick();

                // Guardar diff state y aplicar al editor
                editorSidebar.setDiffRanges(filePath, ranges);
                if (editorSidebarRef.value?.showDiff) {
                    editorSidebarRef.value.showDiff(ranges);
                }
            } catch (e) {
                console.error('[handleFileEditComplete] Error:', e);
            }
        }

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
                    // Sincronizar disabledMcpServers con el estado real del backend
                    const backendDisabled = (data.servers || [])
                        .filter(s => s.status === 'disabled')
                        .map(s => s.name);
                    tabs.updateTabSettings(tabId, { disabledMcpServers: backendDisabled });
                    tab.mcpReady = true;
                },
                assistant: () => {
                    const blocks = msg.processAssistantBlocks(data.blocks);
                    blocks.forEach(block => {
                        msg.addMessageToTab(tab, block);
                        if (block.type === 'tool_use') {
                            console.log('[diff] tool_use block:', block.name, 'id:', block.id, 'input keys:', Object.keys(block.input || {}));
                        }
                        // Capture before-content for Write/Edit tools
                        if (block.type === 'tool_use' && (block.name === 'Write' || block.name === 'Edit')) {
                            captureBeforeContent(block);
                        }
                    });
                },
                user: () => {
                    if (data.blocks) {
                        const results = msg.processToolResultBlocks(data.blocks);
                        results.forEach(r => {
                            msg.addMessageToTab(tab, r);
                            console.log('[diff] tool_result — toolUseId:', r.toolUseId, 'pendingDiffs has it:', pendingDiffs.has(r.toolUseId), 'pendingDiffs keys:', [...pendingDiffs.keys()]);
                            // Check if this result corresponds to a pending diff
                            if (r.toolUseId && pendingDiffs.has(r.toolUseId)) {
                                handleFileEditComplete(r.toolUseId);
                            }
                        });
                    }
                },
                result: () => {
                    if (data.blocks) {
                        const results = msg.processToolResultBlocks(data.blocks);
                        results.forEach(r => msg.addMessageToTab(tab, r));
                    }
                    msg.addMessageToTab(tab, {
                        type: 'result',
                        subtype: data.subtype,
                        cost: data.cost,
                        usage: data.usage,
                        totalCostUsd: data.total_cost_usd,
                        durationMs: data.duration_ms,
                        durationApiMs: data.duration_api_ms,
                    });

                    // Actualizar stats acumuladas del tab
                    if (data.usage) {
                        tabs.updateTabStats(
                            tabId,
                            data.usage,
                            data.total_cost_usd,
                            data.duration_ms,
                            data.duration_api_ms
                        );
                    }

                    tab.isProcessing = false;
                },
                system: () => {
                    msg.addMessageToTab(tab, { type: 'system', message: data.message });
                },
                file_view: () => {
                    planContent.value = data.content || '';
                    planTab.value = tab;
                    showPlanModal.value = true;
                },
                todo_update: () => {
                    todoSidebar.setTodos(data.todos || []);
                    tasksSidebar.setTasks(data.todos || []);
                },
                lsp_open_result: () => {
                    editorSidebar.handleLspMessage(data);
                },
                lsp_response: () => {
                    editorSidebar.handleLspMessage(data);
                },
                lsp_notification: () => {
                    editorSidebar.handleLspMessage(data);
                },
            };

            handlers[data.type]?.();
        }

        // ===== Tabs Handlers =====
        async function handleNewTab() {
            const tabId = await tabs.createTab();
            if (!tabId) return; // Usuario canceló diálogo en Tauri
            const tab = tabs.getTab(tabId);
            if (tab) {
                ws.connectTab(tab, handleMessage);
            }
            updateLspConnection();
        }

        function handleSwitchTab(tabId) {
            tabs.switchTab(tabId);
            updateLspConnection();
        }

        function handleCloseTab(tabId) {
            const tab = tabs.getTab(tabId);
            if (tab) {
                ws.sendCommand(tab, '/destroy');
                ws.disconnectTab(tab);
            }
            tabs.closeTab(tabId);
        }

        function handleRenameTab(tabId, newName) {
            tabs.renameTab(tabId, newName);
        }

        function handleSetTabColor(tabId, color) {
            tabs.setTabColor(tabId, color);
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
            if (tabId) {
                tabs.clearTabMessages(tabId);
                tabs.resetTabStats(tabId);
            }
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

        // ===== LSP Connection =====
        function updateLspConnection() {
            const tab = tabs.activeTab.value;
            if (tab?.ws?.readyState === WebSocket.OPEN) {
                editorSidebar.setLspSendFunction((data) => {
                    if (tab.ws?.readyState === WebSocket.OPEN) {
                        tab.ws.send(JSON.stringify(data));
                    }
                });
                // Re-open active file in new session's LSP
                editorSidebar.reconnectLsp();
            } else {
                editorSidebar.setLspSendFunction(null);
            }
        }

        async function handleOpenFile(path) {
            const name = path.split(/[\\/]/).pop();
            const ext = name.split('.').pop().toLowerCase();
            const langMap = {
                py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript',
                tsx: 'typescript', html: 'html', css: 'css', json: 'json',
                md: 'markdown', txt: 'text',
            };

            // Si el archivo ya está abierto, solo activarlo (no re-fetch)
            const existing = editorSidebar.openFiles.value.find(f => f.path === path);
            if (existing) {
                editorSidebar.setActiveFile(path);
                return;
            }

            // Abrir con placeholder y expandir
            editorSidebar.openFile(path, name, '// Cargando...', langMap[ext] || 'text');

            // Fetch contenido real
            try {
                const res = await fetch(API_BASE + '/api/file?path=' + encodeURIComponent(path));
                if (!res.ok) {
                    const err = await res.json();
                    editorSidebar.updateFileContent(path, `// Error: ${err.error}`);
                    return;
                }
                const data = await res.json();
                editorSidebar.updateFileContent(path, data.content);
            } catch (e) {
                editorSidebar.updateFileContent(path, `// Error de conexión: ${e.message}`);
            }
        }

        function handleFileDirty({ path }) {
            editorSidebar.markDirty(path);
        }

        async function handleSaveFile({ path, content }) {
            try {
                const res = await fetch(API_BASE + '/api/file', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, content }),
                });
                if (!res.ok) {
                    const err = await res.json();
                    console.error('[handleSaveFile] error:', err.error);
                    return;
                }
                editorSidebar.markClean(path);
                editorSidebar.updateFileContent(path, content);
                if (editorSidebarRef.value?.showSaveStatus) {
                    editorSidebarRef.value.showSaveStatus('Saved \u2713');
                }
            } catch (e) {
                console.error('[handleSaveFile] fetch failed:', e);
            }
        }

        function handleEditorContentUpdate({ path, content }) {
            const files = editorSidebar.openFiles.value;
            const file = files.find(f => f.path === path);
            if (file) file.content = content;
        }

        function handleClearDiff({ path }) {
            editorSidebar.clearDiff(path);
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
        onMounted(async () => {
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
                updateLspConnection();
            });

            // Conexion: marcar tab como fallido
            window.addEventListener('tab-reconnect-failed', (event) => {
                const tab = tabs.getTab(event.detail.tabId);
                if (tab) tab.reconnectFailed = true;
            });

            // Restaurar estado de UI ANTES de restaurar tabs
            const uiDeps = {
                serverLogs,
                terminal,
                todoSidebar,
                tasksSidebar,
                filetree,
                editorSidebar,
            };
            await uiState.restore(uiDeps);

            // Setup auto-save para UI state
            uiState.setupAutoSave(uiDeps);

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

                const allTabs = tabs.tabsArray.value;
                if (allTabs.length > 0) {
                    if (savedActiveTabId && tabs.getTab(savedActiveTabId)) {
                        tabs.switchTab(savedActiveTabId);
                    } else {
                        tabs.switchTab(allTabs[0].id);
                    }

                    // Reconectar todos los tabs — si no tienen sessionId, el backend crea sesión nueva
                    allTabs.forEach(tab => {
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
                uiState.saveNow(uiDeps);
            });
        });

        return {
            sharedState,
            showMcpModal,
            showSettingsModal,
            showPlanModal,
            planContent,
            handlePlanApprove,
            handlePlanReject,
            serverLogs,
            terminal,
            terminalOpen,
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
            editorSidebar,
            editorSidebarRef,
            editorSidebarOpenFiles,
            editorSidebarActiveFilePath,
            editorSidebarExpanded,
            editorSidebarLspClient,
            editorSidebarDiffRanges,
            handleNewTab,
            handleSwitchTab,
            handleCloseTab,
            handleRenameTab,
            handleSetTabColor,
            handleSend,
            handleChangeModel,
            handleStop,
            handleClear,
            handleDisconnect,
            handleOpenMcp,
            handleOpenSettings,
            handleApplyMcp,
            handleSaveSettings,
            handleOpenFile,
            handleFileDirty,
            handleSaveFile,
            handleEditorContentUpdate,
            handleClearDiff,
            isMobileValue,
            mobileDrawer,
            toggleMobileDrawer,
            closeMobileDrawer,
            filetreeWidthValue,
            editorWidthValue,
            tasksWidthValue,
            activeScrollRatio,
            handleScrollChange,
        };
    },
});

app.component('AppHeader', AppHeader);
app.component('MessageList', MessageList);
app.component('InputBar', InputBar);
app.component('ActionToolbar', ActionToolbar);
app.component('McpModal', McpModal);
app.component('SettingsModal', SettingsModal);
app.component('TerminalSidebar', TerminalSidebar);
app.component('FiletreeSidebar', FiletreeSidebar);
app.component('filetree-node', FiletreeNode);
app.component('TodoSidebar', TodoSidebar);
app.component('TasksSidebar', TasksSidebar);
app.component('EditorSidebar', EditorSidebar);
app.component('PlanModal', PlanModal);

app.mount('#app');
