// ===== Composable: Gestión de Mensajes =====

import { ref, computed, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const MAX_RENDERED_MESSAGES = 200;

/**
 * Myers diff O(ND) — retorna diff de líneas.
 * [{type: 'equal'|'remove'|'add', oldLine: number, newLine: number, content: string}]
 * oldLine/newLine son 0-based (null si no aplica al lado).
 */
export function computeLineDiff(oldStr, newStr) {
    const oldLines = (oldStr || '').split('\n');
    const newLines = (newStr || '').split('\n');
    if (oldLines.length > 0 && oldLines[oldLines.length - 1] === '') oldLines.pop();
    if (newLines.length > 0 && newLines[newLines.length - 1] === '') newLines.pop();

    const N = oldLines.length;
    const M = newLines.length;
    const MAX = N + M;
    if (MAX === 0) return [];

    // Myers algorithm
    const V = new Array(2 * MAX + 1);
    const trace = [];
    V[MAX + 1] = 0;

    outer:
    for (let D = 0; D <= MAX; D++) {
        const v = new Array(2 * MAX + 1);
        for (let k = -D; k <= D; k += 2) {
            let x;
            if (k === -D || (k !== D && V[MAX + k - 1] < V[MAX + k + 1])) {
                x = V[MAX + k + 1]; // down (add)
            } else {
                x = V[MAX + k - 1] + 1; // right (remove)
            }
            let y = x - k;
            while (x < N && y < M && oldLines[x] === newLines[y]) {
                x++; y++;
            }
            v[MAX + k] = x;
            if (x >= N && y >= M) {
                trace.push(v.slice());
                break outer;
            }
        }
        trace.push(v.slice());
        for (let i = 0; i < v.length; i++) V[i] = v[i] ?? V[i];
    }

    // Backtrack to get edit script
    let x = N, y = M;
    const edits = [];
    for (let D = trace.length - 1; D > 0; D--) {
        const v = trace[D];
        const vPrev = trace[D - 1];
        let k = x - y;
        let prevK;
        if (k === -D || (k !== D && (vPrev[MAX + k - 1] ?? 0) < (vPrev[MAX + k + 1] ?? 0))) {
            prevK = k + 1; // down (add)
        } else {
            prevK = k - 1; // right (remove)
        }

        const prevX = vPrev[MAX + prevK] ?? 0;
        const prevY = prevX - prevK;

        // Diagonal (equal)
        while (x > prevX && y > prevY) {
            x--; y--;
            edits.push({ type: 'equal', oldLine: x, newLine: y });
        }

        if (D > 0) {
            if (x === prevX) {
                y--;
                edits.push({ type: 'add', oldLine: null, newLine: y, content: newLines[y] });
            } else {
                x--;
                edits.push({ type: 'remove', oldLine: x, newLine: null, content: oldLines[x] });
            }
        }
    }
    // Remaining diagonal at D=0
    while (x > 0 && y > 0) {
        x--; y--;
        edits.push({ type: 'equal', oldLine: x, newLine: y });
    }

    edits.reverse();

    // Fill content for equal lines
    for (const e of edits) {
        if (e.type === 'equal') {
            e.content = oldLines[e.oldLine];
        }
    }

    return edits;
}

/**
 * Computa líneas de diff entre old_string y new_string (formato legacy para MessageList).
 * Retorna array de { type: 'context'|'remove'|'add', sign: ' '|'-'|'+', lineNum, content }
 */
export function computeDiffLines(oldStr, newStr) {
    const lines = computeLineDiff(oldStr, newStr);
    const result = [];
    let lastType = null;

    for (const line of lines) {
        // Add context line before change block (1 line)
        if ((line.type === 'remove' || line.type === 'add') && lastType === 'equal') {
            const prev = result[result.length - 1];
            if (prev && prev.type === 'context') {
                // already there from last equal
            }
        }

        switch (line.type) {
            case 'equal':
                result.push({ type: 'context', sign: ' ', lineNum: (line.oldLine ?? 0) + 1, content: line.content });
                break;
            case 'remove':
                result.push({ type: 'remove', sign: '-', lineNum: (line.oldLine ?? 0) + 1, content: line.content });
                break;
            case 'add':
                result.push({ type: 'add', sign: '+', lineNum: (line.newLine ?? 0) + 1, content: line.content });
                break;
        }
        lastType = line.type;
    }

    return result;
}

export function useMessages() {
    const messagesContainer = ref(null);

    /**
     * Renderiza markdown de forma segura (DOMPurify + marked)
     */
    function safeMarkdown(text) {
        if (typeof text !== 'string') return '';

        try {
            const raw = window.marked ? window.marked.parse(text) : text;
            return window.DOMPurify ? window.DOMPurify.sanitize(raw) : raw;
        } catch (e) {
            console.error('[useMessages] Error rendering markdown:', e);
            return text;
        }
    }

    /**
     * Escapa HTML para inyección segura
     */
    function escapeHtml(text) {
        if (typeof text !== 'string') text = String(text);
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Procesa bloques de mensajes del asistente
     */
    function processAssistantBlocks(blocks) {
        if (!blocks || !Array.isArray(blocks)) return [];

        return blocks.map(block => {
            switch (block.type) {
                case 'text':
                    return {
                        type: 'text',
                        content: block.text || '',
                        html: safeMarkdown(block.text || ''),
                    };

                case 'tool_use':
                    return {
                        type: 'tool_use',
                        id: block.id,
                        name: block.name,
                        input: block.input,
                        info: getToolInfo(block.name, block.input),
                    };

                case 'thinking':
                    return {
                        type: 'thinking',
                        content: block.thinking || '',
                    };

                default:
                    return {
                        type: 'unknown',
                        ...block,
                    };
            }
        });
    }

    /**
     * Obtiene información resumida de un tool use
     */
    function getToolInfo(name, input) {
        if (!input) return '';

        switch (name) {
            case 'Bash':
                return input.command || input.description || '';

            case 'Read':
            case 'Write':
            case 'Edit':
                return input.file_path || '';

            case 'Grep':
                const pattern = input.pattern || '';
                const path = input.path ? `  ${input.path}` : '';
                return `${pattern}${path}`;

            case 'Glob':
                return input.pattern || '';

            case 'AskUserQuestion':
                return 'Pregunta al usuario';

            default:
                return JSON.stringify(input);
        }
    }

    /**
     * Procesa bloques de resultado de tool
     */
    function processToolResultBlocks(blocks) {
        if (!blocks || !Array.isArray(blocks)) return [];

        const results = blocks
            .filter(block => block.type === 'tool_result')
            .map(block => ({
                type: 'tool_result',
                toolUseId: block.tool_use_id,
                content: formatToolResult(block.content),
                is_error: block.is_error || false,
            }));

        return results;
    }

    /**
     * Formatea el contenido de un resultado
     */
    function formatToolResult(content) {
        if (typeof content === 'string') return content;
        if (content === null || content === undefined) return '';
        return JSON.stringify(content, null, 2);
    }

    /**
     * Trunca mensajes para no exceder el máximo
     */
    function trimMessages(messages) {
        if (!messages || messages.length <= MAX_RENDERED_MESSAGES) return messages;

        return messages.slice(-MAX_RENDERED_MESSAGES);
    }

    /**
     * Agrega un mensaje al buffer del tab
     */
    function addMessageToTab(tab, message) {
        if (!tab) return false;

        if (!tab.messages) {
            tab.messages = [];
        }

        tab.messages.push(message);

        // También agregar a renderedMessages
        if (!tab.renderedMessages) {
            tab.renderedMessages = [];
        }

        // Manejo especial para tool_result: agrupar con su tool_use
        if (message.type === 'tool_result') {
            const toolUseIndex = tab.renderedMessages.findIndex(
                msg => msg.type === 'tool_use' && msg.id === message.toolUseId
            );

            if (toolUseIndex !== -1) {
                const existingToolUse = tab.renderedMessages[toolUseIndex];
                tab.renderedMessages.splice(toolUseIndex, 1, {
                    ...existingToolUse,
                    result: message.content,
                    resultIsError: message.is_error,
                });
            } else {
                tab.renderedMessages.push(message);
            }
        }
        // No agregar result (ya se procesan sus bloques arriba)
        else if (message.type !== 'result') {
            tab.renderedMessages.push(message);
        }

        // Truncar si excede máximo
        tab.renderedMessages = trimMessages(tab.renderedMessages);

        return true;
    }

    /**
     * Limpia todos los mensajes de un tab
     */
    function clearTabMessages(tab) {
        if (!tab) return false;

        tab.messages = [];
        tab.renderedMessages = [];
        return true;
    }

    /**
     * Scrollea al final del contenedor
     */
    async function scrollToBottom() {
        await nextTick();

        if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
    }

    /**
     * Extrae pregunta de usuario de un mensaje
     */
    function extractAskUserQuestion(data) {
        if (data.type === 'ask_user_question' && data.questions) {
            return data.questions;
        }
        return null;
    }

    /**
     * Extrae solicitud de aprobación de tool
     */
    function extractToolApproval(data) {
        if (data.type === 'tool_approval_request') {
            return {
                toolName: data.tool_name,
                input: data.input,
            };
        }
        return null;
    }

    /**
     * Extrae file view
     */
    function extractFileView(data) {
        if (data.type === 'file_view') {
            return {
                filePath: data.file_path,
                content: data.content,
            };
        }
        return null;
    }

    /**
     * Verifica si un mensaje es loading-trigger
     */
    function shouldTriggerLoading(data) {
        if (data.type === 'assistant' && data.blocks) {
            return data.blocks.some(b => b.type === 'tool_use');
        }
        return false;
    }

    /**
     * Verifica si un mensaje es resultado final
     */
    function isFinalResult(data) {
        return data.type === 'result';
    }

    return {
        messagesContainer,
        safeMarkdown,
        escapeHtml,
        processAssistantBlocks,
        processToolResultBlocks,
        getToolInfo,
        formatToolResult,
        trimMessages,
        addMessageToTab,
        clearTabMessages,
        scrollToBottom,
        extractAskUserQuestion,
        extractToolApproval,
        extractFileView,
        shouldTriggerLoading,
        isFinalResult,
        computeDiffLines,
    };
}
