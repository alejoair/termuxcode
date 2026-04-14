// ===== Composable: Gestión de Conexión WebSocket =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const WS_URL = 'ws://localhost:2025';
const MAX_RECONNECT_ATTEMPTS = 10;
const INITIAL_RECONNECT_DELAY = 3000;
const MAX_RECONNECT_DELAY = 30000;

export function useWebSocket() {
    /**
     * Conecta un tab al WebSocket
     * @param {Object} tab - El objeto tab reactivo
     * @param {Function} onMessage - Callback para mensajes recibidos (data, tabId) => void
     */
    function connectTab(tab, onMessage) {
        if (!tab) return;

        console.log('[WebSocket] connectTab called for:', tab.id, 'readyState:', tab.ws?.readyState);

        // Ya está conectando o conectado
        if (tab.ws && (tab.ws.readyState === WebSocket.CONNECTING || tab.ws.readyState === WebSocket.OPEN)) {
            console.log('[WebSocket] Already connecting/connected, skipping');
            return;
        }

        // Cancelar timer de reconexión anterior
        if (tab.reconnectTimeout) {
            clearTimeout(tab.reconnectTimeout);
            tab.reconnectTimeout = null;
        }

        const tabId = tab.id;
        tab.isConnected = false;
        console.log('[WebSocket] Set isConnected=false, creating WebSocket...');

        try {
            // Construir URL con parámetros
            const params = new URLSearchParams();

            if (tab.sessionId) {
                params.set('session_id', tab.sessionId);
            }

            if (tab.cwd) {
                params.set('cwd', tab.cwd);
            }

            // Opciones desde tab.settings
            const settings = tab.settings || {};
            const opts = {};

            if (settings.permission_mode) opts.permission_mode = settings.permission_mode;
            if (settings.model) opts.model = settings.model;
            if (settings.system_prompt) opts.system_prompt = settings.system_prompt;
            if (settings.rolling_window) opts.rolling_window = parseInt(settings.rolling_window);
            if (settings.tools && settings.tools.length > 0) opts.tools = settings.tools;
            if (Array.isArray(settings.disabledMcpServers)) opts.disabledMcpServers = settings.disabledMcpServers;

            if (Object.keys(opts).length > 0) {
                params.set('options', JSON.stringify(opts));
            }

            const wsUrl = params.toString() ? `${WS_URL}?${params.toString()}` : WS_URL;
            const ws = new WebSocket(wsUrl);

            // Guardar referencia en el tab
            tab.ws = ws;

            // ===== Event Handlers =====

            ws.onopen = () => {
                // Verificar que este ws no es stale
                if (tab.ws !== ws) return;

                console.log(`[WebSocket] Tab ${tabId} connected`);
                tab._reconnecting = false;
                tab.isConnected = true;
                tab.reconnectAttempts = 0;

                // Notificar cambio de estado
                window.dispatchEvent(new CustomEvent('tab-connected', { detail: { tabId } }));
            };

            ws.onmessage = (event) => {
                // Verificar que este ws no es stale
                if (tab.ws !== ws) return;

                try {
                    const data = JSON.parse(event.data);

                    // Manejar session_id update (re-key)
                    if (data.type === 'session_id') {
                        handleSessionIdUpdate(tab, data.session_id);
                        return;
                    }

                    // Intercept server logs — dispatch via CustomEvent (no per-tab)
                    if (data.type === 'server_log') {
                        window.dispatchEvent(new CustomEvent('server-log', { detail: data }));
                        return;
                    }
                    if (data.type === 'server_log_history') {
                        window.dispatchEvent(new CustomEvent('server-log-history', { detail: data }));
                        return;
                    }

                    // Intercept filetree snapshot — dispatch via CustomEvent (no per-tab)
                    if (data.type === 'filetree_snapshot') {
                        window.dispatchEvent(new CustomEvent('filetree-snapshot', { detail: data }));
                        return;
                    }

                    // Callback al componente padre — usar tab.id (se actualiza tras re-key)
                    if (onMessage) {
                        onMessage(data, tab.id);
                    }
                } catch (e) {
                    console.error('[WebSocket] Error parsing message:', e);
                }
            };

            ws.onclose = () => {
                // Verificar que este ws no es stale
                if (tab.ws !== ws) return;

                console.log(`[WebSocket] Tab ${tabId} disconnected (attempt ${tab.reconnectAttempts})`);
                tab._reconnecting = false;
                tab.isConnected = false;
                tab.reconnectAttempts = (tab.reconnectAttempts || 0) + 1;

                // Limpiar referencia
                tab.ws = null;

                // Notificar cambio de estado
                window.dispatchEvent(new CustomEvent('tab-disconnected', { detail: { tabId } }));

                // Verificar si debe reconectar
                if (tab.reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
                    console.error(`[WebSocket] Tab ${tabId} max reconnection attempts reached`);
                    window.dispatchEvent(new CustomEvent('tab-reconnect-failed', { detail: { tabId } }));
                    return;
                }

                // Exponential backoff
                const delay = Math.min(
                    INITIAL_RECONNECT_DELAY * Math.pow(2, tab.reconnectAttempts - 1),
                    MAX_RECONNECT_DELAY
                );

                console.log(`[WebSocket] Tab ${tabId} reconnecting in ${delay}ms...`);

                tab.reconnectTimeout = setTimeout(() => {
                    connectTab(tab, onMessage);
                }, delay);
            };

            ws.onerror = (error) => {
                // Verificar que este ws no es stale
                if (tab.ws !== ws) return;

                console.error(`[WebSocket] Tab ${tabId} error:`, error);
                tab._reconnecting = false;

                window.dispatchEvent(new CustomEvent('tab-error', { detail: { tabId, error } }));
            };

        } catch (e) {
            console.error(`[WebSocket] Tab ${tabId} connection error:`, e);
            tab.isConnected = false;
        }
    }

    /**
     * Desconecta un tab del WebSocket
     */
    function disconnectTab(tab) {
        if (!tab) return;

        // Cancelar timer de reconexión
        if (tab.reconnectTimeout) {
            clearTimeout(tab.reconnectTimeout);
            tab.reconnectTimeout = null;
        }

        // Cerrar WebSocket
        if (tab.ws) {
            try {
                tab.ws.close();
            } catch (e) {
                console.warn('[WebSocket] Error closing WebSocket:', e);
            }
            tab.ws = null;
        }

        tab.isConnected = false;
        tab.reconnectAttempts = 0;
    }

    /**
     * Envía datos al WebSocket de un tab
     */
    function sendTab(tab, data) {
        if (!tab || !tab.ws) return false;

        if (tab.ws.readyState !== WebSocket.OPEN) {
            console.warn('[WebSocket] Cannot send, not connected');
            return false;
        }

        try {
            tab.ws.send(JSON.stringify(data));
            return true;
        } catch (e) {
            console.error('[WebSocket] Error sending message:', e);
            return false;
        }
    }

    /**
     * Envía un mensaje de usuario
     */
    function sendUserMessage(tab, content, attachments = []) {
        return sendTab(tab, { content, attachments });
    }

    /**
     * Envía un comando
     */
    function sendCommand(tab, command) {
        return sendTab(tab, { command });
    }

    /**
     * Envía respuesta a pregunta del usuario
     */
    function sendQuestionResponse(tab, responses, cancelled = false) {
        return sendTab(tab, {
            type: 'question_response',
            responses,
            cancelled,
        });
    }

    /**
     * Envía respuesta de aprobación de tool
     */
    function sendToolApprovalResponse(tab, approved, input) {
        return sendTab(tab, {
            type: 'tool_approval_response',
            approved,
            input,
        });
    }

    /**
     * Maneja la actualización de session_id (re-key del tab)
     */
    function handleSessionIdUpdate(tab, newSessionId) {
        const oldId = tab.id;
        const newId = newSessionId;

        if (oldId === newId) return;

        console.log(`[WebSocket] Re-keying tab: ${oldId} -> ${newId}`);

        // Notificar al componente padre para que actualice el Map de tabs
        window.dispatchEvent(new CustomEvent('tab-session-id-update', {
            detail: { oldId, newId }
        }));
    }

    return {
        connectTab,
        disconnectTab,
        sendTab,
        sendUserMessage,
        sendCommand,
        sendQuestionResponse,
        sendToolApprovalResponse,
    };
}
