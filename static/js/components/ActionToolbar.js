// Componente: Action Toolbar
export default {
    template: `
        <div class="action-toolbar">
            <div class="toolbar-inner flex items-center justify-center gap-2 flex-wrap">
                <select
                    :value="selectedModel"
                    @change="$emit('change-model', $event.target.value)"
                    class="bg-base border border-border rounded px-3 py-2 text-txt text-sm focus:outline-none focus:border-border-focus"
                >
                    <option value="sonnet">sonnet</option>
                    <option value="opus">opus</option>
                    <option value="haiku">haiku</option>
                </select>

                <button
                    v-for="btn in buttons"
                    :key="btn.action"
                    @click="canClick(btn) && $emit(btn.action)"
                    :disabled="!canClick(btn)"
                    :title="btnTitle(btn)"
                    :class="[
                        'flex items-center gap-1 px-3 py-2 rounded text-sm transition-colors',
                        canClick(btn)
                            ? 'bg-surface hover:bg-raised text-txt cursor-pointer'
                            : 'bg-base text-muted cursor-not-allowed'
                    ]"
                >
                    <svg v-if="btn.action === 'open-settings' && !toolsReady" class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                    <svg v-else-if="btn.icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="btn.icon"></svg>
                    <span v-if="btn.label">{{ btn.label }}</span>
                </button>

                <!-- MCP button with loading state -->
                <button
                    @click="mcpReady && $emit('open-mcp')"
                    :disabled="!mcpReady"
                    :title="mcpReady ? 'MCP Servers' : 'Cargando MCP servers...'"
                    :class="[
                        'flex items-center gap-1 px-3 py-2 rounded text-sm transition-colors',
                        mcpReady
                            ? 'bg-surface hover:bg-raised text-txt cursor-pointer'
                            : 'bg-base text-muted cursor-not-allowed'
                    ]"
                >
                    <svg v-if="!mcpReady" class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
                    </svg>
                    <span>MCP</span>
                </button>
            </div>
        </div>
    `,

    props: {
        selectedModel: {
            type: String,
            default: 'sonnet',
        },
        mcpReady: {
            type: Boolean,
            default: false,
        },
        toolsReady: {
            type: Boolean,
            default: false,
        },
    },

    emits: ['change-model', 'stop', 'clear', 'disconnect', 'open-mcp', 'open-settings'],

    setup(props) {
        const buttons = [
            {
                action: 'stop',
                title: 'Detener',
                label: 'Stop',
                icon: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>',
            },
            {
                action: 'clear',
                title: 'Limpiar',
                label: 'Limpiar',
                icon: '<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>',
            },
            {
                action: 'disconnect',
                title: 'Reconectar',
                label: 'Reconectar',
                icon: '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>',
            },
            {
                action: 'open-settings',
                title: 'Configuración',
                label: 'Config',
                icon: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>',
            },
        ];

        function canClick(btn) {
            if (btn.action === 'open-settings') return props.toolsReady;
            return true;
        }

        function btnTitle(btn) {
            if (btn.action === 'open-settings' && !props.toolsReady) return 'Cargando herramientas...';
            return btn.title;
        }

        return {
            buttons,
            canClick,
            btnTitle,
        };
    },
};
