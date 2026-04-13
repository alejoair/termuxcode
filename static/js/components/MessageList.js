import { ref, watch, nextTick, onMounted } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { computeDiffLines } from '../composables/useMessages.js';

// Componente: Lista de Mensajes
export default {
    template: `
        <div ref="container" class="h-full">
            <div v-if="!messages || messages.length === 0" class="text-center text-muted py-8">
                Inicia una conversación...
            </div>

            <div v-else class="p-4 space-y-4">
                <!-- Messages -->
                <div
                    v-for="(msg, idx) in messages"
                    :key="idx"
                    :class="['message', getMessageClass(msg.type)]"
                >
                    <!-- Label -->
                    <div v-if="msg.type !== 'thinking'" class="message-label">
                        {{ getMessageLabel(msg.type) }}
                    </div>

                    <!-- Content -->
                    <div class="bubble">
                        <!-- Assistant text with markdown (msg.type === 'text') -->
                        <div
                            v-if="msg.type === 'text' && msg.html"
                            class="markdown-content"
                            v-html="msg.html"
                        ></div>

                        <!-- User message -->
                        <div v-else-if="msg.type === 'user'" class="text-content">
                            {{ msg.content }}
                        </div>

                        <!-- System message -->
                        <div v-else-if="msg.type === 'system'" class="text-content">
                            {{ msg.message }}
                        </div>

                        <!-- Tool Use: Edit — diff view -->
                        <div v-else-if="msg.type === 'tool_use' && msg.name === 'Edit'" class="tool-group">
                            <div class="tool-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">▸</span>
                                    <span class="tool-name">Edit</span>
                                    <span style="font-size:0.75rem;color:var(--color-text-muted);margin-left:0.5rem;">{{ msg.input.file_path }}</span>
                                </div>
                                <div class="accordion-item-content">
                                    <div class="diff-view">
                                        <div
                                            v-for="(dl, i) in getDiffLines(msg)"
                                            :key="i"
                                            :class="['diff-line', dl.type]"
                                        >
                                            <span class="diff-line-num">{{ dl.lineNum }}</span>
                                            <span class="diff-line-sign">{{ dl.sign }}</span>
                                            <span class="diff-line-content">{{ dl.content }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <!-- Tool Result agrupado -->
                            <div v-if="msg.result" class="tool-result-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">▸</span>
                                    <span class="tool-result-label">resultado</span>
                                </div>
                                <div class="tool-content accordion-item-content">
                                    <pre>{{ truncateContent(msg.result) }}</pre>
                                </div>
                            </div>
                        </div>

                        <!-- Tool Use: otros — accordion genérico -->
                        <div v-else-if="msg.type === 'tool_use'" class="tool-group">
                            <div class="tool-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">▸</span>
                                    <span class="tool-name">{{ msg.name }}</span>
                                </div>
                                <div class="tool-content accordion-item-content">
                                    {{ msg.info }}
                                </div>
                            </div>
                            <!-- Tool Result agrupado -->
                            <div v-if="msg.result" class="tool-result-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">▸</span>
                                    <span class="tool-result-label">resultado</span>
                                </div>
                                <div class="tool-content accordion-item-content">
                                    <pre>{{ truncateContent(msg.result) }}</pre>
                                </div>
                            </div>
                        </div>

                        <!-- Thinking Block -->
                        <div v-else-if="msg.type === 'thinking'" class="thinking-block accordion-item">
                            <div class="tool-header accordion-item-toggle">
                                <span class="tool-chevron">▸</span>
                                <span class="thinking-label">pensamiento</span>
                            </div>
                            <div class="thinking-content accordion-item-content">
                                {{ msg.content }}
                            </div>
                        </div>

                        <!-- Tool Result (sin tool_use asociado - fallback) -->
                        <div v-else-if="msg.type === 'tool_result'" class="tool-result-block accordion-item">
                            <div class="tool-header accordion-item-toggle">
                                <span class="tool-chevron">▸</span>
                                <span class="tool-result-label">resultado</span>
                            </div>
                            <div class="tool-content accordion-item-content">
                                <pre>{{ truncateContent(msg.content) }}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,

    props: {
        messages: {
            type: Array,
            default: () => [],
        },
    },

    emits: ['mounted'],

    setup(props, { emit }) {
        const container = ref(null);

        // Auto-scroll al final cuando cambian los mensajes
        watch(
            () => props.messages,
            async () => {
                await nextTick();
                scrollToBottom();
            },
            { deep: true }
        );

        function getMessageClass(type) {
            switch (type) {
                case 'user':
                    return 'user';
                case 'text':
                    return 'assistant';
                case 'system':
                    return 'system';
                case 'tool_use':
                    return 'tool-call';
                case 'thinking':
                    return 'thinking-msg';
                case 'tool_result':
                    return 'tool-result';
                default:
                    return '';
            }
        }

        function getMessageLabel(type) {
            switch (type) {
                case 'user':
                    return 'Tu';
                case 'text':
                    return 'Claude';
                default:
                    return '';
            }
        }

        function scrollToBottom() {
            if (container.value) {
                container.value.scrollTop = container.value.scrollHeight;
            }
        }

        function getDiffLines(msg) {
            if (!msg.input) return [];
            return computeDiffLines(msg.input.old_string, msg.input.new_string);
        }

        function truncateContent(content) {
            if (!content || typeof content !== 'string') return content;
            const limit = 1000;
            if (content.length > limit) {
                return content.slice(0, limit) + '\n\n...[truncated]';
            }
            return content;
        }

        // Manejar accordion toggle
        onMounted(() => {
            if (!container.value) return;

            container.value.addEventListener('click', (e) => {
                const toggle = e.target.closest('.accordion-item-toggle');
                if (!toggle) return;

                const item = toggle.closest('.accordion-item');
                if (!item) return;

                const content = item.querySelector('.accordion-item-content');
                if (!content) return;

                const isOpen = item.classList.contains('open');

                // Toggle current
                item.classList.toggle('open', !isOpen);
                content.style.display = isOpen ? '' : 'block';

                // Rotar chevron
                const chevron = toggle.querySelector('.tool-chevron');
                if (chevron) {
                    chevron.style.transform = isOpen ? '' : 'rotate(90deg)';
                }
            });

            emit('mounted', container.value);
        });

        return {
            container,
            getMessageClass,
            getMessageLabel,
            scrollToBottom,
            getDiffLines,
            truncateContent,
        };
    },
};
