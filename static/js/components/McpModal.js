import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Componente: Modal MCP Servers
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <!-- Header -->
                <div class="p-4 border-b border-border flex justify-between items-center">
                    <h3 class="text-lg font-semibold">MCP Servers</h3>
                    <button
                        @click="handleClose"
                        class="text-muted hover:text-txt transition-colors"
                    >
                        ×
                    </button>
                </div>

                <!-- Content -->
                <div class="p-4">
                    <div v-if="servers.length === 0" class="text-center text-muted py-8">
                        No hay servidores MCP configurados
                    </div>

                    <div v-else class="space-y-3">
                        <div
                            v-for="server in servers"
                            :key="server.name"
                            class="p-3 bg-surface rounded border border-border"
                        >
                            <div class="flex items-center justify-between mb-2">
                                <div class="flex items-center gap-2">
                                    <div
                                        :class="[
                                            'w-2 h-2 rounded-full',
                                            isServerDisabled(server.name) ? 'bg-muted' : getStatusColor(server.status)
                                        ]"
                                    ></div>
                                    <span class="font-medium">{{ server.name }}</span>
                                </div>

                                <button
                                    @click="toggleServer(server.name)"
                                    :class="[
                                        'px-2 py-1 text-xs rounded transition-colors',
                                        isServerDisabled(server.name)
                                            ? 'bg-surface hover:bg-raised'
                                            : 'bg-accent hover:bg-accent'
                                    ]"
                                >
                                    {{ isServerDisabled(server.name) ? 'Habilitar' : 'Deshabilitar' }}
                                </button>
                            </div>

                            <div v-if="server.error" class="text-xs text-err mb-2">
                                {{ server.error }}
                            </div>

                            <div v-if="server.tools && server.tools.length > 0" class="text-xs text-muted">
                                <div class="font-medium mb-1">Herramientas:</div>
                                <div class="flex flex-wrap gap-1">
                                    <span
                                        v-for="tool in server.tools.slice(0, 5)"
                                        :key="tool.name"
                                        class="px-1.5 py-0.5 bg-raised rounded"
                                    >
                                        {{ tool.name }}
                                    </span>
                                    <span v-if="server.tools.length > 5" class="px-1.5 py-0.5 bg-raised rounded">
                                        +{{ server.tools.length - 5 }} más
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-border flex gap-2">
                    <button
                        @click="handleClose"
                        class="flex-1 bg-surface hover:bg-raised text-txt py-2 rounded transition-colors"
                    >
                        Cerrar
                    </button>
                    <button
                        @click="handleApply"
                        :disabled="!hasChanges"
                        :class="[
                            'flex-1 py-2 rounded transition-colors',
                            hasChanges
                                ? 'bg-accent hover:bg-accent text-txt'
                                : 'bg-surface text-muted cursor-not-allowed'
                        ]"
                    >
                        Aplicar
                    </button>
                </div>
            </div>
        </div>
    `,

    props: ['tabId', 'servers', 'disabledMcpServers'],

    emits: ['close', 'apply'],

    setup(props, { emit }) {
        // Copia local de los servers deshabilitados
        const localDisabled = ref(new Set(props.disabledMcpServers || []));

        const hasChanges = computed(() => {
            const original = new Set(props.disabledMcpServers || []);
            if (localDisabled.value.size !== original.size) return true;
            for (const name of localDisabled.value) {
                if (!original.has(name)) return true;
            }
            return false;
        });

        const servers = computed(() => props.servers || []);

        function getStatusColor(status) {
            switch (status) {
                case 'connected':
                    return 'bg-ok';
                case 'error':
                    return 'bg-err';
                default:
                    return 'bg-warn';
            }
        }

        function isServerDisabled(serverName) {
            return localDisabled.value.has(serverName);
        }

        function toggleServer(serverName) {
            if (localDisabled.value.has(serverName)) {
                localDisabled.value.delete(serverName);
            } else {
                localDisabled.value.add(serverName);
            }
            // Forzar reactividad en Set
            localDisabled.value = new Set(localDisabled.value);
        }

        function handleClose() {
            emit('close');
        }

        function handleApply() {
            emit('apply', [...localDisabled.value]);
        }

        return {
            localDisabled,
            hasChanges,
            servers,
            getStatusColor,
            isServerDisabled,
            toggleServer,
            handleClose,
            handleApply,
        };
    },
};
