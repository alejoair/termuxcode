// Componente: Typing Indicator
export default {
    template: `
        <div v-if="visible" class="fixed bottom-32 left-1/2 transform -translate-x-1/2 bg-raised border border-border rounded-full px-4 py-2 flex items-center gap-2 z-40">
            <div class="typing-label text-sm">Claude</div>
            <div class="typing-bubble flex gap-1">
                <span class="typing-dot w-2 h-2 bg-accent rounded-full animate-bounce"></span>
                <span class="typing-dot w-2 h-2 bg-accent rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
                <span class="typing-dot w-2 h-2 bg-accent rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
            </div>
        </div>
    `,

    props: {
        visible: {
            type: Boolean,
            default: false,
        },
    },
};
