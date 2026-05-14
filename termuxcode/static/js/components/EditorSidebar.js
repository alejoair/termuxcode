// Componente: Editor Sidebar (panel derecho con CodeMirror 6)

import { computed, watch } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState, Compartment } from '@codemirror/state';
import { oneDark } from '@codemirror/theme-one-dark';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { html as htmlLang } from '@codemirror/lang-html';
import { css as cssLang } from '@codemirror/lang-css';
import { json as jsonLang } from '@codemirror/lang-json';
import { markdown as mdLang } from '@codemirror/lang-markdown';
import { diffExtension, setDiffRanges as applyDiffRanges, clearDiffDecorations } from '../editor/diff-extensions.js';
import { useResizable } from '../composables/useResizable.js';
import { getFileIcon } from '../composables/useFileIcons.js';

function getLang(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
        case 'py': return python();
        case 'js': return javascript();
        case 'jsx': return javascript({ jsx: true });
        case 'ts': return javascript({ typescript: true });
        case 'tsx': return javascript({ jsx: true, typescript: true });
        case 'html': case 'htm': return htmlLang();
        case 'css': return cssLang();
        case 'json': return jsonLang();
        case 'md': case 'markdown': return mdLang();
        default: return [];
    }
}

function fileIconSvg(name) {
    const ext = name.split('.').pop().toLowerCase();
    const inner = getFileIcon(ext);
    return `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${inner}</svg>`;
}

