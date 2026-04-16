// ===== Composable: Todo Sidebar (singleton) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Refs singleton — compartidas entre todas las instancias
const todos = ref([]);
const isOpen = ref(false);

export function useTodoSidebar() {
    const pendingCount = computed(() => todos.value.filter(t => t.status === 'pending' || t.status === 'in_progress').length);
    const completedCount = computed(() => todos.value.filter(t => t.status === 'completed').length);

    function toggleSidebar() {
        isOpen.value = !isOpen.value;
    }

    function setOpen(val) {
        isOpen.value = val;
    }

    function setTodos(newTodos) {
        todos.value = newTodos || [];
    }

    function clearTodos() {
        todos.value = [];
    }

    return {
        todos,
        isOpen,
        pendingCount,
        completedCount,
        toggleSidebar,
        setOpen,
        setTodos,
        clearTodos,
    };
}
