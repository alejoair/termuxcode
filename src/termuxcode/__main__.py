"""Punto de entrada principal para python -m termuxcode"""
import sys
from pathlib import Path

# Asegurar que src está en el path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from .tui.app import ClaudeChat

if __name__ == "__main__":
    app = ClaudeChat()
    app.run()
