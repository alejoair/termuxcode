"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
import asyncio
import json
import os
from typing import TYPE_CHECKING, Callable

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.schemas.main_agent_schema import MainAgentResponse
from termuxcode.core.history_manager import MessageHistory
from termuxcode.core.memory.blackboard import Blackboard


if TYPE_CHECKING:
    from termuxcode.tui.chat import ChatLog

# Tools que detienen el turno al ser detectadas
_STOP_TOOLS = frozenset({"AskUserQuestion", "StructuredOutput"})


def _get_field(structured: dict | None, key: str, default=None):
    """Obtener un campo del structured output con valor por defecto."""
    if not structured:
        return default
    return structured.get(key, default)


def _build_bb_context() -> str:
    """Build a system context string from the Blackboard contents."""
    bb = Blackboard("app")
    data = bb.get("project")
    if not data:
        return ""

    lines = ["<project_context>"]
    _flatten_to_lines(data, lines, prefix="")
    lines.append("</project_context>")
    return "\n".join(lines)


def _flatten_to_lines(data: dict, lines: list, prefix: str) -> None:
    """Recursively flatten a dict into readable lines."""
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_to_lines(value, lines, path)
        elif isinstance(value, list):
            if value and len(value) <= 10:
                items = ", ".join(str(v) for v in value)
                lines.append(f"{path}: {items}")
            elif value:
                lines.append(f"{path}: ({len(value)} items)")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{path}: []")
        else:
            lines.append(f"{path}: {value}")


