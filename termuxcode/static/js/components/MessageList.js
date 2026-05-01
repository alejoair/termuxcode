import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { computeDiffLines } from '../composables/useMessages.js';

const LOADING_MESSAGES = [
    'Inicializando red neuronal',
    'Cargando contexto del proyecto',
    'Analizando patrones de codigo',
    'Calibrando flujo de tokens',
    'Mapeando dependencias',
    'Procesando AST',
    'Ejecutando heuristicas',
    'Sincronizando contexto',
    'Decodificando embeddings',
    'Evaluando hipotesis',
    'Resolviendo ambiguedades',
    'Generando soluciones',
    'Indexando simbolos',
    'Explorando el grafo de codigo',
    'Optimizando la respuesta',
    'Calculando la mejor estrategia',
    'Construyendo el plan de accion',
    'Recopilando informacion relevante',
    'Verificando invariantes',
    'Expandiendo macros',
];

const LOADING_TIPS = [
    'Usa /stop para interrumpir la respuesta',
    'La sidebar de archivos se actualiza tras cada query',
    'Las tareas del agente aparecen en el widget de TODO',
    'Los logs del servidor se ven en la sidebar de logs',
    'Puedes cambiar el modelo desde la configuracion',
    'Usa la modal MCP para gestionar servidores',
];

