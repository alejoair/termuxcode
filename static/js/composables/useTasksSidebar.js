// ===== Composable: Tasks Sidebar (singleton) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Refs singleton — compartidas entre todas las instancias
const tasks = ref([]);
const isOpen = ref(false);
const expanded = ref(true);

export function useTasksSidebar() {
    const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length);
    const inProgressCount = computed(() => tasks.value.filter(t => t.status === 'in_progress').length);
    const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length);
    const totalCount = computed(() => tasks.value.length);
    const progressPercent = computed(() => {
        if (tasks.value.length === 0) return 0;
        return Math.round((completedCount.value / tasks.value.length) * 100);
    });

    function setTasks(newTasks) {
        tasks.value = newTasks || [];
    }

    function toggleSidebar() {
        isOpen.value = !isOpen.value;
    }

    function toggleExpanded() {
        expanded.value = !expanded.value;
    }

    function clearTasks() {
        tasks.value = [];
    }

    return {
        tasks,
        isOpen,
        expanded,
        pendingCount,
        inProgressCount,
        completedCount,
        totalCount,
        progressPercent,
        setTasks,
        toggleSidebar,
        toggleExpanded,
        clearTasks,
    };
}
