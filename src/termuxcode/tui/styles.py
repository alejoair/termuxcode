"""CSS simple para layout vertical como mother.py"""

CSS = """
Screen {
    layout: vertical;
}

/* Header - altura fija pequeña */
Header {
    height: 3;
}

/* Contenedor del chat - ocupa el espacio restante */
VerticalScroll#chat-container {
    height: 1fr;
    width: 100%;
}

/* ChatLog */
ChatLog {
    height: 100%;
    width: 100%;
    background: $surface;
    color: $foreground;
    scrollbar-gutter: auto;
}

/* Bottom container (tabs + input) - altura fija */
#bottom-container {
    height: 5;
    width: 100%;
    background: $panel;
    border-top: solid $primary;
}

/* Tabs */
Tabs {
    height: 1;
    background: $panel;
    border-bottom: solid $primary 50%;
}

Tab {
    padding: 0 2;
    text-style: bold;
}

Tab.--active {
    background: $primary;
    color: $background;
}

/* Input container */
#input-container {
    height: 3;
    padding: 1 2;
}

/* Input */
#message-input {
    width: 100%;
    max-height: 3;
}

/* Placeholder del input */
#message-input > .input--placeholder {
    color: $text 50%;
    text-style: dim;
}

"""
