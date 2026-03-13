"""Estilos del chat - ChatLog y container"""

CHAT_CSS = """
/* ═══════════════════════════════════════════════════════════════
   CHAT CONTAINER - Ocupa todo el espacio disponible
   ═══════════════════════════════════════════════════════════════ */
#chat-container {
    height: 1fr;
    width: 100%;
    background: $background;
    overflow-x: hidden;
    overflow-y: auto;
}

/* ChatLog widget */
#messages {
    height: 100%;
    width: 100%;
    background: $background;
    color: $text;
    scrollbar-gutter: stable;
    scrollbar-size: 1 1;
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
"""
