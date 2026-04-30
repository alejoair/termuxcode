// ===== Composable: Persistencia en LocalStorage =====

import { watch } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const STORAGE_KEY = 'ccm_tabs';
const STORAGE_VERSION = '1'; // Para migraciones futuras

export function useStorage(tabs, activeTabId) {
    /**
     * Guarda el estado de los tabs en localStorage
     */
    function saveTabs(serializedTabs) {
        try {
            const data = {
                version: STORAGE_VERSION,
                tabs: serializedTabs,
                activeTabId: activeTabId.value,
                timestamp: Date.now(),
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error('[useStorage] Error saving tabs:', e);
        }
    }

    /**
     * Carga el estado de los tabs desde localStorage
     */
    function loadTabs() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return { tabs: [], activeTabId: null };

            const data = JSON.parse(saved);

            // Migración de versión si es necesario
            if (data.version !== STORAGE_VERSION) {
                console.warn('[useStorage] Version mismatch, migrating...');
                // Aquí iría la lógica de migración
            }

            return {
                tabs: data.tabs || [],
                activeTabId: data.activeTabId || null,
            };
        } catch (e) {
            console.error('[useStorage] Error loading tabs:', e);
            return { tabs: [], activeTabId: null };
        }
    }

    /**
     * Limpia todos los tabs del localStorage
     */
    function clearStorage() {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            console.error('[useStorage] Error clearing storage:', e);
        }
    }

    /**
     * Configura auto-guardado cuando cambian los tabs
     */
    function setupAutoSave(serializeFn) {
        const stopWatch = watch(
            tabs,
            () => {
                const serialized = serializeFn();
                saveTabs(serialized);
            },
            { deep: true }
        );

        return stopWatch;
    }

    /**
     * Guarda configuración adicional (no tabs)
     */
    function saveSetting(key, value) {
        try {
            const settingsKey = `ccm_settings_${key}`;
            localStorage.setItem(settingsKey, JSON.stringify(value));
        } catch (e) {
            console.error('[useStorage] Error saving setting:', e);
        }
    }

    /**
     * Carga configuración adicional
     */
    function loadSetting(key, defaultValue = null) {
        try {
            const settingsKey = `ccm_settings_${key}`;
            const saved = localStorage.getItem(settingsKey);
            return saved ? JSON.parse(saved) : defaultValue;
        } catch (e) {
            console.error('[useStorage] Error loading setting:', e);
            return defaultValue;
        }
    }

    return {
        saveTabs,
        loadTabs,
        clearStorage,
        setupAutoSave,
        saveSetting,
        loadSetting,
    };
}
