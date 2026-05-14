#!/usr/bin/env python3
"""Hooks del SDK para integración LSP — Closure factories.

Cada factory recibe un LspManager y retorna un hook que lo captura por closure.
Esto permite que cada sesión tenga sus propios hooks vinculados a su propio LspManager.
"""

import os
from collections.abc import Callable, Coroutine
from typing import Any

from termuxcode.connection.lsp.uri import normalize_path
from termuxcode.connection.lsp_manager import LspManager
from termuxcode.connection.lsp_analyzer.symbols import diag_key
from termuxcode.ws_config import logger


def _format_block_reason(error: str, language: str = "Python") -> str:
    """Genera un reason educativo para el bloqueo por syntax error."""
    if language == "Python":
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

    return f"""{language} error detected by language server: {error}

Each Edit must produce valid code. Consider making smaller, incremental edits."""


def _format_diagnostic_error(diag: dict) -> str:
    """Formatea un diagnóstico LSP como texto legible."""
    msg = diag.get("message", "unknown error")
    try:
        rng = diag["range"]["start"]
        line = rng["line"] + 1  # LSP es 0-based
        return f"line {line}: {msg}"
    except (KeyError, TypeError):
        return msg


# ---------------------------------------------------------------------------
# Factory: PreToolUse hooks — se ejecutan ANTES de que la tool corra
# ---------------------------------------------------------------------------

def make_pre_tool_use_hook(lsp_manager: LspManager) -> Callable[..., Coroutine[Any, Any, dict]]:
    """Crea un PreToolUse hook para Write|Edit que captura el LspManager por closure."""
    async def hook(input_data: dict, tool_use_id: str, context: dict) -> dict:
        return {"continue_": True}  # DISABLED: blocking handled externally
        logger.debug(f"PreToolUse hook invocado: tool_name={input_data.get('tool_name')}")
        manager = lsp_manager
        if not manager or not manager._initialized:
            logger.debug(f"PreToolUse hook: LSP no inicializado, passthrough")
            return {"continue_": True}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        file_path = normalize_path(tool_input.get("file_path", ""))

        if not manager.is_supported_file(file_path):
            return {"continue_": True}

        if tool_name == "Write":
            code = tool_input.get("content", "")
            if not code.strip():
                return {"continue_": True}

            # Snapshot de diagnósticos antes
            baseline = manager.get_pre_edit_diagnostics(file_path)

            # Validar código nuevo
            errors = await manager.validate_file(file_path, code)
            if errors:
                # Verificar si estos errores ya existían (baseline)
                # Usar diag_key para comparar por mensaje, no por dict completo
                baseline_keys = {diag_key(e) for e in baseline}
                new_errors = [e for e in errors if diag_key(e) not in baseline_keys]
                if new_errors:
                    error_msgs = "; ".join(_format_diagnostic_error(e) for e in new_errors[:3])
                    logger.info(f"LSP PreToolUse BLOCK: Write on {os.path.basename(file_path)} — {error_msgs}")
                    return {
                        "decision": "block",
                        "reason": _format_block_reason(error_msgs)
                    }

        elif tool_name == "Edit":
            new_string = tool_input.get("new_string", "")
            if not new_string.strip():
                return {"continue_": True}

            # Si el archivo no existe, validar el fragmento
            if not os.path.isfile(file_path):
                return {"continue_": True}

            # Leer archivo actual y simular edición
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    current = f.read()
            except OSError:
                return {"continue_": True}

            old_string = tool_input.get("old_string", "")
            if old_string not in current:
                return {"continue_": True}

            # Snapshot de diagnósticos antes
            baseline = manager.get_pre_edit_diagnostics(file_path)

            result = current.replace(old_string, new_string, 1)

            # Validar archivo resultante
            errors = await manager.validate_file(file_path, result)
            if errors:
                # Comparar con baseline — no bloquear errores preexistentes
                # Usar diag_key para comparar por mensaje, no por dict completo
                baseline_keys = {diag_key(e) for e in baseline}
                new_errors = [e for e in errors if diag_key(e) not in baseline_keys]
                if new_errors:
                    error_msgs = "; ".join(_format_diagnostic_error(e) for e in new_errors[:3])
                    logger.info(f"LSP PreToolUse BLOCK: Edit on {os.path.basename(file_path)} — {error_msgs}")
                    return {
                        "decision": "block",
                        "reason": _format_block_reason(error_msgs)
                    }
                else:
                    logger.info(f"LSP PreToolUse ALLOW (baseline had errors): Edit on {os.path.basename(file_path)}")

        return {"continue_": True}
    return hook


