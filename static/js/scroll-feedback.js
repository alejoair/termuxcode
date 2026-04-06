// ===== Scroll Feedback — Feedback inmersivo para el chat =====

import { dom } from './state.js';

// ===== Configuracion =====
const config = {
    enabled: true,
    // Vibracion proporcional al scroll
    minPulse: 10,             // ms - pulso minimo (scroll lento)
    maxPulse: 25,             // ms - pulso maximo (scroll rapido)
    cooldownSlow: 350,        // ms entre pulsos (scroll lento)
    cooldownFast: 100,        // ms entre pulsos (scroll rapido)

    // Vibracion al llegar a bordes
    borderPulse: [10, 30, 10],
    borderCooldown: 300,

    // Over-scroll
    overscrollBasePulse: 8,
    overscrollCooldown: 80,

    // Swipe rapido
    fastSwipeThreshold: 0.8,  // px/ms
    fastSwipePulse: [4, 8, 4, 8, 4],
};

// ===== Estado interno =====
let lastScrollTime = 0;
let lastPulseTime = 0;
let lastBorderTime = 0;
let lastOverscrollTime = 0;
let overscrollCount = 0;
let lastScrollTop = 0;
let scrollVelocity = 0;
let glowTimer = null;

// ===== Soporte del navegador =====
const supportsVibration = 'vibrate' in navigator;

// ===== Inicializacion =====
export function initScrollFeedback() {
    const messagesContainer = dom.messages;
    if (!messagesContainer) {
        console.warn('[ScrollFeedback] Contenedor de mensajes no encontrado');
        return;
    }

    messagesContainer.addEventListener('scroll', onScroll, { passive: true });
    messagesContainer.addEventListener('touchstart', onTouchStart, { passive: true });
    messagesContainer.addEventListener('touchend', onTouchEnd, { passive: true });
}

// ===== Touch handlers =====
// ===== Visual glow =====
function flashGlow() {
    const el = dom.messages;
    if (!el) return;
    el.style.outline = '3px solid red';
    clearTimeout(glowTimer);
    glowTimer = setTimeout(() => { el.style.outline = ''; }, 300);
}

// ===== Touch handlers =====
function onTouchStart() {
    scrollVelocity = 0;
    overscrollCount = 0;
    // Desbloquear vibracion en Chrome (requiere primer user gesture)
    if (supportsVibration) navigator.vibrate(1);
}

function onTouchEnd() {
    scrollVelocity = 0;
    overscrollCount = 0;
}

// ===== Scroll handler =====
function onScroll(e) {
    if (!config.enabled || !supportsVibration) return;

    const target = e.target;
    const scrollTop = target.scrollTop;
    const scrollHeight = target.scrollHeight;
    const clientHeight = target.clientHeight;

    const now = Date.now();

    // Calcular distancia y velocidad
    const distance = Math.abs(scrollTop - lastScrollTop);
    const timeDelta = now - lastScrollTime;

    if (timeDelta > 0 && lastScrollTime > 0) {
        scrollVelocity = distance / timeDelta; // px/ms
    }

    lastScrollTime = now;
    lastScrollTop = scrollTop;

    // Limites
    const atTop = scrollTop <= 2;
    const atBottom = scrollTop + clientHeight >= scrollHeight - 2;
    const inMiddle = !atTop && !atBottom;

    // ===== Scroll normal — pulso proporcional a la distancia =====
    // Cooldown dinamico: lento = espaciado, rapido = junto
    const speedFactor = Math.min(scrollVelocity / config.fastSwipeThreshold, 1);
    const cooldown = Math.round(config.cooldownSlow - speedFactor * (config.cooldownSlow - config.cooldownFast));

    if (inMiddle && distance > 0 && now - lastPulseTime >= cooldown) {
        lastPulseTime = now;

        if (scrollVelocity > config.fastSwipeThreshold) {
            // Swipe rapido — patron multiple
            navigator.vibrate(config.fastSwipePulse);
        } else {
            // Scroll normal — pulso proporcional a la distancia recorrida
            const intensity = Math.min(distance / 50, 1); // 0-1 basado en px movidos
            const pulse = Math.round(config.minPulse + intensity * (config.maxPulse - config.minPulse));
            navigator.vibrate(pulse);
        }
        flashGlow();
        overscrollCount = 0;
    }

    // ===== Bordes — pulso de rebote =====
    if ((atTop || atBottom) && now - lastBorderTime >= config.borderCooldown) {
        lastBorderTime = now;
        navigator.vibrate(config.borderPulse);
        flashGlow();
    }

    // ===== Over-scroll =====
    if ((atTop || atBottom) && distance === 0 && now - lastOverscrollTime >= config.overscrollCooldown) {
        lastOverscrollTime = now;
        overscrollCount++;
        const pulse = Math.min(config.overscrollBasePulse + overscrollCount * 2, 30);
        navigator.vibrate([pulse, 15, pulse]);
        flashGlow();
    }
}

// ===== API publica =====
export function setScrollFeedbackEnabled(enabled) {
    config.enabled = enabled;
}

export function getScrollFeedbackConfig() {
    return { ...config };
}
