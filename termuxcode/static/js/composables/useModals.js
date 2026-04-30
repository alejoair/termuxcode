// ===== Composable: Gestión de Modales =====

import { reactive, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export function useModals() {
    // Estado de modales
    const state = reactive({
        question: null,      // { questions, tabId, ws }
        approval: null,      // { toolName, input, tabId, ws }
        mcp: null,           // { tabId, ws }
        settings: null,      // { tabId }
        fileView: null,      // { filePath, content, tabId, ws }
        plan: null,          // { plan, tabId }
    });

    // Computed
    const hasModalOpen = computed(() => {
        return !!(state.question || state.approval || state.mcp ||
                  state.settings || state.fileView || state.plan);
    });

    // Question Modal
    function showQuestionModal(questions, tabId, ws) {
        state.question = {
            questions: questions.map(q => ({
                question: q.question,
                header: q.header || '',
                options: q.options || [],
                multiSelect: q.multiSelect || false,
            })),
            tabId,
            ws,
            selectedAnswers: new Map(),
        };
    }

    function hideQuestionModal() {
        state.question = null;
    }

    function setQuestionAnswer(questionIndex, answerIndex) {
        if (!state.question) return;

        const question = state.question.questions[questionIndex];
        if (question.multiSelect) {
            // Multi-select: toggle
            const current = state.question.selectedAnswers.get(questionIndex) || [];
            if (current.includes(answerIndex)) {
                state.question.selectedAnswers.set(
                    questionIndex,
                    current.filter(i => i !== answerIndex)
                );
            } else {
                state.question.selectedAnswers.set(questionIndex, [...current, answerIndex]);
            }
        } else {
            // Single-select: replace
            state.question.selectedAnswers.set(questionIndex, answerIndex);
        }
    }

    function submitQuestionAnswers() {
        if (!state.question) return null;

        const result = {
            responses: Array.from(state.question.selectedAnswers.entries()).map(([qIdx, answer]) => {
                const question = state.question.questions[qIdx];
                return {
                    question: question.question,
                    answers: Array.isArray(answer) ? answer : [answer],
                };
            }),
            cancelled: false,
        };

        hideQuestionModal();
        return result;
    }

    function cancelQuestionAnswers() {
        hideQuestionModal();
        return { cancelled: true };
    }

    // Approval Modal
    function showApprovalModal(toolName, input, tabId, ws) {
        state.approval = {
            toolName,
            input: JSON.stringify(input, null, 2),
            tabId,
            ws,
        };
    }

    function hideApprovalModal() {
        state.approval = null;
    }

    // MCP Modal
    function showMcpModal(tabId, ws) {
        state.mcp = {
            tabId,
            ws,
        };
    }

    function hideMcpModal() {
        state.mcp = null;
    }

    // Settings Modal
    function showSettingsModal(tabId) {
        state.settings = {
            tabId,
        };
    }

    function hideSettingsModal() {
        state.settings = null;
    }

    // File View Modal
    function showFileViewModal(filePath, content, tabId, ws) {
        state.fileView = {
            filePath,
            content,
            tabId,
            ws,
        };
    }

    function hideFileViewModal() {
        state.fileView = null;
    }

    // Plan Modal
    function showPlanModal(plan, tabId) {
        state.plan = {
            plan,
            tabId,
        };
    }

    function hidePlanModal() {
        state.plan = null;
    }

    // Cerrar todos
    function closeAll() {
        state.question = null;
        state.approval = null;
        state.mcp = null;
        state.settings = null;
        state.fileView = null;
        state.plan = null;
    }

    return {
        state,
        hasModalOpen,

        // Question
        showQuestionModal,
        hideQuestionModal,
        setQuestionAnswer,
        submitQuestionAnswers,
        cancelQuestionAnswers,

        // Approval
        showApprovalModal,
        hideApprovalModal,

        // MCP
        showMcpModal,
        hideMcpModal,

        // Settings
        showSettingsModal,
        hideSettingsModal,

        // File View
        showFileViewModal,
        hideFileViewModal,

        // Plan
        showPlanModal,
        hidePlanModal,

        // General
        closeAll,
    };
}
