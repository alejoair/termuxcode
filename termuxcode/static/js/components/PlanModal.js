import { computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Componente: Modal Plan
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-2xl w-full max-h-[90vh] flex flex-col">
                <div class="p-4 border-b border-border flex justify-between items-center flex-shrink-0">
                    <h3 class="text-lg font-semibold">Plan</h3>
                    <button
                        @click="handleReject"
                        class="text-muted hover:text-txt transition-colors text-xl leading-none"
                    >
                        ×
                    </button>
                </div>
                <div class="p-4 overflow-y-auto flex-1">
                    <div class="markdown-content prose prose-invert max-w-none" v-html="renderedPlan"></div>
                </div>
                <div class="p-4 border-t border-border flex gap-2 flex-shrink-0">
                    <button
                        @click="handleReject"
                        class="flex-1 bg-err/80 hover:bg-err text-txt py-2 rounded transition-colors font-medium"
                    >
                        Rechazar
                    </button>
                    <button
                        @click="handleApprove"
                        class="flex-1 bg-ok/80 hover:bg-ok text-txt py-2 rounded transition-colors font-medium"
                    >
                        Aceptar
                    </button>
                </div>
            </div>
        </div>
    `,

    props: ['plan'],

    emits: ['approve', 'reject'],

    setup(props, { emit }) {
        const renderedPlan = computed(() => {
            if (!props.plan) return '<em>No hay plan disponible</em>';
            try {
                const raw = window.marked ? window.marked.parse(props.plan) : props.plan.replace(/\n/g, '<br>');
                return window.DOMPurify ? window.DOMPurify.sanitize(raw) : raw;
            } catch {
                return props.plan;
            }
        });

        function handleApprove() {
            emit('approve');
        }

        function handleReject() {
            emit('reject');
        }

        return {
            renderedPlan,
            handleApprove,
            handleReject,
        };
    },
};
