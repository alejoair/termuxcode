// ===== Renderizado de mensajes y UI =====

import { state, dom } from './state.js';
import { saveTabs } from './storage.js';
import { renderAskUserQuestionInChat, showAskUserQuestion, hideAskUserQuestion, showToolApproval, hideToolApproval, showFileView, hideFileView, hasPendingQuestionModal, getPendingQuestion, showPlanViewer, migrateQuestionModal } from './modals.js';
import { vibrateReceive, vibrateResult, vibrateAttention } from './haptics.js';
import { notifyResult, notifyAskUserQuestion, notifyToolApproval, notifyPlanApproval } from './notifications.js';

export { showAskUserQuestion, hideAskUserQuestion, showToolApproval, hideToolApproval, showFileView, hideFileView, hasPendingQuestionModal, getPendingQuestion, showPlanViewer, trimRenderedMessages };

const MAX_RENDERED_MESSAGES = 200;

function trimRenderedMessages(tab) {
    if (tab.renderedMessages.length > MAX_RENDERED_MESSAGES) {
        tab.renderedMessages = tab.renderedMessages.slice(-MAX_RENDERED_MESSAGES);
    }
}

// ===== Sanitización =====

/** Renderiza markdown de forma segura (DOMPurify + marked) */
function safeMarkdown(text) {
    if (typeof text !== 'string') return '';
    const raw = marked.parse(text);
    return window.DOMPurify ? window.DOMPurify.sanitize(raw) : raw;
}

/** Escapa HTML para inyección segura en innerHTML */
function escapeHtml(text) {
    if (typeof text !== 'string') text = String(text);
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Flag para deshabilitar animaciones durante re-render de tabs
let _skipAnimations = false;

export function skipAnimationsDuring(fn) {
    _skipAnimations = true;
    fn();
    _skipAnimations = false;
}

export { escapeHtml };

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
    if (_skipAnimations) msgDiv.classList.add('no-anim');

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
        contentDiv.innerHTML = safeMarkdown(text);
        bubble.appendChild(contentDiv);
    } else {
        bubble.textContent = text;
    }

    msgDiv.appendChild(bubble);
    dom.messages.appendChild(msgDiv);
    scrollToBottom();
}

function createToolUseEl(name, input, toolId) {
    let info = '';
    if (name === 'Bash') info = input.command || input.description || '';
    else if (['Read', 'Write', 'Edit'].includes(name)) info = input.file_path || '';
    else if (name === 'Grep') info = `${input.pattern || ''}${input.path ? '  ' + input.path : ''}`;
    else if (name === 'Glob') info = input.pattern || '';
    else info = JSON.stringify(input);

    const el = document.createElement('div');
    el.className = 'accordion-item tool-block';
    if (toolId) el.dataset.toolId = toolId;
    el.innerHTML = `
        <div class="accordion-item-toggle tool-header">
            <span class="tool-chevron">▸</span>
            <span class="tool-name">${escapeHtml(name)}</span>
        </div>
        <div class="accordion-item-content">
            <div class="tool-content">${escapeHtml(info)}</div>
        </div>`;
    return el;
}

function createToolResultEl(rawContent) {
    const text = typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent);

    const el = document.createElement('div');
    el.className = 'accordion-item tool-block tool-result-block';
    el.innerHTML = `
        <div class="accordion-item-toggle tool-header">
            <span class="tool-chevron">▸</span>
            <span class="tool-name tool-result-label">resultado</span>
        </div>
        <div class="accordion-item-content">
            <div class="tool-content">${escapeHtml(text)}</div>
        </div>`;
    return el;
}

function insertToolResults(blocks, tabId) {
    if (state.activeTabId !== tabId) return;
    for (const block of blocks) {
        if (block.type !== 'tool_result') continue;
        const toolUseEl = dom.messages.querySelector(`[data-tool-id="${block.tool_use_id}"]`);
        const resultEl = createToolResultEl(block.content);
        if (toolUseEl) {
            toolUseEl.after(resultEl);
        } else {
            // fallback: añadir al final del último tool-call bubble
            const lastToolCall = dom.messages.querySelector('.tool-call-bubble:last-of-type');
            if (lastToolCall) {
                lastToolCall.appendChild(resultEl);
            } else {
                // fallback 2: añadir al final del último bubble de asistente
                const lastBubble = dom.messages.querySelector('.assistant-bubble:last-of-type');
                if (lastBubble) lastBubble.appendChild(resultEl);
            }
        }
    }
    scrollToBottom();
}

