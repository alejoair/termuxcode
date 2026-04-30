// Componente: Modal Tool Approval
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
                <!-- Header -->
                <div class="p-4 border-b border-border">
                    <h3 class="text-lg font-semibold">Aprobación de Herramienta</h3>
                </div>

                <!-- Content -->
                <div class="p-4 space-y-4">
                    <div>
                        <label class="text-sm text-muted">Herramienta</label>
                        <div class="mt-1 p-2 bg-surface rounded font-mono text-sm">
                            {{ modal.toolName }}
                        </div>
                    </div>

                    <div>
                        <label class="text-sm text-muted">Input</label>
                        <div class="mt-1 p-2 bg-surface rounded font-mono text-sm overflow-x-auto">
                            <pre>{{ modal.input }}</pre>
                        </div>
                    </div>

                    <div class="bg-warn/20 border border-warn/50 rounded p-3">
                        <p class="text-sm text-warn">
                            ¿Deseas aprobar la ejecución de esta herramienta?
                        </p>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-border flex gap-2">
                    <button
                        @click="handleReject"
                        class="flex-1 bg-err hover:bg-err text-txt py-2 rounded transition-colors"
                    >
                        Rechazar
                    </button>
                    <button
                        @click="handleApprove"
                        class="flex-1 bg-ok hover:bg-ok text-txt py-2 rounded transition-colors"
                    >
                        Aprobar
                    </button>
                </div>
            </div>
        </div>
    `,

    props: ['modal'],

    emits: ['approve', 'reject'],

    setup(props, { emit }) {
        function handleApprove() {
            emit('approve', { approved: true });
        }

        function handleReject() {
            emit('reject', { approved: false });
        }

        return {
            handleApprove,
            handleReject,
        };
    },
};
