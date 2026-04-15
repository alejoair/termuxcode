// Componente: Log Sidebar (panel colapsable de logs del servidor)
import { ref, watch, nextTick, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export default {
    template: `
        <transition v-if="!isMobile" name="sidebar">
            <div
                v-if="isOpen"
                class="flex flex-col h-full bg-base border-r border-border w-96 flex-shrink-0 select-text"
            >
                <!-- Header -->
                <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-txt">Server Logs</span>
                        <span v-if="errorCount > 0" class="px-1.5 py-0.5 text-xs rounded bg-err/20 text-err font-mono">{{ errorCount }}</span>
                        <span v-if="warnCount > 0" class="px-1.5 py-0.5 text-xs rounded bg-warn/20 text-warn font-mono">{{ warnCount }}</span>
                    </div>
                    <div class="flex items-center gap-1">
                        <!-- Filtro -->
                        <select
                            :value="currentFilter"
                            @change="$emit('set-filter', $event.target.value)"
                            class="bg-surface text-txt text-xs border border-border rounded px-1 py-0.5 outline-none focus:border-border-focus"
                        >
                            <option value="ALL">All</option>
                            <option value="DEBUG">Debug</option>
                            <option value="INFO">Info</option>
                            <option value="WARNING">Warning</option>
                            <option value="ERROR">Error</option>
                        </select>
                        <!-- Clear -->
                        <button
                            @click="$emit('clear')"
                            title="Limpiar logs"
                            class="w-6 h-6 flex items-center justify-center text-muted hover:text-err transition-colors rounded text-sm"
                        >&#x2715;</button>
                        <!-- Close -->
                        <button
                            @click="$emit('toggle')"
                            title="Cerrar sidebar"
                            class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded text-sm"
                        >&times;</button>
                    </div>
                </div>

                <!-- Log entries -->
                <div ref="logContainer" class="flex-1 overflow-y-auto font-mono text-xs leading-relaxed">
                    <div
                        v-for="(log, i) in logs"
                        :key="i"
                        :class="['px-3 py-0.5 border-b border-border/30', levelClass(log.level)]"
                    >
                        <span class="text-muted">[{{ log.timestamp }}]</span>
                        <span :class="['font-bold', levelClass(log.level)]">[{{ log.level }}]</span>
                        <span class="ml-1 break-all">{{ log.message }}</span>
                    </div>
                    <div v-if="logs.length === 0" class="px-3 py-4 text-center text-muted">
                        No hay logs
                    </div>
                </div>
            </div>
        </transition>

        <!-- Mobile: sin transition, sin width classes -->
        <div v-if="isMobile && isOpen" class="flex flex-col h-full bg-base select-text">
            <!-- Header -->
            <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-txt">Server Logs</span>
                    <span v-if="errorCount > 0" class="px-1.5 py-0.5 text-xs rounded bg-err/20 text-err font-mono">{{ errorCount }}</span>
                    <span v-if="warnCount > 0" class="px-1.5 py-0.5 text-xs rounded bg-warn/20 text-warn font-mono">{{ warnCount }}</span>
                </div>
                <div class="flex items-center gap-1">
                    <select
                        :value="currentFilter"
                        @change="$emit('set-filter', $event.target.value)"
                        class="bg-surface text-txt text-xs border border-border rounded px-1 py-0.5 outline-none focus:border-border-focus"
                    >
                        <option value="ALL">All</option>
                        <option value="DEBUG">Debug</option>
                        <option value="INFO">Info</option>
                        <option value="WARNING">Warning</option>
                        <option value="ERROR">Error</option>
                    </select>
                    <button
                        @click="$emit('clear')"
                        title="Limpiar logs"
                        class="w-6 h-6 flex items-center justify-center text-muted hover:text-err transition-colors rounded text-sm"
                    >&#x2715;</button>
                </div>
            </div>

            <!-- Log entries -->
            <div ref="logContainer" class="flex-1 overflow-y-auto font-mono text-xs leading-relaxed">
                <div
                    v-for="(log, i) in logs"
                    :key="i"
                    :class="['px-3 py-0.5 border-b border-border/30', levelClass(log.level)]"
                >
                    <span class="text-muted">[{{ log.timestamp }}]</span>
                    <span :class="['font-bold', levelClass(log.level)]">[{{ log.level }}]</span>
                    <span class="ml-1 break-all">{{ log.message }}</span>
                </div>
                <div v-if="logs.length === 0" class="px-3 py-4 text-center text-muted">
                    No hay logs
                </div>
            </div>

            <!-- Mobile: close button at bottom -->
            <div class="flex-shrink-0 border-t border-border p-2">
                <button @click="$emit('toggle')"
                    class="w-full py-2 rounded bg-surface text-txt text-xs hover:bg-raised transition-colors">
                    Cerrar
                </button>
            </div>
        </div>
    `,

    props: {
        isOpen: { type: Boolean, default: false },
        logs: { type: Array, default: () => [] },
        errorCount: { type: Number, default: 0 },
        warnCount: { type: Number, default: 0 },
        currentFilter: { type: String, default: 'ALL' },
        isMobile: { type: Boolean, default: false },
    },

    emits: ['toggle', 'clear', 'set-filter'],

    setup(props) {
        const logContainer = ref(null);

        function levelClass(level) {
            switch (level) {
                case 'ERROR': return 'text-err';
                case 'WARNING': return 'text-warn';
                case 'INFO': return 'text-ok';
                case 'DEBUG': return 'text-muted';
                default: return 'text-txt';
            }
        }

        // Auto-scroll al bottom cuando llegan nuevos logs
        watch(() => props.logs.length, async () => {
            await nextTick();
            if (logContainer.value) {
                logContainer.value.scrollTop = logContainer.value.scrollHeight;
            }
        });

        return { logContainer, levelClass };
    },
};
