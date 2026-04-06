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
        const ws = new WebSocket(wsUrl);
        tab.ws = ws;

        // Capturar referencia para ignorar eventos de WebSockets stale
        // (si disconnectTab() cierra este ws y crea uno nuevo, los handlers
        // del ws viejo deben ser no-ops)
        ws.onopen = () => {
            if (tab.ws !== ws) return; // Stale WebSocket
            const currentTabId = tab.id;
            tab.isConnected = true;
            updateTabStatus(currentTabId, 'connected');

            if (state.activeTabId === currentTabId) {
                dom.statusDot.classList.add('connected');
                dom.statusText.textContent = 'Conectado';
                addSystemMessage('Conectado al servidor', currentTabId);
                vibrateConnect();
            }

            updateGlobalStatus();
        };

        ws.onmessage = (event) => {
            if (tab.ws !== ws) return; // Stale WebSocket
            try {
                const data = JSON.parse(event.data);
                const currentTabId = tab.id;
                if (state.activeTabId === currentTabId) {
                    handleMessage(data, currentTabId);
                } else {
                    tab.messages.push(data);
                }
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };

        ws.onclose = () => {
            if (tab.ws !== ws) return; // Stale WebSocket
            const currentTabId = tab.id;
            tab.isConnected = false;
            updateTabStatus(currentTabId, 'disconnected');
            hideLoading(currentTabId);

            if (state.activeTabId === currentTabId) {
                dom.statusDot.classList.remove('connected');
                dom.statusText.textContent = 'Desconectado';
                addSystemMessage('Desconectado del servidor', currentTabId);
                vibrateDisconnect();
                notifyDisconnect();
            }

            updateGlobalStatus();

            // Auto reconnect
            tab.reconnectTimeout = setTimeout(() => {
                const reconnectTabId = tab.id;
                if (state.activeTabId === reconnectTabId) {
                    dom.statusText.textContent = 'Reconectando...';
                }
                connectTab(reconnectTabId);
            }, 3000);
        };

        ws.onerror = () => {
            if (tab.ws !== ws) return; // Stale WebSocket
            const currentTabId = tab.id;
            if (state.activeTabId === currentTabId) {
                addSystemMessage('Error de conexion', currentTabId);
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
