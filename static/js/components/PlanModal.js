// Componente: Modal Plan
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-4 border-b border-border flex justify-between items-center">
                    <h3 class="text-lg font-semibold">Plan</h3>
                    <button
                        @click="handleClose"
                        class="text-muted hover:text-txt transition-colors"
                    >
                        ×
                    </button>
                </div>
                <div class="p-4">
                    <div class="prose prose-invert max-w-none">
                        <div v-html="plan || 'No hay plan disponible'"></div>
                    </div>
                </div>
            </div>
        </div>
    `,

    props: ['plan'],

    emits: ['close'],

    setup(props, { emit }) {
        function handleClose() {
            emit('close');
        }

        return {
            handleClose,
        };
    },
};
