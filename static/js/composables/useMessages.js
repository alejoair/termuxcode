// ===== Composable: Gestión de Mensajes =====

import { ref, computed, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const MAX_RENDERED_MESSAGES = 200;

/**
 * Computa líneas de diff entre old_string y new_string.
 * Retorna array de { type: 'context'|'remove'|'add', sign: ' '|'-'|'+', lineNum, content }
 */
export function computeDiffLines(oldStr, newStr) {
    const oldLines = (oldStr || '').split('\n');
    const newLines = (newStr || '').split('\n');

    // Strip trailing empty line from trailing newline
    if (oldLines.length > 1 && oldLines[oldLines.length - 1] === '') oldLines.pop();
    if (newLines.length > 1 && newLines[newLines.length - 1] === '') newLines.pop();

    const result = [];

    // Find common prefix length
    let prefixLen = 0;
    const minLen = Math.min(oldLines.length, newLines.length);
    while (prefixLen < minLen && oldLines[prefixLen] === newLines[prefixLen]) {
        prefixLen++;
    }

    // Find common suffix length (don't overlap with prefix)
    let suffixLen = 0;
    while (
        suffixLen < (oldLines.length - prefixLen) &&
        suffixLen < (newLines.length - prefixLen) &&
        oldLines[oldLines.length - 1 - suffixLen] === newLines[newLines.length - 1 - suffixLen]
    ) {
        suffixLen++;
    }

    const contextBefore = Math.min(1, prefixLen);
    const contextAfter = Math.min(1, suffixLen);

    // Context lines before the change
    for (let i = prefixLen - contextBefore; i < prefixLen; i++) {
        if (i >= 0) {
            result.push({ type: 'context', sign: ' ', lineNum: i + 1, content: oldLines[i] });
        }
    }

    // Removed lines
    const removeStart = prefixLen;
    const removeEnd = oldLines.length - suffixLen;
    for (let i = removeStart; i < removeEnd; i++) {
        result.push({ type: 'remove', sign: '-', lineNum: i + 1, content: oldLines[i] });
    }

    // Added lines
    const addStart = prefixLen;
    const addEnd = newLines.length - suffixLen;
    for (let i = addStart; i < addEnd; i++) {
        result.push({ type: 'add', sign: '+', lineNum: i + 1, content: newLines[i] });
    }

    // Context lines after the change
    for (let i = oldLines.length - suffixLen; i < oldLines.length - suffixLen + contextAfter; i++) {
        if (i < oldLines.length) {
            result.push({ type: 'context', sign: ' ', lineNum: i + 1, content: oldLines[i] });
        }
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
