import { computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Componente: Tasks Sidebar (panel derecho siempre visible, slim/expanded modes)
export default {
    template: `
        <div
            :class="[
                'flex flex-col h-full bg-base select-text overflow-hidden',
                isMobile
                    ? ''
                    : 'border-l border-border flex-shrink-0 transition-[width] duration-200 ' + (expanded ? 'w-80' : 'w-12')
            ]"
        >
            <!-- ===== Slim mode (solo desktop) ===== -->
            <template v-if="!isMobile && !expanded">
                <div
                    @click="$emit('toggle-expanded')"
                    class="flex flex-col items-center py-2 h-full cursor-pointer"
                >
                    <!-- Progress bar vertical -->
                    <div class="w-1 h-4 bg-border rounded-full overflow-hidden mb-3" :title="progressPercent + '%'">
                        <div class="w-full bg-ok transition-all duration-500 rounded-full" :style="{ height: progressPercent + '%' }"></div>
                    </div>
                    <!-- Task icons stacked vertically -->
                    <div class="flex flex-col gap-1.5 overflow-y-auto flex-1 py-1">
                        <div
                            v-for="task in tasks"
                            :key="task.id"
                            class="flex items-center justify-center"
                            :title="task.content || task.subject"
                        >
                            <!-- completed -->
                            <div v-if="task.status === 'completed'"
                                class="w-2.5 h-2.5 rounded-full bg-ok flex items-center justify-center">
                            </div>
                            <!-- in_progress -->
                            <div v-else-if="task.status === 'in_progress'"
                                class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse">
                            </div>
                            <!-- pending -->
                            <div v-else
                                class="w-2.5 h-2.5 rounded-full bg-border">
                            </div>
                        </div>
                    </div>
                    <!-- Count badge -->
                    <div class="mt-2 text-[10px] font-mono text-muted" :title="totalCount + ' tasks'">
                        {{ totalCount }}
                    </div>
                </div>
            </template>

            <!-- ===== Expanded mode (siempre en mobile) ===== -->
            <template v-if="isMobile || expanded">
                <!-- Header -->
                <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-txt">Tasks</span>
                        <span class="text-xs text-muted font-mono">{{ completedCount }}/{{ totalCount }}</span>
                    </div>
                    <button v-if="!isMobile" @click="$emit('toggle-expanded')" title="Colapsar"
                        class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>

                <!-- Progress bar -->
                <div class="h-0.5 bg-border flex-shrink-0">
                    <div class="h-full bg-ok transition-all duration-500"
                        :style="{ width: progressPercent + '%' }"></div>
                </div>

                <!-- Status summary -->
                <div class="flex items-center gap-3 px-3 py-1.5 border-b border-border/50 flex-shrink-0 text-[10px] text-muted">
                    <span v-if="inProgressCount > 0" class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                        {{ inProgressCount }} activas
                    </span>
                    <span v-if="pendingCount > 0" class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-border"></span>
                        {{ pendingCount }} pendientes
                    </span>
                    <span v-if="completedCount > 0" class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-ok"></span>
                        {{ completedCount }} hechas
                    </span>
                </div>

                <!-- Task list -->
                <div class="flex-1 overflow-y-auto min-h-0">
                    <div v-if="tasks.length === 0" class="px-3 py-6 text-center text-muted text-xs">
                        No hay tasks
                    </div>
                    <div
                        v-for="task in tasks"
                        :key="task.id"
                        :class="[
                            'flex items-start gap-2 px-3 py-2 border-b border-border/30 transition-colors',
                            task.status === 'in_progress' ? 'bg-blue-500/5' : 'hover:bg-surface/50'
                        ]"
                    >
                        <!-- Status icon -->
                        <div class="flex-shrink-0 mt-0.5">
                            <div v-if="task.status === 'completed'"
                                class="w-4 h-4 rounded-full bg-ok/20 flex items-center justify-center">
                                <svg class="w-2.5 h-2.5 text-ok" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                                </svg>
                            </div>
                            <div v-else-if="task.status === 'in_progress'"
                                class="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin">
                            </div>
                            <div v-else
                                class="w-4 h-4 rounded-full border-2 border-border">
                            </div>
                        </div>
                        <!-- Content -->
                        <div class="flex-1 min-w-0">
                            <div class="text-xs leading-relaxed"
                                :class="task.status === 'completed' ? 'text-muted line-through' : 'text-txt'">
                                {{ task.content || task.subject }}
                            </div>
                            <div v-if="task.description && task.status !== 'completed'"
                                class="text-[10px] text-muted mt-0.5 leading-relaxed line-clamp-2">
                                {{ task.description }}
                            </div>
                            <div v-if="task.activeForm && task.status === 'in_progress'"
                                class="flex items-center gap-1 mt-1 text-[10px] text-blue-400">
                                <svg class="w-2.5 h-2.5 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                                {{ task.activeForm }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Stats section -->
                <div v-if="stats" class="border-t border-border flex-shrink-0">
                    <div class="px-3 py-1.5 space-y-0.5 text-[10px]">
                        <!-- Totals -->
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
                            <span class="text-ok font-mono">{{ formatNumber(stats.totalCacheReadTokens) }}</span>
                        </div>
                        <div v-if="stats.totalCacheCreationTokens > 0" class="flex items-center justify-between">
                            <span class="text-muted">Cache creation:</span>
                            <span class="text-txt font-mono">{{ formatNumber(stats.totalCacheCreationTokens) }}</span>
                        </div>
                        <div class="flex items-center justify-between font-semibold">
                            <span class="text-muted">Cost:</span>
                            <span class="text-txt font-mono">\${{ stats.totalCostUsd.toFixed(4) }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-muted">Duration:</span>
                            <span class="text-txt font-mono">{{ formatDuration(stats.totalDurationMs) }}</span>
                        </div>
                        <div v-if="stats.totalApiDurationMs > 0" class="flex items-center justify-between">
                            <span class="text-muted">API time:</span>
                            <span class="text-txt font-mono">{{ formatDuration(stats.totalApiDurationMs) }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-muted">Queries:</span>
                            <span class="text-txt font-mono">{{ stats.queryCount }}</span>
                        </div>
                    </div>

                    <!-- Per query breakdown -->
                    <div v-if="stats.perQuery && stats.perQuery.length > 0" class="border-t border-border/50 px-3 py-1.5">
                        <div class="flex items-center justify-between text-[10px] mb-1">
                            <span class="text-muted font-semibold">Per query</span>
                            <button
                                @click="showPerQuery = !showPerQuery"
                                class="text-muted hover:text-txt transition-colors"
                            >
                                {{ showPerQuery ? '−' : '+' }}
                            </button>
                        </div>
                        <div v-if="showPerQuery" class="space-y-0.5 max-h-32 overflow-y-auto text-[10px]">
                            <div
                                v-for="q in reversedPerQuery"
                                :key="q.queryNumber"
                                class="flex items-center justify-between bg-zinc-800/50 rounded px-1.5 py-0.5"
                            >
                                <span class="text-muted">Q{{ q.queryNumber }}</span>
                                <span class="text-txt font-mono">{{ formatNumber(q.inputTokens) }} / {{ formatNumber(q.outputTokens) }}</span>
                                <span class="text-muted font-mono">\${{ q.costUsd.toFixed(4) }}</span>
                                <span class="text-muted">{{ formatDuration(q.durationMs) }}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Mobile: close button at bottom -->
                <div v-if="isMobile" class="flex-shrink-0 border-t border-border p-2">
                    <button @click="$emit('toggle-expanded')"
                        class="w-full py-2 rounded bg-surface text-txt text-xs hover:bg-raised transition-colors">
                        Cerrar
                    </button>
                </div>
            </template>
        </div>
    `,

    props: {
        tasks: { type: Array, default: () => [] },
        expanded: { type: Boolean, default: false },
        totalCount: { type: Number, default: 0 },
        progressPercent: { type: Number, default: 0 },
        pendingCount: { type: Number, default: 0 },
        inProgressCount: { type: Number, default: 0 },
        completedCount: { type: Number, default: 0 },
        stats: { type: Object, default: null },
        isMobile: { type: Boolean, default: false },
    },

    emits: ['toggle-expanded'],

    setup(props) {
        const reversedPerQuery = computed(() => {
            if (!props.stats?.perQuery) return [];
            return [...props.stats.perQuery].reverse();
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
            reversedPerQuery,
            showPerQuery: false,
            formatNumber,
            formatDuration,
        };
    },
};