export default {
    template: `
        <div
            :class="[
                'flex flex-col h-full bg-base select-text overflow-hidden editor-sidebar',
                isMobile
                    ? ''
                    : 'border-l border-border flex-shrink-0 relative' + (expanded ? '' : ' w-12')
            ]"
            :style="isMobile || !expanded ? {} : { width: effectiveWidth + 'px', transition: isResizing ? 'none' : 'width 0.2s' }"
        >
            <!-- Resize handle (izquierda, es sidebar derecha) -->
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
                    <!-- Code icon -->
                    <svg class="w-4 h-4 text-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <!-- File icons stacked vertically -->
                    <div class="flex flex-col gap-1 overflow-y-auto flex-1 py-1">
                        <div
                            v-for="file in openFiles"
                            :key="file.path"
                            class="flex items-center justify-center relative"
                            :title="file.name + (file.dirty ? ' (modificado)' : '')"
                        >
                            <span class="text-muted" v-html="fileIcon(file.name)"></span>
                            <span v-if="file.dirty" class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-yellow-400"></span>
                        </div>
                    </div>
                    <!-- Count badge -->
                    <div class="mt-2 text-[10px] font-mono text-muted" :title="openFiles.length + ' archivos'">
                        {{ openFiles.length }}
                    </div>
                </div>
            </template>

            <!-- ===== Expanded mode (siempre en mobile) ===== -->
            <template v-if="isMobile || expanded">
                <!-- Header -->
                <div class="flex items-center justify-between px-3 py-1.5 border-b border-border flex-shrink-0">
                    <div class="flex items-center gap-2">
                        <svg class="w-3.5 h-3.5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                        </svg>
                        <span class="text-xs font-medium text-txt">Editor</span>
                        <span class="text-xs text-muted font-mono" v-if="activeFile">{{ activeFile.name }}</span>
                        <span v-if="activeFile && activeFile.dirty" class="w-2 h-2 rounded-full bg-yellow-400" title="Sin guardar"></span>
                    </div>
                    <div class="flex items-center gap-1">
                        <!-- Save button -->
                        <button v-if="activeFile && activeFileDirty" @click="handleSave" title="Guardar (Ctrl+S)"
                            class="w-6 h-6 flex items-center justify-center text-yellow-400 hover:text-yellow-300 transition-colors rounded">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round"
                                    d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                            </svg>
                        </button>
                        <!-- Clear diff button -->
                        <button v-if="hasDiff" @click="handleClearDiff" title="Descartar diff"
                            class="w-6 h-6 flex items-center justify-center text-ok hover:text-accent transition-colors rounded">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                        <!-- Save status -->
                        <span v-if="saveStatus" class="text-[10px] text-green-400 mr-1">{{ saveStatus }}</span>
                        <button v-if="!isMobile" @click="$emit('toggle-expanded')" title="Colapsar"
                            class="w-6 h-6 flex items-center justify-center text-muted hover:text-txt transition-colors rounded">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                            </svg>
                        </button>
                    </div>
                </div>

                <!-- Tabs bar -->
                <div v-if="openFiles.length > 0"
                    class="flex border-b border-border overflow-x-auto flex-shrink-0"
                    style="scrollbar-width: none; -ms-overflow-style: none;">
                    <div
                        v-for="file in openFiles"
                        :key="file.path"
                        :class="['editor-tab', file.path === activeFilePath ? 'active' : '']"
                        @click="$emit('set-active', file.path)"
                    >
                        <span class="editor-tab-icon" v-html="fileIcon(file.name)"></span>
                        <span>{{ file.name }}</span>
                        <span v-if="file.dirty" class="w-1.5 h-1.5 rounded-full bg-yellow-400 ml-0.5"></span>
                        <span class="close-btn" @click.stop="$emit('close-file', file.path)">&times;</span>
                    </div>
                </div>

                <!-- Editor container -->
                <div ref="editorContainer" class="flex-1 overflow-hidden min-h-0"></div>

                <!-- Empty state -->
                <div v-if="openFiles.length === 0" class="flex-1 flex items-center justify-center text-muted text-xs">
                    No hay archivos abiertos
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
        openFiles: { type: Array, default: () => [] },
        activeFilePath: { type: String, default: null },
        expanded: { type: Boolean, default: false },
        isMobile: { type: Boolean, default: false },
        expandedWidth: { type: Number, default: 500 },
        diffRanges: { type: Object, default: null },
    },

    emits: ['toggle-expanded', 'close-file', 'set-active', 'file-dirty', 'save-file', 'update-content', 'clear-diff'],

    setup(props) {
        const { width: resizedWidth, isResizing, resizeHandleProps } = useResizable({
            storageKey: 'editor_sidebar_width',
            defaultWidth: props.expandedWidth,
            minWidth: 300,
            maxWidth: 900,
            side: 'right',
        });

        const effectiveWidth = computed(() => resizedWidth.value);

        // When width changes, tell CodeMirror to recalculate layout
        watch(effectiveWidth, () => {
            // editorView is in data(), accessible via this in methods
            // but in setup we can't access it. Use requestAnimationFrame instead.
            requestAnimationFrame(() => {
                const editorEl = document.querySelector('.editor-sidebar .cm-editor');
                if (editorEl && editorEl.cmView) {
                    editorEl.cmView.view.requestMeasure();
                }
            });
        });

        return { isResizing, resizeHandleProps, effectiveWidth };
    },

    data() {
        return {
            editorView: null,
            saveStatus: '',
            hasDiff: false,
            _saveStatusTimeout: null,
            _langCompartment: new Compartment(),
            _diffCompartment: new Compartment(),
            _dirtyListener: null,
        };
    },

    computed: {
        activeFile() {
            return this.openFiles.find(f => f.path === this.activeFilePath) || null;
        },
        activeContent() {
            return this.activeFile?.content ?? '';
        },
        activeFileDirty() {
            return this.activeFile?.dirty ?? false;
        },
    },

    watch: {
        expanded(val) {
            if (val) {
                this.$nextTick(() => this.mountEditor());
            } else {
                this.destroyEditor();
            }
        },
        activeFilePath(newPath, oldPath) {
            // Before switching, preserve current editor content
            if (oldPath && this.editorView) {
                const content = this.editorView.state.doc.toString();
                this.$emit('update-content', { path: oldPath, content });
            }
            if (this.expanded) {
                this.$nextTick(() => this.updateEditor());
            }
            // Re-apply diff for the new active file
            this.$nextTick(() => {
                if (this.diffRanges && this.diffRanges.addRanges?.length + this.diffRanges.removeRanges?.length > 0) {
                    this._applyDiffToView(this.diffRanges);
                } else {
                    this._clearDiffFromView();
                }
            });
        },
        activeContent(newVal) {
            if (this.expanded) {
                // Skip if editor already shows this content (e.g. after save)
                if (this.editorView && this.editorView.state.doc.toString() === newVal) return;
                this.$nextTick(() => this.updateEditor());
            }
        },
        diffRanges(newRanges) {
            this.$nextTick(() => {
                if (newRanges && (newRanges.addRanges?.length + newRanges.removeRanges?.length > 0)) {
                    this._applyDiffToView(newRanges);
                } else {
                    this._clearDiffFromView();
                }
            });
        },
    },

    mounted() {
        if (this.expanded) {
            this.$nextTick(() => this.mountEditor());
        }
        // Ctrl+S listener
        this._keydownHandler = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.handleSave();
            }
        };
        document.addEventListener('keydown', this._keydownHandler);
    },

    beforeUnmount() {
        this.destroyEditor();
        if (this._keydownHandler) {
            document.removeEventListener('keydown', this._keydownHandler);
            this._keydownHandler = null;
        }
        if (this._saveStatusTimeout) {
            clearTimeout(this._saveStatusTimeout);
        }
    },

    methods: {
        mountEditor() {
            const container = this.$refs.editorContainer;
            if (!container || this.editorView) return;

            const file = this.activeFile;
            const content = file ? file.content : '';
            const lang = file ? getLang(file.name) : [];

            this._dirtyListener = EditorView.updateListener.of((tr) => {
                if (tr.docChanged && this.activeFilePath) {
                    this.$emit('file-dirty', { path: this.activeFilePath });
                    // Auto-clear diff when user edits
                    if (this.hasDiff) {
                        this._clearDiffFromView();
                    }
                }
            });

            try {
                this.editorView = new EditorView({
                    state: EditorState.create({
                        doc: content,
                        extensions: [
                            basicSetup, oneDark,
                            this._langCompartment.of(lang),
                            this._diffCompartment.of(diffExtension()),
                            this._dirtyListener,
                        ],
                    }),
                    parent: container,
                });
            } catch (e) {
                console.error('[EditorSidebar] Error creating editor:', e);
            }
        },

        updateEditor() {
            if (!this.editorView) {
                this.mountEditor();
                return;
            }
            const file = this.activeFile;
            if (!file) return;

            try {
                const currentContent = this.editorView.state.doc.toString();
                const lang = getLang(file.name);
                const dispatches = [];

                // Reconfigure language compartment
                dispatches.push(this._langCompartment.reconfigure(lang));
                // Note: _diffCompartment NO se reconfigura aquí — el StateField
                // mapea las decoraciones automáticamente con decorations.map(tr.changes)

                // Only replace document content if it actually changed
                if (currentContent !== file.content) {
                    dispatches.push({
                        changes: {
                            from: 0,
                            to: currentContent.length,
                            insert: file.content,
                        },
                    });
                }

                this.editorView.dispatch(...dispatches);
            } catch (e) {
                console.error('[EditorSidebar] Error updating editor:', e);
            }
        },

        destroyEditor() {
            if (this.editorView) {
                this.editorView.destroy();
                this.editorView = null;
            }
            // Recreate compartments so next mountEditor starts fresh
            this._langCompartment = new Compartment();
            this._diffCompartment = new Compartment();
            this._dirtyListener = null;
            this.hasDiff = false;
        },

        handleSave() {
            if (!this.editorView || !this.activeFilePath) return;
            const content = this.editorView.state.doc.toString();
            this.$emit('save-file', { path: this.activeFilePath, content });
        },

        /**
         * Show diff decorations from externally provided ranges.
         * Called by app-vue.js after computing diff.
         * @param {{ addRanges: Array, removeRanges: Array }} ranges
         */
        showDiff(ranges) {
            this._applyDiffToView(ranges);
        },

        _applyDiffToView(ranges) {
            if (!this.editorView) return;
            applyDiffRanges(this.editorView, ranges);
            this.hasDiff = true;
        },

        _clearDiffFromView() {
            if (!this.editorView) return;
            clearDiffDecorations(this.editorView);
            this.hasDiff = false;
        },

        handleClearDiff() {
            this._clearDiffFromView();
            if (this.activeFilePath) {
                this.$emit('clear-diff', { path: this.activeFilePath });
            }
        },

        showSaveStatus(text) {
            this.saveStatus = text;
            if (this._saveStatusTimeout) clearTimeout(this._saveStatusTimeout);
            this._saveStatusTimeout = setTimeout(() => {
                this.saveStatus = '';
            }, 2000);
        },

        fileIcon(name) {
            return fileIconSvg(name);
        },
    },
};
