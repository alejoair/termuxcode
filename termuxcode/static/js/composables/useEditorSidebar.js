// ===== Composable: Editor Sidebar (singleton) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// API base: in Tauri mode (tauri:// protocol) relative URLs don't work
const _API_BASE = window.location.protocol === 'tauri:' ? 'http://localhost:1988' : '';
// Singleton refs — compartidos entre todas las instancias
const openFiles = ref([]);
const activeFilePath = ref(null);
const expanded = ref(false);

// Diff state: path → { ranges: { addRanges, removeRanges } }
const diffState = ref({});

// Flag para inicialización desde estado persistido
let _initialized = false;

const DEFAULT_FILE = {
    path: '__welcome__.py',
    name: 'welcome.py',
    content: [
        '# TERMUXCODE Editor',
        '# Double-click files in the file tree to open them here',
        '',
        'def greet(name: str) -> str:',
        '    """Generate a greeting message."""',
        '    return f"Hello, {name}!"',
        '',
        '',
        'def fibonacci(n: int) -> list[int]:',
        '    """Return first n Fibonacci numbers."""',
        '    if n <= 0:',
        '        return []',
        '    if n == 1:',
        '        return [0]',
        '    fib = [0, 1]',
        '    for _ in range(2, n):',
        '        fib.append(fib[-1] + fib[-2])',
        '    return fib',
        '',
        '',
        'if __name__ == "__main__":',
        '    print(greet("World"))',
        '    print(fibonacci(10))',
    ].join('\n'),
    language: 'python',
    dirty: false,
};

// Pre-load default file (solo si no se restaura desde estado persistido)
// initializeFromState() se llama desde useUiState.restore() antes del primer render.
// Si no se llama, se carga el default en la primera invocación.
let _defaultLoaded = false;
function _ensureDefault() {
    if (_defaultLoaded) return;
    _defaultLoaded = true;
    if (openFiles.value.length === 0) {
        openFiles.value = [DEFAULT_FILE];
        activeFilePath.value = DEFAULT_FILE.path;
    }
}

export function useEditorSidebar() {
    const activeFile = computed(() =>
        openFiles.value.find(f => f.path === activeFilePath.value) || null
    );

    const openFileCount = computed(() => openFiles.value.length);

    function openFile(path, name, content, language) {
        const existing = openFiles.value.find(f => f.path === path);
        if (existing) {
            // Si ya existe, actualizar contenido y activar
            if (content !== undefined) existing.content = content;
            activeFilePath.value = path;
            expanded.value = true;
            return;
        }
        openFiles.value = [...openFiles.value, { path, name, content: content || '', language: language || 'text', dirty: false }];
        activeFilePath.value = path;
        expanded.value = true;
    }

    function closeFile(path) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        const wasActive = activeFilePath.value === path;
        openFiles.value = openFiles.value.filter(f => f.path !== path);
        if (wasActive) {
            if (openFiles.value.length > 0) {
                const newIdx = Math.min(idx, openFiles.value.length - 1);
                activeFilePath.value = openFiles.value[newIdx].path;
            } else {
                activeFilePath.value = null;
                expanded.value = false;
            }
        }
    }

    function setActiveFile(path) {
        const file = openFiles.value.find(f => f.path === path);
        if (!file) return;
        const oldPath = activeFilePath.value;
        if (oldPath === path) return;
        activeFilePath.value = path;
    }

    function toggleExpanded() {
        expanded.value = !expanded.value;
    }

    function setExpanded(val) {
        expanded.value = val;
    }

    function updateFileContent(path, content) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        // Mutate in-place first so the editor watcher can compare correctly,
        // then trigger reactivity by replacing the array
        const updated = { ...openFiles.value[idx], content };
        const newFiles = [...openFiles.value];
        newFiles[idx] = updated;
        openFiles.value = newFiles;
    }

    function markDirty(path) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        openFiles.value = openFiles.value.map(f =>
            f.path === path ? { ...f, dirty: true } : f
        );
    }

    function markClean(path) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        openFiles.value = openFiles.value.map(f =>
            f.path === path ? { ...f, dirty: false } : f
        );
    }

    // ── Diff state ────────────────────────────────────────────

    function setDiffRanges(path, ranges) {
        diffState.value = { ...diffState.value, [path]: ranges };
    }

    function getDiffRanges(path) {
        return diffState.value[path] || null;
    }

    function clearDiff(path) {
        const next = { ...diffState.value };
        delete next[path];
        diffState.value = next;
    }

    function clearAllDiffs() {
        diffState.value = {};
    }

    /**
     * Inicializa el estado del editor desde datos persistidos.
     * Se llama una vez desde useUiState.restore() antes del primer render.
     * @param {{ expanded: boolean, width: number, openFiles: Array, activeFilePath: string|null }} state
     */
    async function initializeFromState(state) {
        if (_initialized) return;
        _initialized = true;
        _defaultLoaded = true; // Prevenir carga del default

        if (!state) {
            openFiles.value = [DEFAULT_FILE];
            activeFilePath.value = DEFAULT_FILE.path;
            return;
        }

        // Restaurar estado expandido
        if (state.expanded !== undefined) expanded.value = state.expanded;

        // Restaurar archivos abiertos (sin contenido — se fetch vía /api/file)
        if (state.openFiles && state.openFiles.length > 0) {
            const files = state.openFiles.map(f => ({
                path: f.path,
                name: f.name,
                content: '// Cargando...',
                language: f.language || 'text',
                dirty: false,
            }));
            openFiles.value = files;
            activeFilePath.value = state.activeFilePath || files[0].path;

            // Fetch contenido real de cada archivo en paralelo
            await Promise.allSettled(
                files.map(async (f) => {
                    try {
                        const res = await fetch(_API_BASE + '/api/file?path=' + encodeURIComponent(f.path));
                        if (res.ok) {
                            const data = await res.json();
                            updateFileContent(f.path, data.content);
                        } else {
                            updateFileContent(f.path, `// Error: archivo no encontrado`);
                        }
                    } catch {
                        updateFileContent(f.path, `// Error de conexión`);
                    }
                })
            );
        } else {
            openFiles.value = [DEFAULT_FILE];
            activeFilePath.value = DEFAULT_FILE.path;
        }
    }

    return {
        openFiles,
        activeFilePath,
        activeFile,
        expanded,
        openFileCount,
        openFile,
        closeFile,
        setActiveFile,
        toggleExpanded,
        setExpanded,
        initializeFromState,
        updateFileContent,
        markDirty,
        markClean,
        // Diff
        setDiffRanges,
        getDiffRanges,
        clearDiff,
        clearAllDiffs,
    };
}
