// Componente: App Header (con Tabs)
import { computed, ref, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export default {
    template: `
        <div class="app-header border-b border-border" @click="colorPickerTabId = null">
            <!-- Header: titulo + status -->
            <div :class="['app-header-inner flex items-center justify-between', isMobile ? 'px-2 py-2' : 'px-4 py-3']">
                <div class="flex items-center gap-3">
                    <!-- Log toggle (desktop) -->
                    <button
                        v-if="!isMobile"
                        @click="$emit('toggle-sidebar')"
                        title="Server Logs"
                        :class="['w-7 h-7 flex items-center justify-center transition-colors rounded', logOpen ? 'text-txt bg-surface' : 'text-muted hover:text-txt']"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
                        </svg>
                    </button>
                    <!-- Todo toggle (desktop) -->
                    <button
                        v-if="!isMobile && todoCount > 0"
                        @click="$emit('toggle-todo-sidebar')"
                        :title="todoCount + ' tareas'"
                        :class="['w-7 h-7 flex items-center justify-center transition-colors rounded', todoOpen ? 'text-txt bg-surface' : 'text-muted hover:text-txt']"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </button>

                    <div v-if="!isMobile" class="title-wrapper">
                        <div class="title terminal-title text-txt">
                            <span class="terminal-prompt">&gt;</span> TERMUXCODE<span class="terminal-cursor">_</span>
                        </div>
                    </div>
                </div>
                <div class="right flex items-center gap-4">
                    <span v-if="!isMobile && cwd" class="text-sm text-txt font-mono truncate max-w-[400px] bg-surface px-2 py-0.5 rounded border border-border" :title="cwd">{{ cwd }}</span>
                    <div class="status flex items-center gap-2">
                        <div :class="['w-2 h-2 rounded-full', localStatusColor]"></div>
                        <span v-if="!isMobile" class="text-sm text-muted">{{ localStatusText }}</span>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div :class="['app-tabs', isMobile ? 'px-2 pb-1' : 'px-4 pb-2']">
                <div :class="['app-tabs-inner flex items-center gap-2', isMobile ? 'mobile-tabs-scroll' : '']">
                    <div class="tabs-header flex gap-1 flex-1" :class="isMobile ? 'mobile-tabs-scroll' : ''">
                        <button
                            v-for="tab in localTabs"
                            :key="tab.id"
                            @click="editingTabId !== tab.id && state.activeTabId !== tab.id && handleSwitchTab(tab.id)"
                            :class="[
                                'relative flex items-center gap-2 rounded transition-colors border-2 flex-shrink-0',
                                isMobile ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm',
                                state.activeTabId === tab.id
                                    ? (tab.color ? '' : 'bg-surface text-txt border-border-focus')
                                    : (tab.color ? '' : 'bg-base/50 text-muted border-transparent hover:bg-raised/50')
                            ]"
                            :style="getTabStyle(tab, state.activeTabId === tab.id)"
                        >
                            <!-- Connection dot -->
                            <span :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', tab.isConnected ? 'bg-ok' : 'bg-err']"></span>

                            <!-- Name or rename input -->
                            <input
                                v-if="editingTabId === tab.id"
                                :class="'tab-rename-input-' + tab.id + ' bg-transparent border-none outline-none text-txt w-20 max-w-28 min-w-0'"
                                :value="editingName"
                                @input="editingName = $event.target.value"
                                @keydown.enter.stop="commitRename(tab.id)"
                                @keydown.escape.stop="cancelRename()"
                                @blur="commitRename(tab.id)"
                                @click.stop
                            />
                            <span
                                v-else
                                @click.stop="state.activeTabId === tab.id ? startRename(tab) : handleSwitchTab(tab.id)"
                                :title="state.activeTabId === tab.id ? 'Click para renombrar' : ''"
                                :class="state.activeTabId === tab.id ? 'cursor-text hover:opacity-70' : ''"
                            >{{ tab.name }}</span>

                            <!-- Color swatch (desktop only) -->
                            <button
                                v-if="!isMobile"
                                @click.stop="toggleColorPicker(tab.id, $event)"
                                class="w-2.5 h-2.5 rounded-full flex-shrink-0 border border-border/50 hover:scale-125 transition-transform"
                                :style="{ backgroundColor: tab.color || '#475569' }"
                                title="Tab color"
                            ></button>

                            <!-- Color picker dropdown -->
                            <div
                                v-if="colorPickerTabId === tab.id"
                                class="absolute top-full left-0 z-50 mt-1 p-1.5 bg-surface border border-border rounded shadow-lg flex gap-1 flex-wrap"
                                style="min-width: 128px;"
                                @click.stop
                            >
                                <button
                                    v-for="c in TAB_COLORS"
                                    :key="c.value || 'default'"
                                    @click="selectColor(tab.id, c.value, $event)"
                                    :title="c.label"
                                    class="w-4 h-4 rounded-full border-2 hover:scale-110 transition-transform"
                                    :class="tab.color === c.value ? 'border-txt' : 'border-transparent'"
                                    :style="{ backgroundColor: c.value || '#475569' }"
                                ></button>
                            </div>

                            <!-- Cost badge (desktop only) -->
                            <span v-if="!isMobile && tab.stats && tab.stats.totalCostUsd > 0" class="text-xs text-muted font-mono ml-1">
                                \${{ tab.stats.totalCostUsd.toFixed(3) }}
                            </span>

                            <!-- Close -->
                            <span @click.stop="handleCloseTab(tab.id)" class="ml-1 hover:text-err transition-colors flex-shrink-0">×</span>
                        </button>
                    </div>
                    <button
                        @click="handleNewTab"
                        title="Nueva pestaña"
                        :class="['bg-surface hover:bg-raised text-txt rounded flex items-center justify-center text-xl transition-colors flex-shrink-0', isMobile ? 'w-7 h-7' : 'w-8 h-8']"
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
        isMobile: {
            type: Boolean,
            default: false,
        },
        todoCount: {
            type: Number,
            default: 0,
        },
        todoOpen: {
            type: Boolean,
            default: false,
        },
        logOpen: {
            type: Boolean,
            default: false,
        },
    },

    emits: ['switch-tab', 'close-tab', 'new-tab', 'rename-tab', 'set-tab-color', 'toggle-sidebar', 'toggle-todo-sidebar', 'toggle-filetree', 'toggle-editor', 'toggle-tasks'],

    setup(props, { emit }) {
        const localTabs = computed(() => props.state.tabsArray);
        const localStatusColor = computed(() => props.state.statusColor);
        const localStatusText = computed(() => props.state.statusText);
        const cwd = computed(() => props.state.activeCwd);

        // ===== Rename state =====
        const editingTabId = ref(null);
        const editingName = ref('');

        // ===== Color picker state =====
        const colorPickerTabId = ref(null);

        const TAB_COLORS = [
            { label: 'Default', value: null },
            { label: 'Teal',    value: '#0d9488' },
            { label: 'Sky',     value: '#0ea5e9' },
            { label: 'Purple',  value: '#a855f7' },
            { label: 'Pink',    value: '#ec4899' },
            { label: 'Orange',  value: '#f97316' },
            { label: 'Amber',   value: '#f59e0b' },
            { label: 'Green',   value: '#22c55e' },
            { label: 'Red',     value: '#f43f5e' },
        ];

        // ===== Rename handlers =====
        function startRename(tab) {
            if (colorPickerTabId.value) { colorPickerTabId.value = null; return; }
            editingTabId.value = tab.id;
            editingName.value = tab.name;
            nextTick(() => {
                document.querySelector(`.tab-rename-input-${tab.id}`)?.select();
            });
        }

        function commitRename(tabId) {
            if (editingName.value.trim()) emit('rename-tab', tabId, editingName.value.trim());
            editingTabId.value = null;
        }

        function cancelRename() {
            editingTabId.value = null;
        }

        // ===== Color picker handlers =====
        function toggleColorPicker(tabId, event) {
            event.stopPropagation();
            colorPickerTabId.value = colorPickerTabId.value === tabId ? null : tabId;
        }

        function selectColor(tabId, color, event) {
            event.stopPropagation();
            emit('set-tab-color', tabId, color);
            colorPickerTabId.value = null;
        }

        // ===== Tab style =====
        function getTabStyle(tab, isActive) {
            if (!tab.color) return {};
            return {
                borderColor: tab.color,
                backgroundColor: tab.color + (isActive ? '28' : '10'),
                color: 'var(--color-txt)',
            };
        }

        // ===== Existing handlers =====
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
            cwd,
            TAB_COLORS,
            editingTabId,
            editingName,
            colorPickerTabId,
            startRename,
            commitRename,
            cancelRename,
            toggleColorPicker,
            selectColor,
            getTabStyle,
            handleSwitchTab,
            handleCloseTab,
            handleNewTab,
        };
    },
};
