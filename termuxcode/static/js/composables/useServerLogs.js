// ===== Composable: Logs del Servidor (estado global, no per-tab) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const MAX_LOGS = 500;

// Estado global singleton (se comparte entre todas las instancias)
const logs = ref([]);
const isOpen = ref(false);
const levelFilter = ref('ALL');

export function useServerLogs() {
    const filteredLogs = computed(() => {
        if (levelFilter.value === 'ALL') return logs.value;
        return logs.value.filter(l => l.level === levelFilter.value);
    });

    const errorCount = computed(() => logs.value.filter(l => l.level === 'ERROR').length);
    const warnCount = computed(() => logs.value.filter(l => l.level === 'WARNING').length);

    function addLog(entry) {
        logs.value.push(entry);
        if (logs.value.length > MAX_LOGS) {
            logs.value = logs.value.slice(-MAX_LOGS);
        }
    }

    function addLogBatch(entries) {
        if (!entries || entries.length === 0) return;
        logs.value.push(...entries);
        if (logs.value.length > MAX_LOGS) {
            logs.value = logs.value.slice(-MAX_LOGS);
        }
    }

    function clearLogs() {
        logs.value = [];
    }

    function toggleSidebar() {
        isOpen.value = !isOpen.value;
    }

    function setOpen(val) {
        isOpen.value = val;
    }

    function setLevelFilter(level) {
        levelFilter.value = level;
    }

    return {
        logs,
        isOpen,
        levelFilter,
        filteredLogs,
        errorCount,
        warnCount,
        addLog,
        addLogBatch,
        clearLogs,
        toggleSidebar,
        setOpen,
        setLevelFilter,
    };
}
