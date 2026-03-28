// ===== Renderizado de mensajes y UI =====

import { state, dom } from './state.js';
import { saveTabs } from './storage.js';

export function scrollToBottom() {
    dom.messages.scrollTop = dom.messages.scrollHeight;
}

export function showLoading(tabId) {
    if (state.activeTabId !== tabId) return;
    hideLoading(tabId);

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
}

export function hideLoading(tabId) {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
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

export function renderAskUserQuestionInChat(questions, tabId) {
    if (state.activeTabId !== tabId) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';

    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = 'Claude';
    msgDiv.appendChild(label);

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'markdown-content';

    let html = '<div class="chat-question">';
    questions.forEach(q => {
        html += `<strong>${escapeHtml(q.header || 'Pregunta')}:</strong> ${escapeHtml(q.question)}<br>`;
        html += '<ul>';
        q.options.forEach(opt => {
            html += `<li><strong>${escapeHtml(opt.label)}</strong>`;
            if (opt.description) html += ` - ${escapeHtml(opt.description)}`;
            html += '</li>';
        });
        html += '</ul>';
    });
    html += '</div>';

    contentDiv.innerHTML = html;
    bubble.appendChild(contentDiv);
    msgDiv.appendChild(bubble);
    dom.messages.appendChild(msgDiv);
    scrollToBottom();
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

    // Manejar AskUserQuestion
    if (data.type === 'ask_user_question') {
        hideLoading(tabId);
        // Guardar en historial para persistencia
        tab.renderedMessages.push(data);
        saveTabs();
        // Mostrar en el chat
        renderAskUserQuestionInChat(data.questions, tabId);
        // Mostrar modal
        showAskUserQuestion(data.questions, tabId, tab.ws);
        return;
    }

    // Guardar en renderedMessages (excepto system repetitivos)
    if (data.type !== 'system' || data.message.includes('Conectado')) {
        tab.renderedMessages.push(data);
    }

    if (data.type === 'assistant') {
        hideLoading(tabId);
        renderAssistantBlocks(data.blocks, tabId);
    } else if (data.type === 'result') {
        hideLoading(tabId);
    } else if (data.type === 'system') {
        addSystemMessage(data.message, tabId);
    }
}

// ===== AskUserQuestion Component =====

let currentQuestionModal = null;

export function showAskUserQuestion(questions, tabId, ws) {
    // Remover modal existente si hay
    hideAskUserQuestion();

    const overlay = document.createElement('div');
    overlay.className = 'question-overlay';
    overlay.id = 'questionOverlay';

    const selectedAnswers = new Map(); // questionIndex -> Set of selected option indices

    questions.forEach((_, idx) => selectedAnswers.set(idx, new Set()));

    const questionsHtml = questions.map((q, qIdx) => `
        <div class="question-block" data-question-index="${qIdx}">
            <div class="question-header">
                <span class="question-chip">${escapeHtml(q.header || 'Pregunta')}</span>
            </div>
            <div class="question-text">${escapeHtml(q.question)}</div>
            ${q.multiSelect ? '<div class="question-multiselect-hint">Puedes seleccionar varias opciones</div>' : ''}
            <div class="question-options">
                ${q.options.map((opt, oIdx) => `
                    <div class="question-option"
                         data-question-index="${qIdx}"
                         data-option-index="${oIdx}"
                         data-multi-select="${q.multiSelect}">
                        <div class="question-option-checkbox">
                            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="question-option-content">
                            <div class="question-option-label">${escapeHtml(opt.label)}</div>
                            ${opt.description ? `<div class="question-option-description">${escapeHtml(opt.description)}</div>` : ''}
                        </div>
                    </div>
                    ${opt.preview ? `
                        <div class="question-preview" data-preview-for="${qIdx}-${oIdx}" style="display:none">
                            ${escapeHtml(opt.preview)}
                        </div>
                    ` : ''}
                `).join('')}
            </div>
        </div>
    `).join('');

    overlay.innerHTML = `
        <div class="question-modal">
            ${questionsHtml}
            <div class="question-actions">
                <button class="question-btn question-btn-cancel" id="questionCancelBtn">
                    Cancelar
                </button>
                <button class="question-btn question-btn-submit" id="questionSubmitBtn">
                    Responder
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    currentQuestionModal = { overlay, questions, selectedAnswers, ws, tabId };

    // Agregar event listeners
    overlay.querySelectorAll('.question-option').forEach(opt => {
        opt.addEventListener('click', (e) => {
            const qIdx = parseInt(opt.dataset.questionIndex);
            const oIdx = parseInt(opt.dataset.optionIndex);
            const multiSelect = opt.dataset.multiSelect === 'true';

            const answers = currentQuestionModal.selectedAnswers.get(qIdx);
            if (multiSelect) {
                if (answers.has(oIdx)) {
                    answers.delete(oIdx);
                } else {
                    answers.add(oIdx);
                }
            } else {
                answers.clear();
                answers.add(oIdx);
            }
            updateOptionUI(qIdx);
        });
    });

    overlay.querySelector('#questionCancelBtn').addEventListener('click', () => {
        hideAskUserQuestion();
    });

    overlay.querySelector('#questionSubmitBtn').addEventListener('click', () => {
        const { questions, selectedAnswers, ws, tabId } = currentQuestionModal;

        const responses = questions.map((q, qIdx) => {
            const selected = Array.from(selectedAnswers.get(qIdx));
            const selectedLabels = selected.map(oIdx => q.options[oIdx].label);

            if (q.multiSelect) {
                return selectedLabels;
            } else {
                return selectedLabels[0] || null;
            }
        });

        // Formatear respuesta para mostrar en el chat
        let responseText = '';
        questions.forEach((q, qIdx) => {
            const r = responses[qIdx];
            if (Array.isArray(r)) {
                responseText += `${q.header || 'Pregunta'}: ${r.join(', ')}\n`;
            } else if (r) {
                responseText += `${q.header || 'Pregunta'}: ${r}\n`;
            }
        });
        responseText = responseText.trim();

        // Enviar respuesta al backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'question_response',
                responses
            }));
        }

        // Mostrar respuesta en el chat como mensaje del usuario
        addMessage('user', responseText, tabId);

        // Guardar en historial
        const tab = state.tabs.get(tabId);
        if (tab) {
            tab.renderedMessages.push({ type: 'user', content: responseText });
            saveTabs();
        }

        hideAskUserQuestion();
    });

    console.log('AskUserQuestion modal shown, questions:', questions.length);
}

function updateOptionUI(qIdx) {
    const { overlay, selectedAnswers, questions } = currentQuestionModal;
    const answers = selectedAnswers.get(qIdx);
    const multiSelect = questions[qIdx].multiSelect;

    // Actualizar todas las opciones de esta pregunta
    const options = overlay.querySelectorAll(`.question-option[data-question-index="${qIdx}"]`);
    options.forEach(opt => {
        const oIdx = parseInt(opt.dataset.optionIndex);
        const isSelected = answers.has(oIdx);
        opt.classList.toggle('selected', isSelected);

        // Mostrar/ocultar preview
        const preview = overlay.querySelector(`.question-preview[data-preview-for="${qIdx}-${oIdx}"]`);
        if (preview) {
            preview.style.display = isSelected ? 'block' : 'none';
        }

        // En single-select, desmarcar otras
        if (!multiSelect && isSelected) {
            options.forEach(other => {
                if (other !== opt) {
                    other.classList.remove('selected');
                    const otherIdx = parseInt(other.dataset.optionIndex);
                    const otherPreview = overlay.querySelector(`.question-preview[data-preview-for="${qIdx}-${otherIdx}"]`);
                    if (otherPreview) otherPreview.style.display = 'none';
                }
            });
        }
    });
}

export function hideAskUserQuestion() {
    if (currentQuestionModal) {
        currentQuestionModal.overlay.remove();
        currentQuestionModal = null;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
