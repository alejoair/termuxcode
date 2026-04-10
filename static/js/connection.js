// ===== Conexion WebSocket =====

import { state, dom, WS_URL } from './state.js';
import { addSystemMessage, updateTabStatus, updateGlobalStatus, handleMessage, hideLoading } from './ui.js';
import { vibrateConnect, vibrateDisconnect, vibrateError } from './haptics.js';
import { notifyDisconnect, notifyConnectionError } from './notifications.js';

const MAX_RECONNECT_ATTEMPTS = 10;
const INITIAL_RECONNECT_DELAY = 3000;
const MAX_RECONNECT_DELAY = 30000;

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
            tab.reconnectAttempts = 0;
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
            tab.reconnectAttempts = (tab.reconnectAttempts || 0) + 1;
            updateTabStatus(currentTabId, 'disconnected');
            hideLoading(currentTabId);

            if (state.activeTabId === currentTabId) {
                dom.statusDot.classList.remove('connected');

                if (tab.reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
                    dom.statusText.textContent = 'Sin conexion';
                    addSystemMessage(`No se pudo reconectar tras ${MAX_RECONNECT_ATTEMPTS} intentos`, currentTabId);
                    vibrateError();
                    updateGlobalStatus();
                    return;
                }

                dom.statusText.textContent = `Reconectando (${tab.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`;
                // Solo mostrar mensaje de desconexión en el primer intento
                if (tab.reconnectAttempts === 1) {
                    addSystemMessage('Desconectado del servidor', currentTabId);
                    vibrateDisconnect();
                    notifyDisconnect();
                }
            }

            updateGlobalStatus();

            // Exponential backoff
            const delay = Math.min(
                INITIAL_RECONNECT_DELAY * Math.pow(2, tab.reconnectAttempts - 1),
                MAX_RECONNECT_DELAY
            );

            tab.reconnectTimeout = setTimeout(() => {
                const reconnectTabId = tab.id;
                if (state.activeTabId === reconnectTabId) {
                    dom.statusText.textContent = 'Reconectando...';
                }
                connectTab(reconnectTabId);
            }, delay);
        };

        ws.onerror = () => {
            if (tab.ws !== ws) return; // Stale WebSocket
            const currentTabId = tab.id;
            // Solo mostrar mensaje de error en el primer intento, no en cada reintento
            if (state.activeTabId === currentTabId && tab.reconnectAttempts <= 1) {
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
    tab.reconnectAttempts = 0;
    updateTabStatus(tabId, 'disconnected');
}
