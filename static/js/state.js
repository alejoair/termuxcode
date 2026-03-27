// ===== Estado global y configuracion =====

export const WS_URL = 'ws://localhost:8769';
export const STORAGE_KEY = 'ccm_tabs';

export const state = {
    tabs: new Map(),
    activeTabId: null,
    tabCounter: 0,
};

// Referencias DOM
export const dom = {
    messages: document.getElementById('messages'),
    input: document.getElementById('prompt'),
    statusDot: document.getElementById('globalStatusDot'),
    statusText: document.getElementById('globalStatusText'),
};
