#!/usr/bin/env python3
"""Hooks del SDK para integración LSP con Jedi."""

import os

from termuxcode.connection.jedi_analyzer import JediAnalyzer
from termuxcode.ws_config import logger


# ---------------------------------------------------------------------------
# PreToolUse hooks — se ejecutan ANTES de que la tool corra
# ---------------------------------------------------------------------------

async def pre_tool_use_lsp_hook(input_data, tool_use_id, context):
    """PreToolUse para Write|Edit: valida sintaxis antes de escribir.

    - Extrae el código de tool_input (content en Write, new_string en Edit)
    - Ejecuta ast.parse() (instantáneo, sin dependencias)
    - Si hay SyntaxError → bloquea la tool y Claude ve el error
    - Si pasa → la tool procede normalmente
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Solo archivos .py
    if not JediAnalyzer.is_python_file(file_path):
        return {"continue_": True}

    # Extraer código a validar
    if tool_name == "Write":
        code = tool_input.get("content", "")
    elif tool_name == "Edit":
        code = tool_input.get("new_string", "")
    else:
        return {"continue_": True}

    # Skip si no hay código (ej: edits vacíos)
    if not code.strip():
        return {"continue_": True}

    # Validar sintaxis
    ok, error = JediAnalyzer.validate_syntax(code)
    if not ok:
        logger.info(f"LSP PreToolUse BLOCK: {tool_name} on {os.path.basename(file_path)} — {error}")
        return {
            "decision": "block",
            "reason": f"Python syntax error: {error}"
        }

    return {"continue_": True}


# ---------------------------------------------------------------------------
# PostToolUse hooks — se ejecutan DESPUÉS de que la tool corrió
# ---------------------------------------------------------------------------

async def post_tool_use_read_hook(input_data, tool_use_id, context):
    """PostToolUse para Read: inyecta contexto semántico con Jedi.

    Cuando Claude lee un archivo .py, este hook:
    - Analiza el archivo con Jedi
    - Extrae símbolos, tipos, signatures, imports
    - Los inyecta como additionalContext para que Claude tenga info semántica
    """
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Solo archivos .py
    if not JediAnalyzer.is_python_file(file_path):
        return {"continue_": True}

    # Generar contexto semántico
    context_str = JediAnalyzer.analyze_file(file_path)
    if not context_str:
        return {"continue_": True}

    logger.info(f"LSP PostToolUse Read: enriched {os.path.basename(file_path)}")

    return {
        "continue_": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context_str
        }
    }


async def post_tool_use_edit_hook(input_data, tool_use_id, context):
    """PostToolUse para Write|Edit: valida el resultado con pyflakes.

    Después de que se escribió/editó un archivo .py:
    - Corre pyflakes para detectar errores lógicos (si está instalado)
    - Inyecta warnings como additionalContext
    - Claude ve los problemas y puede corregirlos en el siguiente turno
    """
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Solo archivos .py
    if not JediAnalyzer.is_python_file(file_path):
        return {"continue_": True}

    # Verificar que el archivo existe (puede haber fallado la escritura)
    if not os.path.isfile(file_path):
        return {"continue_": True}

    # Analizar con pyflakes
    issues = JediAnalyzer.check_file(file_path)
    if not issues:
        return {"continue_": True}

    warnings = "\n".join(
        f"  L{i['line']}: {i['msg']}" for i in issues[:15]  # Limitar a 15 warnings
    )
    logger.info(f"LSP PostToolUse Edit: {len(issues)} issues in {os.path.basename(file_path)}")

    return {
        "continue_": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"[LSP Warnings for {os.path.basename(file_path)}]\n{warnings}"
        }
    }
