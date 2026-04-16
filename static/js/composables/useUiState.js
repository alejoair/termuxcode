// ===== Composable: useUiState — Persistencia centralizada del estado de UI =====
// NOTA: Los anchos de sidebars se persisten individualmente via useResizable (ccm_settings_*).
// Este composable persiste: isOpen/expanded, expandedPaths, openFiles, levelFilter, scrollRatio.

import { ref, watch } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const STORAGE_KEY = 'ccm_ui_state';

const DEFAULT_STATE = {
    version: '1',
    sidebars: {
        log: { isOpen: false },
        filetree: { expanded: false, expandedPaths: [] },
        editor: { expanded: false, openFiles: [], activeFilePath: null },
        tasks: { expanded: false },
        todo: { isOpen: false },
    },
    logs: { levelFilter: 'ALL' },
    messages: { scrollRatio: {} },
};

let _instance = null;

export function useUiState() {
    if (_instance) return _instance;

    const scrollRatioMap = ref({});

    function load() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return JSON.parse(JSON.stringify(DEFAULT_STATE));
            const parsed = JSON.parse(raw);
            return {
                version: parsed.version || DEFAULT_STATE.version,
                sidebars: { ...DEFAULT_STATE.sidebars, ...(parsed.sidebars || {}) },
                logs: { ...DEFAULT_STATE.logs, ...(parsed.logs || {}) },
                messages: { ...DEFAULT_STATE.messages, ...(parsed.messages || {}) },
            };
        } catch {
            return JSON.parse(JSON.stringify(DEFAULT_STATE));
        }
    }

    function save(stateObj) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stateObj));
        } catch {}
    }

    /**
     * Restaura el estado de UI en todos los composables de sidebars.
     * Debe llamarse antes de restaurar tabs.
     * @param {object} deps - { serverLogs, todoSidebar, tasksSidebar, filetree, editorSidebar }
     */
    async function restore(deps) {
        const state = load();

        // Restaurar scroll ratios
        if (state.messages?.scrollRatio) {
            scrollRatioMap.value = state.messages.scrollRatio;
        }

        // Restaurar log sidebar
        const logState = state.sidebars?.log;
        if (logState) {
            deps.serverLogs.setOpen(logState.isOpen ?? false);
        }

        // Restaurar filtro de logs
        if (state.logs?.levelFilter) {
            deps.serverLogs.setLevelFilter(state.logs.levelFilter);
        }

        // Restaurar filetree sidebar
        const ftState = state.sidebars?.filetree;
        if (ftState) {
            deps.filetree.setExpanded(ftState.expanded ?? false);
            if (ftState.expandedPaths) deps.filetree.setExpandedPaths(ftState.expandedPaths);
        }

        // Restaurar editor sidebar
        const edState = state.sidebars?.editor;
        if (edState) {
            await deps.editorSidebar.initializeFromState({
                expanded: edState.expanded ?? false,
                openFiles: edState.openFiles || [],
                activeFilePath: edState.activeFilePath || null,
            });
        } else {
            await deps.editorSidebar.initializeFromState(null);
        }

        // Restaurar tasks sidebar
        const tasksState = state.sidebars?.tasks;
        if (tasksState) {
            deps.tasksSidebar.setExpanded(tasksState.expanded ?? false);
        }

        // Restaurar todo sidebar
        const todoState = state.sidebars?.todo;
        if (todoState) {
            deps.todoSidebar.setOpen(todoState.isOpen ?? false);
        }
    }

    function saveCurrentState(deps) {
        const editorOpenFiles = deps.editorSidebar.openFiles.value;
        const state = {
            version: '1',
            sidebars: {
                log: { isOpen: deps.serverLogs.isOpen.value },
                filetree: {
                    expanded: deps.filetree.expanded.value,
                    expandedPaths: [...deps.filetree.expandedPaths.value],
                },
                editor: {
                    expanded: deps.editorSidebar.expanded.value,
                    openFiles: editorOpenFiles.map(f => ({
                        path: f.path,
                        name: f.name,
                        language: f.language,
                        dirty: f.dirty,
                    })),
                    activeFilePath: deps.editorSidebar.activeFilePath.value,
                },
                tasks: { expanded: deps.tasksSidebar.expanded.value },
                todo: { isOpen: deps.todoSidebar.isOpen.value },
            },
            logs: { levelFilter: deps.serverLogs.levelFilter.value },
            messages: { scrollRatio: scrollRatioMap.value },
        };
        save(state);
    }

    function saveNow(deps) {
        saveCurrentState(deps);
    }

    function setupAutoSave(deps, debounceMs = 300) {
        let timeout = null;

        function scheduleSave() {
            if (timeout) clearTimeout(timeout);
            timeout = setTimeout(() => saveCurrentState(deps), debounceMs);
        }

        watch([
            deps.serverLogs.isOpen,
            deps.serverLogs.levelFilter,
            deps.todoSidebar.isOpen,
            deps.tasksSidebar.expanded,
            deps.filetree.expanded,
            deps.editorSidebar.expanded,
            deps.editorSidebar.activeFilePath,
            scrollRatioMap,
        ], scheduleSave, { deep: true });

        watch(() => [...deps.filetree.expandedPaths.value], scheduleSave);
        watch(() => deps.editorSidebar.openFiles.value.map(f => f.path), scheduleSave);
    }

    function setScrollRatio(tabId, ratio) {
        scrollRatioMap.value = { ...scrollRatioMap.value, [tabId]: ratio };
    }

    function getScrollRatio(tabId) {
        return scrollRatioMap.value[tabId] ?? null;
    }

    _instance = {
        load,
        save,
        restore,
        saveNow,
        setupAutoSave,
        saveCurrentState,
        setScrollRatio,
        getScrollRatio,
        scrollRatioMap,
    };

    return _instance;
}
