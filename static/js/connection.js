// ===== Conexion WebSocket =====

import { state, dom, WS_URL } from './state.js';
import { addSystemMessage, updateTabStatus, updateGlobalStatus, handleMessage, hideLoading } from './ui.js';
import { vibrateConnect, vibrateDisconnect, vibrateError } from './haptics.js';
import { notifyDisconnect, notifyConnectionError } from './notifications.js';

export function connectTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    if (tab.ws && (tab.ws.readyState === WebSocket.CONNECTING || tab.ws.readyState === WebSocket.OPEN)) {
        return;
    }

    // Cancelar timer de reconexión anterior si existe
    if (tab.reconnectTimeout) {
        clearTimeout(tab.reconnectTimeout);
        tab.reconnectTimeout = null;
    }

    updateTabStatus(tabId, 'connecting');

    try {
        const params = new URLSearchParams();
        if (tab.sessionId) params.set('session_id', tab.sessionId);
        if (tab.cwd) params.set('cwd', tab.cwd);
        const s = tab.settings || {};
        const opts = {};
        if (s.permission_mode) opts.permission_mode = s.permission_mode;
        if (s.model) opts.model = s.model;
        if (s.system_prompt) opts.system_prompt = s.system_prompt;
        if (s.append_system_prompt) opts.append_system_prompt = s.append_system_prompt;
        if (s.max_turns) opts.max_turns = parseInt(s.max_turns);
        if (s.rolling_window) opts.rolling_window = parseInt(s.rolling_window);
        if (s.tools && s.tools.length > 0) opts.tools = s.tools;
        if (s.allowed_tools) opts.allowed_tools = s.allowed_tools.split(',').map(t => t.trim()).filter(Boolean);
        if (s.disallowed_tools) opts.disallowed_tools = s.disallowed_tools.split(',').map(t => t.trim()).filter(Boolean);
        if (Object.keys(opts).length) params.set('options', JSON.stringify(opts));
        const wsUrl = params.toString() ? `${WS_URL}?${params.toString()}` : WS_URL;
        tab.ws = new WebSocket(wsUrl);

        tab.ws.onopen = () => {
            tab.isConnected = true;
            updateTabStatus(tabId, 'connected');

            if (state.activeTabId === tabId) {
                dom.statusDot.classList.add('connected');
                dom.statusText.textContent = 'Conectado';
                addSystemMessage('Conectado al servidor', tabId);
                vibrateConnect();
            }

            updateGlobalStatus();
        };

        tab.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (state.activeTabId === tabId) {
                    handleMessage(data, tabId);
                } else {
                    tab.messages.push(data);
                }
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };

        tab.ws.onclose = () => {
            tab.isConnected = false;
            updateTabStatus(tabId, 'disconnected');
            hideLoading(tabId);

            if (state.activeTabId === tabId) {
                dom.statusDot.classList.remove('connected');
                dom.statusText.textContent = 'Desconectado';
                addSystemMessage('Desconectado del servidor', tabId);
                vibrateDisconnect();
                notifyDisconnect();
            }

            updateGlobalStatus();

            // Auto reconnect
            tab.reconnectTimeout = setTimeout(() => {
                if (state.activeTabId === tabId) {
                    dom.statusText.textContent = 'Reconectando...';
                }
                connectTab(tabId);
            }, 3000);
        };

        tab.ws.onerror = () => {
            if (state.activeTabId === tabId) {
                addSystemMessage('Error de conexion', tabId);
                vibrateError();
                notifyConnectionError();
            }
        };

    } catch (e) {
        console.error('Error connecting:', e);
        updateTabStatus(tabId, 'disconnected');
    }
}

export function disconnectTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    if (tab.reconnectTimeout) {
        clearTimeout(tab.reconnectTimeout);
        tab.reconnectTimeout = null;
    }
    if (tab.ws) {
        tab.ws.close();
        tab.ws = null;
    }
    tab.isConnected = false;
    updateTabStatus(tabId, 'disconnected');
}
