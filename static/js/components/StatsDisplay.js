// ===== Componente: Visualización de Estadísticas =====

import { computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export default {
    template: `
        <div class="stats-display bg-surface border border-border rounded-lg p-3 space-y-2">
            <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-txt">Session Stats</span>
                <button
                    @click="$emit('toggle-expanded')"
                    class="text-xs text-muted hover:text-txt transition-colors"
                >
                    {{ expanded ? '−' : '+' }}
                </button>
            </div>

            <div v-if="expanded && stats" class="space-y-1.5 text-xs">
                <!-- Tokens -->
                <div class="flex items-center justify-between">
                    <span class="text-muted">Input tokens:</span>
                    <span class="text-txt font-mono">{{ formatNumber(stats.totalInputTokens) }}</span>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-muted">Output tokens:</span>
                    <span class="text-txt font-mono">{{ formatNumber(stats.totalOutputTokens) }}</span>
                </div>
                <div v-if="stats.totalCacheReadTokens > 0" class="flex items-center justify-between">
                    <span class="text-muted">Cache read:</span>
                    <span class="text-ok font-mono">{{ formatNumber(stats.totalCacheReadTokens) }} <span class="text-xs">(-90%)</span></span>
                </div>
                <div v-if="stats.totalCacheCreationTokens > 0" class="flex items-center justify-between">
                    <span class="text-muted">Cache creation:</span>
                    <span class="text-txt font-mono">{{ formatNumber(stats.totalCacheCreationTokens) }}</span>
                </div>

                <!-- Costo -->
                <div class="flex items-center justify-between border-t border-border pt-1.5 mt-1.5">
                    <span class="text-muted font-semibold">Total cost:</span>
                    <span class="text-txt font-mono font-semibold">\${{ stats.totalCostUsd.toFixed(4) }}</span>
                </div>

                <!-- Tiempo -->
                <div class="flex items-center justify-between">
                    <span class="text-muted">Duration:</span>
                    <span class="text-txt font-mono">{{ formatDuration(stats.totalDurationMs) }}</span>
                </div>
                <div v-if="stats.totalApiDurationMs > 0" class="flex items-center justify-between">
                    <span class="text-muted">API time:</span>
                    <span class="text-txt font-mono">{{ formatDuration(stats.totalApiDurationMs) }}</span>
                </div>

                <!-- Queries -->
                <div class="flex items-center justify-between">
                    <span class="text-muted">Queries:</span>
                    <span class="text-txt font-mono">{{ stats.queryCount }}</span>
                </div>
            </div>

            <!-- Compact view -->
            <div v-else-if="!expanded && stats" class="flex items-center justify-between text-xs">
                <span class="text-muted font-mono">\${{ stats.totalCostUsd.toFixed(4) }}</span>
                <span class="text-muted font-mono">{{ formatNumber(totalTokens) }} tokens</span>
            </div>
        </div>
    `,

    props: {
        stats: {
            type: Object,
            default: null,
        },
        expanded: {
            type: Boolean,
            default: false,
        },
    },

    emits: ['toggle-expanded'],

    setup(props) {
        const totalTokens = computed(() => {
            if (!props.stats) return 0;
            return props.stats.totalInputTokens + props.stats.totalOutputTokens;
        });

        function formatNumber(num) {
            return num.toLocaleString();
        }

        function formatDuration(ms) {
            if (!ms) return '0ms';
            if (ms < 1000) return `${ms}ms`;
            return `${(ms / 1000).toFixed(1)}s`;
        }

        return {
            totalTokens,
            formatNumber,
            formatDuration,
        };
    },
};
