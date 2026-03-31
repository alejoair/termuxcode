// ===== Modales: AskUserQuestion + Tool Approval =====

import { state, dom } from './state.js';
import { saveTabs } from './storage.js';
import { addMessage, addSystemMessage, showLoading, scrollToBottom } from './ui.js';

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== AskUserQuestion =====

// Map tabId -> modal state (so multiple tabs can have modals simultaneously)
const questionModals = new Map();
const approvalModals = new Map();
const fileViewModals = new Map();

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

export function showAskUserQuestion(questions, tabId, ws) {
    hideAskUserQuestion(tabId);

    const overlay = document.createElement('div');
    overlay.className = 'question-overlay';
    overlay.id = 'questionOverlay';

    const selectedAnswers = new Map();
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
    questionModals.set(tabId, { overlay, questions, selectedAnswers, ws, tabId });

    overlay.querySelectorAll('.question-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const qIdx = parseInt(opt.dataset.questionIndex);
            const oIdx = parseInt(opt.dataset.optionIndex);
            const multiSelect = opt.dataset.multiSelect === 'true';

            const modalState = questionModals.get(tabId);
            if (!modalState) return;
            const answers = modalState.selectedAnswers.get(qIdx);
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
            updateOptionUI(qIdx, tabId);
        });
    });

    overlay.querySelector('#questionCancelBtn').addEventListener('click', () => {
        // Enviar respuesta vacía para desbloquear el backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            const emptyResponses = questions.map(q => q.multiSelect ? [] : null);
            ws.send(JSON.stringify({ type: 'question_response', responses: emptyResponses, cancelled: true }));
        }
        addSystemMessage('Pregunta cancelada', tabId);
        hideAskUserQuestion(tabId);
    });

    overlay.querySelector('#questionSubmitBtn').addEventListener('click', () => {
        const modalState = questionModals.get(tabId);
        if (!modalState) return;
        const { questions, selectedAnswers, ws, tabId: modalTabId } = modalState;

        const responses = questions.map((q, qIdx) => {
            const selected = Array.from(selectedAnswers.get(qIdx));
            const selectedLabels = selected.map(oIdx => q.options[oIdx].label);
            return q.multiSelect ? selectedLabels : (selectedLabels[0] || null);
        });

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

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'question_response', responses }));
        }

        addMessage('user', responseText, tabId);

        const tab = state.tabs.get(tabId);
        if (tab) {
            tab.renderedMessages.push({ type: 'user', content: responseText });
            saveTabs();
        }

        showLoading(tabId);
        hideAskUserQuestion(tabId);
    });
}

