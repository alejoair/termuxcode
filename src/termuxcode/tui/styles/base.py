"""Estilos base - Layout principal"""

BASE_CSS = """
/* ═══════════════════════════════════════════════════════════════
   SCREEN - Layout principal vertical, sin scroll
   ═══════════════════════════════════════════════════════════════ */
Screen {
    layout: vertical;
    background: $background;
    overflow-y: hidden;
    overflow-x: hidden;
}

/* Prevenir scroll cuando algún widget está maximizado (sobrescribe CSS de Textual) */
Screen.-maximized-view {
    overflow-y: hidden !important;
}

/* ═══════════════════════════════════════════════════════════════
   XP BAR - Header compacto arriba
   ═══════════════════════════════════════════════════════════════ */
#xp-bar {
    height: 1;
    width: 100%;
    background: $panel;
    color: gold;
    padding: 0 1;
    content-align: left middle;
}

/* ═══════════════════════════════════════════════════════════════
   BOTTOM CONTAINER - Tabs + Input (fijo abajo, visible con teclado)
   ═══════════════════════════════════════════════════════════════ */
#bottom-container {
    height: auto;
    width: 100%;
    min-height: 3;
    max-height: 5;
    background: $panel;
    padding: 0;
    border-top: solid $primary;
    dock: bottom;
}

/* Fila de tabs (horizontal) */
#tabs-row {
    height: 2;
    width: 100%;
    background: $panel;
    align-horizontal: left;
    align-vertical: middle;
}
"""
