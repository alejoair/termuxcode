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

/* ═══════════════════════════════════════════════════════════════
   CHAT CONTAINER - Solo este tiene scroll
   ═══════════════════════════════════════════════════════════════ */
#chat-container {
    height: 1fr;
    overflow-y: scroll;
    overflow-x: hidden;
    scrollbar-gutter: stable;
    scrollbar-size: 1 1;
}

/* ChatLog widget */
#messages {
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
   INPUT - Campo de mensaje compacto
   Usamos la clase -textual-compact que Textual provee
   ═════════════════════════════════════════════════════════════ */

/* Sobrescribir estilos del input compacto */
#message-input.-textual-compact {
    height: 1;
    background: $surface;
    color: $text;
    padding: 0 1;
    margin-bottom: 1;
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
