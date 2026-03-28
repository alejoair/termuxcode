// ===== termux-code - Entry Point =====

import { state, dom } from './js/state.js';
import { createTab, switchTab, loadTabs, send, sendStop, sendDisconnect, clearChat } from './js/tabs.js';

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

// ===== 3D Starfield Background =====
function initStarfield() {
    const area = dom.messages;
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;opacity:0.7';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const stars = Array.from({ length: 5000 }, () => ({
        x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random()
    }));

    (function draw() {
        const w = window.innerWidth, h = window.innerHeight;
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
        const cx = w / 2, cy = h / 2;
        ctx.clearRect(0, 0, w, h);
        for (const s of stars) {
            s.z -= 0.004;
            if (s.z <= 0) { s.z = 1; s.x = Math.random() * 2 - 1; s.y = Math.random() * 2 - 1; }
            const px = (s.x / s.z) * cx + cx;
            const py = (s.y / s.z) * cy + cy;
            const d = 1 - s.z;
            ctx.globalAlpha = d * 0.6;
            ctx.fillStyle = '#667eea';
            ctx.beginPath();
            ctx.arc(px, py, d * 2.5, 0, Math.PI * 2);
            ctx.fill();
        }
        requestAnimationFrame(draw);
    })();
}

init();
initStarfield();
