// ===== Persistencia en localStorage =====

import { state, STORAGE_KEY, DEFAULT_SETTINGS } from './state.js';

export function saveTabs() {
    const data = Array.from(state.tabs.entries()).map(([id, tab]) => ({
        id,
        name: tab.name,
        cwd: tab.cwd,
        sessionId: tab.sessionId,
        renderedMessages: tab.renderedMessages,
        settings: tab.settings,
        plan: tab.plan || null,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function loadTabsData() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return [];
        return JSON.parse(saved);
    } catch (e) {
        console.error('Error loading tabs:', e);
        return [];
    }
}
