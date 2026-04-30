// ===== Composable: useResizable — Drag-resize para sidebars =====

import { ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

/**
 * Composable reutilizable para resize de sidebars con drag.
 *
 * @param {object} opts
 * @param {string} opts.storageKey - Key para localStorage ('ccm_settings_' + key)
 * @param {number} opts.defaultWidth - Ancho por defecto
 * @param {number} opts.minWidth - Ancho mínimo
 * @param {number} opts.maxWidth - Ancho máximo
 * @param {'left'|'right'} opts.side - Lado del sidebar (define posición del handle)
 * @returns {{ width: ref<number>, isResizing: ref<boolean>, resizeHandleProps: object }}
 */
export function useResizable({ storageKey, defaultWidth, minWidth = 200, maxWidth = 800, side = 'left' }) {
    const STORAGE_PREFIX = 'ccm_settings_';

    // Cargar ancho guardado o usar default
    function loadWidth() {
        try {
            const saved = localStorage.getItem(STORAGE_PREFIX + storageKey);
            if (saved) {
                const val = parseInt(saved, 10);
                if (!isNaN(val) && val >= minWidth && val <= maxWidth) return val;
            }
        } catch {}
        return defaultWidth;
    }

    const width = ref(loadWidth());
    const isResizing = ref(false);

    function saveWidth() {
        try {
            localStorage.setItem(STORAGE_PREFIX + storageKey, String(width.value));
        } catch {}
    }

    function clamp(val) {
        return Math.max(minWidth, Math.min(maxWidth, val));
    }

    function startResize(clientX) {
        if (window.innerWidth < 768) return; // Solo desktop

        const startX = clientX;
        const startWidth = width.value;
        isResizing.value = true;
        document.body.classList.add('is-resizing');

        function onMove(e) {
            const clientXMove = e.touches ? e.touches[0].clientX : e.clientX;
            const delta = clientXMove - startX;
            // Sidebar izquierda: arrastrar a la derecha = más ancho
            // Sidebar derecha: arrastrar a la izquierda = más ancho
            const newWidth = side === 'left' ? startWidth + delta : startWidth - delta;
            width.value = clamp(newWidth);
        }

        function onUp() {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onUp);
            isResizing.value = false;
            document.body.classList.remove('is-resizing');
            saveWidth();
        }

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.addEventListener('touchmove', onMove, { passive: true });
        document.addEventListener('touchend', onUp);
    }

    const resizeHandleProps = {
        onMousedown: (e) => {
            e.preventDefault();
            startResize(e.clientX);
        },
        onTouchstart: (e) => {
            startResize(e.touches[0].clientX);
        },
        class: 'resize-handle',
        style: side === 'left' ? 'right: 0;' : 'left: 0;',
    };

    return { width, isResizing, resizeHandleProps };
}
