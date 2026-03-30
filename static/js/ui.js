// ===== Renderizado de mensajes y UI =====

import { state, dom } from './state.js';
import { saveTabs } from './storage.js';
import { renderAskUserQuestionInChat, showAskUserQuestion, hideAskUserQuestion, showToolApproval, hideToolApproval, showFileView, hideFileView } from './modals.js';

export { showAskUserQuestion, hideAskUserQuestion, showToolApproval, hideToolApproval, showFileView, hideFileView };

export function scrollToBottom() {
    dom.messages.scrollTop = dom.messages.scrollHeight;
}

export function showLoading(tabId) {
    if (state.activeTabId !== tabId) return;
    hideTypingIndicator();

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="typing-label">Claude</div>
        <div class="typing-bubble">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    dom.messages.appendChild(indicator);
    scrollToBottom();
    setWorking(true);
}

export function hideLoading(tabId) {
    hideTypingIndicator();
    setWorking(false);
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function setWorking(active) {
    if (window.setStarfieldWorking) window.setStarfieldWorking(active);
    if (window.setHeaderWorking) window.setHeaderWorking(active);
    const title = document.querySelector('.terminal-title');
    if (title) title.classList.toggle('working', active);
}

export function addMessage(type, text, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    if (type !== 'thinking') {
        const label = document.createElement('div');
        label.className = 'message-label';
        label.textContent = type === 'user' ? 'Tu' : 'Claude';
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
    dom.messages.appendChild(msgDiv);
    scrollToBottom();
}

export function addToolUse(name, input, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message tool';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `<strong>Tool:</strong> ${name}<br><code>${JSON.stringify(input).substring(0, 150)}</code>`;

    msgDiv.appendChild(bubble);
    dom.messages.appendChild(msgDiv);
    scrollToBottom();
}

export function addSystemMessage(text, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system';
    msgDiv.innerHTML = `<div class="bubble">${text}</div>`;
    dom.messages.appendChild(msgDiv);
    scrollToBottom();
}

export function updateTabStatus(tabId, status) {
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

export function updateGlobalStatus() {
    const tabs = Array.from(state.tabs.values());
    const connected = tabs.filter(t => t.isConnected).length;

    dom.statusDot.className = 'status-dot';
    if (connected === tabs.length && tabs.length > 0) {
        dom.statusDot.classList.add('connected');
    }

    dom.statusText.textContent =
        tabs.length > 0 ? `${connected}/${tabs.length} conectados` : 'Sin pestanas';
}

export function renderMessage(data, tabId) {
    if (state.activeTabId !== tabId) return;

    if (data.type === 'user') {
        addMessage('user', data.content, tabId);
    } else if (data.type === 'assistant') {
        renderAssistantBlocks(data.blocks, tabId);
    } else if (data.type === 'result') {
        // Ignorar mensaje de resultado
    } else if (data.type === 'system') {
        addSystemMessage(data.message, tabId);
    } else if (data.type === 'ask_user_question') {
        renderAskUserQuestionInChat(data.questions, tabId);
    }
}

export function renderAssistantBlocks(blocks, tabId) {
    for (const block of blocks) {
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
}

export function handleMessage(data, tabId) {
    console.log('Recibido:', data);

    const tab = state.tabs.get(tabId);
    if (!tab) return;

    // Guardar session_id del SDK
    if (data.type === 'session_id') {
        tab.sessionId = data.session_id;
        saveTabs();
        return;
    }

    // Manejar file view (plan approval)
    if (data.type === 'file_view') {
        hideLoading(tabId);
        showFileView(data.file_path, data.content, tabId, tab.ws);
        return;
    }

    // Manejar tool approval request
    if (data.type === 'tool_approval_request') {
        hideLoading(tabId);
        showToolApproval(data.tool_name, data.input, tabId, tab.ws);
        return;
    }

    // Manejar AskUserQuestion
    if (data.type === 'ask_user_question') {
        hideLoading(tabId);
        tab.renderedMessages.push(data);
        saveTabs();
        renderAskUserQuestionInChat(data.questions, tabId);
        showAskUserQuestion(data.questions, tabId, tab.ws);
        return;
    }

    // Guardar en renderedMessages (excepto system repetitivos)
    if (data.type !== 'system' || data.message.includes('Conectado')) {
        tab.renderedMessages.push(data);
    }

    if (data.type === 'assistant') {
        hideTypingIndicator();
        renderAssistantBlocks(data.blocks, tabId);
        // Si tiene tool_use, el agente sigue trabajando → re-mostrar typing
        const hasToolUse = data.blocks && data.blocks.some(b => b.type === 'tool_use');
        if (hasToolUse) {
            showLoading(tabId);
        }
    } else if (data.type === 'user') {
        // UserMessage contiene ToolResultBlock con resultados de herramientas
        renderAssistantBlocks(data.blocks, tabId);
    } else if (data.type === 'result') {
        // Resultado final: apagar todo
        hideLoading(tabId);
    } else if (data.type === 'system') {
        addSystemMessage(data.message, tabId);
    }
}
