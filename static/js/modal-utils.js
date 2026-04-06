// ===== Utilidades compartidas para modales =====

/**
 * Escapa caracteres HTML para prevenir XSS
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Crea un elemento overlay para un modal
 */
export function createOverlay(id, className = 'question-overlay') {
    const overlay = document.createElement('div');
    overlay.className = className;
    overlay.id = id;
    return overlay;
}

/**
 * Muestra un overlay añadiéndolo al DOM
 */
export function showModal(overlay) {
    document.body.appendChild(overlay);
}

/**
 * Oculta y limpia un modal de un Map de estado
 */
export function hideModal(modalMap, tabId) {
    const state = modalMap.get(tabId);
    if (state) {
        state.overlay.remove();
        modalMap.delete(tabId);
    }
}
