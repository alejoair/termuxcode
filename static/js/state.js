// ===== Estado global y configuracion =====

export const WS_URL = 'ws://localhost:8769';
export const STORAGE_KEY = 'ccm_tabs';

export const DEFAULT_SETTINGS = {
    permission_mode: 'acceptEdits',
    model: 'glm-5',
    system_prompt: '',
    append_system_prompt: '',
    max_turns: '',
    allowed_tools: '',
    disallowed_tools: '',
};

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
