#!/usr/bin/env python3
"""Hooks del SDK para integración LSP con Jedi."""

import os

from termuxcode.connection.jedi_analyzer import JediAnalyzer
from termuxcode.ws_config import logger


def _format_block_reason(error: str) -> str:
    """Genera un reason educativo para el bloqueo por syntax error.

    Incluye instrucciones del patrón stub-first para que Claude sepa cómo proceder.
    """
    return f"""Python syntax error: {error}

Each Edit must be syntactically valid on its own. Use stub-first pattern:
1. Declare structure with `pass` bodies first
2. Then replace each stub with implementation

Example:
  # Step 1 (valid)
  def process_data(items):
      for item in items:
          pass

  # Step 2 (valid) — replace pass with real code
  def process_data(items):
      for item in items:
          print(item)"""


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

    if tool_name == "Write":
        # Write: content es el archivo completo — validar directamente
        code = tool_input.get("content", "")
        if not code.strip():
            return {"continue_": True}

        ok, error = JediAnalyzer.validate_syntax(code)
        if not ok:
            logger.info(f"LSP PreToolUse BLOCK: {tool_name} on {os.path.basename(file_path)} — {error}")
            return {
                "decision": "block",
                "reason": _format_block_reason(error)
            }

    elif tool_name == "Edit":
        # Edit: new_string es un fragmento — simular la edición y validar archivo resultante
        new_string = tool_input.get("new_string", "")
        if not new_string.strip():
            return {"continue_": True}

        # Si el archivo no existe, solo validar new_string
        if not os.path.isfile(file_path):
            ok, error = JediAnalyzer.validate_syntax(new_string)
            if not ok:
                logger.info(f"LSP PreToolUse BLOCK: {tool_name} (new file) on {os.path.basename(file_path)} — {error}")
                return {
                    "decision": "block",
                    "reason": _format_block_reason(error)
                }
            return {"continue_": True}

        # Leer archivo actual y aplicar reemplazo
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                current = f.read()
        except OSError:
            return {"continue_": True}

        old_string = tool_input.get("old_string", "")
        if old_string not in current:
            # old_string no encontrado — dejar que la tool falle naturalmente
            return {"continue_": True}

        # Baseline check: verificar si el archivo actual tiene errores
        baseline_ok, baseline_error = JediAnalyzer.validate_syntax(current)

        result = current.replace(old_string, new_string, 1)

        # Validar archivo resultante completo
        ok, error = JediAnalyzer.validate_syntax(result)
        if not ok:
            if not baseline_ok:
                # El archivo YA tenía errores — Claude probablemente está arreglando
                # No bloquear, pero loggear para debugging
                logger.info(f"LSP PreToolUse ALLOW (baseline had errors): {tool_name} on {os.path.basename(file_path)} — baseline: {baseline_error}, result: {error}")
                return {"continue_": True}

            # El error es NUEVO — bloquear con reason educativo
            logger.info(f"LSP PreToolUse BLOCK: {tool_name} on {os.path.basename(file_path)} — {error}")
            return {
                "decision": "block",
                "reason": _format_block_reason(error)
            }

    else:
        return {"continue_": True}

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
