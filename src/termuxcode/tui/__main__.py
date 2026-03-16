"""Punto de entrada para python -m termuxcode.tui"""
import sys
from pathlib import Path

# Añadir el directorio src al path si es necesario
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from termuxcode.tui.app import ClaudeChat

if __name__ == "__main__":
    # Permitir pasar argumentos de línea de comandos
    app = ClaudeChat()
    app.run()
