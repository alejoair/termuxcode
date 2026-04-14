// Componente: Todo Widget (flotante, siempre visible)
export default {
    template: `
        <div class="fixed right-4 top-20 w-72 z-40 flex flex-col bg-zinc-900/95 backdrop-blur border border-zinc-700 rounded-lg shadow-xl max-h-[70vh]">
            <!-- Header -->
            <div class="flex items-center justify-between px-3 py-2 border-b border-zinc-800 flex-shrink-0">
                <div class="flex items-center gap-2">
                    <svg class="w-3.5 h-3.5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                    </svg>
                    <span class="text-xs font-medium text-zinc-300">Tareas del agente</span>
                </div>
                <div class="flex items-center gap-1.5">
                    <span class="text-xs text-zinc-500">
                        <span class="text-green-400 font-medium">{{ completedCount }}</span>/{{ todos.length }}
                    </span>
                    <button @click="$emit('clear')" title="Limpiar"
                        class="text-zinc-600 hover:text-zinc-400 transition-colors p-0.5 rounded">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Progress bar -->
            <div class="h-0.5 bg-zinc-800 flex-shrink-0">
                <div class="h-full bg-green-600 transition-all duration-500"
                    :style="{ width: todos.length ? (completedCount / todos.length * 100) + '%' : '0%' }">
                </div>
            </div>

            <!-- Lista -->
            <ul class="overflow-y-auto flex-1 py-1">
                <li v-for="todo in todos" :key="todo.id"
                    class="flex items-start gap-2 px-3 py-1.5 hover:bg-zinc-800/40 transition-colors">
                    <!-- Icono de estado -->
                    <div class="flex-shrink-0 mt-0.5">
                        <div v-if="todo.status === 'completed'"
                            class="w-3.5 h-3.5 rounded-full bg-green-600 flex items-center justify-center">
                            <svg class="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                            </svg>
                        </div>
                        <div v-else-if="todo.status === 'in_progress'"
                            class="w-3.5 h-3.5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin">
                        </div>
                        <div v-else
                            class="w-3.5 h-3.5 rounded-full border-2 border-zinc-600">
                        </div>
                    </div>
                    <!-- Texto -->
                    <span class="text-xs leading-relaxed"
                        :class="todo.status === 'completed' ? 'text-zinc-600 line-through' : 'text-zinc-300'">
                        {{ todo.content }}
                    </span>
                </li>
            </ul>
        </div>
    `,

    props: {
        todos: { type: Array, default: () => [] },
        completedCount: { type: Number, default: 0 },
    },

    emits: ['clear'],
};