# ---------------------------------------------------------------------------
# Factory: PostToolUse hooks — se ejecutan DESPUÉS de que la tool corrió
# ---------------------------------------------------------------------------

def make_post_tool_use_read_hook(lsp_manager: LspManager) -> Callable[..., Coroutine[Any, Any, dict]]:
    """Crea un PostToolUse hook para Read que captura el LspManager por closure."""
    async def hook(input_data: dict, tool_use_id: str, context: dict) -> dict:
        logger.debug(f"PostToolUse Read hook invocado: tool_name={input_data.get('tool_name')}")
        manager = lsp_manager
        if not manager or not manager._initialized:
            logger.debug(f"PostToolUse Read hook: LSP no inicializado, passthrough")
            return {"continue_": True}

        tool_input = input_data.get("tool_input", {})
        file_path = normalize_path(tool_input.get("file_path", ""))

        if not manager.is_supported_file(file_path):
            logger.debug(f"PostToolUse Read hook: archivo no soportado {file_path}")
            return {"continue_": True}

        context_str = await manager.analyze_file(file_path)
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
    return hook


def make_post_tool_use_edit_hook(lsp_manager: LspManager) -> Callable[..., Coroutine[Any, Any, dict]]:
    """Crea un PostToolUse hook para Write|Edit que captura el LspManager por closure."""
    async def hook(input_data: dict, tool_use_id: str, context: dict) -> dict:
        logger.debug(f"PostToolUse Edit hook invocado: tool_name={input_data.get('tool_name')}")
        manager = lsp_manager
        if not manager or not manager._initialized:
            logger.debug(f"PostToolUse Edit hook: LSP no inicializado, passthrough")
            return {"continue_": True}

        tool_input = input_data.get("tool_input", {})
        file_path = normalize_path(tool_input.get("file_path", ""))

        if not manager.is_supported_file(file_path):
            logger.debug(f"PostToolUse Edit hook: archivo no soportado {file_path}")
            return {"continue_": True}

        if not os.path.isfile(file_path):
            logger.debug(f"PostToolUse Edit hook: archivo no existe {file_path}")
            return {"continue_": True}

        # Obtener diagnósticos nuevos
        client = manager.get_client(file_path)
        if not client:
            return {"continue_": True}

        diags = client.get_cached_diagnostics(file_path)
        if not diags:
            return {"continue_": True}

        # Formatear todos los diagnósticos (errors + warnings)
        warnings = []
        for d in diags[:15]:
            severity = d.get("severity", 3)
            severity_label = {1: "error", 2: "warning", 3: "info", 4: "hint"}.get(severity, "info")
            msg = d.get("message", "")
            try:
                line = d["range"]["start"]["line"] + 1
                warnings.append(f"  L{line}: [{severity_label}] {msg}")
            except (KeyError, TypeError):
                warnings.append(f"  [{severity_label}] {msg}")

        if not warnings:
            return {"continue_": True}

        logger.info(f"LSP PostToolUse Edit: {len(diags)} diagnostics in {os.path.basename(file_path)}")

        return {
            "continue_": True,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"[LSP Diagnostics for {os.path.basename(file_path)}]\n" + "\n".join(warnings)
            }
        }
    return hook
