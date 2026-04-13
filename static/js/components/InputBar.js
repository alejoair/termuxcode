// Componente: Input Bar
export default {
    template: `
        <div class="input-bar">
            <div class="toolbar-inner flex items-center gap-2">
                <input
                    :value="message"
                    @input="$emit('update:message', $event.target.value)"
                    @keypress.enter.prevent="$emit('send')"
                    type="text"
                    placeholder="Escribe tu mensaje..."
                    class="flex-1 bg-base border border-border rounded px-3 py-2 text-txt placeholder-muted focus:outline-none focus:border-border-focus"
                >
                <button
                    @click="$emit('send')"
                    class="bg-surface hover:bg-raised text-txt p-2 rounded transition-colors"
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
    },

    emits: ['update:message', 'send'],

    setup() {
        return {};
    },
};
