// ===== Feedback haptico (vibraciones) =====

// Deteccion de soporte
const supported = 'vibrate' in navigator;

// Patrones predefinidos (en milisegundos)
export const patterns = {
    send: [30],           // Pulso corto - confirmacion envio
    receive: [20],        // Pulso muy suave - mensaje recibido
    result: [40, 60, 40], // Doble pulso - tarea completada
    error: [80, 40, 80],  // Triple pulso - error
    connect: [20],        // Pulso suave - conectado
    disconnect: [60],     // Pulso medio - desconectado
    attention: [50, 80]   // Doble pulso - requiere atencion (modales)
};

// Funcion principal
function vibrate(pattern) {
    if (supported && pattern) {
        navigator.vibrate(pattern);
    }
}

// Funciones especificas por evento
export function vibrateSend() { vibrate(patterns.send); }
export function vibrateReceive() { vibrate(patterns.receive); }
export function vibrateResult() { vibrate(patterns.result); }
export function vibrateError() { vibrate(patterns.error); }
export function vibrateConnect() { vibrate(patterns.connect); }
export function vibrateDisconnect() { vibrate(patterns.disconnect); }
export function vibrateAttention() { vibrate(patterns.attention); }
