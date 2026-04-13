// Componente: Modal File View
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                <div class="p-4 border-b border-border flex justify-between items-center">
                    <h3 class="text-lg font-semibold">{{ filePath }}</h3>
                    <button
                        @click="handleClose"
                        class="text-muted hover:text-txt transition-colors"
                    >
                        ×
                    </button>
                </div>
                <div class="flex-1 overflow-auto p-4">
                    <pre class="text-sm bg-base p-4 rounded overflow-x-auto">{{ content }}</pre>
                </div>
            </div>
        </div>
    `,

    props: ['filePath', 'content'],

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
