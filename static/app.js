// ===== termux-code - Entry Point =====

import { state, dom, DEFAULT_SETTINGS, AVAILABLE_TOOLS } from './js/state.js';
import { createTab, switchTab, loadTabs, send, sendStop, sendDisconnect, clearChat } from './js/tabs.js';
import { connectTab, disconnectTab } from './js/connection.js';
import { saveTabs } from './js/storage.js';
import { initPipeline } from './js/pipeline.js';
import { initInputFeedback } from './js/input-feedback.js';
import { initScrollFeedback } from './js/scroll-feedback.js';
import { initNotifications } from './js/notifications.js';

// Inicializar Framework7
const f7 = new Framework7({
    el: '#app',
    name: 'termux-code',
    theme: 'auto',
});

async function init() {
    loadTabs();
    initNotifications();

    if (state.tabs.size === 0) {
        await createTab('Chat 1');
    } else {
        const firstTab = state.tabs.keys().next().value;
        switchTab(firstTab);
    }

    dom.input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') send();
    });
}

// Funciones globales (onclick desde HTML)
window.createNewTab = () => createTab();
window.send = send;
window.sendStop = sendStop;
window.sendDisconnect = sendDisconnect;
window.clearChat = clearChat;
window.openSettings = openSettings;
window.changeModel = (model) => {
    const tab = state.tabs.get(state.activeTabId);
    if (tab) {
        tab.settings.model = model;
        saveTabs();
        disconnectTab(state.activeTabId);
        connectTab(state.activeTabId);
    }
};

