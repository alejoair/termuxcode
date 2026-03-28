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
