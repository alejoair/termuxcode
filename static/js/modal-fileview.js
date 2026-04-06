// ===== Modal File View (Plan Viewer) =====

import { state } from './state.js';
import { saveTabs } from './storage.js';
import { addSystemMessage, showLoading, updatePlanButton } from './ui.js';
import { escapeHtml, createOverlay, showModal, hideModal } from './modal-utils.js';

// Map tabId -> modal state
const fileViewModals = new Map();

export function showFileView(filePath, content, tabId, ws) {
    hideFileView(tabId);

    const fileName = filePath.split('/').pop().split('\\').pop();

    const overlay = createOverlay('fileViewOverlay');

    overlay.innerHTML = `
        <div class="question-modal file-view-modal">
            <div class="question-header">
                <span class="question-chip">Plan</span>
                <span class="file-view-path">${escapeHtml(filePath)}</span>
            </div>
            <div class="file-view-content markdown-content">
                ${window.DOMPurify ? window.DOMPurify.sanitize(marked.parse(content)) : marked.parse(content)}
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

    showModal(overlay);
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

        // Guardar el plan en el tab si fue aprobado
        if (allow) {
            const tab = state.tabs.get(tabId);
            if (tab) {
                tab.plan = { filePath, content };
                saveTabs();
                updatePlanButton();
            }
            showLoading(tabId);
        }
        hideFileView(tabId);
    }
}

export function hideFileView(tabId) {
    hideModal(fileViewModals, tabId);
}

// ===== Plan Viewer (solo lectura) =====

export function showPlanViewer(tabId) {
    console.log('[PlanViewer] Opening for tabId:', tabId);
    const tab = state.tabs.get(tabId);
    console.log('[PlanViewer] Tab found:', tab);
    console.log('[PlanViewer] Tab plan:', tab?.plan);
    if (!tab || !tab.plan) {
        console.warn('[PlanViewer] No tab or no plan found');
        return;
    }

    const { filePath, content } = tab.plan;
    const fileName = filePath.split('/').pop().split('\\').pop();

    const overlay = createOverlay('planViewerOverlay');

    overlay.innerHTML = `
        <div class="question-modal file-view-modal">
            <div class="question-header">
                <span class="question-chip">Plan</span>
                <span class="file-view-path">${escapeHtml(filePath)}</span>
            </div>
            <div class="file-view-content markdown-content">
                ${window.DOMPurify ? window.DOMPurify.sanitize(marked.parse(content)) : marked.parse(content)}
            </div>
            <div class="question-actions">
                <button class="question-btn question-btn-submit" id="planViewerCloseBtn">
                    Cerrar
                </button>
            </div>
        </div>
    `;

    showModal(overlay);

    overlay.querySelector('#planViewerCloseBtn').addEventListener('click', () => {
        overlay.remove();
    });

    // Cerrar al hacer clic fuera del modal
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}
