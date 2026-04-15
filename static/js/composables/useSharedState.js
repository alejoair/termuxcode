// ===== Composable: Estado Reactivo Compartido =====
// Centraliza el estado que se pasa via props a los componentes hijos.
// Usa reactive con getters para mantener reactividad cruzada con otros composables.

import { reactive, ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export function useSharedState(tabs) {
    const inputMessage = ref('');

    const state = reactive({
        get activeTabId() { return tabs.activeTabId.value; },
        get tabsArray() { return tabs.tabsArray.value; },
        get statusColor() { return tabs.statusColor.value; },
        get statusText() { return tabs.statusText.value; },
        get activeMessages() {
            const tab = tabs.activeTab.value;
            return tab ? tab.renderedMessages || [] : [];
        },
        get selectedModel() {
            const tab = tabs.activeTab.value;
            return tab?.settings?.model || 'sonnet';
        },
        get activeMcpServers() {
            const tab = tabs.activeTab.value;
            return tab?.mcpServers || [];
        },
        get activeSettings() {
            const tab = tabs.activeTab.value;
            return tab?.settings || {};
        },
        get mcpReady() {
            const tab = tabs.activeTab.value;
            return tab?.mcpReady || false;
        },
        get toolsReady() {
            const tab = tabs.activeTab.value;
            return tab?.toolsReady || false;
        },
        get availableTools() {
            const tab = tabs.activeTab.value;
            return tab?.builtinTools || [];
        },
        get isConnected() {
            const tab = tabs.activeTab.value;
            return tab?.isConnected || false;
        },
        get reconnectFailed() {
            const tab = tabs.activeTab.value;
            return tab?.reconnectFailed || false;
        },
        get hasActiveTab() {
            return !!tabs.activeTab.value;
        },
        get isProcessing() {
            const tab = tabs.activeTab.value;
            return tab?.isProcessing || false;
        },
        get activeCwd() {
            const tab = tabs.activeTab.value;
            return tab?.cwd || '';
        },
        get activeStats() {
            const tab = tabs.activeTab.value;
            return tab?.stats || null;
        },
        get inputMessage() { return inputMessage.value; },
        set inputMessage(v) { inputMessage.value = v; },
    });

    return { state, inputMessage };
}
