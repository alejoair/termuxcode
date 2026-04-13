import { reactive, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Componente: Modal Settings
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <!-- Header -->
                <div class="p-4 border-b border-border flex justify-between items-center">
                    <h3 class="text-lg font-semibold">Configuración</h3>
                    <button
                        @click="handleClose"
                        class="text-muted hover:text-txt transition-colors"
                    >
                        ×
                    </button>
                </div>

                <!-- Content -->
                <div class="p-4 space-y-4">
                    <!-- Session Section -->
                    <div class="settings-section">
                        <h4 class="text-sm font-medium text-muted mb-3">Sesión</h4>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-xs text-muted">Modo de permisos</label>
                                <select
                                    v-model="localSettings.permission_mode"
                                    class="w-full mt-1 bg-surface border border-border rounded px-3 py-2 text-sm"
                                >
                                    <option value="default">default</option>
                                    <option value="acceptEdits">acceptEdits</option>
                                    <option value="plan">plan</option>
                                    <option value="bypassPermissions">bypassPermissions</option>
                                </select>
                            </div>

                            <div>
                                <label class="text-xs text-muted">Modelo</label>
                                <select
                                    v-model="localSettings.model"
                                    class="w-full mt-1 bg-surface border border-border rounded px-3 py-2 text-sm"
                                >
                                    <option value="sonnet">sonnet</option>
                                    <option value="opus">opus</option>
                                    <option value="haiku">haiku</option>
                                </select>
                            </div>

                            <div>
                                <label class="text-xs text-muted">Ventana de historial</label>
                                <input
                                    v-model.number="localSettings.rolling_window"
                                    type="number"
                                    min="10"
                                    class="w-full mt-1 bg-surface border border-border rounded px-3 py-2 text-sm"
                                >
                            </div>
                        </div>
                    </div>

                    <!-- Tools Section -->
                    <div class="settings-section">
                        <h4 class="text-sm font-medium text-muted mb-3">
                            Herramientas
                            <span class="text-xs text-muted font-normal">— vacío = todas</span>
                        </h4>

                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                            <label
                                v-for="tool in availableTools"
                                :key="tool.name"
                                class="flex items-center gap-2 p-2 bg-surface rounded cursor-pointer hover:bg-raised"
                                :title="tool.desc || tool.name"
                            >
                                <input
                                    type="checkbox"
                                    :value="tool.name"
                                    v-model="localSettings.tools"
                                    class="rounded"
                                >
                                <span class="text-xs">{{ tool.name }}</span>
                            </label>
                        </div>
                    </div>

                    <!-- System Prompt Section -->
                    <div class="settings-section">
                        <h4 class="text-sm font-medium text-muted mb-3">Prompts del Sistema</h4>

                        <div>
                            <label class="text-xs text-muted">System prompt</label>
                            <textarea
                                v-model="localSettings.system_prompt"
                                rows="3"
                                class="w-full mt-1 bg-surface border border-border rounded px-3 py-2 text-sm resize-none"
                                placeholder="Prompt personalizado..."
                            ></textarea>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-border flex gap-2">
                    <button
                        @click="handleCancel"
                        class="flex-1 bg-surface hover:bg-raised text-txt py-2 rounded transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        @click="handleSave"
                        class="flex-1 bg-accent hover:bg-accent text-txt py-2 rounded transition-colors"
                    >
                        Guardar
                    </button>
                </div>
            </div>
        </div>
    `,

    props: ['tabId', 'settings', 'availableTools'],

    emits: ['close', 'save'],

    setup(props, { emit }) {
        // Copia local de settings
        const localSettings = reactive({
            permission_mode: props.settings?.permission_mode || 'acceptEdits',
            model: props.settings?.model || 'sonnet',
            rolling_window: props.settings?.rolling_window || 100,
            tools: [...(props.settings?.tools || [])],
            system_prompt: props.settings?.system_prompt || '',
        });

        function handleSave() {
            emit('save', { ...localSettings });
        }

        function handleCancel() {
            emit('close');
        }

        function handleClose() {
            emit('close');
        }

        const availableTools = computed(() => props.availableTools || []);

        return {
            localSettings,
            availableTools,
            handleSave,
            handleCancel,
            handleClose,
        };
    },
};
