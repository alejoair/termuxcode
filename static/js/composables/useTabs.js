// ===== Composable: Gestión de Pestañas =====

import { reactive, ref, computed, watch } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const DEFAULT_SETTINGS = {
    permission_mode: 'acceptEdits',
    model: 'sonnet',
    system_prompt: '',
    rolling_window: 100,
    tools: ['Agent', 'Bash', 'Glob', 'Grep', 'Read', 'Edit', 'Write', 'NotebookEdit',
            'TodoWrite', 'WebSearch', 'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode',
            'EnterWorktree', 'TaskOutput', 'TaskStop', 'Skill',
            'ListMcpResourcesTool', 'ReadMcpResourceTool'],
    disabledMcpServers: [],
};

let tabCounter = 0;

export function useTabs() {
    // Estado reactivo
    const tabs = reactive(new Map());
    const activeTabId = ref(null);

    // Computed properties
    const activeTab = computed(() => {
        return activeTabId.value ? tabs.get(activeTabId.value) : null;
    });

    const tabsArray = computed(() => {
        return Array.from(tabs.values());
    });

    const statusColor = computed(() => {
        const allTabs = tabsArray.value;
        if (allTabs.length === 0) return 'bg-warn';

        const connectedCount = allTabs.filter(t => t.isConnected).length;

        if (connectedCount === allTabs.length) return 'bg-ok';
        if (connectedCount > 0) return 'bg-warn';
        return 'bg-err';
    });

    const statusText = computed(() => {
        const allTabs = tabsArray.value;
        if (allTabs.length === 0) return 'Sin pestañas';
        const connectedCount = allTabs.filter(t => t.isConnected).length;
        const failedCount = allTabs.filter(t => t.reconnectFailed).length;
        if (failedCount === allTabs.length) return 'Sin conexion';
        return `${connectedCount}/${allTabs.length} conectados`;
    });

    // Métodos
    async function createTab(name = null, cwd = null) {
        // En Tauri sin cwd: abrir diálogo de carpeta nativo
        if (!cwd && window.__TAURI__) {
            try {
                const selected = await window.__TAURI__.dialog.open({
                    directory: true,
                    multiple: false,
                    title: 'Select working folder',
                });
                if (!selected) return null; // Usuario canceló
                cwd = selected;
            } catch (e) {
                console.warn('[useTabs] Dialog not available:', e);
            }
        }

        tabCounter++;
        const tabId = `tab_${Date.now()}_${tabCounter}`;
        const tabName = name || `Chat ${tabCounter}`;

        const newTab = reactive({
            id: tabId,
            name: tabName,
            color: null,
            cwd: cwd || null,
            sessionId: null,
            settings: { ...DEFAULT_SETTINGS },
            isConnected: false,
            messages: [],
            renderedMessages: [],
            mcpServers: [],
            mcpReady: false,
            builtinTools: [],
            toolsReady: false,
            // WebSocket connection
            ws: null,
            reconnectTimeout: null,
            reconnectAttempts: 0,
            reconnectFailed: false,
            isProcessing: false,
            // Plan
            plan: null,
            // Stats tracking
            stats: {
                totalInputTokens: 0,
                totalOutputTokens: 0,
                totalCacheCreationTokens: 0,
                totalCacheReadTokens: 0,
                totalCostUsd: 0,
                totalDurationMs: 0,
                totalApiDurationMs: 0,
                queryCount: 0,
                perQuery: [],
            },
        });

        tabs.set(tabId, newTab);
        activeTabId.value = tabId;

        return tabId;
    }

    function switchTab(tabId) {
        if (!tabs.has(tabId)) return false;

        activeTabId.value = tabId;
        return true;
    }

    function closeTab(tabId) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        // Desconectar si está conectado
        if (tab.ws) {
            try {
                tab.ws.close();
            } catch (e) {
                console.warn('[useTabs] Error closing WebSocket:', e);
            }
        }

        // Eliminar del Map
        tabs.delete(tabId);

        // Si era el tab activo, cambiar a otro
        if (activeTabId.value === tabId) {
            const remainingTabs = Array.from(tabs.keys());
            if (remainingTabs.length > 0) {
                activeTabId.value = remainingTabs[0];
            } else {
                activeTabId.value = null;
            }
        }

        return true;
    }

    function renameTab(tabId, newName) {
        const tab = tabs.get(tabId);
        if (!tab || !newName?.trim()) return false;

        tab.name = newName.trim();
        return true;
    }

    function setTabColor(tabId, color) {
        const tab = tabs.get(tabId);
        if (!tab) return false;
        tab.color = color || null;
        return true;
    }

    function getTab(tabId) {
        return tabs.get(tabId);
    }

    function updateTabSessionId(tabId, sessionId) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        // Re-key: migrar del viejo ID al nuevo session_id
        const oldId = tabId;
        const newId = sessionId;

        if (oldId === newId) return true;

        // Crear nuevo tab con el nuevo ID
        tabs.delete(oldId);
        tab.id = newId;
        tab.sessionId = sessionId;
        tabs.set(newId, tab);

        // Actualizar activeTabId si corresponde
        if (activeTabId.value === oldId) {
            activeTabId.value = newId;
        }

        return true;
    }

    function clearTabMessages(tabId) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.messages = [];
        tab.renderedMessages = [];
        return true;
    }

    function updateTabSettings(tabId, settings) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.settings = { ...tab.settings, ...settings };
        return true;
    }

    function updateTabCwd(tabId, cwd) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.cwd = cwd;
        return true;
    }

    function updateTabMcpServers(tabId, servers) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.mcpServers = servers || [];
        return true;
    }

    function updateTabBuiltinTools(tabId, tools) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.builtinTools = tools || [];
        tab.toolsReady = true;
        return true;
    }

    function updateTabPlan(tabId, plan) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.plan = plan;
        return true;
    }

    function resetTabReadyFlags(tabId) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.toolsReady = false;
        tab.mcpReady = false;
        tab.builtinTools = [];
        tab.mcpServers = [];
        return true;
    }

    function updateTabStats(tabId, usage, costUsd, durationMs, apiDurationMs) {
        const tab = tabs.get(tabId);
        if (!tab || !usage) return false;

        tab.stats.totalInputTokens += usage.input_tokens || 0;
        tab.stats.totalOutputTokens += usage.output_tokens || 0;
        tab.stats.totalCacheCreationTokens += usage.cache_creation_input_tokens || 0;
        tab.stats.totalCacheReadTokens += usage.cache_read_input_tokens || 0;

        if (costUsd) {
            tab.stats.totalCostUsd += costUsd;
        }

        if (durationMs) {
            tab.stats.totalDurationMs += durationMs;
        }

        if (apiDurationMs) {
            tab.stats.totalApiDurationMs += apiDurationMs;
        }

        tab.stats.queryCount++;

        // Guardar stats de este turno individual
        tab.stats.perQuery.push({
            queryNumber: tab.stats.queryCount,
            inputTokens: usage.input_tokens || 0,
            outputTokens: usage.output_tokens || 0,
            cacheCreationTokens: usage.cache_creation_input_tokens || 0,
            cacheReadTokens: usage.cache_read_input_tokens || 0,
            costUsd: costUsd || 0,
            durationMs: durationMs || 0,
            apiDurationMs: apiDurationMs || 0,
        });

        return true;
    }

    function resetTabStats(tabId) {
        const tab = tabs.get(tabId);
        if (!tab) return false;

        tab.stats = {
            totalInputTokens: 0,
            totalOutputTokens: 0,
            totalCacheCreationTokens: 0,
            totalCacheReadTokens: 0,
            totalCostUsd: 0,
            totalDurationMs: 0,
            totalApiDurationMs: 0,
            queryCount: 0,
            perQuery: [],
        };

        return true;
    }

    // Serialización para localStorage
    function serializeTabs() {
        return Array.from(tabs.entries()).map(([id, tab]) => ({
            id,
            name: tab.name,
            color: tab.color,
            cwd: tab.cwd,
            sessionId: tab.sessionId,
            renderedMessages: tab.renderedMessages,
            settings: tab.settings,
            plan: tab.plan,
            mcpServers: tab.mcpServers,
            stats: tab.stats,
        }));
    }

    function deserializeTabs(data) {
        if (!Array.isArray(data)) return;

        tabs.clear();
        tabCounter = 0;

        data.forEach((tabData) => {
            const tab = reactive({
                ...tabData,
                color: tabData.color || null,
                isConnected: false,
                mcpReady: false,
                toolsReady: false,
                builtinTools: [],
                messages: [],
                ws: null,
                reconnectTimeout: null,
                reconnectAttempts: 0,
                reconnectFailed: false,
                isProcessing: false,
                stats: tabData.stats || {
                    totalInputTokens: 0,
                    totalOutputTokens: 0,
                    totalCacheCreationTokens: 0,
                    totalCacheReadTokens: 0,
                    totalCostUsd: 0,
                    totalDurationMs: 0,
                    totalApiDurationMs: 0,
                    queryCount: 0,
                    perQuery: [],
                },
            });

            tabs.set(tabData.id, tab);

            // Actualizar contador
            const match = tabData.name.match(/Chat (\d+)/);
            if (match) {
                tabCounter = Math.max(tabCounter, parseInt(match[1]));
            }
        });

        // Restaurar tab activo
        if (tabs.size > 0 && !activeTabId.value) {
            const firstTabId = tabs.keys().next().value;
            activeTabId.value = firstTabId;
        }
    }

    return {
        // Estado
        tabs,
        activeTabId,
        activeTab,
        tabsArray,
        statusColor,
        statusText,

        // Métodos
        createTab,
        switchTab,
        closeTab,
        renameTab,
        setTabColor,
        getTab,
        updateTabSessionId,
        clearTabMessages,
        updateTabSettings,
        updateTabCwd,
        updateTabMcpServers,
        updateTabBuiltinTools,
        updateTabPlan,
        resetTabReadyFlags,
        updateTabStats,
        resetTabStats,

        // Serialización
        serializeTabs,
        deserializeTabs,
    };
}
