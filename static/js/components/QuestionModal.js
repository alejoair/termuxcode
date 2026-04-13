import { reactive, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Componente: Modal AskUserQuestion
export default {
    template: `
        <div class="fixed inset-0 bg-base/80 flex items-center justify-center z-50 p-4">
            <div class="bg-raised border border-border rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
                <!-- Header -->
                <div class="p-4 border-b border-border">
                    <h3 class="text-lg font-semibold">Pregunta</h3>
                </div>

                <!-- Content -->
                <div class="p-4 space-y-4">
                    <div v-for="(q, qIdx) in modal.questions" :key="qIdx" class="question-block">
                        <p class="mb-2 text-sm">{{ q.question }}</p>

                        <div class="space-y-2">
                            <button
                                v-for="(opt, oIdx) in q.options"
                                :key="oIdx"
                                @click="selectOption(qIdx, oIdx)"
                                :class="[
                                    'w-full text-left px-3 py-2 rounded text-sm transition-colors',
                                    isSelected(qIdx, oIdx)
                                        ? 'bg-accent text-txt'
                                        : 'bg-surface hover:bg-raised'
                                ]"
                            >
                                <span class="font-medium">{{ opt.label }}</span>
                                <span v-if="opt.description" class="block text-xs opacity-70 mt-1">
                                    {{ opt.description }}
                                </span>
                            </button>
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
                        @click="handleSubmit"
                        :disabled="!hasAnswers"
                        class="flex-1 bg-accent hover:bg-accent disabled:bg-accent/50 disabled:cursor-not-allowed text-txt py-2 rounded transition-colors"
                    >
                        Enviar
                    </button>
                </div>
            </div>
        </div>
    `,

    props: ['modal'],

    emits: ['submit', 'cancel'],

    setup(props, { emit }) {
        const selectedAnswers = reactive({});

        function isSelected(qIdx, oIdx) {
            const answer = selectedAnswers[qIdx];
            if (Array.isArray(answer)) {
                return answer.includes(oIdx);
            }
            return answer === oIdx;
        }

        function selectOption(qIdx, oIdx) {
            const question = props.modal.questions[qIdx];

            if (question.multiSelect) {
                const current = selectedAnswers[qIdx] || [];
                if (current.includes(oIdx)) {
                    selectedAnswers[qIdx] = current.filter(i => i !== oIdx);
                } else {
                    selectedAnswers[qIdx] = [...current, oIdx];
                }
            } else {
                selectedAnswers[qIdx] = oIdx;
            }
        }

        const hasAnswers = computed(() => {
            return props.modal.questions.every((q, qIdx) => {
                const answer = selectedAnswers[qIdx];
                return answer !== undefined && answer !== null;
            });
        });

        function handleSubmit() {
            const responses = Object.entries(selectedAnswers).map(([qIdx, answer]) => {
                const question = props.modal.questions[parseInt(qIdx)];
                return {
                    question: question.question,
                    answers: Array.isArray(answer) ? answer : [answer],
                };
            });

            emit('submit', { responses, cancelled: false });
        }

        function handleCancel() {
            emit('cancel', { cancelled: true });
        }

        return {
            isSelected,
            selectOption,
            hasAnswers,
            handleSubmit,
            handleCancel,
        };
    },
};
