// ===== termux-code - Entry Point =====

import { state, dom, DEFAULT_SETTINGS } from './js/state.js';
import { createTab, switchTab, loadTabs, send, sendStop, sendDisconnect, clearChat } from './js/tabs.js';
import { connectTab, disconnectTab } from './js/connection.js';
import { saveTabs } from './js/storage.js';

// Inicializar Framework7
const f7 = new Framework7({
    el: '#app',
    name: 'termux-code',
    theme: 'auto',
});

async function init() {
    loadTabs();

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
                    <option value="glm-5">glm-5</option>
                    <option value="glm-5.1">glm-5.1</option>
                    <option value="glm-5-turbo">glm-5-turbo</option>
                </select>
            </div>
            <div class="settings-field">
                <label class="settings-label">Máximo de turnos</label>
                <input class="settings-input" id="cfg-max_turns" type="number" min="1" placeholder="Sin límite" value="${esc(s.max_turns)}">
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
    overlay.querySelector('#cfg-permission_mode').value = s.permission_mode || 'acceptEdits';
    overlay.querySelector('#cfg-model').value = s.model || 'glm-5';
    overlay.querySelector('#settingsCancelBtn').onclick = () => overlay.remove();
    overlay.querySelector('#settingsSaveBtn').onclick = () => {
        tab.settings = {
            permission_mode: overlay.querySelector('#cfg-permission_mode').value,
            model: overlay.querySelector('#cfg-model').value,
            max_turns: overlay.querySelector('#cfg-max_turns').value.trim(),
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

// ===== 3D Starfield Background =====
function initStarfield() {
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;opacity:0.7';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const stars = Array.from({ length: 5000 }, () => ({
        x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random()
    }));

    let working = false;
    // Parámetros interpolados para transición suave
    let curSpeed = 0.004, curAlpha = 0.6, curSize = 2.5, curOpacity = 0.7;
    const IDLE  = { speed: 0.004, alpha: 0.6, size: 2.5, color: '#667eea', opacity: 0.7 };
    const WORK  = { speed: 0.008, alpha: 1.0, size: 4.0, color: '#c4b5fd', opacity: 0.35 };
    let curColor = IDLE.color;

    window.setStarfieldWorking = function(val) {
        working = !!val;
    };

    (function draw() {
        const target = working ? WORK : IDLE;
        curSpeed   += (target.speed   - curSpeed)   * 0.05;
        curAlpha   += (target.alpha   - curAlpha)   * 0.05;
        curSize    += (target.size    - curSize)    * 0.05;
        curOpacity += (target.opacity - curOpacity) * 0.05;
        curColor = target.color;
        canvas.style.opacity = curOpacity;

        const w = window.innerWidth, h = window.innerHeight;
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
        const cx = w / 2, cy = h / 2;
        ctx.clearRect(0, 0, w, h);
        for (const s of stars) {
            s.z -= curSpeed;
            if (s.z <= 0) { s.z = 1; s.x = Math.random() * 2 - 1; s.y = Math.random() * 2 - 1; }
            const px = (s.x / s.z) * cx + cx;
            const py = (s.y / s.z) * cy + cy;
            const d = 1 - s.z;
            ctx.globalAlpha = d * curAlpha;
            ctx.fillStyle = curColor;
            ctx.beginPath();
            ctx.arc(px, py, d * curSize, 0, Math.PI * 2);
            ctx.fill();
        }
        requestAnimationFrame(draw);
    })();
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
initStarfield();
initTypewriter();