export function addSystemMessage(text, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message system';
    if (_skipAnimations) msgDiv.classList.add('no-anim');
    msgDiv.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
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

export function updateCwdDisplay(tabId) {
    const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (!tabEl) return;

    const cwdEl = tabEl.querySelector('.tab-cwd');
    if (!cwdEl) return;

    const tab = state.tabs.get(tabId);
    if (tab && tab.cwd) {
        const parts = tab.cwd.replace(/\\/g, '/').split('/');
        const folderName = parts[parts.length - 1] || tab.cwd;
        cwdEl.textContent = folderName;
        cwdEl.title = tab.cwd;
    } else {
        cwdEl.textContent = '';
        cwdEl.title = '';
    }
}

export function renderMessage(data, tabId) {
    if (state.activeTabId !== tabId) return;

    if (data.type === 'user') {
        if (data.blocks && data.blocks.length > 0) {
            // User message con tool_result blocks
            insertToolResults(data.blocks, tabId);
        } else if (data.content) {
            // User message normal
            addMessage('user', data.content, tabId);
        }
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
    if (state.activeTabId !== tabId) return;
    if (!blocks || blocks.length === 0) return;

    // Thinking blocks van separados (sin burbuja)
    for (const block of blocks) {
        if (block.type === 'thinking') {
            addMessage('thinking', block.thinking, tabId);
        }
    }

    // Separar tool_use del texto
    const toolBlocks = blocks.filter(b => b.type === 'tool_use');
    const textBlocks = blocks.filter(b => b.type === 'text');

    // Renderizar tool calls primero (sin label "Claude", diseño separado)
    for (const block of toolBlocks) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message tool-call';
        if (_skipAnimations) msgDiv.classList.add('no-anim');

        const bubble = document.createElement('div');
        bubble.className = 'bubble tool-call-bubble';
        bubble.appendChild(createToolUseEl(block.name, block.input, block.id));

        msgDiv.appendChild(bubble);
        dom.messages.appendChild(msgDiv);
    }

    // Renderizar texto con label "Claude"
    if (textBlocks.length > 0) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';
        if (_skipAnimations) msgDiv.classList.add('no-anim');

        const label = document.createElement('div');
        label.className = 'message-label';
        label.textContent = 'Claude';
        msgDiv.appendChild(label);

        const bubble = document.createElement('div');
        bubble.className = 'bubble assistant-bubble';

        for (const block of textBlocks) {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'markdown-content';
            contentDiv.innerHTML = safeMarkdown(block.text);
            bubble.appendChild(contentDiv);
        }

        msgDiv.appendChild(bubble);
        dom.messages.appendChild(msgDiv);
    }

    scrollToBottom();
}

export function handleMessage(data, tabId) {
    const tab = state.tabs.get(tabId);
    if (!tab) return;

    // Guardar CWD del backend
    if (data.type === 'cwd') {
        tab.cwd = data.cwd;
        updateCwdDisplay(tabId);
        saveTabs();
        return;
    }

    // Re-key de tab cuando llega session_id del SDK
    if (data.type === 'session_id') {
        const oldId = tabId;
        const newId = data.session_id;
        if (oldId === newId) return;

        // Migrar tab al nuevo ID
        state.tabs.delete(oldId);
        tab.id = newId;
        tab.sessionId = newId;
        state.tabs.set(newId, tab);

        // Actualizar DOM
        const tabEl = document.querySelector(`.tab[data-tab-id="${oldId}"]`);
        if (tabEl) tabEl.dataset.tabId = newId;

        // Actualizar activeTabId si corresponde
        if (state.activeTabId === oldId) {
            state.activeTabId = newId;
        }

        // Migrar estado de modales pendientes
        migrateQuestionModal(oldId, newId);

        saveTabs();
        return;
    }

    // Manejar file view (plan approval)
    if (data.type === 'file_view') {
        hideLoading(tabId);
        showFileView(data.file_path, data.content, tabId, tab.ws);
        vibrateAttention();
        notifyPlanApproval();
        return;
    }

    // Manejar tool approval request
    if (data.type === 'tool_approval_request') {
        hideLoading(tabId);
        showToolApproval(data.tool_name, data.input, tabId, tab.ws);
        vibrateAttention();
        notifyToolApproval(data.tool_name);
        return;
    }

    // Manejar AskUserQuestion
    if (data.type === 'ask_user_question') {
        hideLoading(tabId);
        tab.renderedMessages.push(data);
        saveTabs();
        renderAskUserQuestionInChat(data.questions, tabId);
        showAskUserQuestion(data.questions, tabId, tab.ws);
        vibrateAttention();
        notifyAskUserQuestion();
        return;
    }

    // Guardar en renderedMessages (excepto system repetitivos y result que no se renderizan)
    if (data.type !== 'system' && data.type !== 'result') {
        tab.renderedMessages.push(data);
    } else if (data.type === 'system' && data.message.includes('Conectado')) {
        tab.renderedMessages.push(data);
    }

    if (data.type === 'assistant') {
        hideTypingIndicator();
        renderAssistantBlocks(data.blocks, tabId);
        vibrateReceive();
        // Si tiene tool_use, el agente sigue trabajando → re-mostrar typing
        const hasToolUse = data.blocks && data.blocks.some(b => b.type === 'tool_use');
        if (hasToolUse) {
            showLoading(tabId);
        }
    } else if (data.type === 'user') {
        // UserMessage contiene ToolResultBlock — insertar cada result tras su tool_use
        insertToolResults(data.blocks, tabId);
    } else if (data.type === 'result') {
        // Resultado final: apagar todo
        hideLoading(tabId);
        vibrateResult();
        notifyResult();
    } else if (data.type === 'system') {
        addSystemMessage(data.message, tabId);
        // Si el mensaje indica error del SDK, quitar loading state
        if (data.message.startsWith('Error del SDK') || data.message.startsWith('SDK reconectado') || data.message.startsWith('No se pudo')) {
            hideLoading(tabId);
        }
    }

    trimRenderedMessages(tab);
    saveTabs();
}

export function updatePlanButton() {
    const fabPlan = document.getElementById('fabPlan');
    if (!fabPlan) return;

    const tab = state.tabs.get(state.activeTabId);
    const hasPlan = tab && tab.plan;

    fabPlan.classList.toggle('visible', hasPlan);
}
