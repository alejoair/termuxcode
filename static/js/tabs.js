// ===== Gestion de pestanas =====

import { state, dom, DEFAULT_SETTINGS } from './state.js';
import { saveTabs, loadTabsData } from './storage.js';
import { addMessage, addSystemMessage, renderMessage, updateGlobalStatus, showLoading, hideLoading, showAskUserQuestion, showToolApproval } from './ui.js';
import { connectTab, disconnectTab } from './connection.js';
import { vibrateSend, vibrateError } from './haptics.js';

function createTabElement(tabId, tabName) {
    const template = document.getElementById('tabTemplate');
    const clone = template.content.cloneNode(true);

    const tabEl = clone.querySelector('.tab');
    tabEl.dataset.tabId = tabId;

    const nameEl = tabEl.querySelector('.tab-name');
    nameEl.textContent = tabName;
    nameEl.addEventListener('dblclick', () => renameTab(tabId));

    const closeEl = tabEl.querySelector('.tab-close');
    closeEl.addEventListener('click', (e) => {
        e.stopPropagation();
        closeTab(tabId);
    });

    tabEl.addEventListener('click', () => switchTab(tabId));
    document.getElementById('tabsHeader').appendChild(tabEl);
}

export async function createTab(name, cwd) {
    // Si no se proporciona cwd, abrir diálogo de carpeta (solo en Tauri)
    if (!cwd && window.__TAURI__) {
        try {
            const selected = await window.__TAURI__.dialog.open({
                directory: true,
                multiple: false,
                title: 'Seleccionar carpeta de trabajo',
            });
            if (!selected) return null; // Usuario canceló
            cwd = selected;
        } catch (e) {
            console.warn('Dialog not available:', e);
        }
    }
    // En navegador: cwd queda null, el backend usa su propio directorio

    state.tabCounter++;
    const tabId = `tab_${Date.now()}_${state.tabCounter}`;
    const tabName = name || `Chat ${state.tabCounter}`;

    state.tabs.set(tabId, {
        id: tabId,
        name: tabName,
        cwd: cwd || null,
        ws: null,
        reconnectTimeout: null,
        messages: [],
        renderedMessages: [],
        isConnected: false,
        sessionId: null,
        settings: { ...DEFAULT_SETTINGS },
    });

    createTabElement(tabId, tabName);
    switchTab(tabId);
    connectTab(tabId);

    saveTabs();
    updateGlobalStatus();

    return tabId;
}

export function switchTab(tabId) {
    if (!state.tabs.has(tabId)) return;

    state.activeTabId = tabId;

    document.querySelectorAll('.tab').forEach(el => {
        el.classList.toggle('active', el.dataset.tabId === tabId);
    });

    dom.messages.innerHTML = '';
    const tab = state.tabs.get(tabId);

    for (const msg of tab.renderedMessages) {
        renderMessage(msg, tabId);
    }

    while (tab.messages.length > 0) {
        const data = tab.messages.shift();
        renderMessage(data, tabId);
    }

    // Restaurar modal de pregunta pendiente si existe
    const lastMsg = tab.renderedMessages[tab.renderedMessages.length - 1];
    if (lastMsg && lastMsg.type === 'ask_user_question' && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        showAskUserQuestion(lastMsg.questions, tabId, tab.ws);
    }

    if (!tab.isConnected && tab.ws === null) {
        connectTab(tabId);
    }

    updateGlobalStatus();

    // Actualizar selector de modelo
    const modelSelect = document.getElementById('modelSelector');
    if (modelSelect && tab.settings) {
        modelSelect.value = tab.settings.model || 'sonnet';
    }
}

export function closeTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    disconnectTab(tabId);
    state.tabs.delete(tabId);

    const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (tabEl) tabEl.remove();

    if (state.activeTabId === tabId) {
        const remaining = Array.from(state.tabs.keys());
        if (remaining.length > 0) {
            switchTab(remaining[0]);
        } else {
            state.activeTabId = null;
            dom.messages.innerHTML = '<div class="message system"><div class="bubble">Crea una nueva pestana para comenzar</div></div>';
        }
    }

    saveTabs();
    updateGlobalStatus();
}

export function renameTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    const newName = prompt('Nombre de la pestana:', tab.name);
    if (newName && newName.trim()) {
        tab.name = newName.trim();

        const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
        if (tabEl) {
            tabEl.querySelector('.tab-name').textContent = newName;
        }

        saveTabs();
    }
}

export function send() {
    const tab = state.tabs.get(state.activeTabId);
    if (!tab) {
        addSystemMessage('No hay pestana activa', state.activeTabId);
        return;
    }

    const content = dom.input.value.trim();
    if (!content) return;

    tab.renderedMessages.push({ type: 'user', content });
    saveTabs();
    addMessage('user', content, state.activeTabId);
    vibrateSend();

    if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ content }));
        showLoading(state.activeTabId);
    } else {
        addSystemMessage('No conectado. Reintentando...', state.activeTabId);
        vibrateError();
        connectTab(state.activeTabId);
    }

    dom.input.value = '';
}

export function sendStop() {
    const tab = state.tabs.get(state.activeTabId);
    if (tab && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ command: '/stop' }));
        addSystemMessage('Comando /stop enviado', state.activeTabId);
        vibrateSend();
    }
}

export function sendDisconnect() {
    const tab = state.tabs.get(state.activeTabId);
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

    dom.statusDot.classList.remove('connected');
    dom.statusText.textContent = 'Desconectado';

    connectTab(state.activeTabId);
}

export function clearChat() {
    dom.messages.innerHTML = '';
    addSystemMessage('Chat limpiado', state.activeTabId);
}

export function loadTabs() {
    const data = loadTabsData();
    data.forEach(({ id, name, cwd, sessionId, renderedMessages, settings }) => {
        state.tabs.set(id, {
            id,
            name,
            cwd: cwd || null,
            ws: null,
            reconnectTimeout: null,
            messages: [],
            renderedMessages: renderedMessages || [],
            isConnected: false,
            sessionId: sessionId || null,
            settings: settings || { ...DEFAULT_SETTINGS },
        });
        createTabElement(id, name);

        const match = name.match(/Chat (\d+)/);
        if (match) {
            state.tabCounter = Math.max(state.tabCounter, parseInt(match[1]));
        }
    });
}