function openSettings() {
    if (document.getElementById('settingsOverlay')) return;

    const tab = state.tabs.get(state.activeTabId);
    if (!tab) return;
    const s = tab.settings || { ...DEFAULT_SETTINGS };
    const esc = t => { const d = document.createElement('div'); d.textContent = String(t ?? ''); return d.innerHTML; };

    // Generar checkboxes de tools
    const selectedTools = s.tools || [];
    const toolsCheckboxes = AVAILABLE_TOOLS.map(tool => {
        const checked = selectedTools.includes(tool.name) ? 'checked' : '';
        return `
            <label class="tools-checkbox-label" title="${esc(tool.desc)}">
                <input type="checkbox" class="tools-checkbox" value="${esc(tool.name)}" ${checked}>
                <span class="tools-checkbox-name">${esc(tool.name)}</span>
            </label>
        `;
    }).join('');

    const overlay = document.createElement('div');
    overlay.id = 'settingsOverlay';
    overlay.className = 'question-overlay';
    overlay.innerHTML = `
        <div class="question-modal settings-modal">
            <div class="question-header"><span class="question-chip">Configuración</span></div>
            <div class="settings-field">
                <label class="settings-label">Modo de permisos</label>
                <select class="settings-select" id="cfg-permission_mode">
                    <option value="default">default</option>
                    <option value="acceptEdits">acceptEdits</option>
                    <option value="plan">plan</option>
                    <option value="bypassPermissions">bypassPermissions</option>
                </select>
            </div>
            <div class="settings-field">
                <label class="settings-label">Modelo</label>
                <select class="settings-select" id="cfg-model">
                    <option value="sonnet">sonnet</option>
                    <option value="opus">opus</option>
                    <option value="haiku">haiku</option>
                </select>
            </div>
            <div class="settings-field">
                <label class="settings-label">Máximo de turnos</label>
                <input class="settings-input" id="cfg-max_turns" type="number" min="1" placeholder="Sin límite" value="${esc(s.max_turns)}">
            </div>
            <div class="settings-field">
                <label class="settings-label">Ventana de historial <span class="settings-hint">(mensajes a conservar)</span></label>
                <input class="settings-input" id="cfg-rolling_window" type="number" min="10" placeholder="100" value="${esc(s.rolling_window)}">
            </div>
            <div class="settings-field">
                <label class="settings-label">Herramientas disponibles <span class="settings-hint">(dejar vacío = todas)</span></label>
                <div class="tools-checkbox-grid">
                    ${toolsCheckboxes}
                </div>
            </div>
            <div class="settings-field">
                <label class="settings-label">Herramientas permitidas <span class="settings-hint">(separadas por coma)</span></label>
                <input class="settings-input" id="cfg-allowed_tools" type="text" placeholder="Bash,Edit,Read,..." value="${esc(s.allowed_tools)}">
            </div>
            <div class="settings-field">
                <label class="settings-label">Herramientas bloqueadas <span class="settings-hint">(separadas por coma)</span></label>
                <input class="settings-input" id="cfg-disallowed_tools" type="text" placeholder="WebSearch,..." value="${esc(s.disallowed_tools)}">
            </div>
            <div class="settings-field">
                <label class="settings-label">System prompt</label>
                <textarea class="settings-textarea" id="cfg-system_prompt" rows="3">${esc(s.system_prompt)}</textarea>
            </div>
            <div class="settings-field">
                <label class="settings-label">Append system prompt</label>
                <textarea class="settings-textarea" id="cfg-append_system_prompt" rows="3">${esc(s.append_system_prompt)}</textarea>
            </div>
            <div class="settings-note">Los cambios se aplican en la próxima conexión.</div>
            <div class="question-actions">
                <button class="question-btn question-btn-cancel" id="settingsCancelBtn">Cancelar</button>
                <button class="question-btn question-btn-submit" id="settingsSaveBtn">Guardar</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('#cfg-permission_mode').value = s.permission_mode || 'bypassPermissions';
    overlay.querySelector('#cfg-model').value = s.model || 'sonnet';
    overlay.querySelector('#settingsCancelBtn').onclick = () => overlay.remove();
    overlay.querySelector('#settingsSaveBtn').onclick = () => {
        // Recopilar tools seleccionados
        const selectedTools = Array.from(overlay.querySelectorAll('.tools-checkbox:checked')).map(cb => cb.value);

        tab.settings = {
            permission_mode: overlay.querySelector('#cfg-permission_mode').value,
            model: overlay.querySelector('#cfg-model').value,
            max_turns: overlay.querySelector('#cfg-max_turns').value.trim(),
            rolling_window: parseInt(overlay.querySelector('#cfg-rolling_window').value) || 100,
            tools: selectedTools,
            allowed_tools: overlay.querySelector('#cfg-allowed_tools').value.trim(),
            disallowed_tools: overlay.querySelector('#cfg-disallowed_tools').value.trim(),
            system_prompt: overlay.querySelector('#cfg-system_prompt').value,
            append_system_prompt: overlay.querySelector('#cfg-append_system_prompt').value,
        };
        saveTabs();
        overlay.remove();
        disconnectTab(state.activeTabId);
        connectTab(state.activeTabId);
    };
}

// ===== Typewriter effect en header =====
function initTypewriter() {
    const titleEl = document.querySelector('.terminal-title');
    const TEXT = 'TERMUX-CODE';
    let interval = null;
    let charIndex = 0;

    function getTextNode() {
        // El texto está entre el span.terminal-prompt y span.terminal-cursor
        for (const node of titleEl.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) return node;
        }
        return null;
    }

    function startTyping() {
        if (interval) return;
        charIndex = 0;
        const textNode = getTextNode();
        if (!textNode) return;
        textNode.textContent = ' ';
        interval = setInterval(() => {
            charIndex++;
            if (charIndex > TEXT.length) {
                charIndex = 0;
                textNode.textContent = ' ';
            } else {
                textNode.textContent = ' ' + TEXT.substring(0, charIndex);
            }
        }, 120);
    }

    function stopTyping() {
        if (!interval) return;
        clearInterval(interval);
        interval = null;
        const textNode = getTextNode();
        if (textNode) textNode.textContent = ' ' + TEXT;
    }

    window.setHeaderWorking = function(val) {
        if (val) startTyping(); else stopTyping();
    };
}

init();
initPipeline();
initTypewriter();
initInputFeedback();
initScrollFeedback();
