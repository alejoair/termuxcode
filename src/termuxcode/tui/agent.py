"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
import os
from typing import TYPE_CHECKING, Callable

from claude_agent_sdk import query, ClaudeAgentOptions

from .history import MessageHistory

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
    ):
        self.chat_log = chat_log
        self.history = history
        self.cwd = cwd or os.getcwd()
        self.session_id = session_id
        self.is_active_session = is_active_session or (lambda: True)

    async def query(self, prompt: str) -> None:
        """Ejecutar query del agente con historial en JSONL"""

        # NOTA: El mensaje del usuario ya se mostró en on_input_submitted
        # No lo duplicamos aquí

        # Cargar historial (ya está truncado a max_messages por save())
        history = self.history.load()

        # Construir prompt con el historial y el nuevo mensaje
        full_prompt = self.history.build_prompt(history, prompt)

        # Usar query() del SDK
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            include_partial_messages=False,
            model="opus",
            setting_sources=["project"],
        )

        old_claudecode = os.environ.pop('CLAUDECODE', None)
        assistant_response = ""

        try:
            async for message in query(prompt=full_prompt, options=options):
                # Solo procesar si la sesión sigue activa
                if self.is_active_session():
                    await self._process_message(message)
                # Acumular la respuesta del asistente
                if hasattr(message, 'content') and isinstance(message.content, list):
                    for block in message.content:
                        if block.__class__.__name__ == "TextBlock":
                            assistant_response += block.text
        finally:
            if old_claudecode:
                os.environ['CLAUDECODE'] = old_claudecode

        # Guardar mensaje del usuario y respuesta del asistente en historial
        # (siempre guardar aunque la sesión ya no esté activa)
        self.history.append("user", prompt)
        if assistant_response:
            self.history.append("assistant", assistant_response)

    async def _process_message(self, message) -> None:
        """Procesar mensaje del agente"""
        msg_type = message.__class__.__name__

        if msg_type == "ResultMessage":
            return
        elif msg_type == "AssistantMessage":
            await self._process_assistant(message)
        elif msg_type == "UserMessage":
            await self._process_user(message)

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
