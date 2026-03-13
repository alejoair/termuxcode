"""Estilos base - Layout principal"""

BASE_CSS = """
/* ═══════════════════════════════════════════════════════════════
   SCREEN - Layout principal vertical
   ═══════════════════════════════════════════════════════════════ */
Screen {
    layout: vertical;
    background: $background;
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
   BOTTOM CONTAINER - Tabs + Input (fijo abajo)
   ═══════════════════════════════════════════════════════════════ */
#bottom-container {
    height: auto;
    width: 100%;
    background: $panel;
    padding: 0;
    border-top: solid $primary;
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
