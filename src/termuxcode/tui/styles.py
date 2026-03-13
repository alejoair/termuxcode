"""CSS simple para layout vertical como mother.py"""

CSS = """
Screen {
    layout: vertical;
}

/* Header - altura fija pequeña */
Header {
    height: 3;
    background: $panel;
}

/* Contenedor del chat - ocupa el espacio restante */
VerticalScroll#chat-container {
    height: 1fr;
    width: 100%;
    background: $surface;
}

/* ChatLog */
ChatLog {
    height: 100%;
    width: 100%;
    background: $surface;
    color: $foreground;
    scrollbar-gutter: auto;
    padding: 0 1;
}

/* Bottom container (tabs + input) - altura fija */
#bottom-container {
    height: 7;
    width: 100%;
    background: $panel;
    border-top: solid $primary;
}

/* Contenedor horizontal de tabs + botón */
#tabs-list {
    height: 2;
    width: 100%;
    background: $panel;
}

/* Tabs - altura 2 incluye underline */
Tabs {
    height: 2;
    width: 1fr;
    background: $panel;
}

Tabs .underline--bar {
    color: $primary;
    background: $foreground 10%;
}

/* Tab styling */
Tab {
    padding: 0 2;
    text-style: bold;
    background: transparent;
}

Tab:hover {
    background: $primary 10%;
}

Tab.-active {
    color: $primary;
    background: transparent;
}

Tab:focus {
    background: transparent;
    text-style: bold;
}

/* Botón de nueva sesión */
#new-session-btn {
    height: 1;
    width: 3;
    min-width: 3;
    margin: 0 1;
    background: $primary 20%;
    color: $primary;
    border: none;
}

#new-session-btn:hover {
    background: $primary 40%;
}

#new-session-btn:focus {
    background: $primary;
    color: $background;
}

/* Input container */
#input-container {
    height: 4;
    padding: 0 1;
    background: $panel;
}

/* Input */
#message-input {
    width: 100%;
    height: 3;
    background: $surface;
    border: solid $primary 30%;
    padding: 0 1;
}

#message-input:focus {
    border: solid $primary;
    background: $background;
}

#message-input:focus > .input--cursor {
    background: $primary;
    color: $background;
}

/* Placeholder del input */
#message-input > .input--placeholder {
    color: $text-muted;
    text-style: dim;
}

"""
