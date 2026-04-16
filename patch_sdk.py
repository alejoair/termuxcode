#!/usr/bin/env python3
"""Patch script para el bug de claude-agent-sdk MCP server.

Este script parchea query.py para usar model_dump() en lugar de construir
el dict manualmente, arreglando el bug de validación Pydantic.
"""

import os
import shutil

def patch_sdk():
    """Aplica el parche al SDK."""
    # Ruta al archivo a parchear
    file_path = (r"C:\Users\alejandro.cuartas\AppData\Local\Programs\Python"
                 r"\Python312\Lib\site-packages\claude_agent_sdk\_internal\query.py")

    if not os.path.exists(file_path):
        print(f"❌ Archivo no encontrado: {file_path}")
        print("Verifica que claude-agent-sdk esté instalado.")
        return False

    # Hacer backup
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup creado: {backup_path}")

    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar y reemplazar el código buggy
    old_code = '''                    response_data = {"content": content}
                    if hasattr(result.root, "isError") and result.root.isError:
                        response_data["isError"] = True  # type: ignore[assignment]'''

    new_code = '''                    response_data = result.root.model_dump(exclude_none=True)'''

    if old_code in content:
        content = content.replace(old_code, new_code)

        # Escribir el archivo parcheado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ Parche aplicado exitosamente")
        print("📝 Archivo parcheado:", file_path)
        print("🔄 Para deshacer: copia el backup .bak")
        return True
    else:
        print("❌ No se encontró el código a parchear.")
        print("El SDK puede ya estar parcheado o ser una versión diferente.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PATCH: claude-agent-sdk MCP server fix")
    print("=" * 60)

    if patch_sdk():
        print("\n✨ Ahora prueba tu tool custom nuevamente")
    else:
        print("\n❌ Falló el parche - revisa la ruta del archivo")
