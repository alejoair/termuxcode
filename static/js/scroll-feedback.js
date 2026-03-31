// ===== Scroll Feedback — Feedback inmersivo para el chat =====

import { dom } from './state.js';

// ===== Configuracion =====
const config = {
    enabled: true,
    // Vibracion al hacer scroll
    scrollPulse: 3,           // ms - pulso muy corto
    scrollCooldown: 16,     // ms entre pulsos

    // Vibracion al llegar a bordes
    borderPulse: [8, 20, 8],  // patron de "rebote"
    borderCooldown: 200,    // ms antes de poder repetir

    // Vibracion al "over-scroll" (intentar scrollear mas alla del limite)
    overscrollPulse: [15, 10, 25, 10, 15],  // patron complejo tipo "rebote elástico"
    overscrollIntensity: 0,  // se incrementa con cada intento

    // Swipe rápido
    fastSwipePulse: [2, 1, 2, 1, 2],  // múltiples pulsos rápidos
    fastSwipeThreshold: 15,  // px/ms para considerar swipe rápido
};

// ===== Estado interno =====
let lastScrollTime = 0;
let lastBorderTime = 0;
let overscrollCount = 0;
let lastScrollY = 0;
let scrollVelocity = 0;
let isScrolling = false;
let scrollTimeout = null;

// ===== Soporte del navegador =====
const supportsVibration = 'vibrate' in navigator;

// ===== Inicializacion =====
export function initScrollFeedback() {
    const messagesContainer = dom.messages;
    if (!messagesContainer) {
        console.warn('[ScrollFeedback] Contenedor de mensajes no encontrado');
        return;
    }

    console.log('[ScrollFeedback] Inicializando...');

    // Event listeners para scroll
    messagesContainer.addEventListener('scroll', onScroll, { passive: true });
    messagesContainer.addEventListener('touchstart', onTouchStart, { passive: true });
    messagesContainer.addEventListener('touchend', onTouchEnd, { passive: true });

    console.log('[ScrollFeedback] Listo. Vibracion:', supportsVibration);
}

// ===== Touch handlers =====
function onTouchStart(e) {
    if (!e.touches[0]) return;
    lastScrollY = e.touches[0].clientY;
    isScrolling = true;
    scrollVelocity = 0;
}

function onTouchEnd() {
    isScrolling = false;
    scrollVelocity = 0;
    overscrollCount = 0;

    // Limpiar timeout
    if (scrollTimeout) {
        clearTimeout(scrollTimeout);
        scrollTimeout = null;
    }
}

// ===== Scroll handler =====
function onScroll(e) {
    if (!config.enabled || !supportsVibration) return;

    const target = e.target;
    const scrollTop = target.scrollTop;
    const scrollHeight = target.scrollHeight;
    const clientHeight = target.clientHeight;

    // Calcular velocidad de scroll
    const now = Date.now();
    const timeDelta = now - lastScrollTime;
    if (timeDelta > 0 && lastScrollTime > 0) {
        scrollVelocity = Math.abs(scrollTop - (lastScrollY || scrollTop)) / timeDelta;
    }
    lastScrollTime = now;

    // Detectar si está en los bordes
    const atTop = scrollTop <= 5;
    const atBottom = scrollTop + clientHeight >= scrollHeight - 5;
    const canScrollUp = scrollTop > 0;
    const canScrollDown = scrollTop + clientHeight < scrollHeight;

    // ===== Vibración durante scroll normal =====
    if (canScrollUp && canScrollDown) {
        // Scroll normal - vibración sutil
        if (now - lastScrollTime > config.scrollCooldown) {
            // Vibración más fuerte si el scroll es rápido
            if (scrollVelocity > config.fastSwipeThreshold) {
                // Swipe rápido - pulsos múltiples
                navigator.vibrate(config.fastSwipePulse);
            } else {
                // Scroll normal - pulso simple
                navigator.vibrate(config.scrollPulse);
            }
        }
        overscrollCount = 0;
    }

    // ===== Vibración al llegar a bordes =====
    if ((atTop && canScrollUp) || (atBottom && canScrollDown)) {
        // Ya no hay más contenido para scrollear
        if (now - lastBorderTime > config.borderCooldown) {
            lastBorderTime = now;
            navigator.vibrate(config.borderPulse);
        }
    }

    // ===== Detectar overscroll (intentar scrollear más allá del límite) =====
    // Esto requiere detectar cuando el usuario "tira" del borde
    if (atTop && !canScrollDown || atBottom && !canScrollUp) {
        overscrollCount++;
        if (overscrollCount > 3) {
            // Overscroll detectado - vibración elástica
            const intensity = Math.min(overscrollCount / 10, 1);
            const pattern = generateOverscrollPattern(intensity);
            navigator.vibrate(pattern);
        }
    } else {
        overscrollCount = Math.max(0, overscrollCount - 1);
    }

    // Actualizar último Y
    lastScrollY = scrollTop;
}

// ===== Generar patron de overscroll =====
function generateOverscrollPattern(intensity) {
    // Patrón que simula "rebote" o resistencia
    const basePulse = 5 + Math.floor(intensity * 10);
    const gap = 8 + Math.floor(intensity * 5);
    const secondPulse = 3 + Math.floor(intensity * 6);

    return [basePulse, gap, secondPulse, gap / 2, basePulse / 2];
}

// ===== API publica =====
export function setScrollFeedbackEnabled(enabled) {
    config.enabled = enabled;
}

export function getScrollFeedbackConfig() {
    return { ...config };
}
