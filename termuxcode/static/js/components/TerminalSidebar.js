// Componente: Terminal Sidebar (panel con xterm.js)
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { useResizable } from '../composables/useResizable.js';
import { useTerminal } from '../composables/useTerminal.js';

const TERMINAL_THEME = {
    background: '#0a0f14',
    foreground: '#e2e8f0',
    cursor: '#14b8a6',
    cursorAccent: '#0a0f14',
    selectionBackground: '#243040',
    selectionForeground: '#e2e8f0',
    black: '#0a0f14',
    red: '#f43f5e',
    green: '#22d3ee',
    yellow: '#f59e0b',
    blue: '#0ea5e9',
    magenta: '#a855f7',
    cyan: '#14b8a6',
    white: '#e2e8f0',
    brightBlack: '#64748b',
    brightRed: '#f43f5e',
    brightGreen: '#22d3ee',
    brightYellow: '#f59e0b',
    brightBlue: '#0ea5e9',
    brightMagenta: '#a855f7',
    brightCyan: '#14b8a6',
    brightWhite: '#e2e8f0',
};

export default {
    template: `
        <!-- Desktop -->
        <transition v-if="!isMobile" name="sidebar">
            <div
                v-if="isOpen"
                class="flex flex-col h-full bg-base border-r border-border flex-shrink-0 relative terminal-sidebar"
                :class="{ 'transition-[width] duration-200': !isResizing }"
                :style="{ width: effectiveWidth + 'px' }"
            >
                <!-- Resize handle (derecha, es sidebar izquierda) -->
                <div
                    v-bind="resizeHandleProps"
                    :class="{ active: isResizing }"
                ></div>
                <!-- Header -->
                <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-txt">Terminal</span>
                        <span
                            :class="['w-2 h-2 rounded-full', isConnected ? 'bg-ok' : 'bg-err']"
                            :title="isConnected ? 'Conectado' : 'Desconectado'"
                        ></span>
                    </div>
                    <button
                        @click="reconnect"
                        title="Reconectar"
                        class="w-6 h-6 flex items-center justify-center text-muted hover:text-ok transition-colors rounded text-xs"
                    >↻</button>
                    <button
                        @click="$emit('toggle')"
                        title="Cerrar terminal"
                        class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded text-sm"
                    >&times;</button>
                </div>
                <!-- xterm container -->
                <div ref="terminalContainer" class="flex-1 overflow-hidden min-h-0"></div>
            </div>
        </transition>

        <!-- Mobile -->
        <div v-if="isMobile && isOpen" class="flex flex-col h-full bg-base terminal-sidebar">
            <!-- Header -->
            <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-txt">Terminal</span>
                    <span
                        :class="['w-2 h-2 rounded-full', isConnected ? 'bg-ok' : 'bg-err']"
                        :title="isConnected ? 'Conectado' : 'Desconectado'"
                    ></span>
                </div>
                <button
                    @click="reconnect"
                    title="Reconectar"
                    class="w-6 h-6 flex items-center justify-center text-muted hover:text-ok transition-colors rounded text-xs"
                >↻</button>
                <button
                    @click="$emit('toggle')"
                    title="Cerrar"
                    class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded text-sm"
                >&times;</button>
            </div>
            <!-- xterm container -->
            <div ref="terminalContainer" class="flex-1 overflow-hidden min-h-0"></div>
            <!-- Mobile: special keys bar (2 rows) -->
            <div class="term-keys-bar">
                <!-- Row 1: modifiers + arrows + backspace -->
                <div class="term-keys-row">
                    <button
                        v-for="k in keyRow1" :key="k.label"
                        class="term-key"
                        :class="{ 'term-key-active': k.toggle && activeToggles[k.toggle] }"
                        @touchstart.prevent="onKeyTouch(k, $event)"
                        @mousedown.prevent="onKeyMouse(k, $event)"
                    >{{ k.label }}</button>
                </div>
                <!-- Row 2: navigation + symbols + enter -->
                <div class="term-keys-row">
                    <button
                        v-for="k in keyRow2" :key="k.label"
                        class="term-key"
                        @touchstart.prevent="onKeyTouch(k, $event)"
                        @mousedown.prevent="onKeyMouse(k, $event)"
                    >{{ k.label }}</button>
                </div>
            </div>
        </div>
    `,

    props: {
        isOpen: { type: Boolean, default: false },
        isMobile: { type: Boolean, default: false },
        sidebarWidth: { type: Number, default: 500 },
    },

    emits: ['toggle'],

    setup(props) {
        const terminalContainer = ref(null);
        let term = null;
        let fit = null;
        let resizeObserver = null;

        const terminal = useTerminal();

        // --- Mobile keyboard definitions ---
        const activeToggles = ref({ ctrl: false, alt: false });

        // Escape sequences for special keys
        const ESC = '\x1b';
        const keySequences = {
            Up:    `${ESC}[A`,
            Down:  `${ESC}[B`,
            Right: `${ESC}[C`,
            Left:  `${ESC}[D`,
            Home:  `${ESC}[H`,
            End:   `${ESC}[F`,
            PgUp:  `${ESC}[5~`,
            PgDn:  `${ESC}[6~`,
            Tab:   '\t',
            Esc:   ESC,
            Enter: '\r',
            Del:   `${ESC}[3~`,
            Bs:    '\x7f',
        };

        // Row 1: modifiers + arrows + backspace (8 keys)
        const keyRow1 = [
            { label: 'Ctrl',  toggle: 'ctrl', sticky: true },
            { label: 'Alt',   toggle: 'alt',  sticky: true },
            { label: 'Esc',   seq: keySequences.Esc },
            { label: 'Tab',   seq: keySequences.Tab },
            { label: '\u2190', seq: keySequences.Left },   // ←
            { label: '\u2191', seq: keySequences.Up },     // ↑
            { label: '\u2192', seq: keySequences.Right },  // →
            { label: '\u232B', seq: keySequences.Bs },     // ⌫
        ];

        // Row 2: ↓ under → (pos 7), same 8 keys so columns align
        const keyRow2 = [
            { label: 'Home',  seq: keySequences.Home },
            { label: 'End',   seq: keySequences.End },
            { label: 'PgUp',  seq: keySequences.PgUp },
            { label: 'PgDn',  seq: keySequences.PgDn },
            { label: 'Del',   seq: keySequences.Del },
            { label: '\u2193', seq: keySequences.Down },   // ↓ (under ↑)
            { label: '~', send: '~' },
            { label: '\u23CE', seq: keySequences.Enter },   // ⏎
        ];

        function sendToTerminal(data) {
            if (!term) return;
            term.paste(data);           // write into the terminal input
        }

        function fireKey(keyDef) {
            if (!term) return;

            // Toggle keys
            if (keyDef.toggle) {
                activeToggles.value[keyDef.toggle] = !activeToggles.value[keyDef.toggle];
                return;
            }

            // Build sequence with active modifiers
            let seq = keyDef.seq || '';
            let send = keyDef.send || '';
            const ctrl = activeToggles.value.ctrl;
            const alt = activeToggles.value.alt;

            // Reset toggles after use
            activeToggles.value.ctrl = false;
            activeToggles.value.alt = false;

            if (send) {
                // Plain character — apply modifiers
                if (ctrl) {
                    // Ctrl+A → \x01, Ctrl+B → \x02, etc.
                    const code = send.toUpperCase().charCodeAt(0);
                    if (code >= 64 && code <= 95) {
                        term.input(String.fromCharCode(code - 64));
                        return;
                    }
                }
                if (alt) {
                    term.input(`${ESC}${send}`);
                    return;
                }
                term.input(send);
                return;
            }

            if (seq) {
                if (alt) {
                    // Alt+Arrow → ESC + seq without leading ESC (xterm)
                    term.input(`${ESC}${seq.slice(1)}`);
                } else {
                    term.input(seq);
                }
            }
        }

        function onKeyTouch(keyDef, e) {
            fireKey(keyDef);
        }

        function onKeyMouse(keyDef, e) {
            fireKey(keyDef);
        }

        // Desktop resize
        const { width: resizedWidth, isResizing, resizeHandleProps } = useResizable({
            storageKey: 'terminal_sidebar_width',
            defaultWidth: props.sidebarWidth,
            minWidth: 300,
            maxWidth: 900,
            side: 'left',
        });

        const effectiveWidth = computed(() => resizedWidth.value);
        const isConnected = computed(() => terminal.isConnected.value);

        function createTerminal() {
            if (term) return;
            if (!terminalContainer.value) return;

            term = new Terminal({
                theme: TERMINAL_THEME,
                fontSize: 13,
                fontFamily: 'Menlo, Monaco, Consolas, "Courier New", monospace',
                cursorBlink: true,
                cursorStyle: 'block',
                scrollback: 5000,
                convertEol: true,
            });

            fit = new FitAddon();
            term.loadAddon(fit);
            term.loadAddon(new WebLinksAddon());
            term.open(terminalContainer.value);

            // Fit al tamaño del container
            try { fit.fit(); } catch (e) { /* ignore */ }

            // Registrar en composable (conecta onData/onResize al WS)
            // initTerminal ya llama a connect() si no hay WS activo
            terminal.initTerminal(term, fit);

            // ResizeObserver para auto-fit
            resizeObserver = new ResizeObserver(() => {
                if (fit && term) {
                    try { fit.fit(); } catch (e) { /* ignore */ }
                }
            });
            resizeObserver.observe(terminalContainer.value);
        }

        /**
         * Destruye el xterm pero NO desconecta el WebSocket.
         * El PTY sigue vivo en el backend.
         */
        function destroyTerminal() {
            if (resizeObserver) {
                resizeObserver.disconnect();
                resizeObserver = null;
            }
            if (term) {
                terminal.detachTerminal(); // solo desvincula xterm del WS
                term.dispose();
                term = null;
                fit = null;
            }
        }

        function reconnect() {
            terminal.disconnect();
            setTimeout(() => {
                terminal.connect();
            }, 200);
        }

        // Crear terminal cuando se abre
        watch(() => props.isOpen, async (open) => {
            if (open) {
                await nextTick();
                createTerminal();
            } else {
                destroyTerminal();
            }
        });

        // Crear terminal en mount si ya está abierto (mobile drawer)
        onMounted(async () => {
            if (props.isOpen) {
                await nextTick();
                createTerminal();
            }
        });

        onBeforeUnmount(() => {
            destroyTerminal();
        });

        return {
            terminalContainer,
            effectiveWidth,
            isResizing,
            resizeHandleProps,
            isConnected,
            reconnect,
            // Mobile keyboard
            keyRow1,
            keyRow2,
            activeToggles,
            onKeyTouch,
            onKeyMouse,
        };
    },
};
