// ===== useTerminal.js — Composable singleton para terminal funcional =====

import { ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const TERMINAL_WS_URL = window.location.protocol === 'tauri:'
    ? 'ws://localhost:2088'
    : `ws://${window.location.hostname}:2088`;

// Singleton state (module-level)
const isOpen = ref(false);
const isConnected = ref(false);

let ws = null;
let terminal = null;
let fitAddon = null;
let dataDisposable = null;
let resizeDisposable = null;

function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    if (ws) disconnect();

    ws = new WebSocket(TERMINAL_WS_URL);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        isConnected.value = true;
        // Enviar tamaño actual si el terminal ya está creado
        if (terminal && fitAddon) {
            try {
                fitAddon.fit();
            } catch (e) { /* ignore */ }
        }
    };

    ws.onmessage = (event) => {
        if (!terminal) return;
        if (event.data instanceof ArrayBuffer) {
            terminal.write(new Uint8Array(event.data));
        } else {
            terminal.write(event.data);
        }
    };

    ws.onclose = () => {
        isConnected.value = false;
        ws = null;
    };

    ws.onerror = () => {
        isConnected.value = false;
    };
}

function disconnect() {
    if (dataDisposable) {
        dataDisposable.dispose();
        dataDisposable = null;
    }
    if (resizeDisposable) {
        resizeDisposable.dispose();
        resizeDisposable = null;
    }
    if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        ws.close();
        ws = null;
    }
    isConnected.value = false;
}

function resize(cols, rows) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
}

function initTerminal(term, fit) {
    terminal = term;
    fitAddon = fit;

    // Conectar input del terminal al WebSocket
    dataDisposable = term.onData((data) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(data);
        }
    });

    // Conectar resize del terminal al backend
    resizeDisposable = term.onResize(({ cols, rows }) => {
        resize(cols, rows);
    });

    // Auto-conectar si no hay WS activo
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        connect();
    }
}

/**
 * Desvincula el xterm del WebSocket pero NO desconecta el WS.
 * El PTY sigue vivo en el backend.
 */
function detachTerminal() {
    if (dataDisposable) {
        dataDisposable.dispose();
        dataDisposable = null;
    }
    if (resizeDisposable) {
        resizeDisposable.dispose();
        resizeDisposable = null;
    }
    terminal = null;
    fitAddon = null;
}

/**
 * Destruye todo: terminal + WebSocket + PTY.
 * Solo para cleanup final de la app.
 */
function destroyAll() {
    detachTerminal();
    disconnect();
}

function toggleSidebar() {
    isOpen.value = !isOpen.value;
}

function setOpen(val) {
    isOpen.value = val;
}

export function useTerminal() {
    return {
        isOpen,
        isConnected,
        connect,
        disconnect,
        resize,
        initTerminal,
        detachTerminal,
        destroyAll,
        toggleSidebar,
        setOpen,
    };
}
