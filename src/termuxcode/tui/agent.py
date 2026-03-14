"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
import os
from typing import TYPE_CHECKING, Callable, Optional

from claude_agent_sdk import query, ClaudeAgentOptions

from .history import MessageHistory
from .structured_response import parse_structured_output, STRUCTURED_RESPONSE_SCHEMA

if TYPE_CHECKING:
    from .chat import ChatLog


class AgentClient:
    """Cliente para comunicarse con Claude Agent SDK con historial en JSONL"""

    def __init__(
        self,
        chat_log: 'ChatLog',
        history: MessageHistory,
        cwd: str = None,
        session_id: str = None,
        is_active_session: Callable[[], bool] = None,
        # Callbacks para gamificación
        on_structured_response: Optional[Callable] = None,
        on_tool_used: Optional[Callable] = None,
        # Callback para obtener feedback del agente
        get_agent_feedback: Optional[Callable[[], dict]] = None,
    ):
        self.chat_log = chat_log
        self.history = history
        self.cwd = cwd or os.getcwd()
        self.session_id = session_id
        self.is_active_session = is_active_session or (lambda: True)
        self.on_structured_response = on_structured_response
        self.on_tool_used = on_tool_used
        self.get_agent_feedback = get_agent_feedback

        # Estado de la respuesta estructurada actual
        self.current_structured_response = None
        self.current_assistant_text = ""

    async def query(self, prompt: str) -> None:
        """Ejecutar query del agente con historial en JSONL"""

        # NOTA: El mensaje del usuario ya se mostró en on_input_submitted
        # No lo duplicamos aquí

        # Cargar historial (ya está truncado a max_messages por save())
        history = self.history.load()

        # Obtener feedback para el agente (si está disponible)
        agent_feedback = None
        if self.get_agent_feedback:
            agent_feedback = self.get_agent_feedback()

        # Construir prompt con el historial, feedback y el nuevo mensaje
        full_prompt = self.history.build_prompt_with_feedback(
            history, prompt,
            apply_filters=True,
            agent_feedback=agent_feedback
        )

        # Usar query() del SDK con output_format
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            include_partial_messages=False,
            model="opus",
            setting_sources=["project"],
            output_format={
                "type": "json_schema",
                "schema": STRUCTURED_RESPONSE_SCHEMA
            }
        )

        old_claudecode = os.environ.pop('CLAUDECODE', None)
        # Acumular todos los mensajes del turno para guardar en historial
        turn_messages = [{"role": "user", "content": prompt}]
        assistant_response = ""
        self.current_assistant_text = ""
        self.current_structured_response = None

        try:
            async for message in query(prompt=full_prompt, options=options):
                # Solo procesar si la sesión sigue activa
                if self.is_active_session():
                    await self._process_message(message)
                # Acumular mensajes para el historial
                if hasattr(message, 'content') and isinstance(message.content, list):
                    msg_type = message.__class__.__name__
                    for block in message.content:
                        block_type = block.__class__.__name__

                        if block_type == "TextBlock":
                            assistant_response += block.text
                            self.current_assistant_text += block.text

                        elif block_type == "ToolUseBlock":
                            # Guardar el text acumulado antes del tool_use
                            if assistant_response:
                                turn_messages.append({"role": "assistant", "content": assistant_response})
                                assistant_response = ""
                            turn_messages.append({
                                "role": "tool_use",
                                "content": {
                                    "name": block.name,
                                    "input": str(block.input) if hasattr(block, 'input') else "",
                                }
                            })
                            # Callback de tool used
                            if self.on_tool_used:
                                self.on_tool_used()

                        elif block_type == "ToolResultBlock":
                            turn_messages.append({
                                "role": "tool_result",
                                "content": str(block.content),
                            })
        finally:
            if old_claudecode:
                os.environ['CLAUDECODE'] = old_claudecode

        # Guardar texto final del asistente si queda algo pendiente
        if assistant_response:
            turn_messages.append({"role": "assistant", "content": assistant_response})

        # Determinar si guardar en historial basado en metadata
        should_save = True
        if self.current_structured_response:
            should_save = self.current_structured_response.should_save_to_history

        # Guardar todos los mensajes del turno en historial
        # (siempre guardar aunque la sesión ya no esté activa)
        if should_save:
            self.history.append_batch(turn_messages)
        else:
            # No guardar en historial, pero guardar en un buffer temporal si es necesario
            pass

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
            structured = parse_structured_output(message.structured_output)
            self.current_structured_response = structured

            # Callback de respuesta estructurada para gamificación
            if structured and self.on_structured_response:
                self.on_structured_response(structured)

    async def _process_assistant(self, message) -> None:
        """Procesar AssistantMessage"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                block_type = block.__class__.__name__

                if block_type == "TextBlock":
                    self.chat_log.write_assistant(block.text)

                elif block_type == "ToolUseBlock":
                    tool_input = str(block.input) if hasattr(block, 'input') else None
                    self.chat_log.write_tool(block.name, tool_input)

    async def _process_user(self, message) -> None:
        """Procesar UserMessage (tool results)"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                if block.__class__.__name__ == "ToolResultBlock":
                    self.chat_log.write_result(str(block.content))
