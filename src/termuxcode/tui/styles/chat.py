"""Estilos del chat - ChatLog y container"""

CHAT_CSS = """
/* ═══════════════════════════════════════════════════════════════
   CHAT CONTAINER - Solo este tiene scroll
   ═══════════════════════════════════════════════════════════════ */
#chat-container {
    height: 1fr;
    width: 100%;
    background: $background;
    overflow-y: scroll;
    overflow-x: hidden;
    scrollbar-gutter: stable;
    scrollbar-size: 1 1;
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
