// ===== Settings Modal =====

import { state } from './state.js';
import { saveSettings } from './storage.js';

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = String(text ?? '');
    return div.innerHTML;
}

let overlay = null;

export function showSettingsModal() {
    if (overlay) return;

    const s = state.settings;

    overlay = document.createElement('div');
    overlay.className = 'question-overlay';

    overlay.innerHTML = `
        <div class="question-modal settings-modal">
            <div class="question-header">
                <span class="question-chip">Configuración</span>
            </div>

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
                <input class="settings-input" id="cfg-model" type="text" placeholder="sonnet (por defecto)" value="${escapeHtml(s.model)}">
            </div>

            <div class="settings-field">
                <label class="settings-label">Máximo de turnos</label>
                <input class="settings-input" id="cfg-max_turns" type="number" min="1" placeholder="Sin límite" value="${escapeHtml(s.max_turns)}">
            </div>

            <div class="settings-field">
                <label class="settings-label">Herramientas permitidas <span class="settings-hint">(separadas por coma)</span></label>
                <input class="settings-input" id="cfg-allowed_tools" type="text" placeholder="Bash,Edit,Read,..." value="${escapeHtml(s.allowed_tools)}">
            </div>

            <div class="settings-field">
                <label class="settings-label">Herramientas bloqueadas <span class="settings-hint">(separadas por coma)</span></label>
                <input class="settings-input" id="cfg-disallowed_tools" type="text" placeholder="WebSearch,..." value="${escapeHtml(s.disallowed_tools)}">
            </div>

            <div class="settings-field">
                <label class="settings-label">System prompt</label>
                <textarea class="settings-textarea" id="cfg-system_prompt" rows="3" placeholder="Instrucciones globales para el agente...">${escapeHtml(s.system_prompt)}</textarea>
            </div>

            <div class="settings-field">
                <label class="settings-label">Append system prompt</label>
                <textarea class="settings-textarea" id="cfg-append_system_prompt" rows="3" placeholder="Se añade al system prompt existente...">${escapeHtml(s.append_system_prompt)}</textarea>
            </div>

            <div class="settings-note">Los cambios se aplican en la próxima conexión.</div>

            <div class="question-actions">
                <button class="question-btn question-btn-cancel" id="settingsCancelBtn">Cancelar</button>
                <button class="question-btn question-btn-submit" id="settingsSaveBtn">Guardar</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    overlay.querySelector('#cfg-permission_mode').value = s.permission_mode || 'acceptEdits';

    overlay.querySelector('#settingsCancelBtn').addEventListener('click', hideSettingsModal);
    overlay.querySelector('#settingsSaveBtn').addEventListener('click', () => {
        state.settings.permission_mode = overlay.querySelector('#cfg-permission_mode').value;
        state.settings.model = overlay.querySelector('#cfg-model').value.trim();
        state.settings.max_turns = overlay.querySelector('#cfg-max_turns').value.trim();
        state.settings.allowed_tools = overlay.querySelector('#cfg-allowed_tools').value.trim();
        state.settings.disallowed_tools = overlay.querySelector('#cfg-disallowed_tools').value.trim();
        state.settings.system_prompt = overlay.querySelector('#cfg-system_prompt').value;
        state.settings.append_system_prompt = overlay.querySelector('#cfg-append_system_prompt').value;
        saveSettings();
        hideSettingsModal();
    });
}

export function hideSettingsModal() {
    if (overlay) {
        overlay.remove();
        overlay = null;
    }
}
