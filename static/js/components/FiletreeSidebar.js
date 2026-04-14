// Componente: Filetree Sidebar (panel izquierdo siempre visible, slim/expanded modes)
export default {
    template: `
        <div
            :class="[
                'flex flex-col h-full bg-base border-r border-border flex-shrink-0 select-text overflow-hidden transition-[width] duration-200',
                expanded ? 'w-80' : 'w-12'
            ]"
        >
            <!-- ===== Slim mode ===== -->
            <template v-if="!expanded">
                <div
                    @click="$emit('toggle-expanded')"
                    class="flex flex-col items-center py-2 h-full cursor-pointer"
                >
                    <!-- Folder icon -->
                    <svg class="w-4 h-4 text-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <!-- File icons stacked vertically -->
                    <div class="flex flex-col gap-1 overflow-y-auto flex-1 py-1">
                        <div
                            v-for="node in topLevelItems"
                            :key="node.path"
                            class="flex items-center justify-center"
                            :title="node.name"
                        >
                            <span class="text-xs">{{ nodeIcon(node) }}</span>
                        </div>
                    </div>
                    <!-- Count badge -->
                    <div class="mt-2 text-[10px] font-mono text-muted" :title="fileCount + ' archivos'">
                        {{ fileCount }}
                    </div>
                </div>
            </template>

            <!-- ===== Expanded mode ===== -->
            <template v-else>
                <!-- Header -->
                <div class="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
                    <div class="flex items-center gap-2">
                        <svg class="w-3.5 h-3.5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                        <span class="text-xs font-medium text-txt">Archivos</span>
                        <span class="text-xs text-muted">{{ fileCount }} archivos</span>
                    </div>
                    <div class="flex items-center gap-1">
                        <button @click="$emit('expand-all')" title="Expandir todo"
                            class="text-muted hover:text-txt transition-colors p-0.5 rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                            </svg>
                        </button>
                        <button @click="$emit('collapse-all')" title="Colapsar todo"
                            class="text-muted hover:text-txt transition-colors p-0.5 rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M9 9V4H4m0 0l5 5M9 20v-5H4m0 0l5-5m11-5h-5v5m0-5l-5 5m5 10v-5h5m0 0l-5-5" />
                            </svg>
                        </button>
                        <button @click="$emit('toggle-expanded')" title="Colapsar"
                            class="text-muted hover:text-txt transition-colors p-0.5 rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <!-- Tree -->
                <div class="overflow-y-auto flex-1 py-1 text-xs font-mono">
                    <template v-for="node in tree" :key="node.path">
                        <filetree-node
                            :node="node"
                            :depth="0"
                            :expanded-paths="expandedPaths"
                            @toggle="n => $emit('toggle-path', n.path)"
                        />
                    </template>
                    <div v-if="!tree.length" class="px-3 py-4 text-muted text-center">
                        Sin archivos
                    </div>
                </div>
            </template>
        </div>
    `,

    props: {
        tree: { type: Array, default: () => [] },
        expanded: { type: Boolean, default: false },
        expandedPaths: { type: Set, default: () => new Set() },
        fileCount: { type: Number, default: 0 },
    },

    emits: ['toggle-expanded', 'toggle-path', 'expand-all', 'collapse-all'],

    computed: {
        topLevelItems() {
            return this.tree.slice(0, 30);
        },
    },

    methods: {
        nodeIcon(node) {
            if (node.type === 'dir') return '\uD83D\uDCC1';
            const ext = node.name.split('.').pop().toLowerCase();
            const map = {
                js: '\uD83D\uDCDC', ts: '\uD83D\uDCDC', py: '\uD83D\uDC0D',
                json: '{ }', md: '\uD83D\uDCDD', html: '\uD83C\uDF10',
                css: '\uD83C\uDFA8', vue: '\uD83D\uDE80', yml: '\u2699\uFE0F',
                yaml: '\u2699\uFE0F', sh: '\uD83D\uDDA5\uFE0F', bash: '\uD83D\uDDA5\uFE0F',
                txt: '\uD83D\uDCD4', env: '\uD83D\uDD10', gitignore: '\uD83D\uDD10',
            };
            return map[ext] || '\uD83D\uDCC4';
        },
    },
};

// Sub-componente recursivo para nodos del arbol
const FiletreeNode = {
    name: 'filetree-node',
    template: `
        <div>
            <div @click="node.type === 'dir' && $emit('toggle', node)"
                :class="[
                    'flex items-center gap-1 cursor-pointer px-2 py-0.5 hover:bg-surface/50 transition-colors select-none',
                    node.type === 'file' ? 'text-txt/80' : 'text-txt'
                ]"
                :style="{ paddingLeft: (depth * 12 + 8) + 'px' }"
            >
                <!-- Chevron para dirs -->
                <svg v-if="node.type === 'dir'"
                    class="w-3 h-3 text-muted flex-shrink-0 transition-transform"
                    :class="{ 'rotate-90': isExpanded }"
                    fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
                </svg>
                <span v-else class="w-3 flex-shrink-0"></span>

                <!-- Icono -->
                <span class="flex-shrink-0">{{ icon }}</span>

                <!-- Nombre -->
                <span class="truncate">{{ node.name }}</span>
            </div>

            <!-- Hijos (solo dirs expandidos) -->
            <template v-if="node.type === 'dir' && isExpanded && node.children">
                <filetree-node
                    v-for="child in node.children"
                    :key="child.path"
                    :node="child"
                    :depth="depth + 1"
                    :expanded-paths="expandedPaths"
                    @toggle="n => $emit('toggle', n)"
                />
            </template>
        </div>
    `,

    props: {
        node: { type: Object, required: true },
        depth: { type: Number, default: 0 },
        expandedPaths: { type: Set, default: () => new Set() },
    },

    emits: ['toggle'],

    computed: {
        isExpanded() {
            return this.expandedPaths.has(this.node.path);
        },
        icon() {
            if (this.node.type === 'dir') {
                return this.isExpanded ? '\uD83D\uDCC2' : '\uD83D\uDCC1';
            }
            const ext = this.node.name.split('.').pop().toLowerCase();
            const map = {
                js: '\uD83D\uDCDC', ts: '\uD83D\uDCDC', py: '\uD83D\uDC0D',
                json: '{ }', md: '\uD83D\uDCDD', html: '\uD83C\uDF10',
                css: '\uD83C\uDFA8', vue: '\uD83D\uDE80', yml: '\u2699\uFE0F',
                yaml: '\u2699\uFE0F', sh: '\uD83D\uDDA5\uFE0F', bash: '\uD83D\uDDA5\uFE0F',
                txt: '\uD83D\uDCD4', env: '\uD83D\uDD10', gitignore: '\uD83D\uDD10',
            };
            return map[ext] || '\uD83D\uDCC4';
        },
    },
};

// Exportar sub-componente para registro global
export { FiletreeNode };
