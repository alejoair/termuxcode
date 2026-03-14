"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
from typing import TYPE_CHECKING, Callable, Optional

from claude_agent_sdk import query, ClaudeAgentOptions

from .history import MessageHistory
from .schemas import STRUCTURED_RESPONSE_SCHEMA

if TYPE_CHECKING:
    from .chat import ChatLog


def _get_metadata(structured: dict | None, key: str, default=None):
    """Obtener un campo de metadata con valor por defecto."""
    if not structured or "metadata" not in structured:
        return default
    return structured["metadata"].get(key, default)


class AgentClient:
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
        self.current_assistant_text = ""

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
            include_partial_messages=False,
            model="opus",
            setting_sources=["project", "user"],
            output_format={
                "type": "json_schema",
                "schema": STRUCTURED_RESPONSE_SCHEMA
            }
        )

        old_claudecode = os.environ.pop('CLAUDECODE', None)
        # El mensaje del usuario ya fue guardado en query_handlers.py
        # Solo acumulamos mensajes del asistente para guardarlos incrementalmente
        assistant_response = ""
        self.current_assistant_text = ""
        self.current_structured_response = None

        # Guardar índice inicial para poder actualizar is_useful después
        initial_count = self.history.count()

        try:
            async for message in query(prompt=full_prompt, options=options):
                # Solo procesar si la sesión sigue activa
                if self.is_active_session():
                    await self._process_message(message)
                # Guardar mensajes incrementalmente al historial
                # Por defecto todos son útiles, se actualizarán si la respuesta estructurada dice lo contrario
                if hasattr(message, 'content') and isinstance(message.content, list):
                    msg_type = message.__class__.__name__
                    for block in message.content:
                        block_type = block.__class__.__name__

                        if block_type == "TextBlock":
                            assistant_response += block.text
                            self.current_assistant_text += block.text

                        elif block_type == "ToolUseBlock":
                            # Guardar el texto acumulado del asistente antes del tool_use
                            if assistant_response:
                                self.history.append_single("assistant", assistant_response, is_useful=True)
                                assistant_response = ""

                            # Guardar tool_use inmediatamente
                            self.history.append_single("tool_use", {
                                "name": block.name,
                                "input": str(block.input) if hasattr(block, 'input') else "",
                            }, is_useful=True)

                        elif block_type == "ToolResultBlock":
                            # Guardar tool_result inmediatamente
                            self.history.append_single("tool_result", str(block.content), is_useful=True)
        finally:
            if old_claudecode:
                os.environ['CLAUDECODE'] = old_claudecode

        # Guardar texto final del asistente si queda algo pendiente
        if assistant_response:
            self.history.append_single("assistant", assistant_response, is_useful=True)

        # Verificar si la respuesta estructurada indica que no es útil
        # Si es así, actualizar todos los mensajes del turno actual
        is_useful_to_record = True
        if self.current_structured_response:
            is_useful_to_record = _get_metadata(self.current_structured_response, "is_useful_to_record_in_history", True)

        if not is_useful_to_record:
            # Marcar todos los mensajes del turno actual como no útiles
            self._mark_turn_as_not_useful(initial_count)

    def _mark_turn_as_not_useful(self, start_index: int) -> None:
        """Marca todos los mensajes desde start_index como no útiles.

        Solo marca los mensajes del asistente, los mensajes del usuario
        siempre se marcan como útiles.

        Args:
            start_index: Índice desde donde empezar a marcar (exclusivo)
        """
        import json

        history = self.history.load()
        if start_index >= len(history):
            return

        # Actualizar is_useful a False solo para los mensajes del asistente del turno actual
        updated = False
        for i in range(start_index, len(history)):
            # Solo marcar mensajes del asistente como no útiles
            if history[i].get("role") == "assistant" and history[i].get("is_useful", True):
                history[i]["is_useful"] = False
                updated = True

        if updated:
            # Guardar el historial actualizado
            self.history.save(history)

    async def _process_message(self, message) -> None:
        """Procesar mensaje del agente"""
        msg_type = message.__class__.__name__

        if msg_type == "ResultMessage":
            await self._process_result(message)
        elif msg_type == "AssistantMessage":
            await self._process_assistant(message)
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
                tag = _get_metadata(structured, "tag", "INFO")
                sys.stderr.write(f"[DEBUG] Got tag: {tag}\n")
                sys.stderr.write(f"[DEBUG] Got metadata keys: {list(structured.get('metadata', {}).keys())}\n")
            sys.stderr.flush()

            # Renderizar el texto acumulado del asistente con el tag del structured output
            if self.current_assistant_text:
                tag = _get_metadata(structured, "tag", "INFO")
                # Debug: imprimir el tag
                sys.stderr.write(f"[DEBUG] Tag from structured output: {tag}\n")
                sys.stderr.flush()
                self.chat_log.write_assistant(self.current_assistant_text, structured_tag=tag)

    async def _process_assistant(self, message) -> None:
        """Procesar AssistantMessage"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                block_type = block.__class__.__name__

                if block_type == "TextBlock":
                    # Guardar texto en memoria, NO renderizar todavía
                    # Se renderizará cuando recibamos el structured_output
                    self.chat_log.write_streaming(block.text)

                elif block_type == "ToolUseBlock":
                    tool_input = str(block.input) if hasattr(block, 'input') else None
                    self.chat_log.write_tool(block.name, tool_input)

    async def _process_user(self, message) -> None:
        """Procesar UserMessage (tool results)"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                if block.__class__.__name__ == "ToolResultBlock":
                    self.chat_log.write_result(str(block.content))
