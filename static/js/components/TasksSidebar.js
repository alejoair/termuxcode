// Componente: Tasks Sidebar (panel derecho colapsable con slim/expanded modes)
export default {
    template: `
        <transition name="sidebar-right">
            <div
                v-if="isOpen"
                :class="[
                    'flex flex-col h-full bg-base border-l border-border flex-shrink-0 select-text overflow-hidden',
                    expanded ? 'w-80' : 'w-12'
                ]"
            >
                <!-- ===== Slim mode ===== -->
                <template v-if="!expanded">
                    <div class="flex flex-col items-center py-2 h-full">
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
                        <!-- Expand button -->
                        <button @click="$emit('toggle-expanded')" title="Expandir"
                            class="mt-1 w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                    </div>
                </template>

                <!-- ===== Expanded mode ===== -->
                <template v-else>
                    <!-- Header -->
                    <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-bold text-txt">Tasks</span>
                            <span class="text-xs text-muted font-mono">{{ completedCount }}/{{ totalCount }}</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <!-- Collapse button -->
                            <button @click="$emit('toggle-expanded')" title="Colapsar"
                                class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                                </svg>
                            </button>
                            <!-- Close -->
                            <button @click="$emit('toggle')" title="Cerrar"
                                class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded text-sm">
                                &times;
                            </button>
                        </div>
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
                </template>
            </div>
        </transition>
    `,

    props: {
        isOpen: { type: Boolean, default: false },
        tasks: { type: Array, default: () => [] },
        expanded: { type: Boolean, default: true },
        totalCount: { type: Number, default: 0 },
        progressPercent: { type: Number, default: 0 },
        pendingCount: { type: Number, default: 0 },
        inProgressCount: { type: Number, default: 0 },
        completedCount: { type: Number, default: 0 },
    },

    emits: ['toggle', 'toggle-expanded'],
};
