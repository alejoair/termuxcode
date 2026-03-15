"""Estilos completos de la TUI - Consolidado"""

CSS = """
/* ═══════════════════════════════════════════════════════════════
   SCREEN - Layout principal vertical, sin scroll
   ═══════════════════════════════════════════════════════════════ */
Screen {
    layout: vertical;
    background: $background;
    overflow-y: hidden;
    overflow-x: hidden;
}

/* ═══════════════════════════════════════════════════════════════
   XP BAR - Header compacto arriba
   ═══════════════════════════════════════════════════════════════ */
#xp-bar {
    height: 1;
    background: $panel;
    color: gold;
    padding: 0 1;
    content-align: left middle;
}

/* ChatLog - ocupa el espacio restante y scrollea */
#messages {
    height: 1fr;
    padding: 0 1;
}

/* Scrollbar minimalista */
#messages .scrollbar {
    background: $panel;
    color: $primary;
}

#messages .scrollbar:hover {
    background: $primary 20%;
}

#messages .scrollbar:focus {
    background: $primary 30%;
}

/* ═══════════════════════════════════════════════════════════
   BOTTOM CONTAINER - Tabs + Input (fijo abajo, visible con teclado)
   ═══════════════════════════════════════════════════════════ */
#bottom-container {
    height: auto;
    background: $panel;
    padding: 0;
    border-top: solid $primary;
    dock: bottom;
}

/* Fila de tabs (horizontal) */
#tabs-row {
    height: 2;
    background: $panel;
    align-horizontal: left;
    align-vertical: middle;
}

/* Spacer de 2 líneas para evitar que el input quede tapado por la barra de navegación */
#bottom-spacer {
    height: 2;
}

/* ═══════════════════════════════════════════════════════════
   INPUT ROW - Contenedor para input + botón Stop
   ═══════════════════════════════════════════════════════════ */
#input-row {
    height: 3;
    background: $panel;
    align-horizontal: left;
    align-vertical: middle;
    padding: 0 1;
    gap: 1;
}

/* ═══════════════════════════════════════════════════════════
   INPUT - Campo de mensaje compacto
   Usamos la clase -textual-compact que Textual provee
   ═════════════════════════════════════════════════════════════ */

/* Sobrescribir estilos del input compacto */
#message-input.-textual-compact {
    height: 1;
    background: $surface;
    color: $text;
    padding: 0 1;
    margin-bottom: 0;
    width: 1fr;
}

#message-input.-textual-compact:focus {
    background: $surface-darken-1;
}

/* Cursor */
#message-input.-textual-compact .input--cursor {
    background: $primary;
    color: $background;
}

/* Placeholder */
#message-input.-textual-compact .input--placeholder {
    color: $text-muted;
    text-style: italic;
}

/* ═══════════════════════════════════════════════════════════════
   TABS - En fila horizontal con botón
   ═══════════════════════════════════════════════════════════════ */
#sessions-tabs {
    height: 2;
    width: 1fr;
    background: $panel;
    border-bottom: solid $primary 50%;
}

/* Ocultar underline bar de Textual */
#sessions-tabs .underline--bar {
    display: none;
}

#sessions-tabs Tab {
    height: 2;
    padding: 0 1;
    text-style: none;
    background: transparent;
    color: $text-muted;
}

#sessions-tabs Tab:hover {
    background: $panel;
}

#sessions-tabs Tab.-active {
    color: $primary;
    text-style: bold;
}

/* Botón nueva sesión */
#new-session-btn {
    height: 2;
    width: 3;
    min-width: 3;
    padding: 0;
    margin: 0;
    background: transparent;
    color: $primary;
    border: none;
    text-style: bold;
}

#new-session-btn:hover {
    background: $primary 20%;
}

#new-session-btn:focus {
    background: $primary 20%;
    text-style: bold;
}

/* Botón Stop - al lado del input, mismo tamaño */
#stop-btn {
    height: 3;
    width: 3;
    min-width: 3;
    padding: 0;
    margin: 0;
    background: transparent;
    color: $warning;
    border: none;
    text-style: bold;
    align-vertical: middle;
}

/* Hover: warning color más claro */
#stop-btn:hover {
    background: $warning 20%;
    color: $warning;
}

/* Focus: indicación visual */
#stop-btn:focus {
    background: $warning 20%;
    text-style: bold;
}

/* Disabled: desvanecer significativamente */
#stop-btn:disabled {
    opacity: 0.3;
    color: $text-muted;
}

/* Active momentáneo al hacer click */
#stop-btn.-active {
    background: $warning;
    color: $text;
}

/* ═══════════════════════════════════════════════════════════════
   ACHIEVEMENT POPUP - Overlay en la parte inferior
   ═══════════════════════════════════════════════════════════════ */
AchievementPopup {
    display: none;
    height: 2;
    width: 100%;
    background: $primary 20%;
    color: $text;
    padding: 0 1;
    border-top: solid $primary;
    dock: bottom;
    layer: overlay;
}

AchievementPopup.visible {
    display: block;
}

/* ═══════════════════════════════════════════════════════════════
   LEVEL UP BANNER - Overlay en la parte superior
   ═══════════════════════════════════════════════════════════════ */
LevelUpBanner {
    display: none;
    height: 1;
    width: 100%;
    background: $success 30%;
    color: $success;
    text-style: bold;
    padding: 0 1;
    content-align: center middle;
    dock: top;
    layer: overlay;
}

LevelUpBanner.visible {
    display: block;
}
"""
