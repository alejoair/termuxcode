// ===== Composable: Editor Sidebar (singleton) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import { WsLspClient } from './WsLspClient.js';

// Singleton refs — compartidos entre todas las instancias
const openFiles = ref([]);
const activeFilePath = ref(null);
const expanded = ref(false);

// Singleton LSP client
const lspClient = new WsLspClient();

// Supported languages for LSP
const LSP_LANGUAGES = new Set(['python', 'javascript', 'typescript', 'html', 'css', 'json']);

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

// Pre-load default file
openFiles.value = [DEFAULT_FILE];
activeFilePath.value = DEFAULT_FILE.path;

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
            // Re-open in LSP if language is supported
            _lspOpenFile(path, content || existing.content, language || existing.language);
            return;
        }
        openFiles.value = [...openFiles.value, { path, name, content: content || '', language: language || 'text', dirty: false }];
        activeFilePath.value = path;
        expanded.value = true;
        // Open in LSP if language is supported
        _lspOpenFile(path, content || '', language || 'text');
    }

    function closeFile(path) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        const wasActive = activeFilePath.value === path;
        openFiles.value = openFiles.value.filter(f => f.path !== path);
        if (wasActive) {
            lspClient.close();
            if (openFiles.value.length > 0) {
                const newIdx = Math.min(idx, openFiles.value.length - 1);
                activeFilePath.value = openFiles.value[newIdx].path;
                // Re-open new active file in LSP
                const newFile = openFiles.value[newIdx];
                _lspOpenFile(newFile.path, newFile.content, newFile.language);
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
        // Switch LSP document
        lspClient.close();
        _lspOpenFile(file.path, file.content, file.language);
    }

    function toggleExpanded() {
        expanded.value = !expanded.value;
    }

    function updateFileContent(path, content) {
        const idx = openFiles.value.findIndex(f => f.path === path);
        if (idx === -1) return;
        // Replace the entry to guarantee reactivity triggers
        openFiles.value = openFiles.value.map(f =>
            f.path === path ? { ...f, content } : f
        );
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

    // ── LSP integration ──────────────────────────────────────────────

    function setLspSendFunction(fn) {
        lspClient.setSendFunction(fn);
    }

    function handleLspMessage(data) {
        lspClient.handleMessage(data);
    }

    function getLspClient() {
        return lspClient;
    }

    function _lspOpenFile(path, content, language) {
        if (!lspClient._sendFn) return;
        if (!LSP_LANGUAGES.has(language)) return;
        lspClient.open(path, content, language);
    }

    function reconnectLsp() {
        const file = activeFile.value;
        if (!file) return;
        lspClient.close();
        _lspOpenFile(file.path, file.content, file.language);
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
        updateFileContent,
        markDirty,
        markClean,
        // LSP
        setLspSendFunction,
        handleLspMessage,
        getLspClient,
        reconnectLsp,
    };
}
