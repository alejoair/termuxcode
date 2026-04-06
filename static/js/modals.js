// ===== Barrel export para modales =====
// Mantiene la API pública compatible con ui.js

import { hideAskUserQuestion } from './modal-question.js';
import { hideToolApproval } from './modal-approval.js';
import { hideFileView } from './modal-fileview.js';

// Re-exportar desde modal-question.js
export {
    showAskUserQuestion,
    hideAskUserQuestion,
    renderAskUserQuestionInChat,
    hasPendingQuestionModal,
    getPendingQuestion,
    migrateQuestionModal
} from './modal-question.js';

// Re-exportar desde modal-approval.js
export {
    showToolApproval,
    hideToolApproval
} from './modal-approval.js';

// Re-exportar desde modal-fileview.js
export {
    showFileView,
    hideFileView,
    showPlanViewer
} from './modal-fileview.js';

// Cleanup function que limpia todos los modales de un tab
export function cleanupTabModals(tabId) {
    hideAskUserQuestion(tabId);
    hideToolApproval(tabId);
    hideFileView(tabId);
}
