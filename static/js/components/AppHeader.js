// Componente: App Header (con Tabs)
import { computed, toRefs } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export default {
    template: `
        <div class="app-header border-b border-border">
            <!-- Header: titulo + status -->
            <div class="app-header-inner flex items-center justify-between px-4 py-3">
                <div class="flex items-center gap-3">
                    <button
                        @click="$emit('toggle-sidebar')"
                        title="Server Logs"
                        class="w-7 h-7 flex items-center justify-center text-muted hover:text-txt transition-colors rounded"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
                        </svg>
                    </button>
                    <div class="title-wrapper">
                    <div class="title terminal-title text-txt">
                        <span class="terminal-prompt">&gt;</span> TERMUXCODE<span class="terminal-cursor">_</span>
                    </div>
                </div>
                </div>
                <div class="right">
                    <div class="status flex items-center gap-2">
                        <div :class="['w-2 h-2 rounded-full', localStatusColor]"></div>
                        <span class="text-sm text-muted">{{ localStatusText }}</span>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="app-tabs px-4 pb-2">
                <div class="app-tabs-inner flex items-center gap-2">
                    <div class="tabs-header flex gap-1 flex-1">
                        <button
                            v-for="tab in localTabs"
                            :key="tab.id"
                            @click="handleSwitchTab(tab.id)"
                            :class="[
                                'flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors border-2',
                                state.activeTabId === tab.id
                                    ? 'bg-surface text-txt border-border-focus'
                                    : 'bg-base/50 text-muted border-transparent hover:bg-raised/50'
                            ]"
                        >
                            <span :class="['w-1.5 h-1.5 rounded-full', tab.isConnected ? 'bg-ok' : 'bg-err']"></span>
                            <span>{{ tab.name }}</span>
                            <span
                                @click.stop="handleCloseTab(tab.id)"
                                class="ml-1 hover:text-err transition-colors"
                            >×</span>
                        </button>
                    </div>
                    <button
                        @click="handleNewTab"
                        title="Nueva pestaña"
                        class="bg-surface hover:bg-raised text-txt w-8 h-8 rounded flex items-center justify-center text-xl transition-colors flex-shrink-0"
                    >+</button>
                </div>
            </div>
        </div>
    `,

    props: {
        state: {
            type: Object,
            required: true,
        },
    },

    emits: ['switch-tab', 'close-tab', 'new-tab', 'toggle-sidebar'],

    setup(props, { emit }) {
        const localTabs = computed(() => props.state.tabsArray);
        const localStatusColor = computed(() => props.state.statusColor);
        const localStatusText = computed(() => props.state.statusText);

        function handleSwitchTab(tabId) {
            emit('switch-tab', tabId);
        }

        function handleCloseTab(tabId) {
            emit('close-tab', tabId);
        }

        function handleNewTab() {
            emit('new-tab');
        }

        return {
            localTabs,
            localStatusColor,
            localStatusText,
            handleSwitchTab,
            handleCloseTab,
            handleNewTab,
        };
    },
};
