// ===== Conexion WebSocket =====

import { state, dom, WS_URL } from './state.js';
import { addSystemMessage, updateTabStatus, updateGlobalStatus, handleMessage } from './ui.js';

export function connectTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    if (tab.ws && (tab.ws.readyState === WebSocket.CONNECTING || tab.ws.readyState === WebSocket.OPEN)) {
        return;
    }

    updateTabStatus(tabId, 'connecting');

    try {
        const wsUrl = tab.sessionId ? `${WS_URL}?session_id=${tab.sessionId}` : WS_URL;
        tab.ws = new WebSocket(wsUrl);

        tab.ws.onopen = () => {
            tab.isConnected = true;
            updateTabStatus(tabId, 'connected');

            if (state.activeTabId === tabId) {
                dom.statusDot.classList.add('connected');
                dom.statusText.textContent = 'Conectado';
                addSystemMessage('Conectado al servidor', tabId);
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

            if (state.activeTabId === tabId) {
                dom.statusDot.classList.remove('connected');
                dom.statusText.textContent = 'Desconectado';
                addSystemMessage('Desconectado del servidor', tabId);
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
