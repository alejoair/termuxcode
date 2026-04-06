// ===== Modal Tool Approval =====

import { addSystemMessage, showLoading } from './ui.js';
import { escapeHtml, createOverlay, showModal, hideModal } from './modal-utils.js';

// Map tabId -> modal state
const approvalModals = new Map();

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

    const overlay = createOverlay('toolApprovalOverlay');

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

    showModal(overlay);
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
    hideModal(approvalModals, tabId);
}
