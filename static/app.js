// ===== Claude Code Mobile - Multi-Tab System (basado en test_websocket.html) =====

const WS_URL = 'ws://localhost:8769';
const STORAGE_KEY = 'ccm_tabs';

// Estado global
const state = {
    tabs: new Map(),  // tabId -> { ws, reconnectTimeout, messages, isConnected, sessionId }
    activeTabId: null,
    tabCounter: 0,
};

// Referencias DOM
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('prompt');
const globalStatusDot = document.getElementById('globalStatusDot');
const globalStatusText = document.getElementById('globalStatusText');

// ===== Crear nueva pestaña =====
function createTab(name) {
    state.tabCounter++;
    const tabId = `tab_${Date.now()}_${state.tabCounter}`;
    const tabName = name || `Chat ${state.tabCounter}`;

    state.tabs.set(tabId, {
        id: tabId,
        name: tabName,
        ws: null,
        reconnectTimeout: null,
        messages: [],          // Mensajes pendientes (cuando pestaña inactiva)
        renderedMessages: [],  // Todos los mensajes ya renderizados
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

// ===== Crear elemento de pestaña en el DOM =====
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

// ===== Cambiar a una pestaña =====
function switchTab(tabId) {
    if (!state.tabs.has(tabId)) return;

    state.activeTabId = tabId;

    // Actualizar clase active de pestañas
    document.querySelectorAll('.tab').forEach(el => {
        el.classList.toggle('active', el.dataset.tabId === tabId);
    });

    // Limpiar y mostrar mensajes de la pestaña
    messagesEl.innerHTML = '';
    const tab = state.tabs.get(tabId);

    // Renderizar todos los mensajes guardados
    for (const msg of tab.renderedMessages) {
        renderMessage(msg, tabId);
    }

    // Procesar mensajes pendientes (ya estarán en renderedMessages desde handleMessage)
    while (tab.messages.length > 0) {
        const data = tab.messages.shift();
        renderMessage(data, tabId);
    }

    if (!tab.isConnected && tab.ws === null) {
        renderSystemMessage('Conectando...', tabId);
        connectTab(tabId);
    }

    updateGlobalStatus();
}

// ===== Renderizar mensaje sin guardar (para switchTab) =====
function renderMessage(data, tabId) {
    if (state.activeTabId !== tabId) return;

    if (data.type === 'user') {
        addMessage('user', data.content, tabId);
    } else if (data.type === 'assistant') {
        for (const block of data.blocks) {
            if (block.type === 'text') {
                addMessage('assistant', block.text, tabId);
            } else if (block.type === 'thinking') {
                addMessage('thinking', block.thinking, tabId);
            } else if (block.type === 'tool_use') {
                addToolUse(block.name, block.input, tabId);
            } else if (block.type === 'tool_result') {
                const content = typeof block.content === 'string'
                    ? block.content.substring(0, 200)
                    : JSON.stringify(block.content).substring(0, 200);
                addMessage('tool', `Resultado: ${content}...`, tabId);
            }
        }
    } else if (data.type === 'result') {
        renderSystemMessage(`Fin | Turnos: ${data.num_turns} | Razón: ${data.stop_reason}`, tabId);
    } else if (data.type === 'system') {
        renderSystemMessage(data.message, tabId);
    }
}

function renderSystemMessage(text, tabId) {
    if (state.activeTabId !== tabId) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system';
    msgDiv.innerHTML = `<div class="bubble">${text}</div>`;
    messagesEl.appendChild(msgDiv);
    scrollToBottom();
}

// ===== Cerrar pestaña =====
function closeTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    disconnectTab(tabId);
    state.tabs.delete(tabId);

    // Remover elemento DOM
    const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (tabEl) tabEl.remove();

    // Si cerramos la pestaña activa, cambiar a otra
    if (state.activeTabId === tabId) {
        const remaining = Array.from(state.tabs.keys());
        if (remaining.length > 0) {
            switchTab(remaining[0]);
        } else {
            state.activeTabId = null;
            messagesEl.innerHTML = '<div class="message system"><div class="bubble">Crea una nueva pestaña para comenzar</div></div>';
        }
    }

    saveTabs();
    updateGlobalStatus();
}

// ===== Renombrar pestaña =====
function renameTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    const newName = prompt('Nombre de la pestaña:', tab.name);
    if (newName && newName.trim()) {
        tab.name = newName.trim();

        const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
        if (tabEl) {
            const nameEl = tabEl.querySelector('.tab-name');
            nameEl.textContent = newName;
        }

        saveTabs();
    }
}

// ===== Conectar pestaña =====
function connectTab(tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    if (tab.ws && (tab.ws.readyState === WebSocket.CONNECTING || tab.ws.readyState === WebSocket.OPEN)) {
        return;
    }

    updateTabStatus(tabId, 'connecting');

    try {
        tab.ws = new WebSocket(WS_URL);

        tab.ws.onopen = () => {
            tab.isConnected = true;
            updateTabStatus(tabId, 'connected');

            // Enviar sessionId para reanudar sesión si existe
            if (tab.sessionId) {
                tab.ws.send(JSON.stringify({
                    type: 'resume',
                    session_id: tab.sessionId
                }));
            }

            if (state.activeTabId === tabId) {
                globalStatusDot.classList.add('connected');
                globalStatusText.textContent = 'Conectado';
                addSystemMessage('Conectado al servidor ✓', tabId);
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
                globalStatusDot.classList.remove('connected');
                globalStatusText.textContent = 'Desconectado';
                addSystemMessage('Desconectado del servidor', tabId);
            }

            updateGlobalStatus();

            // Auto reconnect
            tab.reconnectTimeout = setTimeout(() => {
                if (state.activeTabId === tabId) {
                    globalStatusText.textContent = 'Reconectando...';
                }
                connectTab(tabId);
            }, 3000);
        };

        tab.ws.onerror = () => {
            if (state.activeTabId === tabId) {
                addSystemMessage('Error de conexión', tabId);
            }
        };

    } catch (e) {
        console.error('Error connecting:', e);
        updateTabStatus(tabId, 'disconnected');
    }
}

// ===== Desconectar pestaña =====
function disconnectTab(tabId) {
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

// ===== Actualizar indicador de estado de pestaña =====
function updateTabStatus(tabId, status) {
    const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (!tabEl) return;

    const statusDot = tabEl.querySelector('.tab-status-dot');
    statusDot.className = 'tab-status-dot';

    if (status === 'connected') {
        statusDot.classList.add('connected');
    } else if (status === 'connecting') {
        statusDot.classList.add('connecting');
    }
}

// ===== Actualizar estado global =====
function updateGlobalStatus() {
    const tabs = Array.from(state.tabs.values());
    const connected = tabs.filter(t => t.isConnected).length;

    globalStatusDot.className = 'status-dot';
    if (connected === tabs.length && tabs.length > 0) {
        globalStatusDot.classList.add('connected');
    }

    globalStatusText.textContent =
        tabs.length > 0 ? `${connected}/${tabs.length} conectados` : 'Sin pestañas';
}

// ===== Manejar mensaje recibido =====
function handleMessage(data, tabId) {
    console.log('Recibido:', data);

    const tab = state.tabs.get(tabId);
    if (!tab) return;

    if (data.type === 'session_id') {
        // Guardar sessionId para futuras reconexiones
        tab.sessionId = data.session_id;
        saveTabs();
        return;
    }

    // Guardar mensaje en renderedMessages (excepto system repetitivos)
    if (data.type !== 'system' || data.message.includes('Conectado')) {
        tab.renderedMessages.push(data);
        saveTabs();  // Persistir cambios
    }

    if (data.type === 'assistant') {
        for (const block of data.blocks) {
            if (block.type === 'text') {
                addMessage('assistant', block.text, tabId);
            } else if (block.type === 'thinking') {
                addMessage('thinking', block.thinking, tabId);
            } else if (block.type === 'tool_use') {
                addToolUse(block.name, block.input, tabId);
            } else if (block.type === 'tool_result') {
                const content = typeof block.content === 'string'
                    ? block.content.substring(0, 200)
                    : JSON.stringify(block.content).substring(0, 200);
                addMessage('tool', `Resultado: ${content}...`, tabId);
            }
        }
    } else if (data.type === 'result') {
        addSystemMessage(`Fin | Turnos: ${data.num_turns} | Razón: ${data.stop_reason}`, tabId);
    } else if (data.type === 'system') {
        addSystemMessage(data.message, tabId);
    }
}

// ===== Agregar mensaje =====
function addMessage(type, text, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    if (type !== 'thinking') {
        const label = document.createElement('div');
        label.className = 'message-label';
        label.textContent = type === 'user' ? 'Tú' : 'Claude';
        msgDiv.appendChild(label);
    }

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (type === 'assistant') {
        const contentDiv = document.createElement('div');
        contentDiv.className = 'markdown-content';
        contentDiv.innerHTML = marked.parse(text);
        bubble.appendChild(contentDiv);
    } else {
        bubble.textContent = text;
    }

    msgDiv.appendChild(bubble);
    messagesEl.appendChild(msgDiv);
    scrollToBottom();
}

// ===== Agregar mensaje de herramienta =====
function addToolUse(name, input, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message tool';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `<strong>Tool:</strong> ${name}<br><code>${JSON.stringify(input).substring(0, 150)}</code>`;

    msgDiv.appendChild(bubble);
    messagesEl.appendChild(msgDiv);
    scrollToBottom();
}

// ===== Agregar mensaje del sistema =====
function addSystemMessage(text, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system';
    msgDiv.innerHTML = `<div class="bubble">${text}</div>`;
    messagesEl.appendChild(msgDiv);
    scrollToBottom();
}

// ===== Scroll al final =====
function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ===== Enviar mensaje =====
function send() {
    const tab = state.tabs.get(state.activeTabId);
    if (!tab) {
        addSystemMessage('No hay pestaña activa', state.activeTabId);
        return;
    }

    const content = inputEl.value.trim();
    if (!content) return;

    // Guardar mensaje del usuario en renderedMessages
    tab.renderedMessages.push({ type: 'user', content });
    saveTabs();  // Persistir cambios
    addMessage('user', content, state.activeTabId);

    if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ content }));
    } else {
        addSystemMessage('No conectado. Reintentando...', state.activeTabId);
        connectTab(state.activeTabId);
    }

    inputEl.value = '';
}

