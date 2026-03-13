"""Estilos de tabs y sesiones"""

TABS_CSS = """
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

#sessions-tabs Tab:focus {
    background: transparent;
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
"""