class MainAgentClient:
    """Cliente para comunicarse con Claude Agent SDK con historial en JSONL"""

    def __init__(
        self,
        chat_log: 'ChatLog',
        history: MessageHistory,
        cwd: str = None,
        session_id: str = None,
        is_active_session: Callable[[], bool] = None,
    ):
        self.chat_log = chat_log
        self.history = history
        self.cwd = cwd or os.getcwd()
        self.session_id = session_id
        self.is_active_session = is_active_session or (lambda: True)

        # Estado de la respuesta estructurada actual
        self.current_structured_response = None

    async def query(self, prompt: str) -> None:
        """Ejecutar query del agente con historial en JSONL"""

        # NOTA: El mensaje del usuario ya se guardó en on_input_submitted
        # No lo duplicamos aquí

        # Cargar historial (ya está truncado a max_messages por save())
        history = self.history.load()

        # Construir prompt con el historial y el nuevo mensaje
        full_prompt = self.history.build_prompt(history, prompt, apply_filters=True)

        # Inyectar contexto del Blackboard al inicio del prompt
        bb_context = _build_bb_context()
        if bb_context:
            full_prompt = bb_context + "\n\n" + full_prompt

        # Usar query() del SDK con output_format y tools restringidas
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            include_partial_messages=True,
            model="opus",
            setting_sources=["project", "user"],
            tools=["Bash", "Edit", "Glob", "Grep", "Read", "Write", "StructuredOutput"],
            output_format={
                "type": "json_schema",
                "schema": MainAgentResponse.model_json_schema()
            },
        )

        old_claudecode = os.environ.pop('CLAUDECODE', None)
        # El mensaje del usuario ya fue guardado en query_handlers.py
        # Solo acumulamos mensajes del asistente para guardarlos incrementalmente
        assistant_response = ""
        self.current_structured_response = None

        # Referencia al generador para limpieza controlada
        query_gen = None

        try:
            # Crear el generador del query
            query_gen = query(prompt=full_prompt, options=options)

            async for message in query_gen:
                # Solo procesar si la sesión sigue activa
                if self.is_active_session():
                    await self._process_message(message, skip_tools=_STOP_TOOLS)
                # Guardar mensajes incrementalmente al historial
                if hasattr(message, 'content') and isinstance(message.content, list):
                    for block in message.content:
                        block_type = block.__class__.__name__

                        if block_type == "TextBlock":
                            assistant_response += block.text

                        elif block_type == "ToolUseBlock":
                            # Guardar el texto acumulado del asistente antes del tool_use
                            if assistant_response:
                                self.history.append_single("assistant", assistant_response)
                                assistant_response = ""

                            # Guardar tool_use inmediatamente
                            self.history.append_single("tool_use", {
                                "name": block.name,
                                "input": str(block.input) if hasattr(block, 'input') else "",
                            })

                            # Nota: Los STOP_TOOLS (AskUserQuestion, StructuredOutput) se detectan
                            # en _process_assistant para mostrar UI, pero NO hacemos break aquí
                            # para permitir que llegue el ResultMessage con el usage.

                        elif block_type == "ToolResultBlock":
                            # Guardar tool_result inmediatamente
                            self.history.append_single("tool_result", str(block.content))

                # No hacer break aquí - esperar ResultMessage para obtener usage
                # El break ocurrirá naturalmente cuando el SDK termine el stream
        except asyncio.CancelledError:
            # Permitir que la cancelación se propague correctamente
            # El SDK limpiará sus recursos en su propio contexto
            raise
        finally:
            # Restaurar la variable de entorno
            if old_claudecode:
                os.environ['CLAUDECODE'] = old_claudecode

        # Guardar texto final del asistente si queda algo pendiente
        if assistant_response:
            self.history.append_single("assistant", assistant_response)

    async def _process_message(self, message, skip_tools=None) -> None:
        """Procesar mensaje del agente"""
        msg_type = message.__class__.__name__

        if msg_type == "ResultMessage":
            await self._process_result(message)
        elif msg_type == "AssistantMessage":
            await self._process_assistant(message, skip_tools=skip_tools)
        elif msg_type == "UserMessage":
            await self._process_user(message)

    async def _process_result(self, message) -> None:
        """Procesar ResultMessage - extraer structured_output y usage"""
        # Debug: ver qué tiene el mensaje
        import sys
        sys.stderr.write(f"[DEBUG] ResultMessage attrs: {dir(message)}\n")
        sys.stderr.write(f"[DEBUG] Has usage: {hasattr(message, 'usage')}\n")
        if hasattr(message, 'usage'):
            sys.stderr.write(f"[DEBUG] usage value: {message.usage}\n")
            sys.stderr.write(f"[DEBUG] usage type: {type(message.usage)}\n")
        sys.stderr.flush()

        # Guardar usage en Blackboard (tokens acumulados por sesión)
        if hasattr(message, 'usage') and message.usage:
            bb = Blackboard("app")
            # Usar clave por sesión para evitar acumulación global
            token_key = f"sessions.{self.session_id}.tokens"
            cost_key = f"sessions.{self.session_id}.cost"
            current = bb.get(token_key) or {"input": 0, "output": 0}
            usage = message.usage
            # Puede ser dict o objeto con atributos
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
            else:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0

            new_tokens = {
                "input": current["input"] + input_tokens,
                "output": current["output"] + output_tokens,
            }
            sys.stderr.write(f"[DEBUG] Saving tokens for session {self.session_id}: {new_tokens}\n")
            sys.stderr.flush()
            await bb.set(token_key, new_tokens)  # await para disparar eventos
            # Costo si está disponible
            if hasattr(message, 'total_cost_usd') and message.total_cost_usd:
                current_cost = bb.get(cost_key) or 0.0
                await bb.set(cost_key, current_cost + message.total_cost_usd)  # await para disparar eventos

        if hasattr(message, 'structured_output'):
            # Debug: imprimir el structured output crudo
            import sys
            import json
            sys.stderr.write(f"[DEBUG] Raw structured_output: {json.dumps(message.structured_output, indent=2)}\n")
            sys.stderr.flush()

            # Usar el dict directamente del SDK
            structured = message.structured_output
            self.current_structured_response = structured

            # Debug: imprimir los campos obtenidos
            if structured:
                tag = _get_field(structured, "tag", "INFO")
                sys.stderr.write(f"[DEBUG] Got tag: {tag}\n")
                sys.stderr.write(f"[DEBUG] Got structured keys: {list(structured.keys())}\n")
            sys.stderr.flush()

    async def _process_assistant(self, message, skip_tools=None) -> None:
        """Procesar AssistantMessage"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                block_type = block.__class__.__name__

                if block_type == "TextBlock":
                    # Mostrar texto directamente con header y Markdown
                    self.chat_log.write_assistant(block.text)

                elif block_type == "ToolUseBlock":
                    if skip_tools and block.name in skip_tools:
                        continue
                    tool_input = str(block.input) if hasattr(block, 'input') else None
                    self.chat_log.write_tool(block.name, tool_input)

    async def _process_user(self, message) -> None:
        """Procesar UserMessage (tool results)"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                if block.__class__.__name__ == "ToolResultBlock":
                    self.chat_log.write_result(str(block.content))
