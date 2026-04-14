// ===== Composable: Filetree Sidebar (singleton) =====

import { ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

// Refs singleton — compartidas entre todas las instancias
const tree = ref([]);
const cwd = ref('');
const expanded = ref(false);
const expandedPaths = ref(new Set());

export function useFiletree() {
    const fileCount = computed(() => {
        let count = 0;
        function walk(nodes) {
            for (const n of nodes) {
                if (n.type === 'file') count++;
                else if (n.children) walk(n.children);
            }
        }
        walk(tree.value);
        return count;
    });

    const dirCount = computed(() => {
        let count = 0;
        function walk(nodes) {
            for (const n of nodes) {
                if (n.type === 'dir') {
                    count++;
                    if (n.children) walk(n.children);
                }
            }
        }
        walk(tree.value);
        return count;
    });

    function setTree(entries, newCwd) {
        tree.value = entries || [];
        if (newCwd) cwd.value = newCwd;
    }

    function togglePath(path) {
        const s = new Set(expandedPaths.value);
        if (s.has(path)) s.delete(path);
        else s.add(path);
        expandedPaths.value = s;
    }

    function toggleExpanded() {
        expanded.value = !expanded.value;
    }

    function collapseAll() {
        expandedPaths.value = new Set();
    }

    function expandAll() {
        const s = new Set();
        function walk(nodes) {
            for (const n of nodes) {
                if (n.type === 'dir') {
                    s.add(n.path);
                    if (n.children) walk(n.children);
                }
            }
        }
        walk(tree.value);
        expandedPaths.value = s;
    }

    return {
        tree,
        cwd,
        expanded,
        expandedPaths,
        fileCount,
        dirCount,
        setTree,
        togglePath,
        toggleExpanded,
        collapseAll,
        expandAll,
    };
}
