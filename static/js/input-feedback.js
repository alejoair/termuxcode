// ===== Feedback del Input — Sistema inmersivo de escritura =====

import { dom } from './state.js';

// ===== Configuracion =====
const config = {
    enabled: {
        haptic: true,      // Vibracion por tecla
        glow: true,        // Destello en el borde
        particles: true,   // Particulas del cursor
        breathe: true,     // Boton enviar "respira"
        sound: false,      // Sonido de tecla (desactivado por defecto)
    },
    // Patrones de vibracion (ms)
    hapticPatterns: {
        key: [8],          // Pulso muy corto por tecla
        space: [12],       // Un poco mas largo para espacio
        enter: [15],       // Enter mas notorio
        backspace: [5, 3, 8],  // Patrón de "romper" - dos pulsos rápidos
    },
    // Cooldown para no saturar (ms)
    glowCooldown: 50,
    particleCooldown: 30,
    hapticCooldown: 20,
    backspaceCooldown: 10,  // Más rápido para borrar
};

// ===== Estado interno =====
let lastGlowTime = 0;
let lastParticleTime = 0;
let lastHapticTime = 0;
let lastBackspaceTime = 0;
let backspaceHeldTime = 0;
let backspaceInterval = null;
let particleContainer = null;
let sendBtn = null;

// ===== Soporte del navegador =====
const supportsVibration = 'vibrate' in navigator;
let audioContext = null;
let keySound = null;

// ===== Inicializacion =====
export function initInputFeedback() {
    const input = dom.input;
    if (!input) {
        console.warn('[InputFeedback] Input no encontrado');
        return;
    }

    console.log('[InputFeedback] Inicializando...');

    // Encontrar boton de enviar
    sendBtn = document.querySelector('.btn-send');

    // Crear contenedor de particulas
    createParticleContainer();

    // Precargar sonido (solo si esta activado)
    if (config.enabled.sound) {
        initSound();
    }

    // Event listeners
    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKeyDown);
    input.addEventListener('keyup', onKeyUp);
    input.addEventListener('focus', onFocus);
    input.addEventListener('blur', onBlur);

    // Estado inicial del boton
    updateSendButtonState();

    console.log('[InputFeedback] Listo. Haptic:', supportsVibration, 'Input:', input.id);
}

// ===== Crear contenedor de particulas =====
function createParticleContainer() {
    const inputWrapper = dom.input.closest('.input-wrapper') || dom.input.parentElement;

    particleContainer = document.createElement('div');
    particleContainer.className = 'input-particles';

    // Posicionar relativo al input wrapper
    inputWrapper.style.position = 'relative';
    inputWrapper.appendChild(particleContainer);

    console.log('[InputFeedback] Contenedor de particulas creado');
}

// ===== Sonido (Web Audio API) =====
function initSound() {
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
        console.warn('Web Audio API no soportada');
        config.enabled.sound = false;
    }
}

function playKeySound() {
    if (!config.enabled.sound || !audioContext) return;

    // Crear oscilador para un click suave
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();

    osc.connect(gain);
    gain.connect(audioContext.destination);

    // Frecuencia baja para sonido de tecla
    osc.frequency.value = 800 + Math.random() * 200;
    osc.type = 'sine';

    // Envelope muy corto
    const now = audioContext.currentTime;
    gain.gain.setValueAtTime(0.08, now);
    gain.gain.exponentialDecayTo && gain.gain.exponentialDecayTo(0.001, now + 0.05);
    gain.gain.setValueAtTime(0.08, now);
    gain.gain.linearRampToValueAtTime(0.001, now + 0.05);

    osc.start(now);
    osc.stop(now + 0.05);
}

// ===== Haptico =====
function triggerHaptic(key) {
    if (!config.enabled.haptic || !supportsVibration) return;

    const now = Date.now();
    if (now - lastHapticTime < config.hapticCooldown) return;
    lastHapticTime = now;

    let pattern = config.hapticPatterns.key;
    if (key === ' ') pattern = config.hapticPatterns.space;
    if (key === 'Enter') pattern = config.hapticPatterns.enter;

    navigator.vibrate(pattern);
}

// ===== Haptico especial para backspace (mantenido) =====
function triggerBackspaceHaptic() {
    if (!config.enabled.haptic || !supportsVibration) return;

    const now = Date.now();
    if (now - lastBackspaceTime < config.backspaceCooldown) return;
    lastBackspaceTime = now;

    // Vibración con variaciones aleatorias mientras se mantiene presionado
    backspaceHeldTime += 1;

    // Generar patrón aleatorio que se siente como "romper/triturar"
    const baseDuration = 3 + Math.random() * 5;  // 3-8ms
    const gap = 2 + Math.random() * 6;           // 2-8ms de pausa
    const secondPulse = 1 + Math.random() * 3;   // 1-4ms segundo pulso

    // A medida que pasa más tiempo, la vibración se vuelve más intensa y rápida
    const intensity = Math.min(backspaceHeldTime / 10, 1);  // 0-1
    const boostedDuration = baseDuration + (intensity * 4);
    const reducedGap = Math.max(gap - (intensity * 3), 1);

    // Patrón: pulso principal, pausa, micro-pulso
    const pattern = [boostedDuration, reducedGap, secondPulse];

    navigator.vibrate(pattern);
}

