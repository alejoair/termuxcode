"""CSS responsive para la TUI"""

CSS = """
Screen {
    layout: vertical;
    height: 100%;
}

/* ChatLog */
ChatLog {
    height: 1fr;
    width: 100%;
    background: $surface;
    color: $foreground;
    overflow-y: scroll;
    scrollbar-gutter: auto;
}

/* Header */
#header {
    height: auto;
    padding: 0 1;
    background: $panel;
    border-bottom: solid $primary 50%;
    content-align: center middle;
    min-height: 1;
}

/* Ocultar header en pantallas pequeñas */
Screen.-small #header {
    display: none;
}

/* Contenedor del chat */
#chat-container {
    height: 1fr;
    width: 100%;
}

/* Input container */
#input-container {
    height: auto;
    padding: 1 2;
    background: $panel;
    border-top: solid $primary;
    min-height: 3;
}

/* Input */
#message-input {
    width: 100%;
    max-height: 10;
}

/* Placeholder del input */
#message-input > .input--placeholder {
    color: $text 50%;
    text-style: dim;
}

/* Responsive: pantallas pequeñas */
Screen.-small {
    & #input-container {
        padding: 0 1;
    }
}

/* Responsive: pantallas medianas */
Screen.-medium {
    & #chat-container {
        padding: 1 2;
    }
}

/* Responsive: pantallas grandes */
Screen.-large {
    & #chat-container {
        padding: 2 4;
    }
}
"""