// Componente: Lista de Mensajes
export default {
    template: `
        <div ref="container" class="h-full">
            <div v-if="!messages || messages.length === 0" class="text-center text-muted py-8">
                Inicia una conversacion...
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
                    <div class="bubble" style="position:relative;">
                        <!-- Per-query stats badge (top-right corner of assistant text) -->
                        <div v-if="msg.type === 'text' && msg.queryStats" class="query-stats-badge">
                            <span title="Input tokens">{{ formatTokens(msg.queryStats.inputTokens) }} in</span>
                            <span class="text-border">|</span>
                            <span title="Output tokens">{{ formatTokens(msg.queryStats.outputTokens) }} out</span>
                        </div>
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
                                    <span class="tool-chevron">&#9656;</span>
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
                                    <span class="tool-chevron">&#9656;</span>
                                    <span class="tool-result-label">resultado</span>
                                </div>
                                <div class="tool-content accordion-item-content">
                                    <pre>{{ truncateContent(msg.result) }}</pre>
                                </div>
                            </div>
                        </div>

                        <!-- Tool Use: otros — accordion generico -->
                        <div v-else-if="msg.type === 'tool_use'" class="tool-group">
                            <div class="tool-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">&#9656;</span>
                                    <span class="tool-name">{{ msg.name }}</span>
                                </div>
                                <div class="tool-content accordion-item-content">
                                    {{ msg.info }}
                                </div>
                            </div>
                            <!-- Tool Result agrupado -->
                            <div v-if="msg.result" class="tool-result-block accordion-item">
                                <div class="tool-header accordion-item-toggle">
                                    <span class="tool-chevron">&#9656;</span>
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
                                <span class="tool-chevron">&#9656;</span>
                                <span class="thinking-label">pensamiento</span>
                            </div>
                            <div class="thinking-content accordion-item-content">
                                {{ msg.content }}
                            </div>
                        </div>

                        <!-- Ask User Question (inline in chat) -->
                        <div v-else-if="msg.type === 'ask_user_question'" class="ask-question-block">
                            <div v-for="(q, qi) in msg.questions" :key="qi" class="mb-3">
                                <span v-if="q.header" class="inline-block text-xs font-medium px-2 py-0.5 rounded bg-accent/20 text-accent mb-1">
                                    {{ q.header }}
                                </span>
                                <p class="text-sm mb-1">{{ q.question }}</p>
                                <ul class="list-disc list-inside text-xs text-muted space-y-0.5">
                                    <li v-for="(opt, oi) in q.options" :key="oi">{{ opt.label }}</li>
                                </ul>
                            </div>
                        </div>

                        <!-- Tool Result (sin tool_use asociado - fallback) -->
                        <div v-else-if="msg.type === 'tool_result'" class="tool-result-block accordion-item">
                            <div class="tool-header accordion-item-toggle">
                                <span class="tool-chevron">&#9656;</span>
                                <span class="tool-result-label">resultado</span>
                            </div>
                            <div class="tool-content accordion-item-content">
                                <pre>{{ truncateContent(msg.content) }}</pre>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Loading message (retro game style) -->
                <div v-if="isProcessing" class="message assistant loading-msg">
                    <div class="message-label">Claude</div>
                    <div class="bubble" style="border-left-color: #0d9488;">
                        <div class="font-mono text-xs space-y-2">
                            <!-- Progress bar -->
                            <div class="flex items-center gap-2">
                                <span class="text-teal-600">&#9484;</span>
                                <div class="flex-1 h-3 bg-zinc-800 rounded-sm overflow-hidden border border-zinc-700 relative">
                                    <div class="loading-bar-fill h-full transition-all duration-300 ease-out"
                                         :style="{ width: Math.max(3, loadingProgress) + '%', background: 'linear-gradient(90deg, #0d9488, #14b8a6, #2dd4bf)' }">
                                    </div>
                                    <div class="loading-bar-shimmer absolute inset-0"></div>
                                </div>
                                <span class="text-teal-500 w-8 text-right font-bold">{{ Math.round(loadingProgress) }}%</span>
                                <span class="text-teal-600">&#9492;</span>
                            </div>

                            <!-- Status line -->
                            <div class="flex items-center gap-1.5 text-teal-400/90 pl-1">
                                <span class="loading-spinner-icon">&#10227;</span>
                                <span>{{ loadingMessage }}</span>
                                <span class="loading-cursor text-teal-300">&#9608;</span>
                            </div>

                            <!-- Tip line -->
                            <div class="text-zinc-600 pl-1 flex items-center gap-1.5">
                                <span class="text-zinc-700">&#9472;&#9472;</span>
                                <span class="text-zinc-500">{{ loadingTip }}</span>
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
        isProcessing: {
            type: Boolean,
            default: false,
        },
        scrollRatio: {
            type: Number,
            default: null,
        },
    },

    emits: ['mounted', 'scroll-change'],

    setup(props, { emit }) {
        const container = ref(null);
        let _hasRestoredScroll = false;
        let _scrollTimeout = null;
        let _isMounted = false;

        // Loading state
        const loadingProgress = ref(0);
        const loadingMessage = ref(LOADING_MESSAGES[0]);
        const loadingTip = ref(LOADING_TIPS[0]);
        let _loadingStartTime = 0;
        let _progressInterval = null;
        let _messageInterval = null;
        let _tipInterval = null;

        function _pickRandom(arr) {
            return arr[Math.floor(Math.random() * arr.length)];
        }

        function _startLoading() {
            _loadingStartTime = Date.now();
            loadingProgress.value = 0;
            loadingMessage.value = _pickRandom(LOADING_MESSAGES);
            loadingTip.value = _pickRandom(LOADING_TIPS);

            _progressInterval = setInterval(() => {
                const elapsed = Date.now() - _loadingStartTime;
                // Curva asintotica: rapido al inicio, lento despues (nunca llega a 95%)
                loadingProgress.value = Math.min(95, 100 * (1 - Math.exp(-elapsed / 12000)));
            }, 150);

            _messageInterval = setInterval(() => {
                loadingMessage.value = _pickRandom(LOADING_MESSAGES);
            }, 3000);

            _tipInterval = setInterval(() => {
                loadingTip.value = _pickRandom(LOADING_TIPS);
            }, 7000);
        }

        function _stopLoading() {
            loadingProgress.value = 100;
            clearInterval(_progressInterval);
            clearInterval(_messageInterval);
            clearInterval(_tipInterval);
            _progressInterval = null;
            _messageInterval = null;
            _tipInterval = null;
        }

        // Watch processing state
        watch(() => props.isProcessing, (val) => {
            if (val) {
                _startLoading();
                nextTick(() => scrollToBottom());
            } else {
                _stopLoading();
            }
        });

        // Auto-scroll al final cuando cambian los mensajes
        watch(
            () => props.messages,
            async () => {
                await nextTick();
                if (!_hasRestoredScroll) {
                    scrollToBottom();
                }
            },
            { deep: true }
        );

        onUnmounted(() => {
            _isMounted = false;
            _stopLoading();
            if (_scrollTimeout) {
                clearTimeout(_scrollTimeout);
                _scrollTimeout = null;
            }
        });

        function getMessageClass(type) {
            switch (type) {
                case 'user': return 'user';
                case 'text': return 'assistant';
                case 'system': return 'system';
                case 'tool_use': return 'tool-call';
                case 'thinking': return 'thinking-msg';
                case 'tool_result': return 'tool-result';
                case 'ask_user_question': return 'assistant';
                default: return '';
            }
        }

        function getMessageLabel(type) {
            switch (type) {
                case 'user': return 'Tu';
                case 'text': return 'Claude';
                case 'system': return 'Sistema';
                case 'ask_user_question': return 'Claude';
                default: return '';
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

        function formatTokens(n) {
            if (!n) return '0';
            if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
            return String(n);
        }

        // Manejar accordion toggle
        onMounted(() => {
            _isMounted = true;
            if (!container.value) return;

            // Restaurar posición de scroll si hay ratio guardado
            if (props.scrollRatio != null && props.scrollRatio > 0) {
                nextTick(() => {
                    if (container.value) {
                        const targetTop = props.scrollRatio * container.value.scrollHeight;
                        container.value.scrollTop = targetTop;
                        _hasRestoredScroll = true;
                    }
                });
            }

            // Emitir scroll-change con debounce al hacer scroll manual
            container.value.addEventListener('scroll', () => {
                if (_scrollTimeout) clearTimeout(_scrollTimeout);
                _scrollTimeout = setTimeout(() => {
                    if (!_isMounted || !container.value) return;
                    const ratio = container.value.scrollHeight > 0
                        ? container.value.scrollTop / container.value.scrollHeight
                        : 0;
                    emit('scroll-change', ratio);
                }, 200);
            }, { passive: true });

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
            loadingProgress,
            loadingMessage,
            loadingTip,
            getMessageClass,
            getMessageLabel,
            scrollToBottom,
            getDiffLines,
            truncateContent,
            formatTokens,
        };
    },
};
