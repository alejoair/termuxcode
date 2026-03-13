#!/usr/bin/env python3
"""
Script para copiar archivos estáticos de textual_serve al directorio custom de termuxcode.
Ejecuta este script cuando actualices textual_serve o si necesitas recrear los archivos estáticos.
"""

import importlib.resources
import shutil
from pathlib import Path


def copy_static_files():
    """Copiar archivos estáticos de textual_serve al directorio web local."""

    # Obtener el directorio base del proyecto
    project_root = Path(__file__).parent.parent
    web_static_dir = project_root / "src" / "termuxcode" / "web" / "static"
    web_templates_dir = project_root / "src" / "termuxcode" / "web" / "templates"

    # Crear directorios si no existen
    (web_static_dir / "css").mkdir(parents=True, exist_ok=True)
    (web_static_dir / "fonts").mkdir(parents=True, exist_ok=True)
    (web_static_dir / "images").mkdir(parents=True, exist_ok=True)
    (web_static_dir / "js").mkdir(parents=True, exist_ok=True)
    web_templates_dir.mkdir(parents=True, exist_ok=True)

    # Intentar usar importlib.resources (Python 3.9+)
    try:
        import textual_serve

        # Obtener el directorio de textual_serve
        serve_path = Path(textual_serve.__file__).parent
        serve_static = serve_path / "static"
        serve_templates = serve_path / "templates"

        if not serve_static.exists():
            print(f"Error: No se encontró el directorio estático de textual_serve: {serve_static}")
            return False

        if not serve_templates.exists():
            print(f"Error: No se encontró el directorio de templates de textual_serve: {serve_templates}")
            return False

        # Copiar archivos CSS
        print("Copiando archivos CSS...")
        xterm_src = serve_static / "css" / "xterm.css"
        if xterm_src.exists():
            shutil.copy2(xterm_src, web_static_dir / "css" / "xterm.css")
            print(f"  [OK] xterm.css")
        else:
            print(f"  [WARNING] No se encontro: xterm.css")

        # Copiar archivos de fuentes
        print("Copiando archivos de fuentes...")
        fonts_dir = serve_static / "fonts"
        if fonts_dir.exists():
            for font_file in fonts_dir.glob("*.ttf"):
                shutil.copy2(font_file, web_static_dir / "fonts" / font_file.name)
                print(f"  [OK] {font_file.name}")
        else:
            print(f"  [WARNING] No se encontro directorio de fuentes")

        # Copiar imágenes
        print("Copiando imágenes...")
        bg_src = serve_static / "images" / "background.png"
        if bg_src.exists():
            shutil.copy2(bg_src, web_static_dir / "images" / "background.png")
            print(f"  [OK] background.png")
        else:
            print(f"  [WARNING] No se encontro: background.png")

        # Copiar archivos JavaScript
        print("Copiando archivos JavaScript...")
        textual_js_src = serve_static / "js" / "textual.js"
        if textual_js_src.exists():
            shutil.copy2(textual_js_src, web_static_dir / "js" / "textual.js")
            print(f"  [OK] textual.js")
        else:
            print(f"  [WARNING] No se encontro: textual.js")

        print("\n[OK] Archivos estaticos copiados exitosamente")
        print(f"\nDestino: {web_static_dir}")

        return True

    except ImportError:
        print("Error: No se pudo importar textual_serve.")
        print("Asegúrate de que textual_serve esté instalado:")
        print("  pip install textual-serve")
        return False


if __name__ == "__main__":
    copy_static_files()
