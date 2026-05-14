// Componente: Filetree Sidebar (panel izquierdo siempre visible, slim/expanded modes)
import { computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { useResizable } from '../composables/useResizable.js';
import { getFileIcon, getFolderIcon, getFileColor } from '../composables/useFileIcons.js';

export default {
    template: `
        <div
            :class="[
                'flex flex-col h-full bg-base select-text overflow-hidden',
                isMobile
                    ? ''
                    : 'border-r border-border flex-shrink-0 relative' + (expanded ? '' : ' w-12')
            ]"
            :style="isMobile || !expanded ? {} : { width: effectiveWidth + 'px', transition: isResizing ? 'none' : 'width 0.2s' }"
        >
            <!-- Resize handle (derecha, es sidebar izquierda) -->
            <div
                v-if="!isMobile && expanded"
                v-bind="resizeHandleProps"
                :class="{ active: isResizing }"
            ></div>
            <!-- ===== Slim mode (solo desktop) ===== -->
            <template v-if="!isMobile && !expanded">
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
                            <svg v-if="node.type === 'dir'" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="getFolderIcon(false)"></svg>
                            <svg v-else class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="nodeIcon(node)"></svg>
                        </div>
                    </div>
                    <!-- Count badge -->
                    <div class="mt-2 text-[10px] font-mono text-muted" :title="fileCount + ' archivos'">
                        {{ fileCount }}
                    </div>
                </div>
            </template>

            <!-- ===== Expanded mode (siempre en mobile) ===== -->
            <template v-if="isMobile || expanded">
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
                        <button v-if="!isMobile" @click="$emit('toggle-expanded')" title="Colapsar"
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
                            @open-file="p => $emit('open-file', p)"
                        />
                    </template>
                    <div v-if="!tree.length" class="px-3 py-4 text-muted text-center">
                        Sin archivos
                    </div>
                </div>

                <!-- Mobile: close button at bottom -->
                <div v-if="isMobile" class="flex-shrink-0 border-t border-border p-2" style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom, 0px))">
                    <button @click="$emit('toggle-expanded')"
                        class="w-full py-2 rounded bg-surface text-txt text-xs hover:bg-raised transition-colors">
                        Cerrar
                    </button>
                </div>
            </template>
        </div>
    `,

    props: {
        tree: { type: Array, default: () => [] },
        expanded: { type: Boolean, default: false },
        expandedPaths: { type: Set, default: () => new Set() },
        fileCount: { type: Number, default: 0 },
        isMobile: { type: Boolean, default: false },
        expandedWidth: { type: Number, default: 320 },
    },

    emits: ['toggle-expanded', 'toggle-path', 'expand-all', 'collapse-all', 'open-file'],

    setup(props) {
        const { width: resizedWidth, isResizing, resizeHandleProps } = useResizable({
            storageKey: 'filetree_sidebar_width',
            defaultWidth: props.expandedWidth,
            minWidth: 200,
            maxWidth: 600,
            side: 'left',
        });

        const effectiveWidth = computed(() => resizedWidth.value);

        return { isResizing, resizeHandleProps, effectiveWidth };
    },

    computed: {
        topLevelItems() {
            return this.tree.slice(0, 30);
        },
    },

    methods: {
        getFolderIcon,
        nodeIcon(node) {
            if (node.type === 'dir') return getFolderIcon(false);
            const ext = node.name.split('.').pop().toLowerCase();
            return getFileIcon(ext);
        },
    },
};

// Sub-componente recursivo para nodos del arbol
const FiletreeNode = {
    name: 'filetree-node',
    template: `
        <div>
            <div @click="node.type === 'dir' ? $emit('toggle', node) : $emit('open-file', node.path)"
                class="relative flex items-center gap-1 cursor-pointer py-0.5 hover:bg-surface/60 transition-colors select-none"
                :style="{ paddingLeft: (depth * 12 + 8) + 'px', paddingRight: '6px' }"
            >
                <!-- Chevron para dirs -->
                <svg v-if="node.type === 'dir'"
                    class="w-3 h-3 flex-shrink-0 transition-transform"
                    :class="isExpanded ? 'rotate-90' : ''"
                    :style="{ color: iconColor }"
                    fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
                </svg>
                <span v-else class="w-3 flex-shrink-0"></span>

                <!-- Icono SVG con color -->
                <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke-width="2"
                    :style="{ stroke: iconColor }"
                    v-html="icon"></svg>

                <!-- Nombre: dirs en blanco brillante, files con color del tipo -->
                <span class="truncate text-xs"
                    :style="{ color: node.type === 'dir' ? '#e2e8f0' : iconColor }">
                    {{ node.name }}
                </span>
            </div>

            <!-- Hijos con línea guía vertical -->
            <div v-if="node.type === 'dir' && isExpanded && node.children" class="relative">
                <!-- línea guía: posicionada al nivel del icono de esta carpeta -->
                <div class="absolute top-0 bottom-0 pointer-events-none"
                    :style="{ left: (depth * 12 + 15) + 'px', width: '1px', background: '#243040' }">
                </div>
                <filetree-node
                    v-for="child in node.children"
                    :key="child.path"
                    :node="child"
                    :depth="depth + 1"
                    :expanded-paths="expandedPaths"
                    @toggle="n => $emit('toggle', n)"
                    @open-file="p => $emit('open-file', p)"
                />
            </div>
        </div>
    `,

    props: {
        node: { type: Object, required: true },
        depth: { type: Number, default: 0 },
        expandedPaths: { type: Set, default: () => new Set() },
    },

    emits: ['toggle', 'open-file'],

    computed: {
        isExpanded() {
            return this.expandedPaths.has(this.node.path);
        },
        ext() {
            if (this.node.type === 'dir') return '';
            return this.node.name.split('.').pop().toLowerCase();
        },
        icon() {
            if (this.node.type === 'dir') return getFolderIcon(this.isExpanded);
            return getFileIcon(this.ext);
        },
        iconColor() {
            return getFileColor(this.ext, this.node.type === 'dir');
        },
    },
};

// Exportar sub-componente para registro global
export { FiletreeNode };