function updateOptionUI(qIdx, tabId) {
    const modalState = questionModals.get(tabId);
    if (!modalState) return;
    const { overlay, selectedAnswers, questions } = modalState;
    const answers = selectedAnswers.get(qIdx);
    const multiSelect = questions[qIdx].multiSelect;

    const options = overlay.querySelectorAll(`.question-option[data-question-index="${qIdx}"]`);
    options.forEach(opt => {
        const oIdx = parseInt(opt.dataset.optionIndex);
        const isSelected = answers.has(oIdx);
        opt.classList.toggle('selected', isSelected);

        const preview = overlay.querySelector(`.question-preview[data-preview-for="${qIdx}-${oIdx}"]`);
        if (preview) {
            preview.style.display = isSelected ? 'block' : 'none';
        }

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

export function hideAskUserQuestion(tabId) {
    const modalState = questionModals.get(tabId);
    if (modalState) {
        modalState.overlay.remove();
        questionModals.delete(tabId);
    }
}

// ===== Tool Approval =====

// (approvalModals Map already declared at top)

function getToolDisplayInfo(toolName, input) {
    if (toolName === 'Bash') {
        return {
            title: 'Ejecutar comando',
            detail: input.command || '',
            description: input.description || ''
        };
    } else if (toolName === 'Write') {
        return {
            title: 'Escribir archivo',
            detail: input.file_path || '',
            description: ''
        };
    } else if (toolName === 'Edit') {
        return {
            title: 'Editar archivo',
            detail: input.file_path || '',
            description: ''
        };
    }
    return {
        title: toolName,
        detail: JSON.stringify(input).substring(0, 200),
        description: ''
    };
}

export function showToolApproval(toolName, input, tabId, ws) {
    hideToolApproval(tabId);

    const info = getToolDisplayInfo(toolName, input);

    const overlay = document.createElement('div');
    overlay.className = 'question-overlay';
    overlay.id = 'toolApprovalOverlay';

    overlay.innerHTML = `
        <div class="question-modal">
            <div class="question-header">
                <span class="question-chip">${escapeHtml(toolName)}</span>
            </div>
            <div class="question-text">${escapeHtml(info.title)}</div>
            ${info.description ? `<div style="color: var(--text-secondary); font-size: 13px; margin-bottom: var(--spacing-sm);">${escapeHtml(info.description)}</div>` : ''}
            <div class="question-preview" style="display:block">${escapeHtml(info.detail)}</div>
            <div class="question-actions">
                <button class="question-btn question-btn-deny" id="approvalDenyBtn">
                    Denegar
                </button>
                <button class="question-btn question-btn-allow" id="approvalAllowBtn">
                    Permitir
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    approvalModals.set(tabId, { overlay, ws, tabId });

    overlay.querySelector('#approvalAllowBtn').addEventListener('click', () => {
        sendApprovalResponse(true);
    });

    overlay.querySelector('#approvalDenyBtn').addEventListener('click', () => {
        sendApprovalResponse(false);
    });

    function sendApprovalResponse(allow) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'tool_approval_response', allow }));
        }
        addSystemMessage(`${toolName}: ${allow ? 'Permitido' : 'Denegado'}`, tabId);
        showLoading(tabId);
        hideToolApproval(tabId);
    }
}

export function hideToolApproval(tabId) {
    const modalState = approvalModals.get(tabId);
    if (modalState) {
        modalState.overlay.remove();
        approvalModals.delete(tabId);
    }
}

// ===== File View (Plan Viewer) =====

// (fileViewModals Map already declared at top)

export function showFileView(filePath, content, tabId, ws) {
    hideFileView(tabId);

    const fileName = filePath.split('/').pop().split('\\').pop();

    const overlay = document.createElement('div');
    overlay.className = 'question-overlay';
    overlay.id = 'fileViewOverlay';

    overlay.innerHTML = `
        <div class="question-modal file-view-modal">
            <div class="question-header">
                <span class="question-chip">Plan</span>
                <span class="file-view-path">${escapeHtml(filePath)}</span>
            </div>
            <div class="file-view-content markdown-content">
                ${marked.parse(content)}
            </div>
            <div class="question-actions">
                <button class="question-btn question-btn-deny" id="fileViewRejectBtn">
                    Rechazar
                </button>
                <button class="question-btn question-btn-allow" id="fileViewApproveBtn">
                    Aprobar
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    fileViewModals.set(tabId, { overlay, ws, tabId });

    overlay.querySelector('#fileViewApproveBtn').addEventListener('click', () => {
        sendFileViewResponse(true);
    });

    overlay.querySelector('#fileViewRejectBtn').addEventListener('click', () => {
        sendFileViewResponse(false);
    });

    function sendFileViewResponse(allow) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'tool_approval_response', allow }));
        }
        addSystemMessage(`Plan: ${allow ? 'Aprobado' : 'Rechazado'}`, tabId);
        if (allow) showLoading(tabId);
        hideFileView(tabId);
    }
}

export function hideFileView(tabId) {
    const modalState = fileViewModals.get(tabId);
    if (modalState) {
        modalState.overlay.remove();
        fileViewModals.delete(tabId);
    }
}

// ===== Cleanup =====

export function cleanupTabModals(tabId) {
    hideAskUserQuestion(tabId);
    hideToolApproval(tabId);
    hideFileView(tabId);
}

export function hasPendingQuestionModal(tabId) {
    return questionModals.has(tabId);
}

export function getPendingQuestion(tabId) {
    return questionModals.get(tabId);
}
