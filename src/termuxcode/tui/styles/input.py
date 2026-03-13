"""Estilos del input"""

INPUT_CSS = """
/* ═══════════════════════════════════════════════════════════════
   INPUT - Campo de mensaje compacto
   Usamos la clase -textual-compact que Textual provee
   ═══════════════════════════════════════════════════════════════ */

/* Sobrescribir estilos del input compacto */
#message-input.-textual-compact {
    width: 100%;
    height: 1;
    background: $surface;
    color: $text;
    padding: 0 1;
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
"""
