// Componente: Input Bar
import { ref, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

export default {
    template: `
        <div class="input-bar">
            <div class="toolbar-inner flex items-center gap-2">
                <!-- Sin pestaña activa -->
                <div v-if="noTab" class="flex-1 h-[38px] bg-base border border-border rounded flex items-center justify-center">
                    <span class="text-sm text-muted">Crea una pestaña para empezar</span>
                </div>
                <!-- Reconexion fallida -->
                <div v-else-if="disabled && failed" class="flex-1 h-[38px] bg-base border border-err/50 rounded flex items-center justify-center">
                    <span class="text-sm text-err">Reconexion fallida</span>
                </div>
                <!-- Reconectando (loading animation) -->
                <div v-else-if="disabled" class="flex-1 h-[38px] bg-base border border-border rounded overflow-hidden relative">
                    <div class="loading-bar"></div>
                    <span class="absolute inset-0 flex items-center justify-center text-sm text-muted">{{ loadingText }}</span>
                </div>
                <!-- Input normal (desktop: input, mobile: textarea) -->
                <input
                    v-else-if="!isMobile"
                    :value="message"
                    @input="$emit('update:message', $event.target.value)"
                    @keypress.enter.prevent="$emit('send')"
                    type="text"
                    placeholder="Escribe tu mensaje..."
                    class="flex-1 bg-base border border-border rounded px-3 py-2 text-txt placeholder-muted focus:outline-none focus:border-border-focus"
                >
                <textarea
                    v-else
                    ref="mobileInput"
                    :value="message"
                    @input="handleMobileInput($event)"
                    rows="1"
                    placeholder="Escribe tu mensaje..."
                    class="flex-1 bg-base border border-border rounded px-3 py-2 text-txt placeholder-muted focus:outline-none focus:border-border-focus resize-none max-h-32 overflow-y-auto"
                    style="min-height: 38px;"
                ></textarea>
                <button
                    @click="!disabled && $emit('send')"
                    :disabled="disabled"
                    :class="[
                        'p-2 rounded transition-colors flex-shrink-0',
                        disabled
                            ? 'bg-base text-muted cursor-not-allowed'
                            : 'bg-surface hover:bg-raised text-txt'
                    ]"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
        </div>
    `,

    props: {
        message: {
            type: String,
            default: '',
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        failed: {
            type: Boolean,
            default: false,
        },
        noTab: {
            type: Boolean,
            default: false,
        },
        loadingText: {
            type: String,
            default: 'Reconectando...',
        },
        isMobile: {
            type: Boolean,
            default: false,
        },
    },

    emits: ['update:message', 'send'],

    setup(props, { emit }) {
        const mobileInput = ref(null);

        function handleMobileInput(event) {
            emit('update:message', event.target.value);
            // Auto-resize textarea
            nextTick(() => {
                const el = event.target;
                if (el) {
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 128) + 'px';
                }
            });
        }

        return { mobileInput, handleMobileInput };
    },
};
