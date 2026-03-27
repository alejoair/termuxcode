// ===== Gestion de pestanas =====

import { state, dom } from './state.js';
import { saveTabs, loadTabsData } from './storage.js';
import { addMessage, addSystemMessage, renderMessage, updateGlobalStatus } from './ui.js';
import { connectTab, disconnectTab } from './connection.js';

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

export function createTab(name) {
    state.tabCounter++;
    const tabId = `tab_${Date.now()}_${state.tabCounter}`;
    const tabName = name || `Chat ${state.tabCounter}`;

    state.tabs.set(tabId, {
        id: tabId,
        name: tabName,
        ws: null,
        reconnectTimeout: null,
        messages: [],
        renderedMessages: [],
        isConnected: false,
        sessionId: null,
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

    if (!tab.isConnected && tab.ws === null) {
        connectTab(tabId);
    }

    updateGlobalStatus();
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

    if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ content }));
    } else {
        addSystemMessage('No conectado. Reintentando...', state.activeTabId);
        connectTab(state.activeTabId);
    }

    dom.input.value = '';
}

export function sendStop() {
    const tab = state.tabs.get(state.activeTabId);
    if (tab && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ command: '/stop' }));
        addSystemMessage('Comando /stop enviado', state.activeTabId);
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
    data.forEach(({ id, name, sessionId, renderedMessages }) => {
        state.tabs.set(id, {
            id,
            name,
            ws: null,
            reconnectTimeout: null,
            messages: [],
            renderedMessages: renderedMessages || [],
            isConnected: false,
            sessionId: sessionId || id,
        });
        createTabElement(id, name);

        const match = name.match(/Chat (\d+)/);
        if (match) {
            state.tabCounter = Math.max(state.tabCounter, parseInt(match[1]));
        }
    });
}
