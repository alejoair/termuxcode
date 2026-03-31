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
        tab.settings = {
            permission_mode: overlay.querySelector('#cfg-permission_mode').value,
            model: overlay.querySelector('#cfg-model').value,
            max_turns: overlay.querySelector('#cfg-max_turns').value.trim(),
            rolling_window: parseInt(overlay.querySelector('#cfg-rolling_window').value) || 100,
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

// ===== 3D Starfield Background with Warp Effect =====
function initStarfield() {
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;opacity:0.35';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const stars = Array.from({ length: 5000 }, () => ({
        x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random(),
        pz: Math.random() // previous z for streak calculation
    }));

    // Nebula clouds: slow-moving background blobs that drift through during warp
    const nebulae = Array.from({ length: 6 }, () => ({
        x: Math.random() * 2 - 1,
        y: Math.random() * 2 - 1,
        z: 0.5 + Math.random() * 0.5, // deep in background
        radius: 0.15 + Math.random() * 0.2,
        // Each nebula gets a unique color tint
        hue: Math.floor(Math.random() * 3), // 0=blue, 1=violet, 2=cyan
    }));
    const NEBULA_COLORS = [
        [80, 100, 200],  // deep blue
        [140, 80, 200],  // violet
        [60, 150, 200],  // cyan
    ];

    let working = false;
    let curFlash = 0;
    const IDLE  = { speed: 0.004, alpha: 0.6, size: 2.5, opacity: 0.35 };
    const WORK  = { speed: 0.15, alpha: 1.0, size: 4.0, opacity: 0.55 };
    const COLOR_IDLE = [102, 126, 234]; // #667eea
    const COLOR_WARP = [220, 215, 255]; // bright blueish white for warp

    // Warp progress: 0 = idle, 1 = full warp
    let warpProgress = 0;
    const ENGAGE_RATE = 0.02;    // ~0.8s ease-in to full warp
    const DISENGAGE_RATE = 0.04; // ~0.5s ease-out

    // Ease-in curve: slow start, fast finish (cubic)
    function easeInCubic(t) { return t * t * t; }
    // Ease-out curve for disengaging
    function easeOutQuad(t) { return 1 - (1 - t) * (1 - t); }

    function lerp(a, b, t) { return a + (b - a) * t; }

    window.setStarfieldWorking = function(val) {
        const wasWorking = working;
        working = !!val;
        if (working && !wasWorking) curFlash = 1.0;
    };

    // Color cycle targets for warp variety (blue → violet → cyan → blue)
    const WARP_COLORS = [
        [220, 215, 255], // blueish white
        [200, 170, 255], // violet
        [170, 220, 255], // cyan
        [190, 180, 255], // lavender
    ];
    let warpTime = 0; // accumulates while in warp

    (function draw() {
        // Advance warp progress linearly, apply easing curve after
        if (working && warpProgress < 1) {
            warpProgress = Math.min(1, warpProgress + ENGAGE_RATE);
        } else if (!working && warpProgress > 0) {
            warpProgress = Math.max(0, warpProgress - DISENGAGE_RATE);
        }

        // Apply easing: slow start when engaging, smooth stop when disengaging
        const t = working ? easeInCubic(warpProgress) : easeOutQuad(warpProgress);

        // Speed pulses: intermittent bursts with calm periods
        let speedPulse = 0;
        if (t > 0.5) {
            warpTime += 0.016;
            // Burst envelope: active ~2s, calm ~4s (6s cycle)
            const burstCycle = (warpTime % 6);
            const burstEnvelope = burstCycle < 2 ? Math.sin(burstCycle * Math.PI / 2) : 0;
            speedPulse = Math.sin(warpTime * 3) * burstEnvelope * 0.3 * (t - 0.5) * 2;
        } else {
            warpTime = 0;
        }

        const baseSpeed  = lerp(IDLE.speed, WORK.speed, t);
        const curSpeed   = baseSpeed; // stable speed for star movement & streaks
        const visualSpeed = baseSpeed + baseSpeed * speedPulse * 0.2; // pulsing for nebulae/effects only
        const curAlpha   = lerp(IDLE.alpha,   WORK.alpha,   t);
        const curSize    = lerp(IDLE.size,    WORK.size,    t);
        const curOpacity = lerp(IDLE.opacity, WORK.opacity, t);

        // Color cycling during warp
        let curR, curG, curB;
        if (t > 0.3) {
            // Cycle through warp colors smoothly (~8s full cycle)
            const colorTime = warpTime * 0.8;
            const ci = colorTime % WARP_COLORS.length;
            const idx0 = Math.floor(ci) % WARP_COLORS.length;
            const idx1 = (idx0 + 1) % WARP_COLORS.length;
            const cf = ci - Math.floor(ci); // fractional blend
            const warpR = lerp(WARP_COLORS[idx0][0], WARP_COLORS[idx1][0], cf);
            const warpG = lerp(WARP_COLORS[idx0][1], WARP_COLORS[idx1][1], cf);
            const warpB = lerp(WARP_COLORS[idx0][2], WARP_COLORS[idx1][2], cf);
            // Blend from idle color into cycling warp color
            const ct = Math.min(1, (t - 0.3) / 0.7);
            curR = lerp(COLOR_IDLE[0], warpR, ct);
            curG = lerp(COLOR_IDLE[1], warpG, ct);
            curB = lerp(COLOR_IDLE[2], warpB, ct);
        } else {
            curR = COLOR_IDLE[0]; curG = COLOR_IDLE[1]; curB = COLOR_IDLE[2];
        }

        // Fade flash (~2s decay)
        if (curFlash > 0) curFlash *= 0.97;
        if (curFlash < 0.01) curFlash = 0;

        canvas.style.opacity = curOpacity;

        const w = window.innerWidth, h = window.innerHeight;
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
        const cx = w / 2, cy = h / 2;
        ctx.clearRect(0, 0, w, h);

        // Draw nebula clouds behind stars during warp
        if (t > 0.2) {
            const nebulaAlpha = Math.min(1, (t - 0.2) / 0.3); // fade in as warp builds
            for (const n of nebulae) {
                // Nebulae move toward camera slowly (much slower than stars)
                n.z -= visualSpeed * 0.15;
                if (n.z <= 0.05) {
                    n.z = 0.8 + Math.random() * 0.2;
                    n.x = Math.random() * 2 - 1;
                    n.y = Math.random() * 2 - 1;
                    n.hue = Math.floor(Math.random() * 3);
                    n.radius = 0.15 + Math.random() * 0.2;
                }
                const npx = (n.x / n.z) * cx + cx;
                const npy = (n.y / n.z) * cy + cy;
                const nDepth = 1 - n.z;
                const nRadius = (n.radius / n.z) * Math.min(cx, cy);
                const c = NEBULA_COLORS[n.hue];

                const nebGrad = ctx.createRadialGradient(npx, npy, 0, npx, npy, nRadius);
                nebGrad.addColorStop(0, `rgba(${c[0]},${c[1]},${c[2]},${nebulaAlpha * nDepth * 0.15})`);
                nebGrad.addColorStop(0.4, `rgba(${c[0]},${c[1]},${c[2]},${nebulaAlpha * nDepth * 0.07})`);
                nebGrad.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.globalAlpha = 1;
                ctx.fillStyle = nebGrad;
                ctx.fillRect(npx - nRadius, npy - nRadius, nRadius * 2, nRadius * 2);
            }
        }

        // Streak length factor: how much of the previous position to use
        // At idle speed (~0.004), streakFactor ≈ 0 (dots). At warp (~0.15), streakFactor → 1 (long lines)
        const streakFactor = Math.min(1, Math.max(0, (curSpeed - 0.006) / 0.06));

        const streakMultiplier = 1.5;

        for (const s of stars) {
            s.pz = s.z; // store previous z before moving
            s.z -= curSpeed;
            if (s.z <= 0) {
                s.z = 1; s.pz = 1;
                s.x = Math.random() * 2 - 1;
                s.y = Math.random() * 2 - 1;
            }

            // Current projected position
            const px = (s.x / s.z) * cx + cx;
            const py = (s.y / s.z) * cy + cy;
            const d = 1 - s.z;

            if (streakFactor > 0.05) {
                // Warp mode: draw radial streak lines
                const ppx = (s.x / s.pz) * cx + cx;
                const ppy = (s.y / s.pz) * cy + cy;

                // Fade out streaks near the center to avoid visible radial pattern
                const distFromCenter = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
                const maxDist = Math.sqrt(cx * cx + cy * cy);
                const centerFade = Math.min(1, distFromCenter / (maxDist * 0.25));

                // Extend the tail beyond the previous position for longer streaks
                const dx = px - ppx, dy = py - ppy;
                const tailX = px - dx * streakMultiplier;
                const tailY = py - dy * streakMultiplier;

                // Draw streak with gradient: bright at tip, fading at tail
                const grad = ctx.createLinearGradient(tailX, tailY, px, py);
                const alpha = d * curAlpha * centerFade;
                grad.addColorStop(0, `rgba(${curR|0},${curG|0},${curB|0},0)`);
                grad.addColorStop(0.5, `rgba(${curR|0},${curG|0},${curB|0},${alpha * 0.5})`);
                grad.addColorStop(1, `rgba(${Math.min(255,curR+80)|0},${Math.min(255,curG+80)|0},${Math.min(255,curB+60)|0},${alpha})`);

                ctx.beginPath();
                ctx.moveTo(tailX, tailY);
                ctx.lineTo(px, py);
                ctx.strokeStyle = grad;
                ctx.lineWidth = d * curSize * 0.8;
                ctx.lineCap = 'round';
                ctx.stroke();

                // Bright glowing tip at the leading edge
                ctx.globalAlpha = alpha;
                ctx.fillStyle = `rgba(${Math.min(255,curR+100)|0},${Math.min(255,curG+100)|0},${Math.min(255,curB+80)|0},1)`;
                ctx.beginPath();
                ctx.arc(px, py, d * curSize * 0.5, 0, Math.PI * 2);
                ctx.fill();

                // Extra glow halo around the tip
                if (d > 0.7 && centerFade > 0.5) {
                    ctx.globalAlpha = alpha * 0.3;
                    ctx.fillStyle = `rgba(${Math.min(255,curR+100)|0},${Math.min(255,curG+100)|0},255,0.5)`;
                    ctx.beginPath();
                    ctx.arc(px, py, d * curSize * 1.2, 0, Math.PI * 2);
                    ctx.fill();
                }
            } else {
                // Idle mode: draw dots
                ctx.globalAlpha = d * curAlpha;
                ctx.fillStyle = `rgb(${curR|0},${curG|0},${curB|0})`;
                ctx.beginPath();
                ctx.arc(px, py, d * curSize, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Central flash on warp engage
        if (curFlash > 0) {
            const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w, h) * 0.7);
            gradient.addColorStop(0, `rgba(220, 220, 255, ${curFlash * 0.7})`);
            gradient.addColorStop(0.2, `rgba(180, 170, 255, ${curFlash * 0.4})`);
            gradient.addColorStop(0.5, `rgba(140, 130, 255, ${curFlash * 0.15})`);
            gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.globalAlpha = 1;
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, w, h);
        }

        ctx.globalAlpha = 1;
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