function startBackspaceHaptic() {
    backspaceHeldTime = 0;
    triggerBackspaceHaptic();

    // Iniciar repeticiones rápidas mientras se mantiene
    // En Android keydown no se repite, así que usamos el input event para detectar borrado continuo
    if (backspaceInterval) clearInterval(backspaceInterval);
    backspaceInterval = setInterval(() => {
        // Solo vibrar si el input sigue teniendo contenido
        if (dom.input.value.length > 0) {
            triggerBackspaceHaptic();
        }
    }, 50);  // Cada 50ms mientras se mantiene presionado
}

function stopBackspaceHaptic() {
    if (backspaceInterval) {
        clearInterval(backspaceInterval);
        backspaceInterval = null;
    }
    backspaceHeldTime = 0;
}

// ===== Glow (destello del borde) =====
function triggerGlow() {
    if (!config.enabled.glow) return;

    const now = Date.now();
    if (now - lastGlowTime < config.glowCooldown) return;
    lastGlowTime = now;

    dom.input.classList.add('input-glow-active');

    // Remover clase despues de la animacion
    setTimeout(() => {
        dom.input.classList.remove('input-glow-active');
    }, 150);
}

// ===== Particulas =====
function spawnParticle() {
    if (!config.enabled.particles || !particleContainer) return;

    const now = Date.now();
    if (now - lastParticleTime < config.particleCooldown) return;
    lastParticleTime = now;

    const particle = document.createElement('div');
    particle.className = 'input-particle';

    // Posicion relativa al input
    const inputRect = dom.input.getBoundingClientRect();
    const containerRect = particleContainer.getBoundingClientRect();

    // Posicionar cerca del cursor (aproximado)
    const textLength = dom.input.value.length;
    const charWidth = 8; // Aproximado
    const offsetX = Math.min(textLength * charWidth, inputRect.width - 20);

    particle.style.left = `${offsetX + 10}px`;
    particle.style.top = `${inputRect.height / 2}px`;

    // Angulo aleatorio hacia arriba
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI / 3;
    const velocity = 30 + Math.random() * 20;
    const vx = Math.cos(angle) * velocity;
    const vy = Math.sin(angle) * velocity;

    particleContainer.appendChild(particle);

    // Animar
    let x = 0, y = 0, opacity = 1;
    const gravity = 80;
    const duration = 400;
    const startTime = performance.now();

    function animate(currentTime) {
        const elapsed = (currentTime - startTime) / 1000;
        const progress = (currentTime - startTime) / duration;

        if (progress >= 1) {
            particle.remove();
            return;
        }

        x = vx * elapsed;
        y = vy * elapsed + 0.5 * gravity * elapsed * elapsed;
        opacity = 1 - progress;

        particle.style.transform = `translate(${x}px, ${y}px)`;
        particle.style.opacity = opacity;

        requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
}

// ===== Boton enviar "respirando" =====
function updateSendButtonState() {
    if (!sendBtn || !config.enabled.breathe) return;

    const hasContent = dom.input.value.length > 0;

    if (hasContent) {
        sendBtn.classList.add('btn-send-active');
    } else {
        sendBtn.classList.remove('btn-send-active');
    }
}

// ===== Event Handlers =====
function onInput(e) {
    // Feedback por cada caracter ingresado
    if (e.data) {
        triggerHaptic(e.data);
        triggerGlow();
        spawnParticle();
        playKeySound();
    } else if (e.inputType === 'deleteContentBackward' || e.inputType === 'deleteContentForward') {
        // Al borrar también damos feedback háptico
        triggerBackspaceHaptic();
        triggerGlow();
    }
    updateSendButtonState();
}

function onKeyDown(e) {
    // Feedback especial para ciertas teclas
    if (e.key === 'Enter' && !e.shiftKey) {
        // Enter para enviar - feedback mas fuerte
        triggerHaptic(e.key);
    }

    // Backspace mantenido
    if (e.key === 'Backspace' || e.key === 'Delete') {
        startBackspaceHaptic();
    }
}

function onKeyUp(e) {
    // Detener vibración de backspace al soltar
    if (e.key === 'Backspace' || e.key === 'Delete') {
        stopBackspaceHaptic();
    }
}

function onFocus() {
    dom.input.classList.add('input-focused');
}

function onBlur() {
    dom.input.classList.remove('input-focused');
}

// ===== API publica para configuracion =====
export function setInputFeedbackEnabled(type, enabled) {
    if (type in config.enabled) {
        config.enabled[type] = enabled;

        // Inicializar sonido si se activa por primera vez
        if (type === 'sound' && enabled && !audioContext) {
            initSound();
        }
    }
}

export function getInputFeedbackConfig() {
    return { ...config.enabled };
}
