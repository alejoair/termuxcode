"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
import os
from typing import TYPE_CHECKING, Callable

from claude_agent_sdk import query, ClaudeAgentOptions
from termuxcode.core.schemas.main_agent_schema import MainAgentResponse
from termuxcode.core.history_manager import MessageHistory


if TYPE_CHECKING:
    from termuxcode.tui.chat import ChatLog

# Tools que detienen el turno al ser detectadas
_STOP_TOOLS = frozenset({"AskUserQuestion", "StructuredOutput"})


def _get_field(structured: dict | None, key: str, default=None):
    """Obtener un campo del structured output con valor por defecto."""
    if not structured:
        return default
    return structured.get(key, default)


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

        # Usar query() del SDK con output_format
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            include_partial_messages=True,
            model="opus",
            setting_sources=["project", "user"],
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
        should_stop = False

        try:
            async for message in query(prompt=full_prompt, options=options):
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

                            # Detectar stop tool (después de guardar)
                            if block.name in _STOP_TOOLS:
                                should_stop = True
                                break

                        elif block_type == "ToolResultBlock":
                            # Guardar tool_result inmediatamente
                            self.history.append_single("tool_result", str(block.content))

                if should_stop:
                    break
        finally:
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
        """Procesar ResultMessage - extraer structured_output"""
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