// ===== Enviar comando stop =====
function sendStop() {
    const tab = state.tabs.get(state.activeTabId);
    if (tab && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify({ command: '/stop' }));
        addSystemMessage('Comando /stop enviado', state.activeTabId);
    }
}

// ===== Reconectar pestaña actual =====
function sendDisconnect() {
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

    globalStatusDot.classList.remove('connected');
    globalStatusText.textContent = 'Desconectado';
    updateTabStatus(state.activeTabId, 'disconnected');

    connectTab(state.activeTabId);
}

// ===== Limpiar chat =====
function clearChat() {
    messagesEl.innerHTML = '';
    addSystemMessage('Chat limpiado', state.activeTabId);
}

// ===== Guardar pestañas en localStorage =====
function saveTabs() {
    const data = Array.from(state.tabs.entries()).map(([id, tab]) => ({
        id,
        name: tab.name,
        sessionId: tab.sessionId,
        renderedMessages: tab.renderedMessages,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// ===== Cargar pestañas desde localStorage =====
function loadTabs() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const data = JSON.parse(saved);
            data.forEach(({ id, name, sessionId, renderedMessages }) => {
                state.tabs.set(id, {
                    id,
                    name,
                    ws: null,
                    reconnectTimeout: null,
                    messages: [],
                    renderedMessages: renderedMessages || [],
                    isConnected: false,
                    sessionId: sessionId || null,
                });
                createTabElement(id, name);

                // Extraer contador del nombre
                const match = name.match(/Chat (\d+)/);
                if (match) {
                    state.tabCounter = Math.max(state.tabCounter, parseInt(match[1]));
                }
            });
        }
    } catch (e) {
        console.error('Error loading tabs:', e);
    }
}

// ===== Inicialización =====
function init() {
    loadTabs();

    if (state.tabs.size === 0) {
        createTab('Chat 1');
    } else {
        // Activar la primera pestaña y conectarla
        const firstTab = state.tabs.keys().next().value;
        switchTab(firstTab);
    }

    // Event listener para Enter
    inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') send();
    });
}

// ===== Funciones globales =====
window.createNewTab = () => createTab();
window.send = send;
window.sendStop = sendStop;
window.sendDisconnect = sendDisconnect;
window.clearChat = clearChat;

// Iniciar
init();
